output "raw_bucket_name" {
  value = aws_s3_bucket.raw.id
}

output "workgroup_name" {
  value = aws_redshiftserverless_workgroup.this.workgroup_name
}

output "database_name" {
  value = var.database_name
}

output "redshift_s3_role_arn" {
  value = aws_iam_role.redshift_s3_read.arn
}