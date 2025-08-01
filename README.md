# 自然言語で各種サーバを利用する＝MCPサーバー
## OpenAI Responses API × MCP（Model Context Protocol）
**Python / Docker / Docker Compose 前提での導入手順と連携例（改良版）**

> **重要:** OpenAI **Responses API** から MCP を使うには、`server_url` で到達できる **Remote MCP（HTTP / SSE）** としてサーバを公開する必要があります。`stdio` 専用の MCP はそのままでは使えません（`stdio → HTTP/SSE` ブリッジが必要）。以下は学習・検証向けの雛形です。実際のオプション・起動方法は各リポジトリの README の最新版に従ってください。
---
### 🚀 使用方法
#### 個別サービスの起動
```bash
# Redis MCP サーバーのみ起動
docker-compose -f docker-compose.redis.yml up -d

# PostgreSQL MCP サーバーのみ起動
docker-compose -f docker-compose.postgres.yml up -d
```

#### PostgreSQL MCP サーバーのみ起動
```bash
docker-compose -f docker-compose.postgres.yml up -d
統合環境の起動
bash# 全MCPサーバーを一括起動
docker-compose -f docker-compose.all-mcp.yml up -d

# 特定サービスのみ起動
docker-compose -f docker-compose.all-mcp.yml up -d redis redis-mcp
```
---

## 目次
- [共通の考え方](#共通の考え方)
- [Docker Composeを使う利点](#docker-composeを使う利点)
- [1) データベース系](#1-データベース系)
  - [Redis MCP Server](#redis-mcp-server)
  - [PostgreSQL MCP Server](#postgresql-mcp-server)
  - [Elasticsearch MCP Server](#elasticsearch-mcp-server)
  - [Qdrant MCP Server](#qdrant-mcp-server)
  - [Pinecone MCP Server](#pinecone-mcp-server)
- [2) ファイル／ドキュメント](#2-ファイルドキュメント)
  - [Filesystem MCP Server](#filesystem-mcp-server)
  - [Notion MCP Server](#notion-mcp-server)
- [3) 開発／リポジトリ](#3-開発リポジトリ)
  - [GitHub MCP Server](#github-mcp-server)
- [4) Web／検索](#4-web検索)
  - [Web Search MCP](#web-search-mcp)
- [5) クラウド／インフラ](#5-クラウドインフラ)
  - [Pulumi MCP Server](#pulumi-mcp-server)
- [統合環境の構築](#統合環境の構築)
- [Remote MCP を Responses API から使う際のポイント](#remote-mcp-を-responses-api-から使う際のポイント)
- [`stdio → HTTP/SSE` 変換（mcp-proxy）](#stdio--httpsse-変換mcp-proxy)
- [FastMCP での HTTP 公開（Python 自作向け）](#fastmcp-での-http-公開python-自作向け)
- [Responses API — 最小コード例](#responses-api--最小コード例)
- [備考](#備考)

---

## 共通の考え方
- **Remote MCP（HTTP / SSE）を用意**し、**公開 URL** を `server_url` に設定します。
- 認証が必要な MCP は、**ヘッダ**（例: `Authorization`）を Responses API の `headers` で付与できます。
- **`allowed_tools`** で使用ツールを絞ると安全・安定（最小権限）。
- ローカル検証のみなら `http://127.0.0.1:<port>/mcp` で十分。外部公開は ngrok / Cloudflare Tunnel / リバースプロキシ等を利用。

## Docker Composeを使う利点

- **🐳 統合管理**: 複数のMCPサーバーを一括で起動・停止
- **📝 設定の一元化**: 環境変数とネットワーク設定を1ファイルで管理
- **🔄 再現性**: チーム全体で同じ環境を簡単に再現
- **🌐 ネットワーク**: サービス間の通信が自動的に設定
- **📋 依存関係**: サービス起動順序の制御が可能

---

## 1) データベース系

### Redis MCP Server
- **URL**: https://github.com/redis/mcp-redis
- **概要**: Redis キー／集合／ストリーム／ベクターなどを操作。

**Python（uvx）起動例**
```bash
pip install uv
uvx --from git+https://github.com/redis/mcp-redis.git \
    redis-mcp-server --url redis://localhost:6379/0
```

**Docker単体起動例**
```bash
git clone https://github.com/redis/mcp-redis.git
cd mcp-redis
docker build -t redis-mcp .
docker run --rm -p 8000:8000 \
  -e REDIS_URL=redis://host.docker.internal:6379/0 \
  redis-mcp
# 公開URL（例）: http://localhost:8000/mcp
```

**Docker Compose 構成**
```yaml
# docker-compose.redis.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  redis-mcp:
    build:
      context: https://github.com/redis/mcp-redis.git
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped

volumes:
  redis_data:

networks:
  default:
    name: mcp-network
```

**起動方法**
```bash
# Redis + Redis MCP サーバーを起動
docker-compose -f docker-compose.redis.yml up -d

# ログ確認
docker-compose -f docker-compose.redis.yml logs -f redis-mcp

# 停止
docker-compose -f docker-compose.redis.yml down
```

**Responses API（Python）**
```python
from openai import OpenAI
client = OpenAI()

resp = client.responses.create(
  model="gpt-4.1",
  tools=[{
    "type": "mcp",
    "server_label": "redis",
    "server_url": "http://localhost:8000/mcp",
    # "allowed_tools": ["redis-get", "redis-set"],
    "require_approval": "never"
  }],
  input="Redis にセッションを保存してから取得して。"
)
print(resp.output_text)
```

### PostgreSQL MCP Server
- **URL**: https://github.com/HenkDz/postgresql-mcp-server
- **概要**: PostgreSQL のスキーマ参照、CRUD、パフォーマンス分析など。

**Node / npx単体起動**
```bash
npx @henkey/postgres-mcp-server \
    --connection-string "postgresql://user:pass@localhost:5432/db"
```

**Docker Compose 構成**
```yaml
# docker-compose.postgres.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=testdb
      - POSTGRES_USER=testuser
      - POSTGRES_PASSWORD=testpass
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U testuser -d testdb"]
      interval: 10s
      timeout: 5s
      retries: 5

  postgres-mcp:
    build:
      context: https://github.com/HenkDz/postgresql-mcp-server.git
      dockerfile: Dockerfile
    ports:
      - "8001:8000"
    environment:
      - PG_CONN_STR=postgresql://testuser:testpass@postgres:5432/testdb
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

volumes:
  postgres_data:
```

**起動方法**
```bash
# PostgreSQL + PostgreSQL MCP サーバーを起動
docker-compose -f docker-compose.postgres.yml up -d

# データベース接続確認
docker-compose -f docker-compose.postgres.yml exec postgres psql -U testuser -d testdb -c "\l"
```

**Responses API（Python）**
```python
tools=[{
  "type": "mcp",
  "server_label": "postgres",
  "server_url": "http://localhost:8001/mcp",
  # "allowed_tools": ["execute-sql","schema-management"],
  "require_approval": "never"
}]
```

### Elasticsearch MCP Server
- **URL**: https://github.com/elastic/mcp-server-elasticsearch
- **概要**: Elasticsearch インデックスの検索・操作（実験的）。

**Docker Compose 構成**
```yaml
# docker-compose.elasticsearch.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    ports:
      - "9200:9200"
      - "9300:9300"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5

  es-mcp:
    build:
      context: https://github.com/elastic/mcp-server-elasticsearch.git
      dockerfile: Dockerfile
    ports:
      - "8002:8000"
    environment:
      - ELASTIC_URL=http://elasticsearch:9200
      # - ELASTIC_API_KEY=your-api-key  # 必要に応じて
    depends_on:
      elasticsearch:
        condition: service_healthy
    restart: unless-stopped

volumes:
  es_data:
```

**起動方法**
```bash
docker-compose -f docker-compose.elasticsearch.yml up -d

# Elasticsearch ヘルスチェック
curl http://localhost:9200/_cluster/health
```

### Qdrant MCP Server
- **URL**: https://github.com/qdrant/mcp-server-qdrant
- **概要**: Qdrant をメモリ／検索レイヤーとして活用。

**Docker Compose 構成**
```yaml
# docker-compose.qdrant.yml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:6333/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  qdrant-mcp:
    build:
      context: https://github.com/qdrant/mcp-server-qdrant.git
      dockerfile: Dockerfile
    ports:
      - "8003:8000"
    environment:
      - QDRANT_URL=http://qdrant:6333
      # - QDRANT_API_KEY=your-api-key  # 必要に応じて
    depends_on:
      qdrant:
        condition: service_healthy
    restart: unless-stopped

volumes:
  qdrant_data:
```

### Pinecone MCP Server
- **URL**: https://github.com/pinecone-io/pinecone-mcp
- **概要**: Pinecone のインデックス操作・検索など（Node 実装）。

**Docker Compose 構成**
```yaml
# docker-compose.pinecone.yml
version: '3.8'

services:
  pinecone-mcp:
    image: node:18-alpine
    ports:
      - "8004:8000"
    environment:
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - PORT=8000
    command: |
      sh -c "
        npm install -g @pinecone-database/mcp &&
        npx @pinecone-database/mcp --port 8000 --host 0.0.0.0
      "
    restart: unless-stopped
```

**環境変数ファイル（.env）**
```bash
# .env
PINECONE_API_KEY=your-pinecone-api-key-here
```

**起動方法**
```bash
# .envファイルを作成してAPIキーを設定
echo "PINECONE_API_KEY=your-actual-api-key" > .env

docker-compose -f docker-compose.pinecone.yml --env-file .env up -d
```

## 2) ファイル／ドキュメント

### Filesystem MCP Server
- **URL**: npm パッケージ @modelcontextprotocol/server-filesystem
- **概要**: 指定ディレクトリのファイル読み書き・検索など。

**Docker Compose 構成**
```yaml
# docker-compose.filesystem.yml
version: '3.8'

services:
  filesystem-mcp:
    image: node:18-alpine
    ports:
      - "8005:8000"
    volumes:
      - ./workspace:/workspace:ro  # 読み取り専用でマウント
      - ./data:/data              # 読み書き可能
    environment:
      - PORT=8000
    command: |
      sh -c "
        npm install -g @modelcontextprotocol/server-filesystem &&
        npx @modelcontextprotocol/server-filesystem /workspace /data --port 8000 --host 0.0.0.0
      "
    restart: unless-stopped

volumes:
  workspace_data:
  mcp_data:
```

**起動前準備**
```bash
# 作業ディレクトリを作成
mkdir -p workspace data

# サンプルファイルを配置
echo "Hello MCP!" > workspace/sample.txt
echo "Data file" > data/data.txt
```

### Notion MCP Server
- **URL**: https://github.com/makenotion/notion-mcp-server
- **概要**: Notion との連携（OAuth / トークン）。

**Docker Compose 構成**
```yaml
# docker-compose.notion.yml
version: '3.8'

services:
  notion-mcp:
    image: node:18-alpine
    ports:
      - "8006:8000"
    environment:
      - NOTION_TOKEN=${NOTION_TOKEN}
      - PORT=8000
    command: |
      sh -c "
        npm install -g @notionhq/notion-mcp-server &&
        npx @notionhq/notion-mcp-server --port 8000 --host 0.0.0.0
      "
    restart: unless-stopped
```

## 3) 開発／リポジトリ

### GitHub MCP Server
- **URL**: https://github.com/github/github-mcp-server
- **概要**: リポジトリ参照、Issue/PR 操作、ワークフローなど。

**Docker Compose 構成（自前ホスト版）**
```yaml
# docker-compose.github.yml
version: '3.8'

services:
  github-mcp:
    build:
      context: https://github.com/github/github-mcp-server.git
      dockerfile: Dockerfile
    ports:
      - "8007:8000"
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - PORT=8000
    restart: unless-stopped
```

**Hosted を直接利用する例（Responses API）**
```python
tools=[{
  "type": "mcp",
  "server_label": "github",
  "server_url": "https://api.githubcopilot.com/mcp/",
  "headers": {"Authorization": "Bearer <YOUR_GITHUB_PAT>"},
  "require_approval": "never"
}]
```

## 4) Web／検索

### Web Search MCP
- **URL**: https://github.com/pskill9/web-search
- **概要**: 簡易 Web 検索 MCP（Node 実装）。

**Docker Compose 構成**
```yaml
# docker-compose.websearch.yml
version: '3.8'

services:
  websearch-mcp:
    build:
      context: https://github.com/pskill9/web-search.git
      dockerfile: Dockerfile
    ports:
      - "8008:8000"
    environment:
      - PORT=8000
      # 検索エンジンAPIキーなど（必要に応じて）
      - SEARCH_API_KEY=${SEARCH_API_KEY}
    restart: unless-stopped
```

## 5) クラウド／インフラ

### Pulumi MCP Server
- **URL**: https://github.com/pulumi/mcp-server
- **概要**: Pulumi の情報取得／プレビュー／デプロイなど。

**Docker Compose 構成**
```yaml
# docker-compose.pulumi.yml
version: '3.8'

services:
  pulumi-mcp:
    build:
      context: https://github.com/pulumi/mcp-server.git
      dockerfile: Dockerfile
    ports:
      - "8009:8000"
    environment:
      - PULUMI_ACCESS_TOKEN=${PULUMI_ACCESS_TOKEN}
      - PORT=8000
    volumes:
      - ~/.pulumi:/root/.pulumi:ro  # Pulumi設定をマウント
    restart: unless-stopped
```

## 統合環境の構築

**全MCPサーバーを一括管理するCompose構成**

```yaml
# docker-compose.all-mcp.yml
version: '3.8'

services:
  # データベース系
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: [redis_data:/data]
    command: redis-server --appendonly yes

  postgres:
    image: postgres:15-alpine
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: testdb
      POSTGRES_USER: testuser
      POSTGRES_PASSWORD: testpass
    volumes: [postgres_data:/var/lib/postgresql/data]

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    ports: ["9200:9200"]
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes: [es_data:/usr/share/elasticsearch/data]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: [qdrant_data:/qdrant/storage]

  # MCP サーバー群
  redis-mcp:
    build: https://github.com/redis/mcp-redis.git
    ports: ["8000:8000"]
    environment: [REDIS_URL=redis://redis:6379/0]
    depends_on: [redis]

  postgres-mcp:
    build: https://github.com/HenkDz/postgresql-mcp-server.git
    ports: ["8001:8000"]
    environment: [PG_CONN_STR=postgresql://testuser:testpass@postgres:5432/testdb]
    depends_on: [postgres]

  es-mcp:
    build: https://github.com/elastic/mcp-server-elasticsearch.git
    ports: ["8002:8000"]
    environment: [ELASTIC_URL=http://elasticsearch:9200]
    depends_on: [elasticsearch]

  qdrant-mcp:
    build: https://github.com/qdrant/mcp-server-qdrant.git
    ports: ["8003:8000"]
    environment: [QDRANT_URL=http://qdrant:6333]
    depends_on: [qdrant]

  # 外部API系
  pinecone-mcp:
    image: node:18-alpine
    ports: ["8004:8000"]
    environment: [PINECONE_API_KEY=${PINECONE_API_KEY}]
    command: sh -c "npm i -g @pinecone-database/mcp && npx @pinecone-database/mcp --port 8000 --host 0.0.0.0"

  websearch-mcp:
    build: https://github.com/pskill9/web-search.git
    ports: ["8008:8000"]

  # リバースプロキシ（オプション）
  nginx:
    image: nginx:alpine
    ports: ["80:80"]
    volumes: ["./nginx.conf:/etc/nginx/nginx.conf:ro"]
    depends_on:
      - redis-mcp
      - postgres-mcp
      - es-mcp
      - qdrant-mcp

volumes:
  redis_data:
  postgres_data:
  es_data:
  qdrant_data:

networks:
  default:
    name: mcp-network
```

**リバースプロキシ設定例（nginx.conf）**
```nginx
events {
    worker_connections 1024;
}

http {
    upstream mcp-services {
        server redis-mcp:8000;
        server postgres-mcp:8000;
        server es-mcp:8000;
        server qdrant-mcp:8000;
    }

    server {
        listen 80;

        location /redis/ {
            proxy_pass http://redis-mcp:8000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /postgres/ {
            proxy_pass http://postgres-mcp:8000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # 他のサービスも同様に設定
    }
}
```

**統合環境の起動**
```bash
# 全サービスを起動
docker-compose -f docker-compose.all-mcp.yml up -d

# 特定のサービスのみ起動
docker-compose -f docker-compose.all-mcp.yml up -d redis redis-mcp

# サービスのスケーリング
docker-compose -f docker-compose.all-mcp.yml up -d --scale websearch-mcp=3

# ログ監視
docker-compose -f docker-compose.all-mcp.yml logs -f

# 停止・クリーンアップ
docker-compose -f docker-compose.all-mcp.yml down -v
```

---

## Remote MCP を Responses API から使う際のポイント
- **server_url は必須**：HTTP / SSE の公開 URL を指定。必要に応じて headers で認証情報を付与。
- **allowed_tools で最小権限**：必要なツールのみ許可し、行動空間・リスク・コストを抑制。
- **require_approval の運用**："never"（自動実行）/"always"（都度承認）/"auto" など、用途に応じて選択。
- **stdio サーバはブリッジが必要**：stdio のみの MCP は、そのままでは使えません。mcp-proxy 等で HTTP/SSE に 変換（下記参照）。

## `stdio → HTTP/SSE` 変換（mcp-proxy）

**インストール例**
```bash
pip install uv
uv tool install git+https://github.com/sparfenyuk/mcp-proxy
```

**起動例（Node 系 MCP を HTTP 化して公開）**
```bash
mcp-proxy --port 8000 --host 0.0.0.0 -- \
  npx -y @pinecone-database/mcp
# 公開URL（実装により /mcp または /sse）:
#   http://<host>:8000/mcp   あるいは   http://<host>:8000/sse
```

**Docker Compose での mcp-proxy 利用例**
```yaml
# docker-compose.mcp-proxy.yml
version: '3.8'

services:
  mcp-proxy:
    image: python:3.11-slim
    ports:
      - "8010:8000"
    command: |
      sh -c "
        pip install uv &&
        uv tool install git+https://github.com/sparfenyuk/mcp-proxy &&
        mcp-proxy --port 8000 --host 0.0.0.0 -- npx -y @pinecone-database/mcp
      "
    restart: unless-stopped
```

## FastMCP での HTTP 公開（Python 自作向け）

自作 MCP を Streamable HTTP として即時公開したい場合の最小例：

```python
# server.py
from fastmcp import FastMCP

mcp = FastMCP("demo")

@mcp.tool
def add(a: int, b: int) -> int:
    return a + b

# デフォルト: 127.0.0.1:8000/mcp を公開
mcp.run(transport="http")
```

**Docker Compose での FastMCP 利用例**
```yaml
# docker-compose.fastmcp.yml
version: '3.8'

services:
  fastmcp-demo:
    image: python:3.11-slim
    ports:
      - "8011:8000"
    volumes:
      - ./server.py:/app/server.py
    working_dir: /app
    command: |
      sh -c "
        pip install fastmcp &&
        python server.py
      "
    restart: unless-stopped
```

**起動**
```bash
pip install fastmcp
python server.py
# 公開URL: http://127.0.0.1:8000/mcp
```

## Responses API — 最小コード例

```python
from openai import OpenAI
client = OpenAI()

resp = client.responses.create(
    model="gpt-4.1",
    tools=[{
        "type": "mcp",
        "server_label": "my-remote-mcp",
        "server_url": "http://localhost:8000/mcp",
        # "headers": {"Authorization": "Bearer <TOKEN>"},
        # "allowed_tools": ["tool_a","tool_b"],
        "require_approval": "never"
    }],
    input="MCP 経由のツールで処理して。"
)
print(resp.output_text)
```

**複数MCPサーバーを同時利用する例**
```python
from openai import OpenAI
client = OpenAI()

resp = client.responses.create(
    model="gpt-4.1",
    tools=[
        {
            "type": "mcp",
            "server_label": "redis",
            "server_url": "http://localhost:8000/mcp",
            "allowed_tools": ["redis-get", "redis-set"],
            "require_approval": "never"
        },
        {
            "type": "mcp",
            "server_label": "postgres",
            "server_url": "http://localhost:8001/mcp",
            "allowed_tools": ["execute-sql"],
            "require_approval": "never"
        },
        {
            "type": "mcp",
            "server_label": "websearch",
            "server_url": "http://localhost:8008/mcp",
            "require_approval": "never"
        }
    ],
    input="Redisにデータを保存し、PostgreSQLで分析し、関連情報をWeb検索して統合レポートを作成して。"
)
print(resp.output_text)
```

## 備考

### Docker Composeの運用Tips

**環境別設定ファイルの管理**
```bash
# 開発環境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 本番環境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up

# 特定サービスのみ起動
docker-compose up redis redis-mcp
```

**ヘルスチェックとモニタリング**
```bash
# 全サービスの状態確認
docker-compose ps

# 特定サービスのログ
docker-compose logs -f redis-mcp

# リソース使用量確認
docker stats
```

**トラブルシューティング**
```bash
# サービスの再起動
docker-compose restart redis-mcp

# 設定の再読み込み
docker-compose up -d --force-recreate redis-mcp

# ボリュームを含めて完全削除
docker-compose down -v --remove-orphans
```

### セキュリティの考慮事項

1. **ネットワーク分離**: 本番環境では内部ネットワークを使用
2. **認証・認可**: APIキーやトークンは環境変数で管理
3. **最小権限**: `allowed_tools` で必要最小限のツールのみ許可
4. **監査ログ**: アクセスログとAPIコールの記録
5. **TLS暗号化**: 本番環境ではHTTPS/TLSを必須に

本資料のコマンドは **雛形** です。公開パス（/mcp or /sse）・環境変数・オプション は実装やバージョンで異なるため、各リポジトリの README に従って調整してください。

**Hosted（既に公開済み）エンドポイント** が提供されているMCPは、その URL を server_url に指定するのが最も簡単です。

**本番運用では**、TLS（HTTPS）・認可・ネットワーク制限・監査ログ を用意し、allowed_tools の最小化 を徹底してください。