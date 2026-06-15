# AEKA Infrastructure — AWS Deployment
# ECS Fargate + RDS PostgreSQL + ElastiCache Redis + S3 + CloudFront

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "aeka-terraform-state"
    key    = "infrastructure/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "aeka"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ─── Variables ──────────────────────────────────────────────────────────────

variable "aws_region" {
  default = "us-east-1"
}

variable "environment" {
  default = "staging"
}

variable "app_name" {
  default = "aeka"
}

# ─── VPC & Networking ───────────────────────────────────────────────────────

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = "${var.app_name}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = var.environment != "production"
}

# ─── ECS Cluster ────────────────────────────────────────────────────────────

resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ─── Backend Service ────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.app_name}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "backend"
      image = "${aws_ecr_repository.backend.repository_url}:latest"
      portMappings = [{ containerPort = 8000, protocol = "tcp" }]
      environment = [
        { name = "APP_ENV", value = var.environment },
        { name = "POSTGRES_HOST", value = aws_db_instance.main.address },
        { name = "REDIS_HOST", value = aws_elasticache_cluster.main.cache_nodes[0].address },
      ]
      secrets = [
        { name = "OPENAI_API_KEY", valueFrom = "${aws_secretsmanager_secret.api_keys.arn}:OPENAI_API_KEY::" },
        { name = "ANTHROPIC_API_KEY", valueFrom = "${aws_secretsmanager_secret.api_keys.arn}:ANTHROPIC_API_KEY::" },
        { name = "POSTGRES_PASSWORD", valueFrom = "${aws_secretsmanager_secret.db_password.arn}" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.app_name}-backend"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_service" "backend" {
  name            = "${var.app_name}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.environment == "production" ? 3 : 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = module.vpc.private_subnets
    security_groups = [aws_security_group.backend.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }
}

# ─── RDS PostgreSQL (with pgvector) ─────────────────────────────────────────

resource "aws_db_instance" "main" {
  identifier           = "${var.app_name}-db-${var.environment}"
  engine               = "postgres"
  engine_version       = "16.3"
  instance_class       = var.environment == "production" ? "db.r6g.large" : "db.t4g.micro"
  allocated_storage    = 20
  max_allocated_storage = 100
  db_name              = "aeka"
  username             = "aeka"
  password             = random_password.db.result

  vpc_security_group_ids = [aws_security_group.database.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 7
  deletion_protection     = var.environment == "production"
  skip_final_snapshot     = var.environment != "production"

  # pgvector is available in RDS PostgreSQL 16+
  parameter_group_name = aws_db_parameter_group.pgvector.name
}

resource "aws_db_parameter_group" "pgvector" {
  name   = "${var.app_name}-pgvector"
  family = "postgres16"

  parameter {
    name  = "shared_preload_libraries"
    value = "vector"
  }
}

# ─── ElastiCache Redis ──────────────────────────────────────────────────────

resource "aws_elasticache_cluster" "main" {
  cluster_id           = "${var.app_name}-redis-${var.environment}"
  engine               = "redis"
  node_type            = var.environment == "production" ? "cache.r6g.large" : "cache.t4g.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  security_group_ids   = [aws_security_group.redis.id]
  subnet_group_name    = aws_elasticache_subnet_group.main.name
}

# ─── S3 for Document Storage ────────────────────────────────────────────────

resource "aws_s3_bucket" "documents" {
  bucket = "${var.app_name}-documents-${var.environment}"
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ─── CloudFront CDN (Frontend) ──────────────────────────────────────────────

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  default_root_object = "index.html"

  origin {
    domain_name = aws_lb.frontend.dns_name
    origin_id   = "frontend-alb"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "frontend-alb"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

# ─── Secrets & Passwords ────────────────────────────────────────────────────

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "${var.app_name}/db-password/${var.environment}"
}

resource "aws_secretsmanager_secret" "api_keys" {
  name = "${var.app_name}/api-keys/${var.environment}"
}

# ─── ECR Repositories ──────────────────────────────────────────────────────

resource "aws_ecr_repository" "backend" {
  name                 = "${var.app_name}/backend"
  image_tag_mutability = "MUTABLE"
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${var.app_name}/frontend"
  image_tag_mutability = "MUTABLE"
}

# ─── IAM Roles (stubs — expand per least-privilege) ─────────────────────────

resource "aws_iam_role" "ecs_execution" {
  name = "${var.app_name}-ecs-execution-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" } }]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "${var.app_name}-ecs-task-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" } }]
  })
}

# ─── Outputs ────────────────────────────────────────────────────────────────

output "backend_url" {
  value = "http://${aws_lb.frontend.dns_name}:8000"
}

output "frontend_url" {
  value = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "rds_endpoint" {
  value = aws_db_instance.main.endpoint
}
