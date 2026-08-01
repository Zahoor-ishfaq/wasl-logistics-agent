variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name prefix for resources."
  type        = string
  default     = "wasl"
}

variable "anthropic_api_key" {
  description = "Anthropic API key (passed into the container). Provide via TF_VAR or terraform.tfvars."
  type        = string
  sensitive   = true
}

variable "api_key" {
  description = "The app API key clients must send in X-API-Key."
  type        = string
  sensitive   = true
}
variable "frontend_bucket_name" {
  description = "Unique S3 bucket name for the frontend."
  type        = string
}