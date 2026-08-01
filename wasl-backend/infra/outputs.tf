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