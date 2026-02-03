# Genesis 完全デプロイガイド (初心者向け)

Railway/Vercelしか使ったことない人向けの、ゼロからの完全手順書です。

---

## 目次

1. [事前準備・必要なもの](#1-事前準備必要なもの)
2. [ドメイン取得](#2-ドメイン取得)
3. [Cloudflareセットアップ](#3-cloudflareセットアップ)
4. [SSHキー作成](#4-sshキー作成)
5. [Hetznerアカウント作成・VPS作成](#5-hetznerアカウント作成vps作成)
6. [VPS初期設定](#6-vps初期設定)
7. [Dockerインストール](#7-dockerインストール)
8. [アプリケーションデプロイ](#8-アプリケーションデプロイ)
9. [Cloudflare Tunnel設定 (VPS側)](#9-cloudflare-tunnel設定-vps側)
10. [Cloudflare Tunnel設定 (自宅Ollama)](#10-cloudflare-tunnel設定-自宅ollama)
11. [フロントエンドデプロイ (Cloudflare Pages)](#11-フロントエンドデプロイ-cloudflare-pages)
12. [動作確認](#12-動作確認)
13. [トラブルシューティング](#13-トラブルシューティング)

---

## 1. 事前準備・必要なもの

### 必要なアカウント
- [ ] クレジットカード (Hetzner支払い用)
- [ ] GitHubアカウント (既にあるはず)
- [ ] Cloudflareアカウント (無料、これから作成)
- [ ] Hetznerアカウント (これから作成)

### 必要な情報
- [ ] 使いたいドメイン名を決める (例: `genesis-world.com`)

### ローカルに必要なもの
- [ ] ターミナル (Windows Terminal または PowerShell)
- [ ] Ollama が動いている状態

---

## 2. ドメイン取得

ドメインをまだ持っていない場合は取得します。

### おすすめのドメイン取得先

| サービス | 特徴 |
|---------|------|
| **Cloudflare Registrar** | 最安、Cloudflare連携が楽 |
| **Google Domains** | シンプル、信頼性高 |
| **お名前.com** | 日本語、サポート充実 |

### Cloudflare Registrar での取得手順 (推奨)

1. https://dash.cloudflare.com にアクセス
2. アカウント作成 (まだの場合)
3. 左メニュー「Domain Registration」→「Register Domains」
4. 欲しいドメインを検索 (例: `genesis-world.com`)
5. カートに追加 → 購入

**既にドメインを持っている場合**: Step 3 へ進む

---

## 3. Cloudflareセットアップ

### 3.1 アカウント作成

1. https://dash.cloudflare.com にアクセス
2. 「Sign Up」→ メールとパスワード入力
3. メール認証

### 3.2 ドメインをCloudflareに追加

**Cloudflare以外でドメインを取得した場合のみ必要**

1. ダッシュボード → 「Add a Site」
2. ドメイン名を入力 (例: `genesis-world.com`)
3. 「Free」プランを選択
4. 「Continue」

5. 既存のDNSレコードが表示される → 「Continue」

6. **ネームサーバー変更の指示が出る**:
   ```
   ns1.cloudflare.com
   ns2.cloudflare.com
   ```

7. ドメイン取得元 (お名前.com等) の管理画面で、ネームサーバーを上記に変更

8. Cloudflareに戻り「Done, check nameservers」

9. 反映まで数分〜24時間待つ (通常は数分)

### 3.3 SSL設定確認

1. ドメインを選択 → 左メニュー「SSL/TLS」
2. 「Overview」で「Full (strict)」を選択

---

## 4. SSHキー作成

VPSに安全に接続するためのSSHキーを作成します。

### Windows (PowerShell)

```powershell
# .sshフォルダがなければ作成
mkdir $env:USERPROFILE\.ssh -Force

# SSHキー生成
ssh-keygen -t ed25519 -C "your-email@example.com"
```

**質問への回答:**
```
Enter file in which to save the key: [そのままEnter]
Enter passphrase: [パスフレーズ入力 または 空でEnter]
Enter same passphrase again: [同じものを入力]
```

**キーの確認:**
```powershell
# 公開鍵の内容を表示 (これをHetznerに登録する)
cat $env:USERPROFILE\.ssh\id_ed25519.pub
```

出力例:
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... your-email@example.com
```

**この公開鍵をコピーしておく** (次のステップで使う)

---

## 5. Hetznerアカウント作成・VPS作成

### 5.1 アカウント作成

1. https://www.hetzner.com/cloud にアクセス
2. 右上「Register」をクリック
3. メールアドレス、パスワードを入力
4. メール認証
5. **本人確認** (パスポートまたは免許証の写真をアップロード)
   - 通常1-2営業日で承認される
   - 承認されるとメールが届く

### 5.2 SSHキー登録

1. Hetzner Cloud Console にログイン
2. 左メニュー「Security」→「SSH Keys」
3. 「Add SSH Key」
4. 先ほどコピーした公開鍵を貼り付け
5. Name: `my-windows-pc` など
6. 「Add SSH Key」

### 5.3 VPS作成

1. 左メニュー「Servers」→「Add Server」

2. **Location**:
   - `Ashburn` (アメリカ東海岸) — 日本からのレイテンシ考慮
   - または `Falkenstein` (ドイツ) — 最安

3. **Image**:
   - `Ubuntu` → `24.04`

4. **Type**:
   - 「Shared vCPU」タブ
   - 「x86」
   - **CX22** を選択 (2 vCPU, 4 GB RAM, 40 GB SSD) — €4.35/月

5. **Networking**:
   - ✅ Public IPv4 (チェック入れる)
   - IPv6 はそのまま

6. **SSH Keys**:
   - 先ほど登録したキーにチェック

7. **Name**:
   - `genesis-prod`

8. 「Create & Buy now」をクリック

9. **IPアドレスをメモ** (例: `128.140.xx.xx`)

---

## 6. VPS初期設定

### 6.1 SSH接続

**Windows Terminal または PowerShell で:**

```powershell
ssh root@128.140.xx.xx
```

**初回接続時:**
```
The authenticity of host '128.140.xx.xx' can't be established.
ED25519 key fingerprint is SHA256:xxxxx.
Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
```
→ `yes` と入力してEnter

### 6.2 システム更新

```bash
# パッケージ更新
apt update && apt upgrade -y
```

### 6.3 基本パッケージインストール

```bash
apt install -y curl git ufw fail2ban htop
```

### 6.4 ファイアウォール設定

```bash
# SSH許可
ufw allow OpenSSH

# HTTP/HTTPS許可
ufw allow 80/tcp
ufw allow 443/tcp

# ファイアウォール有効化
ufw enable
```

「Command may disrupt existing SSH connections. Proceed with operation (y|n)?」
→ `y` と入力

### 6.5 スワップ追加 (メモリ不足対策)

```bash
# 2GBのスワップファイル作成
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# 再起動後も有効にする
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# 確認
free -h
```

### 6.6 一般ユーザー作成 (セキュリティ推奨)

```bash
# ユーザー作成
adduser genesis
```

**質問への回答:**
```
New password: [パスワード入力]
Retype new password: [同じパスワード]
Full Name []: [空でEnter]
Room Number []: [空でEnter]
Work Phone []: [空でEnter]
Home Phone []: [空でEnter]
Other []: [空でEnter]
Is the information correct? [Y/n]: Y
```

```bash
# sudo権限付与
usermod -aG sudo genesis

# SSHキーをコピー
cp -r /root/.ssh /home/genesis/
chown -R genesis:genesis /home/genesis/.ssh

# genesisユーザーに切り替え
su - genesis

# 以降はこのユーザーで作業
```

---

## 7. Dockerインストール

**genesisユーザーで実行** (前のステップから継続)

```bash
# Docker公式インストールスクリプト
curl -fsSL https://get.docker.com | sudo sh

# 一般ユーザーでdocker実行可能にする
sudo usermod -aG docker genesis

# グループを反映 (再ログインの代わり)
newgrp docker

# 確認
docker --version
docker compose version
```

出力例:
```
Docker version 24.0.x
Docker Compose version v2.x.x
```

---

## 8. アプリケーションデプロイ

### 8.1 リポジトリクローン

```bash
cd ~
git clone https://github.com/Workwrite-Niidome/genesis.git
cd genesis
```

### 8.2 環境変数ファイル作成

```bash
nano .env
```

**以下を貼り付けて編集:**

```bash
# === Database ===
DATABASE_URL=postgresql+asyncpg://genesis:CHANGE_THIS_PASSWORD@db:5432/genesis
POSTGRES_USER=genesis
POSTGRES_PASSWORD=CHANGE_THIS_PASSWORD
POSTGRES_DB=genesis

# === Redis ===
REDIS_URL=redis://redis:6379/0

# === LLM (後で設定するOllama URL) ===
OLLAMA_HOST=https://ollama.your-domain.com
OLLAMA_MODEL=llama3.1:8b
OLLAMA_CONCURRENCY=8

# === Security ===
SECRET_KEY=GENERATE_THIS
ALLOWED_ORIGINS=https://genesis.your-domain.com

# === World Settings ===
TICK_INTERVAL_SECONDS=60
MAX_AI_COUNT=20
```

**編集が必要な箇所:**

1. `CHANGE_THIS_PASSWORD` → 強力なパスワードに変更
2. `your-domain.com` → 自分のドメインに変更
3. `GENERATE_THIS` → 以下のコマンドで生成した値に置換

```bash
# SECRET_KEY生成 (別のターミナルタブで実行してコピー)
openssl rand -hex 32
```

**nano での編集方法:**
- 矢印キーで移動
- 普通にタイプして編集
- `Ctrl + O` → Enter で保存
- `Ctrl + X` で終了

### 8.3 本番用 docker-compose ファイル作成

```bash
nano docker-compose.prod.yml
```

**以下を貼り付け:**

```yaml
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
    env_file:
      - .env
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
    env_file:
      - .env
    command: celery -A app.worker worker --loglevel=info --concurrency=2

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: always
    depends_on:
      - redis
      - celery-worker
    env_file:
      - .env
    command: celery -A app.worker beat --loglevel=info

volumes:
  postgres_data:
  redis_data:
```

保存: `Ctrl + O` → Enter → `Ctrl + X`

### 8.4 ビルドと起動

```bash
# イメージビルド & コンテナ起動 (初回は5-10分かかる)
docker compose -f docker-compose.prod.yml up -d --build
```

### 8.5 ビルド完了の確認

```bash
# コンテナ状態確認
docker compose -f docker-compose.prod.yml ps
```

全て `running` または `healthy` になっていればOK:
```
NAME                      STATUS
genesis-backend-1         Up (healthy)
genesis-celery-beat-1     Up
genesis-celery-worker-1   Up
genesis-db-1              Up (healthy)
genesis-redis-1           Up (healthy)
```

### 8.6 データベースマイグレーション

```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### 8.7 ローカル動作確認

```bash
curl http://localhost:8000/api/world/state
```

JSONが返ってくればOK。

---

## 9. Cloudflare Tunnel設定 (VPS側)

VPS上のAPIを `api.your-domain.com` で公開します。

### 9.1 cloudflared インストール

```bash
# VPS上で実行
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
```

### 9.2 Cloudflareにログイン

```bash
cloudflared tunnel login
```

**出力:**
```
Please open the following URL and log in with your Cloudflare account:
https://dash.cloudflare.com/argotunnel?callback=...
```

**このURLをコピーして、ローカルPCのブラウザで開く**

1. Cloudflareにログイン
2. ドメインを選択 (genesis用のドメイン)
3. 「Authorize」をクリック
4. 「Success」と表示される
5. VPSのターミナルに戻ると完了している

### 9.3 トンネル作成

```bash
cloudflared tunnel create genesis-api
```

出力例:
```
Tunnel credentials written to /home/genesis/.cloudflared/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.json
Created tunnel genesis-api with id xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**この `xxxxxxxx-xxxx-...` (Tunnel ID) をメモ**

### 9.4 設定ファイル作成

```bash
nano ~/.cloudflared/config.yml
```

**以下を貼り付けて編集:**

```yaml
tunnel: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
credentials-file: /home/genesis/.cloudflared/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.json

ingress:
  - hostname: api.genesis-world.com
    service: http://localhost:8000
  - service: http_status:404
```

**編集箇所:**
- `xxxxxxxx-xxxx-...` → 先ほどメモしたTunnel ID
- `api.genesis-world.com` → 自分のドメイン

### 9.5 DNS設定

```bash
cloudflared tunnel route dns genesis-api api.genesis-world.com
```

(`api.genesis-world.com` を自分のドメインに置き換え)

### 9.6 サービスとして登録

```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

### 9.7 確認

```bash
sudo systemctl status cloudflared
```

`active (running)` と表示されればOK。

**ブラウザで確認:**
```
https://api.genesis-world.com/api/world/state
```
→ JSONが返ってくればOK

---

## 10. Cloudflare Tunnel設定 (自宅Ollama)

自宅PCのOllamaを `ollama.your-domain.com` で公開します。

### 10.1 cloudflared ダウンロード (Windows)

1. https://github.com/cloudflare/cloudflared/releases/latest にアクセス
2. `cloudflared-windows-amd64.exe` をダウンロード
3. `C:\cloudflared\` フォルダを作成してそこに移動

### 10.2 PowerShell (管理者) で実行

**スタートメニュー → 「PowerShell」と検索 → 「管理者として実行」**

```powershell
cd C:\cloudflared
```

### 10.3 Cloudflareにログイン

```powershell
.\cloudflared-windows-amd64.exe tunnel login
```

ブラウザが自動で開く → ログイン → ドメイン選択 → Authorize

### 10.4 トンネル作成

```powershell
.\cloudflared-windows-amd64.exe tunnel create ollama-local
```

**Tunnel ID をメモ**

### 10.5 設定ファイル作成

```powershell
# .cloudflaredフォルダ作成
mkdir $env:USERPROFILE\.cloudflared -Force

# config.yml作成
notepad $env:USERPROFILE\.cloudflared\config.yml
```

**メモ帳が開くので以下を貼り付けて保存:**

```yaml
tunnel: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
credentials-file: C:\Users\kazuk\.cloudflared\xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.json

ingress:
  - hostname: ollama.genesis-world.com
    service: http://localhost:11434
  - service: http_status:404
```

**編集箇所:**
- `xxxxxxxx-xxxx-...` → Tunnel ID
- `kazuk` → 自分のWindowsユーザー名
- `ollama.genesis-world.com` → 自分のドメイン

### 10.6 DNS設定

```powershell
.\cloudflared-windows-amd64.exe tunnel route dns ollama-local ollama.genesis-world.com
```

### 10.7 Windowsサービスとして登録

```powershell
.\cloudflared-windows-amd64.exe service install
```

### 10.8 サービス開始

```powershell
Start-Service cloudflared
```

### 10.9 Ollama設定確認

Ollamaが外部接続を受け付けるように設定:

1. Windowsの「システム環境変数」を開く
   - 検索で「環境変数」→「システム環境変数の編集」
   - 「環境変数」ボタン

2. 「システム環境変数」の「新規」:
   - 変数名: `OLLAMA_HOST`
   - 変数値: `0.0.0.0`

3. Ollamaを再起動 (タスクトレイから終了 → 再起動)

### 10.10 確認

**ブラウザで:**
```
https://ollama.genesis-world.com/api/tags
```

モデル一覧のJSONが返ってくればOK。

---

## 11. フロントエンドデプロイ (Cloudflare Pages)

### 11.1 環境変数ファイル作成 (ローカル)

**Windows PowerShell (ローカル) で:**

```powershell
cd C:\Users\kazuk\genesis\frontend

# 本番用環境変数ファイル作成
@"
VITE_API_URL=https://api.genesis-world.com
VITE_WS_URL=wss://api.genesis-world.com
"@ | Out-File -Encoding utf8 .env.production
```

(`genesis-world.com` を自分のドメインに置き換え)

### 11.2 変更をコミット&プッシュ

```powershell
cd C:\Users\kazuk\genesis
git add frontend/.env.production
git commit -m "Add production environment variables"
git push
```

### 11.3 Cloudflare Pagesプロジェクト作成

1. https://dash.cloudflare.com にログイン
2. 左メニュー「Workers & Pages」→「Pages」
3. 「Create a project」→「Connect to Git」
4. 「GitHub」を選択 → GitHubアカウント連携
5. `genesis` リポジトリを選択
6. 「Begin setup」

### 11.4 ビルド設定

| 項目 | 値 |
|-----|-----|
| Project name | `genesis` (または好きな名前) |
| Production branch | `master` |
| Framework preset | `None` |
| Build command | `cd frontend && npm install && npm run build` |
| Build output directory | `frontend/dist` |

### 11.5 環境変数設定

「Environment variables」セクションで「Add variable」:

| Variable name | Value |
|---------------|-------|
| `VITE_API_URL` | `https://api.genesis-world.com` |
| `VITE_WS_URL` | `wss://api.genesis-world.com` |
| `NODE_VERSION` | `20` |

### 11.6 デプロイ

「Save and Deploy」をクリック

ビルドログが表示される → 数分で完了

### 11.7 カスタムドメイン設定

1. デプロイ完了後、プロジェクト設定 → 「Custom domains」
2. 「Set up a custom domain」
3. `genesis.genesis-world.com` または `genesis-world.com` を入力
4. 「Continue」→ DNS設定は自動で行われる
5. SSL証明書が発行されるまで数分待つ

---

## 12. 動作確認

### 12.1 各エンドポイント確認

**API:**
```
https://api.genesis-world.com/api/world/state
```

**Ollama:**
```
https://ollama.genesis-world.com/api/tags
```

**フロントエンド:**
```
https://genesis-world.com
```
または
```
https://genesis.genesis-world.com
```

### 12.2 Genesisの動作確認

1. フロントエンドにアクセス
2. AIが表示される
3. Tickが進む (左上などで確認)
4. AIをクリックして詳細が見れる

### 12.3 VPS側ログ確認

```bash
# SSH接続
ssh genesis@128.140.xx.xx

# ログ確認
cd ~/genesis
docker compose -f docker-compose.prod.yml logs -f --tail 100
```

---

## 13. トラブルシューティング

### フロントエンドが真っ白

**原因:** API接続エラー

**確認:**
1. ブラウザの開発者ツール (F12) → Console でエラー確認
2. Network タブでAPIリクエストの状態確認

**対処:**
- VITE_API_URL が正しいか確認
- API側のCORS設定 (ALLOWED_ORIGINS) を確認

### APIに接続できない

**確認:**
```bash
# VPSで
curl http://localhost:8000/api/world/state

# Tunnelの状態
sudo systemctl status cloudflared
```

### Ollamaに接続できない

**確認 (Windows PowerShell):**
```powershell
# サービス状態
Get-Service cloudflared

# ログ
Get-Content $env:USERPROFILE\.cloudflared\cloudflared.log -Tail 50
```

**Ollama自体の確認:**
```powershell
curl http://localhost:11434/api/tags
```

### Tickが進まない

**確認:**
```bash
# VPSで
docker compose -f docker-compose.prod.yml logs celery-worker -f
```

**よくある原因:**
- Ollamaに接続できない → Tunnel確認
- DBエラー → マイグレーション再実行

### DBエラー

```bash
# マイグレーション再実行
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# DB接続確認
docker compose -f docker-compose.prod.yml exec db psql -U genesis -d genesis -c "SELECT 1"
```

---

## 運用コマンド集

### ログ確認
```bash
docker compose -f docker-compose.prod.yml logs -f
docker compose -f docker-compose.prod.yml logs celery-worker -f
```

### 再起動
```bash
docker compose -f docker-compose.prod.yml restart
```

### 停止
```bash
docker compose -f docker-compose.prod.yml down
```

### 更新デプロイ
```bash
cd ~/genesis
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

### DBバックアップ
```bash
docker compose -f docker-compose.prod.yml exec db pg_dump -U genesis genesis > backup_$(date +%Y%m%d).sql
```

### DBリストア
```bash
cat backup_20240101.sql | docker compose -f docker-compose.prod.yml exec -T db psql -U genesis -d genesis
```

---

## コスト

| サービス | 月額 |
|---------|------|
| Hetzner CX22 | €4.35 (~¥700) |
| Cloudflare Pages | 無料 |
| Cloudflare Tunnel | 無料 |
| ドメイン (.com) | ~¥1,500/年 (~¥125/月) |
| **合計** | **~¥825/月** |

---

## 次のステップ (オプション)

- [ ] カスタムエラーページ設定
- [ ] 監視設定 (UptimeRobot等)
- [ ] 自動バックアップ設定
- [ ] CDN最適化
