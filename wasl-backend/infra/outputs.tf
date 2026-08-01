output "alb_url" {
  description = "Public URL of the deployed API."
  value       = "http://${aws_lb.api.dns_name}"
}

output "ecr_repository_url" {
  description = "Push the Docker image here."
  value       = aws_ecr_repository.api.repository_url
}
output "frontend_url" {
  description = "CloudFront URL"

  value = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "frontend_bucket" {
  value = aws_s3_bucket.frontend.bucket
}
output "rds_endpoint" {
  description = "PostgreSQL RDS endpoint"
  value       = aws_db_instance.postgres.address
}

output "rds_secret_arn" {
  description = "AWS Secrets Manager ARN containing RDS credentials"
  value       = aws_db_instance.postgres.master_user_secret[0].secret_arn
}