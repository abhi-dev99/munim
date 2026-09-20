# Frontend on AWS App Runner

The Next.js frontend (`frontend/`) deployed to AWS App Runner -- this
submission's live frontend hosting.

**Live URL**: `https://eym73fepx3.ap-south-1.awsapprunner.com`

## What this is, and isn't

This deploys the *same* Docker image the project's own `frontend/Dockerfile`
already builds -- same `NEXT_PUBLIC_API_URL` default
(`https://munim-backend-1051889700424.us-central1.run.app`, the existing
Cloud Run backend), same build process, nothing rewritten. It is **not**
wired to this AWS pipeline's own API Gateway -- that endpoint only has an
invoice-upload route and WhatsApp webhooks today, none of the
dashboard/trader read APIs this frontend actually calls. Pointing it at
the AWS backend instead would just be a broken UI with every request
404ing. This deploys real, working AWS-native *hosting infrastructure*
for the existing frontend, not a rewritten integration.

## Infra

- ECR repository: `munim-frontend` (`753654068031.dkr.ecr.ap-south-1.amazonaws.com/munim-frontend`)
- App Runner service: `munim-frontend`, 1 vCPU / 2 GB, manual deploys
  (`AutoDeploymentsEnabled: false` -- push a new image to ECR and call
  `start-deployment` to update; not wired to CI/CD)
- IAM role `munim-apprunner-ecr-access`: lets App Runner pull from ECR,
  nothing else (AWS managed `AWSAppRunnerServicePolicyForECRAccess`)

## The one real bug hit building this

The Docker image's own `ENV HOSTNAME="0.0.0.0"` / `ENV PORT=3000`
(needed for Next.js's standalone server to bind to all interfaces, not
just localhost) did **not** take effect under App Runner -- the
container started fine internally ("Ready in 0ms", confirmed via the
application logs), but App Runner's own TCP health check on port 3000
consistently failed to reach it, and the deployment failed with
`CREATE_FAILED`. Fixed by setting the *same* values again, explicitly,
via App Runner's own `RuntimeEnvironmentVariables` config -- App Runner's
env var injection appears to take precedence over (or otherwise not
honor) `ENV` values baked into the image itself for this specific
binding. Worth knowing if this image is ever redeployed from a fresh
service definition: the image's own `ENV HOSTNAME`/`PORT` alone isn't
enough on App Runner specifically, even though it's sufficient on Cloud
Run.

## Updating

```
docker build --platform linux/amd64 -t munim-frontend:latest ./frontend
docker tag munim-frontend:latest 753654068031.dkr.ecr.ap-south-1.amazonaws.com/munim-frontend:latest
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 753654068031.dkr.ecr.ap-south-1.amazonaws.com
docker push 753654068031.dkr.ecr.ap-south-1.amazonaws.com/munim-frontend:latest
aws apprunner start-deployment --service-arn arn:aws:apprunner:ap-south-1:753654068031:service/munim-frontend/0a09c0e2e3aa4cdd934feeac86a98636 --region ap-south-1
```
