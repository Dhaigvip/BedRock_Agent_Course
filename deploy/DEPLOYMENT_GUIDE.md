# AWS Deployment Guide — EC2 + Docker Compose

Deploy the entire Travel Concierge stack on a single EC2 instance using the same
`docker-compose.yml` that runs locally. No ALB, no ECS, no CloudFront.

```
Browser
  │  ws://  +  http://
  ▼
EC2 (port 80)
  └─ nginx ──► React UI  (static files)
               │
               │ /ws/* proxy
               ▼
           agent  :8100
           │  └─ mcp-server (subprocess, stdio)
           │
           │ http://
           ▼
        travel-api  :9000
```

**One EC2 instance runs three containers. nginx handles everything on port 80.**
**The mcp-server runs as a subprocess inside the agent container — no separate container needed.**

---

## What you need before starting

- [ ] AWS account open in your browser
- [ ] AWS credentials (Access Key ID + Secret Key) — created in Section 4
- [ ] Terminal with SSH support (Mac/Linux: built-in; Windows: Git Bash or PowerShell)

---

## Step 1 — Create an IAM user with Bedrock permissions

> Skip if you already have a `bedrock` IAM user from Section 4.

**IAM → Users → Create user**

| Field | Value |
|---|---|
| User name | `bedrock` |
| Permissions | Attach policies directly |
| Policies | `AmazonBedrockFullAccess` |

→ **Create user**

**Create an access key:**

**IAM → Users → bedrock → Security credentials → Create access key**

| Field | Value |
|---|---|
| Use case | Application running outside AWS |

→ **Create access key** → copy both values and keep them safe.

---

## Step 2 — Launch an EC2 instance

**EC2 → Instances → Launch instances**

| Field | Value |
|---|---|
| Name | `travel-concierge` |
| AMI | Ubuntu Server 24.04 LTS (Free tier eligible) |
| Instance type | `t3.small` (~$15/month) |
| Key pair | Create new → name: `travel-key` → download the `.pem` file |

**Network settings → Edit:**

| Field | Value |
|---|---|
| Auto-assign public IP | Enable |

Add two inbound rules (in addition to the default SSH rule):

| Type | Port | Source |
|---|---|---|
| SSH | 22 | My IP |
| HTTP | 80 | Anywhere (0.0.0.0/0) |

→ **Launch instance**

**Copy the public IP** — you will use it for the WebSocket URL and to SSH in.

---

## Step 3 — SSH into the instance

Wait ~1 minute for the instance to start, then:

**Mac / Linux:**
```bash
chmod 400 ~/Downloads/travel-key.pem
ssh -i ~/Downloads/travel-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

**Windows (PowerShell):**

First fix the key file permissions (required once — Windows SSH rejects keys accessible by other users):
```powershell
icacls "C:\Users\YOUR_USERNAME\Downloads\travel-key.pem" /inheritance:r /grant:r "YOUR_USERNAME:R"
```
Replace `YOUR_USERNAME` with your Windows username (e.g. `VipulDhaigude`).

Then SSH in:
```powershell
ssh -i C:\Users\YOUR_USERNAME\Downloads\travel-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

> If you see a fingerprint prompt, type `yes` and press Enter.

---

## Step 4 — Install Docker on the EC2 instance

Run these commands inside the SSH session:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Allow running docker without sudo
sudo usermod -aG docker ubuntu
newgrp docker

# Verify
docker --version
docker compose version
```

---

## Step 5 — Clone the repo

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

> Replace with your actual GitHub repo URL.

---

## Step 6 — Create the credentials file

```bash
cp agent/.env.example agent/.env
nano agent/.env
```

Fill in your values:

```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
BEDROCK_KB_ID=your-knowledge-base-id
```

Save: **Ctrl+O → Enter → Ctrl+X**

---

## Step 7 — Start the stack

```bash
VITE_WS_URL=ws://YOUR_EC2_PUBLIC_IP/ws/chat docker compose up --build -d
```

Replace `YOUR_EC2_PUBLIC_IP` with your actual EC2 public IP, e.g.:
```bash
VITE_WS_URL=ws://54.123.45.67/ws/chat docker compose up --build -d
```

> This builds all three images and starts them in the background.
> First build takes 3–5 minutes (downloading base images and dependencies).

Watch the logs to confirm everything started:
```bash
docker compose logs -f
```

You should see all four services start without errors. Press **Ctrl+C** to stop following logs.

---

## Step 8 — Verify

Open your browser and go to:
```
http://YOUR_EC2_PUBLIC_IP
```

You should see the Travel Concierge chat UI with a green **Connected** badge.

Send a test message: `"What is the weather in Tokyo?"`

You should see tokens streaming in word-by-word with tool calls shown in the panel.

---

## Redeploying after a code change

On your local machine, push your changes to GitHub. Then on the EC2:

```bash
git pull
VITE_WS_URL=ws://YOUR_EC2_PUBLIC_IP/ws/chat docker compose up --build -d
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Can't SSH in | Check security group allows port 22 from your IP; verify `.pem` file permissions (`chmod 400`) |
| Page doesn't load | Check security group allows port 80; verify `docker compose ps` shows all containers Up |
| WebSocket disconnects immediately | Check agent logs: `docker compose logs agent` |
| MCP tools failing | Check mcp-server logs: `docker compose logs mcp-server` |
| Bedrock `AccessDeniedException` | IAM user is missing `AmazonBedrockFullAccess` policy |
| Container keeps restarting | Read logs: `docker compose logs <service-name>` |
| Wrong EC2 IP in WebSocket URL | Rebuild: `VITE_WS_URL=ws://NEW_IP/ws/chat docker compose up --build ui -d` |

---

## Check container status

```bash
docker compose ps          # all containers and their status
docker compose logs -f     # live log stream for all services
docker compose logs agent  # logs for one service
```

---

## Teardown (stop charges)

```bash
# Stop and remove all containers
docker compose down
```

Then in the AWS Console:
**EC2 → Instances → select `travel-concierge` → Instance state → Terminate**

> Terminating the instance stops all charges. The EC2 instance costs ~$0.02/hour.
