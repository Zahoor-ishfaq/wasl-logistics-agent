############################################
# Frontend (React + Vite)
# Private S3 + CloudFront
############################################

resource "aws_s3_bucket" "frontend" {
  bucket = var.frontend_bucket_name

  tags = {
    Project = var.project
    Name    = "${var.project}-frontend"
  }
}

resource "aws_s3_bucket_ownership_controls" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

############################################
# CloudFront Origin Access Control
############################################

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "${var.project}-oac"
  description                       = "OAC for Wasl frontend bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

############################################
# React SPA route rewrite
#
# Examples:
# /login                  -> /index.html
# /investigations/123     -> /index.html
# /assets/index-abc.js    -> unchanged
#
# This function is attached only to the S3
# frontend behavior. It cannot rewrite API
# responses or API errors.
############################################

resource "aws_cloudfront_function" "spa_rewrite" {
  name    = "${var.project}-spa-rewrite"
  runtime = "cloudfront-js-2.0"
  comment = "Rewrite React SPA routes to index.html"
  publish = true

  code = <<-EOT
    function handler(event) {
      var request = event.request;
      var uri = request.uri;

      var lastSlash = uri.lastIndexOf("/");
      var lastSegment = uri.substring(lastSlash + 1);

      if (uri.charAt(uri.length - 1) === "/" || lastSegment.indexOf(".") === -1) {
        request.uri = "/index.html";
      }

      return request;
    }
  EOT
}

############################################
# CloudFront Distribution
############################################

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "Wasl frontend and API distribution"

  ##########################################
  # Origin 1: Private S3 frontend
  ##########################################

  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
    origin_id                = "frontend-s3"
  }

  ##########################################
  # Origin 2: FastAPI backend through ALB
  ##########################################

  origin {
    domain_name = aws_lb.api.dns_name
    origin_id   = "backend-alb"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]

      # Useful for AI requests that may take longer
      origin_keepalive_timeout = 5
      origin_read_timeout      = 60
    }
  }

  ##########################################
  # Exact /api request
  ##########################################

  ordered_cache_behavior {
    path_pattern     = "/api"
    target_origin_id = "backend-alb"

    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = [
      "GET",
      "HEAD",
      "OPTIONS",
      "POST",
      "PUT",
      "PATCH",
      "DELETE"
    ]

    cached_methods = [
      "GET",
      "HEAD",
      "OPTIONS"
    ]

    compress = true

    # AWS managed CachingDisabled policy
    cache_policy_id = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"

    # Forwards all headers, cookies and query strings,
    # except the CloudFront Host header.
    # Authorization and X-API-Key are forwarded.
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
  }

  ##########################################
  # All /api/* backend requests
  ##########################################

  ordered_cache_behavior {
    path_pattern     = "/api/*"
    target_origin_id = "backend-alb"

    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = [
      "GET",
      "HEAD",
      "OPTIONS",
      "POST",
      "PUT",
      "PATCH",
      "DELETE"
    ]

    cached_methods = [
      "GET",
      "HEAD",
      "OPTIONS"
    ]

    compress = true

    # AWS managed CachingDisabled policy
    cache_policy_id = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"

    # Forwards Authorization, X-API-Key, cookies,
    # query strings and other viewer values.
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
  }

  ##########################################
  # Default frontend behavior
  ##########################################

  default_cache_behavior {
    target_origin_id       = "frontend-s3"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = [
      "GET",
      "HEAD",
      "OPTIONS"
    ]

    cached_methods = [
      "GET",
      "HEAD"
    ]

    compress = true

    # AWS managed CachingOptimized policy
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6"

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa_rewrite.arn
    }
  }

  ##########################################
  # Restrictions and certificate
  ##########################################

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  tags = {
    Project = var.project
    Name    = "${var.project}-cloudfront"
  }
}

############################################
# Allow CloudFront to read S3
############################################

data "aws_iam_policy_document" "frontend_bucket_policy" {
  statement {
    sid = "AllowCloudFrontReadOnly"

    actions = [
      "s3:GetObject"
    ]

    resources = [
      "${aws_s3_bucket.frontend.arn}/*"
    ]

    principals {
      type = "Service"

      identifiers = [
        "cloudfront.amazonaws.com"
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"

      values = [
        aws_cloudfront_distribution.frontend.arn
      ]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = data.aws_iam_policy_document.frontend_bucket_policy.json
}