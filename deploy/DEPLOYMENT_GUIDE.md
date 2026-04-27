# Step-by-Step AWS Deployment Guide

Deploy the Travel Concierge stack to AWS — three services, fully managed.

```
Browser
  │  wss://
  ▼
CloudFront ──► S3              React UI  (static)
                │
                │  wss://
                ▼
          ALB (port 443)
                │
                ▼
        ECS Fargate            Agent WebSocket API  (:8100)
          agent-service          └─ spawns MCP server subprocess
                │
                │  http://
                ▼
        ECS Fargate            Travel Data API  (:9000)
          travel-api
```

**Time estimate:** ~60 minutes for a first deployment.

---

## Prerequisites

- [ ] AWS account with admin access
- [ ] AWS CLI v2 installed and configured (`aws configure`)
- [ ] Docker Desktop running
- [ ] All three images build locally without errors:
  ```bash
  docker build -t travel-api ./travel-api
  docker build -f agent/Dockerfile -t agent-service .
  docker build -t travel-ui ./ui
  ```

---

## Step 1 — Create ECR Repositories

ECR (Elastic Container Registry) is AWS's private Docker image registry.
You push your images here so ECS can pull them when launching containers.

### Console
1. Open **ECR** → **Repositories** → **Create repository**
2. Create three repositories (repeat for each):

   | Repository name | Visibility |
   |---|---|
   | `travel-api` | Private |
   | `agent-service` | Private |
   | `travel-ui` | Private |

3. Leave all other settings as defaults → **Create**

### CLI (alternative)
```bash
aws ecr create-repository --repository-name travel-api     --region us-east-1
aws ecr create-repository --repository-name agent-service  --region us-east-1
aws ecr create-repository --repository-name travel-ui      --region us-east-1
```

> Note your **Account ID** — visible in the top-right of the AWS console.
> You will need it as `ACCOUNT_ID` in the commands below.

---

## Step 2 — Build and Push Images to ECR

```bash
ACCOUNT_ID=123456789012    # replace with your account ID
REGION=us-east-1
ECR=${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# Authenticate Docker to ECR
aws ecr get-login-password --region $REGION \
  | docker login --username AWS --password-stdin $ECR

# travel-api
docker build -t travel-api ./travel-api
docker tag  travel-api:latest ${ECR}/travel-api:latest
docker push ${ECR}/travel-api:latest

# agent-service  (build context = repo root)
docker build -f agent/Dockerfile -t agent-service .
docker tag  agent-service:latest ${ECR}/agent-service:latest
docker push ${ECR}/agent-service:latest

# travel-ui  (WS URL updated in Step 8 after ALB is created)
docker build -t travel-ui ./ui
docker tag  travel-ui:latest ${ECR}/travel-ui:latest
docker push ${ECR}/travel-ui:latest
```

Verify in **ECR → Repositories** — each repo should show a `latest` tag.

---

## Step 3 — Create IAM Roles

Two roles are needed:

| Role | Purpose |
|---|---|
| `ecsTaskExecutionRole` | Allows ECS to pull ECR images and write CloudWatch logs |
| `agentTaskRole` | Allows the agent container to call Bedrock and read Secrets Manager |

### 3a — ecsTaskExecutionRole

> This role may already exist if you have used ECS before. Check
> **IAM → Roles** and search for `ecsTaskExecutionRole` before creating.

1. **IAM → Roles → Create role**
2. **Trusted entity:** AWS service → **Elastic Container Service Task**
3. **Permissions:** attach `AmazonECSTaskExecutionRolePolicy` (AWS managed)
4. **Role name:** `ecsTaskExecutionRole` → **Create**

### 3b — agentTaskRole

1. **IAM → Roles → Create role**
2. **Trusted entity:** AWS service → **Elastic Container Service Task**
3. **Permissions:** skip for now (attach inline policy next)
4. **Role name:** `agentTaskRole` → **Create**
5. Open `agentTaskRole` → **Add permissions → Create inline policy**
6. Switch to **JSON** tab, paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-micro-v1:0",
        "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0"
      ]
    },
    {
      "Sid": "BedrockRAG",
      "Effect": "Allow",
      "Action": [
        "bedrock-agent-runtime:RetrieveAndGenerate",
        "bedrock-agent-runtime:Retrieve"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SecretsManager",
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:travel-concierge/*"
    }
  ]
}
```

7. **Policy name:** `AgentTaskPolicy` → **Create**

---

## Step 4 — Store Secrets in Secrets Manager

Never bake credentials into Docker images.
ECS pulls secrets from Secrets Manager at container start and injects
them as environment variables.

### Console — create one secret per value

1. **Secrets Manager → Store a new secret**
2. **Secret type:** Other type of secret
3. For each credential, create a **separate secret**:

   | Secret name | Value |
   |---|---|
   | `travel-concierge/AWS_ACCESS_KEY_ID` | your access key |
   | `travel-concierge/AWS_SECRET_ACCESS_KEY` | your secret key |
   | `travel-concierge/BEDROCK_KB_ID` | your knowledge base ID (or leave empty) |

4. **Encryption key:** `aws/secretsmanager` (default) → **Next**
5. **Rotation:** disable → **Next → Store**

> Note the full **ARN** of each secret — you need them for the task definition.

### CLI (alternative)
```bash
aws secretsmanager create-secret \
  --name travel-concierge/AWS_ACCESS_KEY_ID \
  --secret-string "AKIAIOSFODNN7EXAMPLE"

aws secretsmanager create-secret \
  --name travel-concierge/AWS_SECRET_ACCESS_KEY \
  --secret-string "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

---

## Step 5 — Create CloudWatch Log Groups

ECS writes container stdout/stderr to CloudWatch Logs.
Log groups must exist before the task starts.

```bash
aws logs create-log-group --log-group-name /ecs/travel-api    --region us-east-1
aws logs create-log-group --log-group-name /ecs/agent-service --region us-east-1
```

Or in **CloudWatch → Log groups → Create log group**.

---

## Step 6 — Create the ECS Cluster

The cluster is the logical boundary for your Fargate services.

### Console
1. **ECS → Clusters → Create cluster**
2. **Cluster name:** `travel-concierge`
3. **Infrastructure:** AWS Fargate (serverless) ✓
4. Leave everything else as default → **Create**

### CLI
```bash
aws ecs create-cluster --cluster-name travel-concierge
```

---

## Step 7 — Deploy Travel API

### 7a — Register the task definition

1. **ECS → Task definitions → Create new task definition → Create new revision with JSON**
2. Paste the content of `deploy/task-def-travel-api.json`
3. Replace `REPLACE_WITH_ACCOUNT_ID` with your account ID → **Create**

Or via CLI:
```bash
# Edit deploy/task-def-travel-api.json first — replace ACCOUNT_ID
aws ecs register-task-definition \
  --cli-input-json file://deploy/task-def-travel-api.json
```

### 7b — Create the service

1. **ECS → Clusters → travel-concierge → Services → Create**
2. Settings:

   | Field | Value |
   |---|---|
   | Launch type | FARGATE |
   | Task definition | `travel-api` (latest) |
   | Service name | `travel-api` |
   | Desired tasks | `1` |

3. **Networking:**
   - VPC: default VPC
   - Subnets: select all available
   - Security group: create new → allow inbound TCP **9000** from the agent security group (add that rule after agent SG is created)
   - Public IP: **OFF** (travel-api is internal only — the agent calls it)

4. **Load balancer:** None (internal service)
5. → **Create**

### 7c — Note the private IP

Once the task is **RUNNING**:
- **ECS → Clusters → travel-concierge → Services → travel-api → Tasks**
- Click the task → note the **Private IP** (e.g. `10.0.1.45`)

You will use this as `TRAVEL_API_URL=http://10.0.1.45:9000` in the agent task definition.

> **Better option for production:** use AWS Cloud Map (service discovery) so
> the agent can reach travel-api by DNS name (`http://travel-api.local:9000`)
> instead of a hardcoded IP. For the course, the private IP is simpler.

---

## Step 8 — Deploy Agent API

### 8a — Create an Application Load Balancer

The agent uses WebSocket (`ws://`). You need an ALB to expose it publicly
with a stable DNS name. The ALB also handles SSL termination (HTTPS/WSS).

1. **EC2 → Load Balancers → Create load balancer → Application Load Balancer**
2. Settings:

   | Field | Value |
   |---|---|
   | Name | `agent-alb` |
   | Scheme | Internet-facing |
   | IP address type | IPv4 |
   | VPC | default VPC |
   | Subnets | select all AZs |

3. **Security group:** create new → allow inbound **HTTP 80** and **HTTPS 443** from `0.0.0.0/0`

4. **Listeners:**
   - HTTP:80 — add (used for testing; redirect to HTTPS in production)

5. **Target group** (create new):

   | Field | Value |
   |---|---|
   | Target type | IP addresses |
   | Name | `agent-tg` |
   | Protocol | HTTP |
   | Port | 8100 |
   | Health check path | `/` |

6. → **Create load balancer**

> **WebSocket note:** ALB supports WebSocket automatically — no extra config
> needed. Any HTTP/1.1 connection with an `Upgrade: websocket` header is
> passed through transparently.

### 8b — Register the task definition

Edit `deploy/task-def-agent.json`:
- Replace `REPLACE_WITH_ACCOUNT_ID` with your account ID
- Replace `REPLACE_WITH_TRAVEL_API_ALB_DNS` with the travel-api **Private IP** from Step 7c
- Replace the secret ARNs with the ARNs from Step 4

```bash
aws ecs register-task-definition \
  --cli-input-json file://deploy/task-def-agent.json
```

### 8c — Create the service

1. **ECS → Clusters → travel-concierge → Services → Create**
2. Settings:

   | Field | Value |
   |---|---|
   | Launch type | FARGATE |
   | Task definition | `agent-service` (latest) |
   | Service name | `agent-service` |
   | Desired tasks | `1` |

3. **Networking:**
   - VPC: default VPC
   - Subnets: select all
   - Security group: create new → allow inbound TCP **8100** from the ALB security group
   - Public IP: OFF

4. **Load balancing:**
   - Load balancer type: Application Load Balancer
   - Load balancer: `agent-alb`
   - Listener: 80:HTTP
   - Target group: `agent-tg` (existing)

5. → **Create**

### 8d — Note the ALB DNS name

- **EC2 → Load Balancers → agent-alb**
- Copy the **DNS name** (e.g. `agent-alb-1234567890.us-east-1.elb.amazonaws.com`)

Test the WebSocket connection:
```bash
# Install wscat:  npm install -g wscat
wscat -c ws://agent-alb-1234567890.us-east-1.elb.amazonaws.com/ws/chat
# Type: {"message": "Hello", "user_id": "test"}
# You should see streaming token responses
```

---

## Step 9 — Deploy React UI to S3 + CloudFront

### 9a — Create the S3 bucket

1. **S3 → Create bucket**
2. Settings:

   | Field | Value |
   |---|---|
   | Bucket name | `travel-concierge-ui-YOUR_ACCOUNT_ID` (must be globally unique) |
   | Region | us-east-1 |
   | Block all public access | **ON** (CloudFront handles access, not S3 directly) |

3. → **Create bucket**

### 9b — Create the CloudFront distribution

1. **CloudFront → Create distribution**
2. Settings:

   | Field | Value |
   |---|---|
   | Origin domain | select your S3 bucket |
   | Origin access | Origin access control (OAC) → Create new OAC |
   | Default root object | `index.html` |
   | Viewer protocol policy | Redirect HTTP to HTTPS |
   | Cache policy | CachingOptimized |

3. **Custom error responses** (for React SPA routing):
   - Error code: `403` → Response page: `/index.html` → HTTP 200
   - Error code: `404` → Response page: `/index.html` → HTTP 200

4. → **Create distribution** (takes ~5 minutes to deploy globally)

5. Copy the bucket policy shown after OAC creation → paste into S3 bucket policy:
   - **S3 → your bucket → Permissions → Bucket policy → Edit → Paste → Save**

### 9c — Build the UI with the real WebSocket URL

```bash
# Use the ALB DNS name from Step 8d
VITE_WS_URL=ws://agent-alb-1234567890.us-east-1.elb.amazonaws.com/ws/chat \
npm run build --prefix ui
```

> For HTTPS/WSS (production): set up an ACM certificate on the ALB,
> add an HTTPS:443 listener, then use `wss://` here.

### 9d — Upload to S3

```bash
BUCKET=travel-concierge-ui-YOUR_ACCOUNT_ID

# Upload assets with long cache (Vite adds content hashes to filenames)
aws s3 sync ui/dist/ s3://${BUCKET}/ \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "index.html"

# Upload index.html with no-cache so users always get the latest version
aws s3 cp ui/dist/index.html s3://${BUCKET}/index.html \
  --cache-control "no-cache"
```

### 9e — Test

Open your **CloudFront distribution domain** (e.g. `https://d1234abcd.cloudfront.net`).
You should see the Travel Concierge chat UI and the "Connected" badge.

---

## Step 10 — Verify the full stack

Send a test message:

```
"What is the weather in Tokyo?"
```

Expected flow visible in the UI:
1. Token stream starts appearing word by word
2. ToolPanel shows `get_weather` being called with `{"city": "Tokyo"}`
3. ToolPanel shows the result
4. Final answer streams in

Check logs if anything fails:
```bash
# Stream live logs from the agent container
aws logs tail /ecs/agent-service --follow

# Stream live logs from travel-api
aws logs tail /ecs/travel-api --follow
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| UI shows "Reconnecting…" | Agent service not running or ALB misconfigured | Check ECS service events; check ALB target health |
| Agent task keeps restarting | Missing env var or bad secret ARN | Check CloudWatch logs: `/ecs/agent-service` |
| `AccessDeniedException` from Bedrock | `agentTaskRole` missing Bedrock permission | Re-check Step 3b IAM policy |
| travel-api unreachable from agent | Wrong `TRAVEL_API_URL` in task def | Update task def with correct private IP; re-deploy |
| CloudFront returns 403 | S3 bucket policy not updated with OAC | Re-apply the bucket policy from Step 9b |
| WebSocket closes immediately | ALB idle timeout too short | EC2 → Load Balancers → Attributes → Idle timeout → set to 300s |

---

## Teardown (avoid ongoing charges)

```bash
# Delete ECS services (scale to 0 first)
aws ecs update-service --cluster travel-concierge --service agent-service --desired-count 0
aws ecs update-service --cluster travel-concierge --service travel-api    --desired-count 0
aws ecs delete-service --cluster travel-concierge --service agent-service --force
aws ecs delete-service --cluster travel-concierge --service travel-api    --force

# Delete ALB + target group
# (EC2 console → Load Balancers → Delete)

# Empty and delete S3 bucket
aws s3 rm s3://travel-concierge-ui-YOUR_ACCOUNT_ID --recursive
aws s3 rb s3://travel-concierge-ui-YOUR_ACCOUNT_ID

# Disable CloudFront distribution, then delete it (CloudFront console)

# Delete ECR images (to avoid storage costs)
aws ecr delete-repository --repository-name travel-api     --force
aws ecr delete-repository --repository-name agent-service  --force
aws ecr delete-repository --repository-name travel-ui      --force

# Delete secrets
aws secretsmanager delete-secret --secret-id travel-concierge/AWS_ACCESS_KEY_ID     --force-delete-without-recovery
aws secretsmanager delete-secret --secret-id travel-concierge/AWS_SECRET_ACCESS_KEY --force-delete-without-recovery
aws secretsmanager delete-secret --secret-id travel-concierge/BEDROCK_KB_ID         --force-delete-without-recovery
```
