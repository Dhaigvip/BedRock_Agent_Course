# Step-by-Step AWS Deployment Guide

Deploy the Travel Concierge stack entirely through the **AWS Console**.

```
Browser
  │  wss://
  ▼
CloudFront ──► S3              React UI  (static files)
                │
                │  wss://
                ▼
          ALB (port 80)
                │
                ▼
        ECS Fargate            Agent WebSocket API  (:8100)
          agent-service
                │  http://
                ▼
        ECS Fargate            Travel Data API  (:9000)
          travel-api
```

---

## What needs a terminal vs what is portal-only

| Step | Where |
|---|---|
| Docker build + push images to ECR | Terminal (Docker unavoidable) |
| Build React UI with production URL | Terminal (npm build) |
| Upload UI files to S3 | **Portal** (drag and drop) |
| Everything else (IAM, ECS, ALB, CF…) | **Portal** |

> **ECR push commands:** The AWS Console generates the exact commands for you.
> Open any ECR repository → click **View push commands** — copy, paste, done.

---

## Prerequisites

- [ ] **Docker Desktop installed and running** — open Docker Desktop and wait for the engine
  to show "Running" before executing any `docker` command. Build and push will silently
  fail or throw `"Cannot connect to the Docker daemon"` if Docker is not started.
- [ ] AWS CLI installed and configured (`aws configure` done in Section 4)
- [ ] Node.js installed (needed only for `npm run build` in Step 9)
- [ ] AWS account open in your browser, region set to **us-east-1**

---

## Step 0 — Add ECR + ECS Permissions to Your IAM User

> The `bedrock` user created in Section 4 only has `AmazonBedrockFullAccess`.
> Deployment needs additional permissions for ECR (push images) and ECS (create services).
> Do this once before any other step.

**IAM → Users → bedrock → Add permissions → Attach policies directly**

Search for and attach these three managed policies:

| Policy | Why needed |
|---|---|
| `AmazonEC2ContainerRegistryFullAccess` | Push Docker images to ECR |
| `AmazonECS_FullAccess` | Create clusters, task definitions, services |
| `SecretsManagerReadWrite` | Store and read credentials in Secrets Manager |

→ **Add permissions**

Verify with:
```cmd
aws ecr get-login-password --region us-east-1
```
If it returns a long token (not an AccessDeniedException) you are good to go.

---

## Step 1 — Create ECR Repositories

**ECR → Repositories → Create repository** (repeat 3 times)

| Repository name | Visibility |
|---|---|
| `travel-api` | Private |
| `agent-service` | Private |
| `travel-ui` | Private |

Leave all other settings as default → **Create repository**

> **Why only 3 repos and not 4?**
> The MCP server is **not** a separate container. It is bundled inside the
> `agent-service` image and runs as a subprocess — the agent spawns it via
> stdio transport at startup. This is why the agent `Dockerfile` build context
> is the repo root and copies both `agent/` and `mcp-server/` together.

---

## Step 2 — Build and Push Docker Images

The console generates the exact commands for you.

1. Open **ECR → Repositories → travel-api**
2. Click **View push commands** (top right)
3. Copy and run the 4 commands in your terminal

Repeat for `agent-service` and `travel-ui`.

> **Important for agent-service:** the build command shown by the console is:
> ```
> docker build -t agent-service .
> ```
> You must run this from the **repo root** (not the `agent/` folder) and add `-f agent/Dockerfile`:
> ```
> docker build -f agent/Dockerfile -t agent-service .
> ```
> The other 3 commands (login, tag, push) stay exactly as shown.

---

## Step 3 — Create IAM Roles

### Role 1 — ecsTaskExecutionRole

> Skip if it already exists — search **IAM → Roles** for `ecsTaskExecutionRole`.

**IAM → Roles → Create role**

| Field | Value |
|---|---|
| Trusted entity | AWS service |
| Use case | Elastic Container Service → **Elastic Container Service Task** |

Click **Next** → search for and select:
- `AmazonECSTaskExecutionRolePolicy`

Click **Next**

| Field | Value |
|---|---|
| Role name | `ecsTaskExecutionRole` |

→ **Create role**

---

### Role 2 — agentTaskRole

**IAM → Roles → Create role**

| Field | Value |
|---|---|
| Trusted entity | AWS service |
| Use case | Elastic Container Service → **Elastic Container Service Task** |

Click **Next → Next** (skip permissions for now)

| Field | Value |
|---|---|
| Role name | `agentTaskRole` |

→ **Create role**

Now add the Bedrock permission:

1. Open `agentTaskRole` → **Add permissions → Create inline policy**
2. Click the **JSON** tab
3. Replace the content with:

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
      "Resource": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT_ID:secret:travel-concierge/*"
    }
  ]
}
```

4. Replace `YOUR_ACCOUNT_ID` with your 12-digit account ID
5. **Policy name:** `AgentTaskPolicy` → **Create policy**

---

## Step 4 — Store Secrets in Secrets Manager

Create one secret for each value below.

**Secrets Manager → Store a new secret** (repeat 3 times)

Each time:
1. **Secret type:** Other type of secret
2. **Key/value pairs:** clear the default row, add one pair:

| Secret name | Key | Value |
|---|---|---|
| `travel-concierge/AWS_ACCESS_KEY_ID` | `AWS_ACCESS_KEY_ID` | your access key |
| `travel-concierge/AWS_SECRET_ACCESS_KEY` | `AWS_SECRET_ACCESS_KEY` | your secret key |
| `travel-concierge/BEDROCK_KB_ID` | `BEDROCK_KB_ID` | your KB ID (or leave empty) |

3. **Encryption:** `aws/secretsmanager` (default)
4. Click **Next → Next → Store**

**After creating each secret:** open it and copy the full **ARN**
(looks like `arn:aws:secretsmanager:us-east-1:123456789012:secret:travel-concierge/AWS_ACCESS_KEY_ID-AbCdEf`)

You will need all three ARNs in Step 8.

---

## Step 5 — Create CloudWatch Log Groups

**CloudWatch → Log groups → Create log group** (repeat twice)

| Log group name |
|---|
| `/ecs/travel-api` |
| `/ecs/agent-service` |

Leave retention as default → **Create**

---

## Step 6 — Create the ECS Cluster

**ECS → Clusters → Create cluster**

| Field | Value |
|---|---|
| Cluster name | `travel-concierge` |
| Infrastructure | AWS Fargate (serverless) ✓ |

Leave everything else as default → **Create**

---

## Step 7 — Deploy Travel API

### 7a — Create the task definition

**ECS → Task definitions → Create new task definition**

At the top of the form click **Configure via JSON** and paste:

```json
{
  "family": "travel-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "travel-api",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/travel-api:latest",
      "portMappings": [
        { "containerPort": 9000, "protocol": "tcp" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/travel-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "essential": true
    }
  ]
}
```

Replace `YOUR_ACCOUNT_ID` → **Save** → **Create**

---

### 7b — Create the travel-api service

**ECS → Clusters → travel-concierge → Services → Create**

**Environment**

| Field | Value |
|---|---|
| Compute option | Launch type |
| Launch type | FARGATE |

**Deployment configuration**

| Field | Value |
|---|---|
| Application type | Service |
| Task definition | `travel-api` — latest |
| Service name | `travel-api` |
| Desired tasks | `1` |

**Networking**

| Field | Value |
|---|---|
| VPC | default VPC |
| Subnets | select all |
| Security group | Create new — name: `travel-api-sg` |
| Inbound rule | TCP port `9000` — source: Custom `10.0.0.0/8` (VPC internal only) |
| Public IP | **TURN OFF** — travel-api is internal, not public |

**Load balancing:** None

→ **Create**

---

### 7c — Note the private IP

Wait until the task shows **RUNNING** status (refresh every 30 seconds).

**ECS → Clusters → travel-concierge → Services → travel-api → Tasks**
→ click the task ID → copy the **Private IP** (e.g. `10.0.1.45`)

You will use this as `http://10.0.1.45:9000` in the agent task definition.

---

## Step 8 — Deploy Agent API

### 8a — Create a security group for the ALB

**EC2 → Security Groups → Create security group**

| Field | Value |
|---|---|
| Name | `agent-alb-sg` |
| Description | ALB for agent WebSocket API |
| VPC | default VPC |
| Inbound rule | HTTP, port `80`, source `0.0.0.0/0` |

→ **Create security group**

---

### 8b — Create a security group for the agent container

**EC2 → Security Groups → Create security group**

| Field | Value |
|---|---|
| Name | `agent-service-sg` |
| VPC | default VPC |
| Inbound rule | Custom TCP, port `8100`, source: `agent-alb-sg` (select the SG you just created) |

→ **Create security group**

---

### 8c — Create the target group

**EC2 → Target Groups → Create target group**

| Field | Value |
|---|---|
| Target type | IP addresses |
| Target group name | `agent-tg` |
| Protocol | HTTP |
| Port | `8100` |
| VPC | default VPC |
| Health check path | `/` |

→ **Next → Create target group** (no targets to register yet — ECS does this)

---

### 8d — Create the Application Load Balancer

**EC2 → Load Balancers → Create load balancer → Application Load Balancer**

| Field | Value |
|---|---|
| Name | `agent-alb` |
| Scheme | Internet-facing |
| IP address type | IPv4 |
| VPC | default VPC |
| Subnets | select **all** availability zones |
| Security group | `agent-alb-sg` (remove the default one) |

**Listeners and routing**

| Field | Value |
|---|---|
| Protocol | HTTP |
| Port | `80` |
| Default action | Forward to `agent-tg` |

→ **Create load balancer**

> **WebSocket note:** ALB supports WebSocket automatically. Any connection
> with an `Upgrade: websocket` header is passed through without any extra config.

**Set idle timeout to 300 seconds** (important — default 60s will drop long conversations):

- **EC2 → Load Balancers → agent-alb → Attributes → Edit**
- Idle timeout → `300` → **Save**

---

### 8e — Create the agent task definition

**ECS → Task definitions → Create new task definition → Configure via JSON**

Paste the JSON below. Replace:
- `YOUR_ACCOUNT_ID` — your 12-digit account ID
- `TRAVEL_API_PRIVATE_IP` — the IP from Step 7c (e.g. `10.0.1.45`)
- The three `SECRET_ARN_...` placeholders — the ARNs you copied in Step 4

```json
{
  "family": "agent-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn":      "arn:aws:iam::YOUR_ACCOUNT_ID:role/agentTaskRole",
  "containerDefinitions": [
    {
      "name": "agent-service",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/agent-service:latest",
      "portMappings": [
        { "containerPort": 8100, "protocol": "tcp" }
      ],
      "environment": [
        { "name": "AWS_REGION",     "value": "us-east-1" },
        { "name": "TRAVEL_API_URL", "value": "http://TRAVEL_API_PRIVATE_IP:9000" }
      ],
      "secrets": [
        { "name": "AWS_ACCESS_KEY_ID",     "valueFrom": "SECRET_ARN_ACCESS_KEY_ID" },
        { "name": "AWS_SECRET_ACCESS_KEY", "valueFrom": "SECRET_ARN_SECRET_KEY" },
        { "name": "BEDROCK_KB_ID",         "valueFrom": "SECRET_ARN_KB_ID" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group":         "/ecs/agent-service",
          "awslogs-region":        "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "essential": true
    }
  ]
}
```

→ **Save → Create**

---

### 8f — Create the agent service

**ECS → Clusters → travel-concierge → Services → Create**

**Environment**

| Field | Value |
|---|---|
| Compute option | Launch type |
| Launch type | FARGATE |

**Deployment configuration**

| Field | Value |
|---|---|
| Task definition | `agent-service` — latest |
| Service name | `agent-service` |
| Desired tasks | `1` |

**Networking**

| Field | Value |
|---|---|
| VPC | default VPC |
| Subnets | select all |
| Security group | `agent-service-sg` (remove default) |
| Public IP | **TURN OFF** |

**Load balancing**

| Field | Value |
|---|---|
| Load balancer type | Application Load Balancer |
| Load balancer | `agent-alb` |
| Listener | `80:HTTP` — use existing |
| Target group | `agent-tg` — use existing |

→ **Create**

---

### 8g — Copy the ALB DNS name

**EC2 → Load Balancers → agent-alb**

Copy the **DNS name** (e.g. `agent-alb-1234567890.us-east-1.elb.amazonaws.com`)

You will use this in the next step to build the UI.

---

## Step 9 — Deploy React UI

### 9a — Build the UI with the real WebSocket URL

In your terminal, from the repo root:

```bash
# Replace with the ALB DNS name from Step 8g
VITE_WS_URL=ws://agent-alb-1234567890.us-east-1.elb.amazonaws.com/ws/chat \
npm run build --prefix ui
```

This creates `ui/dist/` containing the production React app with your
ALB URL baked in.

---

### 9b — Create the S3 bucket

**S3 → Create bucket**

| Field | Value |
|---|---|
| Bucket name | `travel-concierge-ui` (add your account ID if taken) |
| Region | us-east-1 |
| Block all public access | **ON** (CloudFront handles public access) |
| Versioning | off |

→ **Create bucket**

---

### 9c — Create the CloudFront distribution

**CloudFront → Create distribution**

**Origin**

| Field | Value |
|---|---|
| Origin domain | your S3 bucket (select from dropdown) |
| Origin access | **Origin access control settings (recommended)** |
| Origin access control | Create new OAC → **Create** (default settings are fine) |

**Default cache behavior**

| Field | Value |
|---|---|
| Viewer protocol policy | Redirect HTTP to HTTPS |
| Cache policy | CachingOptimized |

**Settings**

| Field | Value |
|---|---|
| Default root object | `index.html` |

→ **Create distribution**

A yellow banner appears: **"You must update the S3 bucket policy"**
→ click **Copy policy** → keep this copied.

---

### 9d — Update the S3 bucket policy

**S3 → your bucket → Permissions → Bucket policy → Edit**

Paste the policy you just copied → **Save changes**

---

### 9e — Add custom error responses (SPA routing)

**CloudFront → your distribution → Error pages → Create custom error response** (twice)

| HTTP error code | Response page path | HTTP response code |
|---|---|---|
| `403` | `/index.html` | `200` |
| `404` | `/index.html` | `200` |

---

### 9f — Upload the UI files

**S3 → your bucket → Upload**

1. Click **Add files** → select all files inside `ui/dist/` (not the folder, the files)
2. Click **Add folder** → select the `ui/dist/assets/` folder
3. → **Upload**

> **Cache headers via console:**
> After upload, select all files in `assets/` → **Actions → Edit metadata**
> → Add: `Cache-Control` = `public, max-age=31536000, immutable`
>
> Select `index.html` → **Actions → Edit metadata**
> → Add: `Cache-Control` = `no-cache`

---

## Step 10 — Verify end-to-end

1. Open **CloudFront → your distribution** — copy the **Distribution domain name**
   (e.g. `https://d1234abcdef.cloudfront.net`)

2. Open it in your browser — you should see the Travel Concierge chat UI
   with a green **Connected** badge

3. Send a test message: `"What is the weather in Tokyo?"`

4. You should see:
   - Tokens streaming in word-by-word
   - The ToolPanel showing `get_weather` being called
   - A full answer arriving

**If something is wrong — check the logs:**

**CloudWatch → Log groups → /ecs/agent-service → log streams**
→ click the most recent stream to see the container output

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| UI shows "Reconnecting…" | Check agent-service task is RUNNING in ECS; check ALB target health (EC2 → Target Groups → agent-tg → Targets) |
| Agent task keeps stopping | Open CloudWatch → /ecs/agent-service and read the error |
| `AccessDeniedException` from Bedrock | agentTaskRole is missing the Bedrock policy — re-check Step 3b |
| travel-api unreachable | Wrong private IP in TRAVEL_API_URL — update task definition and redeploy |
| CloudFront returns 403 | S3 bucket policy not saved — redo Step 9d |
| WebSocket drops after 60s | ALB idle timeout still at 60 — redo the 300s setting in Step 8d |

---

## Teardown (avoid ongoing charges)

When you are done with the course, delete resources in this order:

1. **ECS → Services** → scale desired count to 0 → delete both services
2. **EC2 → Load Balancers** → delete `agent-alb`
3. **EC2 → Target Groups** → delete `agent-tg`
4. **CloudFront** → disable distribution → wait → delete
5. **S3** → empty the bucket → delete bucket
6. **ECS → Clusters** → delete `travel-concierge`
7. **ECR → Repositories** → delete all three
8. **Secrets Manager** → delete all three secrets
9. **CloudWatch → Log groups** → delete `/ecs/travel-api` and `/ecs/agent-service`
