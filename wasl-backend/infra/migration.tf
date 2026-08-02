# =============================================================================
# Wasl — One-off database migration task
# =============================================================================

resource "aws_ecs_task_definition" "migration" {
  family                   = "${var.project}-migration"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.execution.arn

  container_definitions = jsonencode([
    {
      name      = "migration"
      image     = "${aws_ecr_repository.api.repository_url}:latest"
      essential = true

      command = [
        "alembic",
        "upgrade",
        "head"
      ]

      environment = [
        { name = "DB_HOST", value = aws_db_instance.postgres.address },
        { name = "DB_PORT", value = "5432" },
        { name = "DB_NAME", value = "wasl" },
        { name = "DB_SSLMODE", value = "require" },

        { name = "ANTHROPIC_API_KEY", value = var.anthropic_api_key },
        { name = "API_KEY", value = var.api_key }
      ]

      secrets = [
        {
          name      = "DB_USER"
          valueFrom = "${aws_db_instance.postgres.master_user_secret[0].secret_arn}:username::"
        },
        {
          name      = "DB_PASSWORD"
          valueFrom = "${aws_db_instance.postgres.master_user_secret[0].secret_arn}:password::"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"

        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "migration"
        }
      }
    }
  ])

  depends_on = [
    aws_iam_role_policy.execution_rds_secret,
    aws_iam_role_policy.execution_app_secret
  ]
}