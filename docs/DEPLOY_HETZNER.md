# Genesis デプロイ手順 (Hetzner + Cloudflare)

## 構成図

```
[ユーザー]
    │
    ├── https://genesis.your-domain.com (Frontend)
    │       ↓
    │   [Cloudflare Pages] ← React SPA
    │
    └── https://api.genesis.your-domain.com (Backend API)
            ↓
        [Hetzner VPS]
        ├── Docker
        │   ├── FastAPI (port 8000)
        │   ├── Celery Worker
        │   ├── Celery Beat
        │   ├── PostgreSQL
        │   └── Redis
        │
        └── Cloudflare Tunnel → [自宅PC: Ollama]
```

---

## 事前準備

### 必要なもの
- [ ] Hetzner アカウント (https://www.hetzner.com/cloud)
- [ ] Cloudflare アカウント (https://cloudflare.com)
- [ ] 独自ドメイン (Cloudflareで管理推奨)
- [ ] SSH キーペア

---

## Part 1: Hetzner VPS セットアップ

### 1.1 サーバー作成

1. Hetzner Cloud Console にログイン
2. 「Add Server」をクリック
3. 以下を選択:

| 項目 | 選択 |
|-----|------|
| Location | Falkenstein (eu-central) または Ashburn (us-east) |
| Image | Ubuntu 24.04 |
| Type | **CX22** (2 vCPU, 4GB RAM, 40GB SSD) — €4.35/月 |
| Networking | Public IPv4 にチェック |
| SSH Key | 自分の公開鍵を登録 |
| Name | `genesis-prod` |

4. 「Create & Buy now」

### 1.2 SSH接続

```bash
# IPアドレスはHetznerコンソールで確認
ssh root@<YOUR_SERVER_IP>
```

### 1.3 初期セットアップ

```bash
# システム更新
apt update && apt upgrade -y

# 必要なパッケージ
apt install -y curl git ufw fail2ban

# ファイアウォール設定
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# スワップ追加 (4GB RAMなので念のため)
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# 一般ユーザー作成 (推奨)
adduser genesis
usermod -aG sudo genesis
cp -r ~/.ssh /home/genesis/
chown -R genesis:genesis /home/genesis/.ssh

# 以降は genesis ユーザーで作業
su - genesis
```

### 1.4 Docker インストール

```bash
# Docker公式リポジトリ追加
curl -fsSL https://get.docker.com | sh

# 一般ユーザーでdocker実行可能に
sudo usermod -aG docker genesis
newgrp docker

# Docker Compose確認
docker compose version
```

---

## Part 2: アプリケーションデプロイ

### 2.1 リポジトリクローン

```bash
cd ~
git clone https://github.com/Workwrite-Niidome/genesis.git
cd genesis
```

### 2.2 本番用環境変数設定

```bash
cp .env.example .env
nano .env
```

**.env の編集内容:**

```bash
# === Database ===
DATABASE_URL=postgresql+asyncpg://genesis:YOUR_SECURE_DB_PASSWORD@db:5432/genesis
POSTGRES_USER=genesis
POSTGRES_PASSWORD=YOUR_SECURE_DB_PASSWORD  # 強力なパスワードに変更！
POSTGRES_DB=genesis

# === Redis ===
REDIS_URL=redis://redis:6379/0

# === LLM (自宅Ollamaへの接続) ===
OLLAMA_HOST=https://ollama.your-domain.com  # Part 4で設定
OLLAMA_MODEL=llama3.1:8b
OLLAMA_CONCURRENCY=8

# === API Keys (本番用) ===
# ANTHROPIC_API_KEY=sk-...  # Claude使う場合
# OPENAI_API_KEY=sk-...     # OpenAI使う場合

# === Security ===
SECRET_KEY=YOUR_RANDOM_SECRET_KEY_HERE  # openssl rand -hex 32 で生成
ALLOWED_ORIGINS=https://genesis.your-domain.com

# === World Settings ===
TICK_INTERVAL_SECONDS=60
MAX_AI_COUNT=20
```

**SECRET_KEY生成:**
```bash
openssl rand -hex 32
```

### 2.3 本番用 docker-compose.prod.yml 作成

```bash
nano docker-compose.prod.yml
```

```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: always
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - OLLAMA_HOST=${OLLAMA_HOST}
      - OLLAMA_MODEL=${OLLAMA_MODEL}
      - OLLAMA_CONCURRENCY=${OLLAMA_CONCURRENCY}
      - SECRET_KEY=${SECRET_KEY}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
    ports:
      - "127.0.0.1:8000:8000"
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: always
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - OLLAMA_HOST=${OLLAMA_HOST}
      - OLLAMA_MODEL=${OLLAMA_MODEL}
      - OLLAMA_CONCURRENCY=${OLLAMA_CONCURRENCY}
    command: celery -A app.worker worker --loglevel=info --concurrency=2

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: always
    depends_on:
      - redis
      - celery-worker
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    command: celery -A app.worker beat --loglevel=info

volumes:
  postgres_data:
  redis_data:
```

### 2.4 起動

```bash
# ビルド & 起動
docker compose -f docker-compose.prod.yml up -d --build

# ログ確認
docker compose -f docker-compose.prod.yml logs -f

# DBマイグレーション (初回のみ)
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

---

## Part 3: Cloudflare 設定 (リバースプロキシ + HTTPS)

### 3.1 Cloudflare Tunnel インストール (VPS側)

```bash
# cloudflared インストール
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Cloudflareにログイン
cloudflared tunnel login
# ブラウザが開くのでログイン & ドメイン選択

# トンネル作成
cloudflared tunnel create genesis-api

# 設定ファイル作成
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

**~/.cloudflared/config.yml:**
```yaml
tunnel: genesis-api
credentials-file: /home/genesis/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: api.genesis.your-domain.com
    service: http://localhost:8000
  - service: http_status:404
```

```bash
# DNSレコード作成
cloudflared tunnel route dns genesis-api api.genesis.your-domain.com

# サービスとして登録
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared

# 確認
sudo systemctl status cloudflared
```

---

## Part 4: 自宅Ollama の外部公開 (Cloudflare Tunnel)

### 4.1 Windows に cloudflared インストール

1. https://github.com/cloudflare/cloudflared/releases から `cloudflared-windows-amd64.exe` をダウンロード
2. `C:\cloudflared\` に配置
3. PowerShell (管理者) で:

```powershell
cd C:\cloudflared

# ログイン
.\cloudflared-windows-amd64.exe tunnel login

# トンネル作成
.\cloudflared-windows-amd64.exe tunnel create ollama-local

# 設定ファイル作成
mkdir $env:USERPROFILE\.cloudflared -Force
notepad $env:USERPROFILE\.cloudflared\config.yml
```

**config.yml (Windows):**
```yaml
tunnel: ollama-local
credentials-file: C:\Users\kazuk\.cloudflared\<TUNNEL_ID>.json

ingress:
  - hostname: ollama.your-domain.com
    service: http://localhost:11434
  - service: http_status:404
```

```powershell
# DNSレコード作成
.\cloudflared-windows-amd64.exe tunnel route dns ollama-local ollama.your-domain.com

# Windowsサービスとして登録
.\cloudflared-windows-amd64.exe service install

# サービス開始
Start-Service cloudflared
```

### 4.2 Ollama の設定確認

Ollama が外部接続を受け付けるように環境変数を確認:

```
OLLAMA_HOST=0.0.0.0
```

Windows環境変数に設定し、Ollamaを再起動。

---

## Part 5: Frontend デプロイ (Cloudflare Pages)

### 5.1 ビルド設定

```bash
# ローカルで (Windows側)
cd C:\Users\kazuk\genesis\frontend

# 本番用環境変数
echo "VITE_API_URL=https://api.genesis.your-domain.com" > .env.production
echo "VITE_WS_URL=wss://api.genesis.your-domain.com" >> .env.production
```

### 5.2 Cloudflare Pages 設定

1. Cloudflare Dashboard → Pages → Create a project
2. 「Connect to Git」→ GitHub連携 → `genesis` リポジトリ選択
3. ビルド設定:

| 項目 | 値 |
|-----|-----|
| Framework preset | Vite |
| Build command | `cd frontend && npm install && npm run build` |
| Build output directory | `frontend/dist` |
| Root directory | `/` |

4. Environment variables:
   - `VITE_API_URL` = `https://api.genesis.your-domain.com`
   - `VITE_WS_URL` = `wss://api.genesis.your-domain.com`

5. 「Save and Deploy」

### 5.3 カスタムドメイン設定

1. Pages プロジェクト → Custom domains
2. `genesis.your-domain.com` を追加
3. DNS設定は自動で行われる

---

## Part 6: 動作確認

### 6.1 各サービス確認

```bash
# VPS側
# Backend API
curl https://api.genesis.your-domain.com/api/health

# Ollama (自宅経由)
curl https://ollama.your-domain.com/api/tags

# Docker状態
docker compose -f docker-compose.prod.yml ps
```

### 6.2 ブラウザ確認

1. https://genesis.your-domain.com にアクセス
2. AIが表示されることを確認
3. Tickが進んでいることを確認

---

## トラブルシューティング

### Ollamaに接続できない

```bash
# VPSからOllamaへの疎通確認
curl https://ollama.your-domain.com/api/tags

# Cloudflare Tunnelログ (Windows)
Get-Content "$env:USERPROFILE\.cloudflared\cloudflared.log" -Tail 50

# Ollama自体のログ
# タスクマネージャー → Ollamaプロセス確認
```

### Tickが進まない

```bash
# Celery Worker ログ
docker compose -f docker-compose.prod.yml logs celery-worker -f

# Redis接続確認
docker compose -f docker-compose.prod.yml exec redis redis-cli ping
```

### DBエラー

```bash
# マイグレーション再実行
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# DB直接確認
docker compose -f docker-compose.prod.yml exec db psql -U genesis -d genesis
```

---

## 運用

### ログ確認
```bash
docker compose -f docker-compose.prod.yml logs -f --tail 100
```

### 再起動
```bash
docker compose -f docker-compose.prod.yml restart
```

### 更新デプロイ
```bash
cd ~/genesis
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

### バックアップ (PostgreSQL)
```bash
docker compose -f docker-compose.prod.yml exec db pg_dump -U genesis genesis > backup_$(date +%Y%m%d).sql
```

---

## コスト概算

| サービス | 月額 |
|---------|------|
| Hetzner CX22 | €4.35 (~¥700) |
| Cloudflare Pages | 無料 |
| Cloudflare Tunnel | 無料 |
| ドメイン | ~¥1,500/年 |
| **合計** | **~¥850/月** |
