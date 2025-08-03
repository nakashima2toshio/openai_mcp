## MCP サーバー テストデータ投入とStreamlitアプリ構築ガイド
#### 📋 概要
- このガイドでは、各DB系MCPサーバーにテストデータを投入し、Python StreamlitアプリでOpenAI APIを使ってアクセスする方法を説明します。
### 🛠️ 事前準備
### 1. 必要なツールのインストール
- bash# uvのインストール（Pythonパッケージ管理）
```bash
pip install uv

# プロジェクトディレクトリを作成
mkdir mcp-streamlit-demo
cd mcp-streamlit-demo

# Python環境を作成
uv init streamlit-mcp-app
cd streamlit-mcp-app
```

- 必要なパッケージをインストール
```bash
uv add streamlit openai python-dotenv pandas numpy requests redis psycopg2-binary elasticsearch qdrant-client pinecone-client
```
### 2. 環境変数の設定
- bash# .env ファイルを作成
```bash
cat > .env << 'EOF'
# OpenAI API Key
OPENAI_API_KEY=your-openai-api-key-here

# Pinecone (必要に応じて)
PINECONE_API_KEY=your-pinecone-api-key-here

# Redis設定
REDIS_URL=redis://localhost:6379/0

# PostgreSQL設定
PG_CONN_STR=postgresql://testuser:testpass@localhost:5432/testdb

# Elasticsearch設定
ELASTIC_URL=http://localhost:9200

# Qdrant設定
QDRANT_URL=http://localhost:6333
EOF
```

### 🚀 MCPサーバー群の起動
#### 1. Docker Compose設定ファイルの作成
```bash
# docker-compose.mcp-demo.yml
# version: '3.8'
#
services:
  # === データベース系 ===
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
      - ./init-data/postgres-init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U testuser -d testdb"]
      interval: 10s
      timeout: 5s
      retries: 5

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    ports:
      - "9200:9200"
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

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:6333/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # === MCP サーバー群（開発中はコメントアウト）===
  # redis-mcp:
  #   build: https://github.com/redis/mcp-redis.git
  #   ports: ["8000:8000"]
  #   environment: [REDIS_URL=redis://redis:6379/0]
  #   depends_on:
  #     redis:
  #       condition: service_healthy

  # postgres-mcp:
  #   build: https://github.com/HenkDz/postgresql-mcp-server.git
  #   ports: ["8001:8000"]
  #   environment: [PG_CONN_STR=postgresql://testuser:testpass@postgres:5432/testdb]
  #   depends_on:
  #     postgres:
  #       condition: service_healthy

volumes:
  redis_data:
  postgres_data:
  es_data:
  qdrant_data:

networks:
  default:
    name: mcp-demo-network
```

### 2. データベース起動
- bash# データベース群のみ起動（MCPサーバーは後で）
```bash
docker-compose -f docker-compose.mcp-demo.yml up -d redis postgres elasticsearch qdrant
```

- 起動確認
```bash
docker-compose -f docker-compose.mcp-demo.yml ps
```

### 📊 テストデータの準備と投入
#### 1. ディレクトリ構造の作成
```bash
bashmkdir -p init-data scripts
```
#### 2. PostgreSQL テストデータ

```sql
-- init-data/postgres-init.sql
-- 顧客テーブル
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    age INTEGER,
    city VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 注文テーブル
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    product_name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    quantity INTEGER NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 商品テーブル
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    price DECIMAL(10,2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    description TEXT
);

-- テストデータ投入
INSERT INTO customers (name, email, age, city) VALUES
('田中太郎', 'tanaka@example.com', 35, '東京'),
('佐藤花子', 'sato@example.com', 28, '大阪'),
('鈴木一郎', 'suzuki@example.com', 42, '名古屋'),
('高橋美香', 'takahashi@example.com', 31, '福岡'),
('渡辺健一', 'watanabe@example.com', 29, '札幌');

INSERT INTO products (name, category, price, stock_quantity, description) VALUES
('ノートPC', 'エレクトロニクス', 89800.00, 15, '高性能ノートパソコン'),
('ワイヤレスイヤホン', 'エレクトロニクス', 12800.00, 25, 'ノイズキャンセリング機能付き'),
('コーヒーメーカー', 'キッチン家電', 15600.00, 10, '全自動コーヒーメーカー'),
('ビジネスバッグ', 'ファッション', 8900.00, 20, 'レザー製ビジネスバッグ'),
('スニーカー', 'ファッション', 9800.00, 30, 'ランニングシューズ');

INSERT INTO orders (customer_id, product_name, price, quantity) VALUES
(1, 'ノートPC', 89800.00, 1),
(2, 'ワイヤレスイヤホン', 12800.00, 2),
(3, 'コーヒーメーカー', 15600.00, 1),
(1, 'ビジネスバッグ', 8900.00, 1),
(4, 'スニーカー', 9800.00, 1),
(5, 'ワイヤレスイヤホン', 12800.00, 1),
(2, 'コーヒーメーカー', 15600.00, 1);
```
3. テストデータ投入スクリプト
```python
# scripts/setup_test_data.py
import redis
import json
import requests
from datetime import datetime
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import os
from dotenv import load_dotenv

load_dotenv()

def setup_redis_data():
    """Redisにテストデータを投入"""
    print("🔴 Redis テストデータを投入中...")

    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    # セッションデータ
    sessions = {
        'session:user1': {'user_id': 1, 'username': 'tanaka', 'login_time': '2024-01-15 10:30:00'},
        'session:user2': {'user_id': 2, 'username': 'sato', 'login_time': '2024-01-15 11:15:00'},
        'session:user3': {'user_id': 3, 'username': 'suzuki', 'login_time': '2024-01-15 09:45:00'}
    }

    for key, data in sessions.items():
        r.hset(key, mapping=data)

    # カウンタ情報
    counters = {
        'page_views': 1250,
        'user_registrations': 89,
        'sales_today': 15,
        'active_sessions': 3
    }

    for key, value in counters.items():
        r.set(f'counter:{key}', value)

    # 商品カテゴリ（セット）
    categories = ['エレクトロニクス', 'キッチン家電', 'ファッション', 'スポーツ', '本・メディア']
    for category in categories:
        r.sadd('categories:all', category)

    # 最近の検索履歴（リスト）
    search_terms = ['ノートPC', 'コーヒーメーカー', 'ワイヤレスイヤホン', 'ビジネスバッグ', 'スニーカー']
    for term in search_terms:
        r.lpush('search:recent', term)

    # JSON形式のユーザープロファイル
    user_profiles = {
        'profile:1': {
            'name': '田中太郎',
            'preferences': ['エレクトロニクス', 'ガジェット'],
            'purchase_history': [{'product': 'ノートPC', 'date': '2024-01-10'}]
        },
        'profile:2': {
            'name': '佐藤花子',
            'preferences': ['キッチン家電', 'ファッション'],
            'purchase_history': [{'product': 'ワイヤレスイヤホン', 'date': '2024-01-12'}]
        }
    }

    for key, profile in user_profiles.items():
        r.set(key, json.dumps(profile, ensure_ascii=False))

    print("✅ Redis テストデータ投入完了!")
    return True

def setup_elasticsearch_data():
    """Elasticsearchにテストデータを投入"""
    print("🟡 Elasticsearch テストデータを投入中...")

    es_url = "http://localhost:9200"

    # インデックス作成
    index_mapping = {
        "mappings": {
            "properties": {
                "title": {"type": "text", "analyzer": "standard"},
                "content": {"type": "text", "analyzer": "standard"},
                "category": {"type": "keyword"},
                "author": {"type": "keyword"},
                "published_date": {"type": "date"},
                "tags": {"type": "keyword"},
                "view_count": {"type": "integer"}
            }
        }
    }

    # インデックス作成
    requests.put(f"{es_url}/blog_articles", json=index_mapping)

    # テストドキュメント
    articles = [
        {
            "title": "Python機械学習入門",
            "content": "Pythonを使った機械学習の基礎について説明します。scikit-learnやpandasを使って実際にデータ分析を行ってみましょう。",
            "category": "技術",
            "author": "山田太郎",
            "published_date": "2024-01-15",
            "tags": ["Python", "機械学習", "データサイエンス"],
            "view_count": 1250
        },
        {
            "title": "Dockerコンテナ活用術",
            "content": "Dockerを使ったアプリケーション開発とデプロイメントの実践的な方法を紹介します。Docker Composeも含めて解説。",
            "category": "技術",
            "author": "鈴木花子",
            "published_date": "2024-01-12",
            "tags": ["Docker", "DevOps", "コンテナ"],
            "view_count": 980
        },
        {
            "title": "リモートワークの効率化",
            "content": "在宅勤務で生産性を向上させるための具体的な方法とツールを紹介します。コミュニケーション改善のコツも。",
            "category": "ビジネス",
            "author": "田中一郎",
            "published_date": "2024-01-10",
            "tags": ["リモートワーク", "生産性", "働き方改革"],
            "view_count": 1580
        },
        {
            "title": "Streamlit Web アプリ開発",
            "content": "StreamlitでインタラクティブなWebアプリケーションを作成する方法を実例とともに解説します。",
            "category": "技術",
            "author": "佐藤美香",
            "published_date": "2024-01-08",
            "tags": ["Streamlit", "Python", "Webアプリ"],
            "view_count": 750
        },
        {
            "title": "AI活用ビジネス事例",
            "content": "企業でのAI導入成功事例と失敗事例を分析し、効果的なAI活用のポイントを解説します。",
            "category": "ビジネス",
            "author": "高橋健太",
            "published_date": "2024-01-05",
            "tags": ["AI", "DX", "ビジネス戦略"],
            "view_count": 2100
        }
    ]

    # ドキュメント投入
    for i, article in enumerate(articles, 1):
        requests.post(f"{es_url}/blog_articles/_doc/{i}", json=article)

    # インデックス更新を待つ
    requests.post(f"{es_url}/blog_articles/_refresh")

    print("✅ Elasticsearch テストデータ投入完了!")
    return True

def setup_qdrant_data():
    """Qdrantにベクトルデータを投入"""
    print("🟠 Qdrant テストデータを投入中...")

    client = QdrantClient("localhost", port=6333)

    # コレクション作成
    collection_name = "product_embeddings"

    try:
        client.delete_collection(collection_name=collection_name)
    except:
        pass

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

    # 商品ベクトル（実際は事前計算済みの埋め込みベクトルを使用）
    # ここではサンプルとしてランダムベクトルを使用
    products = [
        {
            "id": 1,
            "name": "高性能ノートPC",
            "category": "エレクトロニクス",
            "description": "プログラミングやデザイン作業に最適な高性能ノートパソコン",
            "price": 89800,
            "vector": np.random.rand(384).tolist()
        },
        {
            "id": 2,
            "name": "ワイヤレスイヤホン",
            "category": "エレクトロニクス",
            "description": "ノイズキャンセリング機能付きの高音質ワイヤレスイヤホン",
            "price": 12800,
            "vector": np.random.rand(384).tolist()
        },
        {
            "id": 3,
            "name": "全自動コーヒーメーカー",
            "category": "キッチン家電",
            "description": "豆から挽ける全自動タイプのコーヒーメーカー",
            "price": 15600,
            "vector": np.random.rand(384).tolist()
        },
        {
            "id": 4,
            "name": "レザービジネスバッグ",
            "category": "ファッション",
            "description": "本革製の高級ビジネスバッグ、ノートPCも収納可能",
            "price": 8900,
            "vector": np.random.rand(384).tolist()
        },
        {
            "id": 5,
            "name": "ランニングシューズ",
            "category": "スポーツ",
            "description": "軽量で通気性の良いランニング専用シューズ",
            "price": 9800,
            "vector": np.random.rand(384).tolist()
        }
    ]

    # ポイント投入
    points = []
    for product in products:
        points.append(
            PointStruct(
                id=product["id"],
                vector=product["vector"],
                payload={
                    "name": product["name"],
                    "category": product["category"],
                    "description": product["description"],
                    "price": product["price"]
                }
            )
        )

    client.upsert(
        collection_name=collection_name,
        points=points
    )

    print("✅ Qdrant テストデータ投入完了!")
    return True

def main():
    """全てのテストデータを投入"""
    print("🚀 MCP テストデータ投入を開始します...\n")

    try:
        setup_redis_data()
        setup_elasticsearch_data()
        setup_qdrant_data()

        print("\n🎉 全てのテストデータ投入が完了しました!")
        print("\n📊 投入されたデータ:")
        print("- Redis: セッション、カウンタ、カテゴリ、検索履歴、ユーザープロファイル")
        print("- PostgreSQL: 顧客、注文、商品データ")
        print("- Elasticsearch: ブログ記事5件")
        print("- Qdrant: 商品ベクトル5件")

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return False

    return True

if __name__ == "__main__":
    main()
```
4. テストデータ投入の実行
```bash
# テストデータ投入スクリプトを実行
uv run python scripts/setup_test_data.py

# データベース接続確認
# PostgreSQL
docker-compose -f docker-compose.mcp-demo.yml exec postgres psql -U testuser -d testdb -c "SELECT * FROM customers;"

# Redis
docker-compose -f docker-compose.mcp-demo.yml exec redis redis-cli KEYS "*"

# Elasticsearch
curl "http://localhost:9200/blog_articles/_search?pretty"

# Qdrant
curl "http://localhost:6333/collections/product_embeddings/points?limit=5"
```

### 🖥️ Streamlitアプリケーションの作成
1. メインアプリケーション
```python
# app.py
import streamlit as st
import openai
import os
import json
import pandas as pd
from dotenv import load_dotenv
import redis
import psycopg2
import requests
from datetime import datetime

# 環境変数を読み込み
load_dotenv()

# OpenAI APIキーの設定
openai.api_key = os.getenv('OPENAI_API_KEY')
client = openai.OpenAI()

# Streamlitページ設定
st.set_page_config(
    page_title="MCP サーバー デモ",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 MCP サーバー × OpenAI API デモ")
st.markdown("---")

# サイドバーでMCPサーバーの状態確認
st.sidebar.header("📊 MCP サーバー状態")

def check_server_status():
    """各サーバーの状態をチェック"""
    status = {}

    # Redis
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        status['Redis'] = "🟢 接続OK"
    except:
        status['Redis'] = "🔴 接続NG"

    # PostgreSQL
    try:
        conn = psycopg2.connect(os.getenv('PG_CONN_STR'))
        conn.close()
        status['PostgreSQL'] = "🟢 接続OK"
    except:
        status['PostgreSQL'] = "🔴 接続NG"

    # Elasticsearch
    try:
        response = requests.get('http://localhost:9200/_cluster/health', timeout=5)
        if response.status_code == 200:
            status['Elasticsearch'] = "🟢 接続OK"
        else:
            status['Elasticsearch'] = "🔴 接続NG"
    except:
        status['Elasticsearch'] = "🔴 接続NG"

    # Qdrant
    try:
        response = requests.get('http://localhost:6333/health', timeout=5)
        if response.status_code == 200:
            status['Qdrant'] = "🟢 接続OK"
        else:
            status['Qdrant'] = "🔴 接続NG"
    except:
        status['Qdrant'] = "🔴 接続NG"

    return status

# サーバー状態表示
status = check_server_status()
for server, state in status.items():
    st.sidebar.text(f"{server}: {state}")

# メインコンテンツ
tab1, tab2, tab3, tab4 = st.tabs(["🔍 データ確認", "🤖 AI チャット", "📊 直接クエリ", "⚙️ 設定"])

with tab1:
    st.header("📊 投入されたテストデータの確認")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔴 Redis データ")
        if st.button("Redis データを表示"):
            try:
                r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

                # セッションデータ
                st.write("**セッションデータ:**")
                session_keys = r.keys('session:*')
                session_data = []
                for key in session_keys:
                    data = r.hgetall(key)
                    data['key'] = key
                    session_data.append(data)
                if session_data:
                    st.dataframe(pd.DataFrame(session_data))

                # カウンタデータ
                st.write("**カウンタ:**")
                counter_keys = r.keys('counter:*')
                counter_data = {}
                for key in counter_keys:
                    counter_data[key] = r.get(key)
                if counter_data:
                    st.json(counter_data)

            except Exception as e:
                st.error(f"Redis接続エラー: {e}")

    with col2:
        st.subheader("🟦 PostgreSQL データ")
        if st.button("PostgreSQL データを表示"):
            try:
                conn = psycopg2.connect(os.getenv('PG_CONN_STR'))

                # 顧客データ
                st.write("**顧客データ:**")
                df_customers = pd.read_sql("SELECT * FROM customers LIMIT 10", conn)
                st.dataframe(df_customers)

                # 注文データ
                st.write("**注文データ:**")
                df_orders = pd.read_sql("SELECT * FROM orders LIMIT 10", conn)
                st.dataframe(df_orders)

                conn.close()
            except Exception as e:
                st.error(f"PostgreSQL接続エラー: {e}")

    # Elasticsearch と Qdrant
    st.subheader("🟡 Elasticsearch データ")
    if st.button("Elasticsearch データを表示"):
        try:
            response = requests.get('http://localhost:9200/blog_articles/_search?size=10')
            if response.status_code == 200:
                data = response.json()
                articles = []
                for hit in data['hits']['hits']:
                    article = hit['_source']
                    article['_id'] = hit['_id']
                    articles.append(article)

                if articles:
                    df_articles = pd.DataFrame(articles)
                    st.dataframe(df_articles)
            else:
                st.error("Elasticsearch データの取得に失敗しました")
        except Exception as e:
            st.error(f"Elasticsearch接続エラー: {e}")

    st.subheader("🟠 Qdrant データ")
    if st.button("Qdrant データを表示"):
        try:
            response = requests.get('http://localhost:6333/collections/product_embeddings/points?limit=10')
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and 'points' in data['result']:
                    products = []
                    for point in data['result']['points']:
                        product = point['payload']
                        product['id'] = point['id']
                        products.append(product)

                    if products:
                        df_products = pd.DataFrame(products)
                        st.dataframe(df_products)
        except Exception as e:
            st.error(f"Qdrant接続エラー: {e}")

with tab2:
    st.header("🤖 AI アシスタント（MCP経由）")
    st.info("⚠️ 注意: この機能は実際のMCPサーバーが稼働している必要があります")

    # チャット履歴
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # チャット履歴表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # チャット入力
    if prompt := st.chat_input("何か質問してください（例：Redisのセッション数を教えて）"):
        # ユーザーメッセージを追加
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # AI応答（MCPサーバーが稼働していない場合のフォールバック）
        with st.chat_message("assistant"):
            response_placeholder = st.empty()

            try:
                # 実際のMCP呼び出し（サーバーが稼働している場合）
                # ここではダミーレスポンスを返す
                response_text = f"""
申し訳ございませんが、現在MCPサーバーが稼働していないため、
直接的なデータベースアクセスができません。

代わりに、以下の情報をお伝えします：
- 質問内容: {prompt}
- 利用可能なデータ: Redis、PostgreSQL、Elasticsearch、Qdrantにテストデータを投入済み
- 次のステップ: MCPサーバーを起動してから再度お試しください

MCPサーバー起動コマンド:
```bash
# 個別起動の例
docker-compose -f docker-compose.mcp-demo.yml up -d redis-mcp postgres-mcp
            """

            response_placeholder.write(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})

        except Exception as e:
            error_msg = f"エラーが発生しました: {e}"
            response_placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
with tab3:
st.header("📊 直接データベースクエリ")
query_type = st.selectbox("クエリタイプを選択",
                         ["Redis", "PostgreSQL", "Elasticsearch", "Qdrant"])

if query_type == "Redis":
    st.subheader("🔴 Redis クエリ")
    redis_command = st.text_input("Redisコマンド", "KEYS *")

    if st.button("実行", key="redis_exec"):
        try:
            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            # 簡単なコマンドのみサポート
            if redis_command.startswith("KEYS"):
                result = r.keys(redis_command.split(" ", 1)[1] if " " in redis_command else "*")
            elif redis_command.startswith("GET"):
                key = redis_command.split(" ", 1)[1]
                result = r.get(key)
            else:
                result = "サポートされていないコマンドです"

            st.code(str(result))
        except Exception as e:
            st.error(f"エラー: {e}")

elif query_type == "PostgreSQL":
    st.subheader("🟦 PostgreSQL クエリ")
    sql_query = st.text_area("SQLクエリ", "SELECT * FROM customers LIMIT 5;")

    if st.button("実行", key="pg_exec"):
        try:
            conn = psycopg2.connect(os.getenv('PG_CONN_STR'))
            df = pd.read_sql(sql_query, conn)
            st.dataframe(df)
            conn.close()
        except Exception as e:
            st.error(f"エラー: {e}")
with tab4:
st.header("⚙️ 設定")
st.subheader("🔧 MCPサーバー起動")
st.code("""

#### MCPサーバー群を起動
```bash
docker-compose -f docker-compose.mcp-demo.yml up -d redis-mcp postgres-mcp
全サービス確認
docker-compose -f docker-compose.mcp-demo.yml ps
ログ確認
docker-compose -f docker-compose.mcp-demo.yml logs -f redis-mcp
""")
st.subheader("🌐 API エンドポイント")
st.write("MCPサーバーが起動したら以下のエンドポイントが利用可能:")
st.json({
    "Redis MCP": "http://localhost:8000/mcp",
    "PostgreSQL MCP": "http://localhost:8001/mcp",
    "Elasticsearch MCP": "http://localhost:8002/mcp",
    "Qdrant MCP": "http://localhost:8003/mcp"
})

st.subheader("🔑 環境変数")
env_vars = {
    "OPENAI_API_KEY": "設定済み" if os.getenv('OPENAI_API_KEY') else "未設定",
    "REDIS_URL": os.getenv('REDIS_URL', '未設定'),
    "PG_CONN_STR": "設定済み" if os.getenv('PG_CONN_STR') else "未設定"
}
st.json(env_vars)
フッター
st.markdown("---")
st.markdown("🚀 MCP Demo App - OpenAI API × MCP サーバー連携のデモンストレーション")
```

### 2. アプリケーション起動

```bash
# Streamlitアプリを起動
uv run streamlit run app.py

# ブラウザで http://localhost:8501 にアクセス
🎯 実行手順まとめ
1. 環境セットアップ
bash# プロジェクト作成
mkdir mcp-streamlit-demo && cd mcp-streamlit-demo
uv init streamlit-mcp-app && cd streamlit-mcp-app

# パッケージインストール
uv add streamlit openai python-dotenv pandas numpy requests redis psycopg2-binary elasticsearch qdrant-client

# 環境変数設定（.envファイル作成）
# OPENAI_API_KEY を実際のキーに設定
2. データベース起動
bash# Docker Compose設定をコピーして配置
# データベース群を起動
docker-compose -f docker-compose.mcp-demo.yml up -d redis postgres elasticsearch qdrant

# 起動確認
docker-compose -f docker-compose.mcp-demo.yml ps
3. テストデータ投入
bash# スクリプトファイルを作成・配置
# テストデータ投入実行
uv run python scripts/setup_test_data.py
4. Streamlitアプリ起動
bash# アプリファイルを作成・配置
# アプリ起動
uv run streamlit run app.py
5. MCPサーバー起動（オプション）
bash# 実際のMCP機能を使用したい場合
docker-compose -f docker-compose.mcp-demo.yml up -d redis-mcp postgres-mcp es-mcp qdrant-mcp
🎉 完成！
これで、各種データベースにテストデータが投入され、Streamlitアプリで確認・操作できる環境が整いました。
次のステップ:

MCPサーバーを実際に起動してOpenAI APIとの連携をテスト
より複雑なクエリや分析機能を追加
リアルタイムデータ更新機能の実装
ユーザー認証機能の追加