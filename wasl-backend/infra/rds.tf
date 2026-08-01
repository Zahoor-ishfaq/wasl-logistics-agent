# =============================================================================
# Wasl — PostgreSQL RDS
#
# Private PostgreSQL database for the Wasl backend.
# Password is generated and managed automatically by AWS Secrets Manager.
# =============================================================================


# --- RDS subnet group --------------------------------------------------------

resource "aws_db_subnet_group" "postgres" {
  name       = "${var.project}-postgres-subnets"
  subnet_ids = data.aws_subnets.default.ids

  tags = {
    Name    = "${var.project}-postgres-subnets"
    Project = var.project
  }
}


# --- RDS security group ------------------------------------------------------
# PostgreSQL can ONLY be reached by the ECS service security group.

resource "aws_security_group" "database" {
  name        = "${var.project}-postgres-sg"
  description = "Allow PostgreSQL access from Wasl ECS tasks only"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "PostgreSQL from ECS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.service.id]
  }

  tags = {
    Name    = "${var.project}-postgres-sg"
    Project = var.project
  }
}


# --- PostgreSQL RDS ----------------------------------------------------------

resource "aws_db_instance" "postgres" {
  identifier = "${var.project}-postgres"

  engine         = "postgres"
  instance_class = "db.t4g.micro"

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "wasl"
  username = "wasl_admin"
  port     = 5432

  # AWS generates the DB password and stores it in Secrets Manager.
  # No database password is stored in terraform.tfvars.
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.database.id]

  publicly_accessible = false
  multi_az            = false

  backup_retention_period = 1

  auto_minor_version_upgrade = true

  # Demo-friendly settings so Terraform can destroy the environment later.
  deletion_protection = false
  skip_final_snapshot = true

  copy_tags_to_snapshot = true

  tags = {
    Name        = "${var.project}-postgres"
    Project     = var.project
    Environment = "production"
  }
}