# Wasl — AWS Deploy Runbook

All commands run from the `wasl-backend/infra/` folder unless noted.
Deploy, screenshot, then DESTROY to protect your budget.

## 0. One-time: secrets file
Copy the example and fill in real values:
    copy terraform.tfvars.example terraform.tfvars
Edit terraform.tfvars:
    anthropic_api_key = "sk-ant-..."
    api_key           = "your-app-api-key"
(terraform.tfvars is gitignored — never commit it.)

## 1. Initialize Terraform
    terraform init

## 2. Create ECR + everything else
    terraform apply
Type "yes". This creates the ECR repo, ALB, ECS, etc.
When done, note the two outputs: ecr_repository_url and alb_url.

## 3. Build & push the Docker image to ECR
From wasl-backend/ (the folder with the Dockerfile):

    # authenticate docker to ECR (replace REGION + ACCOUNT + REPO from the output)
    aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

    # build and tag
    docker build -t wasl-api .
    docker tag wasl-api:latest <ECR_REPOSITORY_URL>:latest

    # push
    docker push <ECR_REPOSITORY_URL>:latest

## 4. Restart the service to pull the new image
    aws ecs update-service --cluster wasl-cluster --service wasl-service --force-new-deployment --region us-east-1

Wait ~2-3 min for the task to start and pass health checks.

## 5. Open the app
Open the alb_url from the terraform output in your browser:
    http://<alb_url>/health      -> should return status ok
    http://<alb_url>/docs        -> API docs
The frontend (if you deploy it separately) points at this URL.

Note: the container's knowledge base starts empty. To ingest into the
running task, easiest is to bake an ingest step or run it locally against
the same store. For a quick demo, the /health will show 0 chunks — you can
mention ingest runs on startup in a fuller deploy.

## 6. SCREENSHOT the live URL (this is the portfolio proof)

## 7. DESTROY everything (stop charges)
    terraform destroy
Type "yes". Confirms all resources are removed. Verify in the AWS console
that ECS, ALB, and ECR are gone.
