# Run from: wasl-backend
# Assumes AWS CLI and Docker are already authenticated/configured.

$ErrorActionPreference = "Stop"

$Ecr = "338658064114.dkr.ecr.us-east-1.amazonaws.com/wasl-api"
$Cluster = "wasl-cluster"
$Service = "wasl-service"
$MigrationTask = "wasl-migration"

Write-Host "1/6 Validating Python..."
python -m pytest -q
python -m ruff check .

Write-Host "2/6 Building API image..."
docker build -t wasl-api:latest .
docker tag wasl-api:latest "${Ecr}:latest"

Write-Host "3/6 Pushing API image..."
docker push "${Ecr}:latest"

Write-Host "4/6 Running Alembic migration on RDS..."
$svc = aws ecs describe-services `
    --cluster $Cluster `
    --services $Service | ConvertFrom-Json

$networkJson = $svc.services[0].networkConfiguration |
    ConvertTo-Json -Depth 6 -Compress

$run = aws ecs run-task `
    --cluster $Cluster `
    --launch-type FARGATE `
    --task-definition $MigrationTask `
    --network-configuration $networkJson | ConvertFrom-Json

if (-not $run.tasks -or $run.tasks.Count -eq 0) {
    throw "Migration task did not start."
}

$taskArn = $run.tasks[0].taskArn
aws ecs wait tasks-stopped --cluster $Cluster --tasks $taskArn

$exitCode = aws ecs describe-tasks `
    --cluster $Cluster `
    --tasks $taskArn `
    --query "tasks[0].containers[0].exitCode" `
    --output text

if ($exitCode -ne "0") {
    throw "Migration failed with exit code $exitCode. Check CloudWatch logs."
}

Write-Host "5/6 Deploying new API task..."
aws ecs update-service `
    --cluster $Cluster `
    --service $Service `
    --force-new-deployment | Out-Null

aws ecs wait services-stable `
    --cluster $Cluster `
    --services $Service

Write-Host "6/6 Final health check..."
Invoke-RestMethod `
    -Uri "http://wasl-alb-366721066.us-east-1.elb.amazonaws.com/api/health"

Write-Host ""
Write-Host "DONE: production now uses RDS PostgreSQL + pgvector."