terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 5.0" }
    archive = { source = "hashicorp/archive", version = "~> 2.4" }
  }
}

data "aws_caller_identity" "current" {}

# --- Raw data S3 bucket ---

resource "aws_s3_bucket" "raw" {
  bucket        = "${var.project_prefix}-raw-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "raw" {
  bucket = aws_s3_bucket.raw.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "raw" {
  bucket                  = aws_s3_bucket.raw.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- Default VPC networking (same eu-west-2d exclusion as the streaming project) ---

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_subnet" "default" {
  for_each = toset(data.aws_subnets.default.ids)
  id       = each.value
}

locals {
  redshift_subnet_ids = [
    for s in data.aws_subnet.default : s.id
    if s.availability_zone != "eu-west-2d"
  ]
}

# --- IAM role Redshift assumes to read from S3 during COPY ---

data "aws_iam_policy_document" "redshift_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["redshift.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "redshift_s3_read" {
  name               = "${var.project_prefix}-redshift-s3-read"
  assume_role_policy = data.aws_iam_policy_document.redshift_assume_role.json
}

data "aws_iam_policy_document" "redshift_s3_read_permissions" {
  statement {
    sid       = "ReadRawBucket"
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.raw.arn, "${aws_s3_bucket.raw.arn}/*"]
  }
}

resource "aws_iam_role_policy" "redshift_s3_read_permissions" {
  name   = "${var.project_prefix}-redshift-s3-read-permissions"
  role   = aws_iam_role.redshift_s3_read.id
  policy = data.aws_iam_policy_document.redshift_s3_read_permissions.json
}

# --- Redshift Serverless ---

resource "aws_redshiftserverless_namespace" "this" {
  namespace_name        = "${var.project_prefix}-namespace"
  db_name                = var.database_name
  manage_admin_password  = true
  iam_roles              = [aws_iam_role.redshift_s3_read.arn]
  default_iam_role_arn   = aws_iam_role.redshift_s3_read.arn
}

resource "aws_redshiftserverless_workgroup" "this" {
  namespace_name       = aws_redshiftserverless_namespace.this.namespace_name
  workgroup_name        = "${var.project_prefix}-workgroup"
  base_capacity         = 8
  subnet_ids            = local.redshift_subnet_ids
  publicly_accessible   = false
}

# --- Lambda: load_sales_data ---

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_execution" {
  name               = "${var.project_prefix}-lambda-execution"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "lambda_permissions" {
  statement {
    sid = "WriteLogs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "arn:aws:logs:eu-west-2:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_prefix}-*:*",
    ]
  }

  statement {
    sid = "UseRedshiftDataAPI"
    actions = [
      "redshift-data:ExecuteStatement",
      "redshift-data:DescribeStatement",
      "redshift-data:GetStatementResult",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "GetRedshiftServerlessCredentials"
    actions   = ["redshift-serverless:GetCredentials"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda_permissions" {
  name   = "${var.project_prefix}-lambda-permissions"
  role   = aws_iam_role.lambda_execution.id
  policy = data.aws_iam_policy_document.lambda_permissions.json
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../../../src/load_sales_data.py"
  output_path = "${path.module}/../../../build/load_sales_data.zip"
}

resource "aws_lambda_function" "load_sales_data" {
  function_name    = "${var.project_prefix}-load-sales-data"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "load_sales_data.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 60

  environment {
    variables = {
      REDSHIFT_WORKGROUP   = aws_redshiftserverless_workgroup.this.workgroup_name
      REDSHIFT_DATABASE    = var.database_name
      REDSHIFT_S3_ROLE_ARN = aws_iam_role.redshift_s3_read.arn
    }
  }
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.load_sales_data.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.raw.arn
}

resource "aws_s3_bucket_notification" "raw_trigger" {
  bucket = aws_s3_bucket.raw.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.load_sales_data.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".csv"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}