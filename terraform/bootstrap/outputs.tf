output "github_actions_role_arn" {
  value = aws_iam_role.github_actions_deploy.arn
}

output "tfstate_bucket_name" {
  value = aws_s3_bucket.tfstate.id
}