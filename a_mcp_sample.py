# streamlit run a_mcp_sample.py --server.port=8501
import streamlit as st
import openai
import os
import json
import pandas as pd
from dotenv import load_dotenv
import redis
import psycopg2
import sqlalchemy  # ←追加：SQLAlchemy インポート
import requests
from datetime import datetime
import time
import traceback

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

st.markdown("<h5>🤖 MCP サーバー × OpenAI API デモ</h5>", unsafe_allow_html=True)
st.markdown("---")

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-good {
        color: #28a745;
        font-weight: bold;
    }
    .status-bad {
        color: #dc3545;
        font-weight: bold;
    }
    .info-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #17a2b8;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# サイドバーでMCPサーバーの状態確認
st.sidebar.header("📊 MCP サーバー状態")


@st.cache_data(ttl=30)  # 30秒キャッシュ
def check_server_status():
    """各サーバーの状態をチェック"""
    status = {}

    # Redis
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=3)
        r.ping()
        status['Redis'] = "🟢 接続OK"
    except Exception as e:
        status['Redis'] = f"🔴 接続NG ({str(e)[:20]}...)"

    # PostgreSQL
    try:
        conn = psycopg2.connect(
            os.getenv('PG_CONN_STR'),
            connect_timeout=3
        )
        conn.close()
        status['PostgreSQL'] = "🟢 接続OK"
    except Exception as e:
        status['PostgreSQL'] = f"🔴 接続NG ({str(e)[:20]}...)"

    # Elasticsearch
    try:
        response = requests.get('http://localhost:9200/_cluster/health', timeout=3)
        if response.status_code == 200:
            status['Elasticsearch'] = "🟢 接続OK"
        else:
            status['Elasticsearch'] = f"🔴 接続NG (Status: {response.status_code})"
    except Exception as e:
        status['Elasticsearch'] = f"🔴 接続NG ({str(e)[:20]}...)"

    # Qdrant
    try:
        response = requests.get('http://localhost:6333/', timeout=3)
        if response.status_code == 200:
            status['Qdrant'] = "🟢 接続OK"
        else:
            status['Qdrant'] = f"🔴 接続NG (Status: {response.status_code})"
    except Exception as e:
        status['Qdrant'] = f"🔴 接続NG ({str(e)[:20]}...)"

    return status


# Redis キー数取得関数（修正版）
@st.cache_data(ttl=60)  # 1分キャッシュ
def get_redis_key_count():
    """Redisキー数を安全に取得"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=3)
        r.ping()
        # scan_iterを使用してメモリ効率良くキー数を取得
        count = 0
        for _ in r.scan_iter():
            count += 1
            if count > 1000:  # 安全のため1000で制限
                return f"{count}+"
        return str(count)
    except Exception:
        return "?"


# サーバー状態表示
if st.sidebar.button("🔄 状態更新"):
    st.cache_data.clear()

status = check_server_status()
for server, state in status.items():
    st.sidebar.markdown(f"**{server}**: {state}")

# 接続中のサーバー数を表示
connected_servers = sum(1 for s in status.values() if "🟢" in s)
st.sidebar.markdown(f"**接続済み**: {connected_servers}/4 サーバー")

# サイドバーにクイックアクション
st.sidebar.markdown("---")
st.sidebar.header("⚡ クイックアクション")

if st.sidebar.button("🚀 Docker起動"):
    st.sidebar.code("docker-compose -f docker-compose.mcp-demo.yml up -d")

if st.sidebar.button("📊 データ再投入"):
    st.sidebar.code("uv run python scripts/setup_test_data.py")

# メインコンテンツ
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 データ確認",
    "🤖 AI チャット",
    "📊 直接クエリ",
    "📈 データ分析",
    "⚙️ 設定"
])

with tab1:
    st.write("📊 投入されたテストデータの確認")

    # データ概要カード
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Redis キー数を修正版で取得
        redis_key_count = get_redis_key_count() if "🟢" in status.get('Redis', '') else "?"
        st.metric(
            label="Redis Keys",
            value=redis_key_count,
            help="Redisに保存されているキーの総数"
        )

    with col2:
        st.metric(
            label="PostgreSQL Tables",
            value="3" if "🟢" in status.get('PostgreSQL', '') else "?",
            help="customers, orders, products"
        )

    with col3:
        st.metric(
            label="ES Documents",
            value="5" if "🟢" in status.get('Elasticsearch', '') else "?",
            help="ブログ記事のドキュメント数"
        )

    with col4:
        st.metric(
            label="Qdrant Vectors",
            value="5" if "🟢" in status.get('Qdrant', '') else "?",
            help="商品ベクトルの数"
        )

    st.markdown("---")

    # データ詳細表示
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔴 Redis データ")
        if st.button("Redis データを表示", key="show_redis"):
            if "🟢" in status.get('Redis', ''):
                try:
                    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                    with st.spinner("Redisデータを取得中..."):
                        # セッションデータ
                        st.write("**🔑 セッションデータ:**")
                        session_keys = list(r.scan_iter('session:*'))
                        if session_keys:
                            session_data = []
                            for key in sorted(session_keys):
                                data = r.hgetall(key)
                                data['session_key'] = key
                                session_data.append(data)

                            df_sessions = pd.DataFrame(session_data)
                            st.dataframe(df_sessions, use_container_width=True)
                        else:
                            st.info("セッションデータが見つかりません")

                        # カウンタデータ
                        st.write("**📊 カウンタデータ:**")
                        counter_keys = list(r.scan_iter('counter:*'))
                        if counter_keys:
                            counter_data = {}
                            for key in sorted(counter_keys):
                                counter_data[key.replace('counter:', '')] = r.get(key)

                            # カウンタをメトリクスとして表示
                            counter_cols = st.columns(2)
                            for i, (key, value) in enumerate(counter_data.items()):
                                with counter_cols[i % 2]:
                                    st.metric(key.replace('_', ' ').title(), value)
                        else:
                            st.info("カウンタデータが見つかりません")

                        # カテゴリセット
                        st.write("**🏷️ カテゴリ:**")
                        categories = r.smembers('categories:all')
                        if categories:
                            st.write(", ".join(sorted(categories)))
                        else:
                            st.info("カテゴリデータが見つかりません")

                        # 検索履歴
                        st.write("**🔍 最近の検索履歴:**")
                        search_history = r.lrange('search:recent', 0, -1)
                        if search_history:
                            for i, term in enumerate(search_history[:5], 1):
                                st.write(f"{i}. {term}")
                        else:
                            st.info("検索履歴が見つかりません")

                        # ユーザープロファイル
                        st.write("**👤 ユーザープロファイル:**")
                        profile_keys = list(r.scan_iter('profile:*'))
                        if profile_keys:
                            for key in sorted(profile_keys):
                                profile_data = json.loads(r.get(key))
                                st.json(profile_data)
                        else:
                            st.info("ユーザープロファイルが見つかりません")

                except Exception as e:
                    st.error(f"Redis接続エラー: {e}")
                    st.code(traceback.format_exc())
            else:
                st.warning("Redis サーバーに接続できません")

    with col2:
        st.subheader("🟦 PostgreSQL データ")
        if st.button("PostgreSQL データを表示", key="show_postgres"):
            if "🟢" in status.get('PostgreSQL', ''):
                try:
                    # SQLAlchemy エンジンを作成
                    engine = sqlalchemy.create_engine(os.getenv('PG_CONN_STR'))

                    with st.spinner("PostgreSQLデータを取得中..."):
                        # 顧客データ
                        st.write("**👥 顧客データ:**")
                        df_customers = pd.read_sql("SELECT * FROM customers ORDER BY id LIMIT 10", engine)
                        st.dataframe(df_customers, use_container_width=True)

                        # 注文データ
                        st.write("**🛒 注文データ:**")
                        df_orders = pd.read_sql("""
                                                SELECT o.*, c.name as customer_name
                                                FROM orders o
                                                         JOIN customers c ON o.customer_id = c.id
                                                ORDER BY o.order_date DESC
                                                LIMIT 10
                                                """, engine)
                        st.dataframe(df_orders, use_container_width=True)

                        # 商品データ
                        st.write("**📦 商品データ:**")
                        df_products = pd.read_sql("SELECT * FROM products ORDER BY id", engine)
                        st.dataframe(df_products, use_container_width=True)

                        # 統計情報
                        st.write("**📈 統計情報:**")
                        stats_col1, stats_col2, stats_col3 = st.columns(3)

                        with stats_col1:
                            customer_count = pd.read_sql("SELECT COUNT(*) as count FROM customers", engine).iloc[0][
                                'count']
                            st.metric("総顧客数", customer_count)

                        with stats_col2:
                            order_count = pd.read_sql("SELECT COUNT(*) as count FROM orders", engine).iloc[0]['count']
                            st.metric("総注文数", order_count)

                        with stats_col3:
                            total_sales = \
                            pd.read_sql("SELECT SUM(price * quantity) as total FROM orders", engine).iloc[0]['total']
                            st.metric("総売上", f"¥{total_sales:,.0f}")

                    # エンジンを閉じる
                    engine.dispose()

                except Exception as e:
                    st.error(f"PostgreSQL接続エラー: {e}")
                    st.code(traceback.format_exc())
            else:
                st.warning("PostgreSQL サーバーに接続できません")

    # Elasticsearch と Qdrant（横幅フル活用）
    st.markdown("---")

    st.subheader("🟡 Elasticsearch データ")
    if st.button("Elasticsearch データを表示", key="show_elasticsearch"):
        if "🟢" in status.get('Elasticsearch', ''):
            try:
                with st.spinner("Elasticsearchデータを取得中..."):
                    response = requests.get(
                        'http://localhost:9200/blog_articles/_search?size=10&sort=published_date:desc')
                    if response.status_code == 200:
                        data = response.json()
                        articles = []
                        for hit in data['hits']['hits']:
                            article = hit['_source']
                            article['_id'] = hit['_id']
                            article['_score'] = hit['_score']
                            articles.append(article)

                        if articles:
                            df_articles = pd.DataFrame(articles)

                            # 記事を展開表示
                            for article in articles:
                                with st.expander(f"📝 {article['title']} (by {article['author']})"):
                                    col_left, col_right = st.columns([2, 1])

                                    with col_left:
                                        st.write(f"**内容:** {article['content']}")
                                        st.write(f"**タグ:** {', '.join(article['tags'])}")

                                    with col_right:
                                        st.write(f"**カテゴリ:** {article['category']}")
                                        st.write(f"**公開日:** {article['published_date']}")
                                        st.write(f"**閲覧数:** {article['view_count']:,}")
                        else:
                            st.info("記事が見つかりません")
                    else:
                        st.error(f"Elasticsearch データの取得に失敗しました (Status: {response.status_code})")
            except Exception as e:
                st.error(f"Elasticsearch接続エラー: {e}")
                st.code(traceback.format_exc())
        else:
            st.warning("Elasticsearch サーバーに接続できません")

    st.subheader("🟠 Qdrant データ")
    if st.button("Qdrant データを表示", key="show_qdrant"):
        if "🟢" in status.get('Qdrant', ''):
            try:
                with st.spinner("Qdrantデータを取得中..."):
                    # まずコレクション一覧を取得
                    collections_response = requests.get('http://localhost:6333/collections', timeout=5)

                    if collections_response.status_code == 200:
                        collections_data = collections_response.json()
                        st.write("**📋 利用可能なコレクション:**")
                        st.json(collections_data)

                        collections = collections_data.get('result', {}).get('collections', [])
                        collection_names = [col['name'] for col in collections]

                        if 'product_embeddings' in collection_names:
                            # コレクションが存在する場合のみデータ取得
                            points_response = requests.get(
                                'http://localhost:6333/collections/product_embeddings/points?limit=10')

                            if points_response.status_code == 200:
                                data = points_response.json()
                                if 'result' in data and 'points' in data['result']:
                                    products = []
                                    for point in data['result']['points']:
                                        product = point['payload'].copy()
                                        product['id'] = point['id']
                                        product['vector_size'] = len(point['vector']) if 'vector' in point else 0
                                        products.append(product)

                                    if products:
                                        df_products = pd.DataFrame(products)
                                        st.dataframe(df_products, use_container_width=True)

                                        # 商品カテゴリ分布
                                        st.write("**📊 カテゴリ分布:**")
                                        if 'category' in df_products.columns:
                                            category_counts = df_products['category'].value_counts()
                                            st.bar_chart(category_counts)
                                        else:
                                            st.info("カテゴリ情報がありません")
                                    else:
                                        st.info("商品ベクトルが見つかりません")
                                else:
                                    st.error("Qdrant データの形式が予期しないものです")
                            else:
                                st.error(f"商品データの取得に失敗しました (Status: {points_response.status_code})")
                        else:
                            st.warning("product_embeddingsコレクションが見つかりません")
                            st.info("利用可能なコレクション: " + ", ".join(
                                collection_names) if collection_names else "なし")

                            # データセットアップの提案
                            st.info("💡 解決方法: データセットアップスクリプトを実行してください")
                            st.code("uv run python scripts/setup_test_data.py")
                    else:
                        st.error(
                            f"Qdrant コレクション一覧の取得に失敗しました (Status: {collections_response.status_code})")

            except Exception as e:
                st.error(f"Qdrant接続エラー: {e}")
                st.code(traceback.format_exc())
        else:
            st.warning("Qdrant サーバーに接続できません")

with tab2:
    st.header("🤖 AI アシスタント（MCP経由）")

    # MCP サーバー状態の確認
    mcp_servers_ready = all(
        "🟢" in status.get(server, '') for server in ['Redis', 'PostgreSQL', 'Elasticsearch', 'Qdrant'])

    if not mcp_servers_ready:
        st.warning("⚠️ 一部のサーバーに接続できません。MCPサーバーを起動してください。")
        st.code("""
# MCPサーバーを起動
docker-compose -f docker-compose.mcp-demo.yml up -d redis-mcp postgres-mcp es-mcp qdrant-mcp

# 状態確認
docker-compose -f docker-compose.mcp-demo.yml ps
        """)

    # OpenAI API キーチェック
    if not os.getenv('OPENAI_API_KEY'):
        st.error("🔑 OPENAI_API_KEY が設定されていません。.envファイルを確認してください。")
        st.stop()

    # チャット履歴の初期化
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # サンプル質問
    st.subheader("💡 サンプル質問")
    sample_questions = [
        "Redisに保存されているセッション数を教えて",
        "PostgreSQLの顧客テーブルから東京在住の顧客を検索して",
        "Elasticsearchで「Python」に関する記事を検索して",
        "Qdrantの商品ベクトルから類似商品を見つけて",
        "今日の売上データを分析して"
    ]

    selected_question = st.selectbox("質問を選択（または下のチャットに直接入力）:",
                                     ["選択してください..."] + sample_questions)

    if selected_question != "選択してください..." and st.button("この質問を使用"):
        st.session_state.messages.append({"role": "user", "content": selected_question})
        st.rerun()

    # チャット履歴表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # チャット入力
    if prompt := st.chat_input("何か質問してください"):
        # ユーザーメッセージを追加
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # AI応答
        with st.chat_message("assistant"):
            response_placeholder = st.empty()

            try:
                with st.spinner("AI が回答を生成中..."):
                    # 実際のOpenAI API呼び出し（MCPサーバーなしの場合のフォールバック）
                    if mcp_servers_ready:
                        # 実際のMCP呼び出しはここに実装
                        # 現在はダミーレスポンスを返す
                        response_text = f"""
🤖 **AI Assistant Response**

質問: "{prompt}"

申し訳ございませんが、現在MCPサーバーとの連携機能は開発中です。
代わりに、利用可能なデータについて説明いたします：

**📊 利用可能なデータ:**
- **Redis**: セッション管理、カウンタ、検索履歴
- **PostgreSQL**: 顧客情報、注文データ、商品カタログ
- **Elasticsearch**: ブログ記事、全文検索
- **Qdrant**: 商品ベクトル、推薦システム

**🔧 次のステップ:**
1. MCPサーバーを起動: `docker-compose -f docker-compose.mcp-demo.yml up -d redis-mcp postgres-mcp`
2. OpenAI Responses API を使用してMCPサーバーに接続
3. 自然言語でデータベースを操作

**💡 現在できること:**
- "📊 直接クエリ" タブで各データベースに直接アクセス
- "🔍 データ確認" タブでテストデータの確認
                        """
                    else:
                        response_text = f"""
⚠️ **データベース接続エラー**

申し訳ございませんが、一部のデータベースサーバーに接続できません。

**接続状況:**
{chr(10).join([f"- {server}: {state}" for server, state in status.items()])}

**解決方法:**
1. Docker Composeでデータベースを起動:
   ```bash
   docker-compose -f docker-compose.mcp-demo.yml up -d
   ```

2. サーバー状態を確認:
   ```bash
   docker-compose -f docker-compose.mcp-demo.yml ps
   ```

3. ログを確認（エラーがある場合）:
   ```bash
   docker-compose -f docker-compose.mcp-demo.yml logs
   ```

サーバーが起動したら、再度お試しください。
                        """

                    # レスポンスをタイプライター風に表示
                    full_response = ""
                    for word in response_text.split():
                        full_response += word + " "
                        response_placeholder.markdown(full_response + "▌")
                        time.sleep(0.05)  # タイプライター効果

                    response_placeholder.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})

            except Exception as e:
                error_msg = f"❌ エラーが発生しました: {e}"
                response_placeholder.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

    # チャット履歴のクリア
    if st.button("🗑️ チャット履歴をクリア"):
        st.session_state.messages = []
        st.rerun()

with tab3:
    st.header("📊 直接データベースクエリ")

    query_type = st.selectbox("クエリタイプを選択",
                              ["Redis", "PostgreSQL", "Elasticsearch", "Qdrant"])

    if query_type == "Redis":
        st.subheader("🔴 Redis クエリ")

        # 事前定義されたクエリ
        redis_queries = {
            "全キー表示"  : "KEYS *",
            "セッション数": "KEYS session:*",
            "カウンタ一覧": "KEYS counter:*",
            "カテゴリ表示": "SMEMBERS categories:all",
            "検索履歴"    : "LRANGE search:recent 0 -1"
        }

        col1, col2 = st.columns([1, 2])

        with col1:
            st.write("**クイッククエリ:**")
            for name, cmd in redis_queries.items():
                if st.button(name, key=f"redis_{name}"):
                    st.session_state.redis_command = cmd

        with col2:
            redis_command = st.text_input(
                "Redisコマンド",
                value=getattr(st.session_state, 'redis_command', 'KEYS *'),
                key="redis_input"
            )

        if st.button("実行", key="redis_exec"):
            if "🟢" in status.get('Redis', ''):
                try:
                    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

                    # 安全なコマンドのみサポート
                    cmd_parts = redis_command.strip().split()
                    cmd = cmd_parts[0].upper()

                    if cmd == "KEYS":
                        pattern = cmd_parts[1] if len(cmd_parts) > 1 else "*"
                        result = r.keys(pattern)
                        st.json(sorted(result))
                    elif cmd == "GET":
                        if len(cmd_parts) > 1:
                            key = cmd_parts[1]
                            result = r.get(key)
                            st.code(str(result))
                        else:
                            st.error("GET コマンドにはキーを指定してください")
                    elif cmd == "HGETALL":
                        if len(cmd_parts) > 1:
                            key = cmd_parts[1]
                            result = r.hgetall(key)
                            st.json(result)
                        else:
                            st.error("HGETALL コマンドにはキーを指定してください")
                    elif cmd == "SMEMBERS":
                        if len(cmd_parts) > 1:
                            key = cmd_parts[1]
                            result = list(r.smembers(key))
                            st.json(sorted(result))
                        else:
                            st.error("SMEMBERS コマンドにはキーを指定してください")
                    elif cmd == "LRANGE":
                        if len(cmd_parts) >= 4:
                            key = cmd_parts[1]
                            start = int(cmd_parts[2])
                            stop = int(cmd_parts[3])
                            result = r.lrange(key, start, stop)
                            st.json(result)
                        else:
                            st.error("LRANGE コマンドの形式: LRANGE key start stop")
                    else:
                        st.error(f"サポートされていないコマンドです: {cmd}")
                        st.info("サポートされているコマンド: KEYS, GET, HGETALL, SMEMBERS, LRANGE")

                except Exception as e:
                    st.error(f"エラー: {e}")
            else:
                st.warning("Redis サーバーに接続できません")

    elif query_type == "PostgreSQL":
        st.subheader("🟦 PostgreSQL クエリ")

        # 事前定義されたクエリ
        pg_queries = {
            "全顧客"    : "SELECT * FROM customers ORDER BY id;",
            "東京の顧客": "SELECT * FROM customers WHERE city = '東京';",
            "最新注文"  : "SELECT o.*, c.name FROM orders o JOIN customers c ON o.customer_id = c.id ORDER BY o.order_date DESC LIMIT 5;",
            "売上統計"  : "SELECT product_name, SUM(price * quantity) as total_sales FROM orders GROUP BY product_name ORDER BY total_sales DESC;",
            "商品在庫"  : "SELECT name, stock_quantity, price FROM products ORDER BY stock_quantity DESC;"
        }

        col1, col2 = st.columns([1, 2])

        with col1:
            st.write("**クイッククエリ:**")
            for name, sql in pg_queries.items():
                if st.button(name, key=f"pg_{name}"):
                    st.session_state.sql_query = sql

        with col2:
            sql_query = st.text_area(
                "SQLクエリ",
                value=getattr(st.session_state, 'sql_query', 'SELECT * FROM customers LIMIT 5;'),
                height=100,
                key="pg_input"
            )

        if st.button("実行", key="pg_exec"):
            if "🟢" in status.get('PostgreSQL', ''):
                try:
                    # 安全性のため、SELECTクエリのみ許可
                    if not sql_query.strip().upper().startswith('SELECT'):
                        st.error("安全性のため、SELECTクエリのみ実行できます")
                    else:
                        # SQLAlchemy エンジンを使用
                        engine = sqlalchemy.create_engine(os.getenv('PG_CONN_STR'))
                        df = pd.read_sql(sql_query, engine)

                        if len(df) > 0:
                            st.dataframe(df, use_container_width=True)

                            # CSVダウンロード機能
                            csv = df.to_csv(index=False).encode('utf-8-sig')
                            st.download_button(
                                label="📥 CSVダウンロード",
                                data=csv,
                                file_name=f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime='text/csv'
                            )
                        else:
                            st.info("クエリの結果は空でした")

                        engine.dispose()

                except Exception as e:
                    st.error(f"エラー: {e}")
            else:
                st.warning("PostgreSQL サーバーに接続できません")

    elif query_type == "Elasticsearch":
        st.subheader("🟡 Elasticsearch クエリ")

        search_term = st.text_input("検索キーワード", "Python")
        search_field = st.selectbox("検索対象フィールド", ["全フィールド", "title", "content", "category", "author"])

        if st.button("検索実行", key="es_exec"):
            if "🟢" in status.get('Elasticsearch', ''):
                try:
                    # 検索クエリの構築
                    if search_field == "全フィールド":
                        query = {
                            "query"    : {
                                "multi_match": {
                                    "query" : search_term,
                                    "fields": ["title^2", "content", "category", "author"]
                                }
                            },
                            "highlight": {
                                "fields": {
                                    "title"  : {},
                                    "content": {}
                                }
                            }
                        }
                    else:
                        query = {
                            "query"    : {
                                "match": {
                                    search_field: search_term
                                }
                            },
                            "highlight": {
                                "fields": {
                                    search_field: {}
                                }
                            }
                        }

                    response = requests.post(
                        'http://localhost:9200/blog_articles/_search',
                        json=query,
                        headers={'Content-Type': 'application/json'}
                    )

                    if response.status_code == 200:
                        data = response.json()
                        hits = data['hits']['hits']

                        if hits:
                            st.success(f"🎯 {len(hits)}件の記事が見つかりました")

                            for hit in hits:
                                article = hit['_source']
                                score = hit['_score']

                                with st.expander(f"📝 {article['title']} (スコア: {score:.2f})"):
                                    col1, col2 = st.columns([3, 1])

                                    with col1:
                                        st.write(f"**内容:** {article['content']}")

                                        # ハイライト表示
                                        if 'highlight' in hit:
                                            st.write("**ハイライト:**")
                                            for field, highlights in hit['highlight'].items():
                                                for highlight in highlights:
                                                    st.markdown(f"• {highlight}", unsafe_allow_html=True)

                                    with col2:
                                        st.metric("閲覧数", f"{article['view_count']:,}")
                                        st.write(f"**著者:** {article['author']}")
                                        st.write(f"**カテゴリ:** {article['category']}")
                                        st.write(f"**公開日:** {article['published_date']}")
                                        st.write(f"**タグ:** {', '.join(article['tags'])}")
                        else:
                            st.info(f"'{search_term}' に関する記事は見つかりませんでした")
                    else:
                        st.error(f"検索に失敗しました (Status: {response.status_code})")

                except Exception as e:
                    st.error(f"エラー: {e}")
            else:
                st.warning("Elasticsearch サーバーに接続できません")

    elif query_type == "Qdrant":
        st.subheader("🟠 Qdrant ベクトル検索")

        st.info("💡 実際のベクトル検索には埋め込みモデルが必要ですが、ここではテスト用の機能を提供します")

        col1, col2 = st.columns(2)

        with col1:
            search_category = st.selectbox("カテゴリで検索",
                                           ["全て", "エレクトロニクス", "キッチン家電", "ファッション", "スポーツ"])
            price_range = st.slider("価格帯", 0, 100000, (0, 100000), step=1000)

        with col2:
            limit = st.number_input("取得件数", min_value=1, max_value=20, value=5)

        if st.button("検索実行", key="qdrant_exec"):
            if "🟢" in status.get('Qdrant', ''):
                try:
                    # フィルター条件の構築
                    filter_conditions = []

                    if search_category != "全て":
                        filter_conditions.append({
                            "key"  : "category",
                            "match": {"value": search_category}
                        })

                    filter_conditions.extend([
                        {"key": "price", "range": {"gte": price_range[0]}},
                        {"key": "price", "range": {"lte": price_range[1]}}
                    ])

                    # 検索リクエスト
                    search_request = {
                        "filter"      : {
                            "must": filter_conditions
                        },
                        "limit"       : limit,
                        "with_payload": True
                    }

                    response = requests.post(
                        'http://localhost:6333/collections/product_embeddings/points/search',
                        json=search_request,
                        headers={'Content-Type': 'application/json'}
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if 'result' in data and data['result']:
                            points = data['result']

                            st.success(f"🎯 {len(points)}件の商品が見つかりました")

                            # 商品一覧表示
                            products = []
                            for point in points:
                                product = point['payload']
                                product['id'] = point['id']
                                if 'score' in point:
                                    product['similarity_score'] = point['score']
                                products.append(product)

                            df_results = pd.DataFrame(products)
                            st.dataframe(df_results, use_container_width=True)

                            # 商品詳細カード
                            for product in products:
                                with st.expander(f"🛍️ {product['name']} - ¥{product['price']:,}"):
                                    col1, col2 = st.columns([2, 1])

                                    with col1:
                                        st.write(f"**説明:** {product['description']}")
                                        st.write(f"**カテゴリ:** {product['category']}")

                                    with col2:
                                        st.metric("価格", f"¥{product['price']:,}")
                                        if 'similarity_score' in product:
                                            st.metric("類似度スコア", f"{product['similarity_score']:.3f}")
                        else:
                            st.info("条件に合う商品は見つかりませんでした")
                    else:
                        st.error(f"検索に失敗しました (Status: {response.status_code})")

                except Exception as e:
                    st.error(f"エラー: {e}")
            else:
                st.warning("Qdrant サーバーに接続できません")

with tab4:
    st.header("📈 データ分析とダッシュボード")

    if all("🟢" in status.get(server, '') for server in ['PostgreSQL', 'Redis']):
        try:
            # SQLAlchemy エンジンを作成
            engine = sqlalchemy.create_engine(os.getenv('PG_CONN_STR'))

            # 売上分析
            st.subheader("💰 売上分析")

            col1, col2, col3 = st.columns(3)

            # 総売上
            total_sales = pd.read_sql("SELECT SUM(price * quantity) as total FROM orders", engine).iloc[0]['total']
            with col1:
                st.metric("総売上", f"¥{total_sales:,.0f}")

            # 平均注文価格
            avg_order = pd.read_sql("SELECT AVG(price * quantity) as avg FROM orders", engine).iloc[0]['avg']
            with col2:
                st.metric("平均注文価格", f"¥{avg_order:,.0f}")

            # 注文数
            order_count = pd.read_sql("SELECT COUNT(*) as count FROM orders", engine).iloc[0]['count']
            with col3:
                st.metric("総注文数", f"{order_count:,}")

            # 商品別売上
            st.subheader("📊 商品別売上")
            product_sales = pd.read_sql("""
                                        SELECT product_name,
                                               SUM(price * quantity) as total_sales,
                                               COUNT(*)              as order_count
                                        FROM orders
                                        GROUP BY product_name
                                        ORDER BY total_sales DESC
                                        """, engine)

            col1, col2 = st.columns(2)

            with col1:
                st.bar_chart(product_sales.set_index('product_name')['total_sales'])

            with col2:
                st.bar_chart(product_sales.set_index('product_name')['order_count'])

            # 顧客分析
            st.subheader("👥 顧客分析")

            customer_stats = pd.read_sql("""
                                         SELECT c.city,
                                                COUNT(c.id)                            as customer_count,
                                                COUNT(o.id)                            as total_orders,
                                                COALESCE(SUM(o.price * o.quantity), 0) as total_spent
                                         FROM customers c
                                                  LEFT JOIN orders o ON c.id = o.customer_id
                                         GROUP BY c.city
                                         ORDER BY total_spent DESC
                                         """, engine)

            col1, col2 = st.columns(2)

            with col1:
                st.write("**都市別顧客数**")
                st.bar_chart(customer_stats.set_index('city')['customer_count'])

            with col2:
                st.write("**都市別売上**")
                st.bar_chart(customer_stats.set_index('city')['total_spent'])

            # Redis統計
            st.subheader("🔴 Redis 統計")

            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

            redis_col1, redis_col2, redis_col3 = st.columns(3)

            with redis_col1:
                active_sessions = len(r.keys('session:*'))
                st.metric("アクティブセッション", active_sessions)

            with redis_col2:
                page_views = r.get('counter:page_views') or 0
                st.metric("ページビュー", f"{page_views:,}")

            with redis_col3:
                search_count = r.llen('search:recent')
                st.metric("検索履歴数", search_count)

            # エンジンを閉じる
            engine.dispose()

        except Exception as e:
            st.error(f"データ分析エラー: {e}")
    else:
        st.warning("データ分析には PostgreSQL と Redis の接続が必要です")

with tab5:
    st.header("⚙️ 設定とヘルプ")

    # システム情報
    st.subheader("🖥️ システム情報")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**環境変数:**")
        env_status = {
            "OPENAI_API_KEY": "設定済み" if os.getenv('OPENAI_API_KEY') else "❌ 未設定",
            "REDIS_URL"     : os.getenv('REDIS_URL', '未設定'),
            "PG_CONN_STR"   : "設定済み" if os.getenv('PG_CONN_STR') else "❌ 未設定",
            "ELASTIC_URL"   : os.getenv('ELASTIC_URL', 'http://localhost:9200'),
            "QDRANT_URL"    : os.getenv('QDRANT_URL', 'http://localhost:6333')
        }

        for key, value in env_status.items():
            if "❌" in str(value):
                st.error(f"**{key}**: {value}")
            else:
                st.success(f"**{key}**: {value}")

    with col2:
        st.write("**サーバー接続状況:**")
        for server, state in status.items():
            if "🟢" in state:
                st.success(f"**{server}**: 接続OK")
            else:
                st.error(f"**{server}**: 接続NG")

    # Docker コマンド
    st.subheader("🐳 Docker 管理コマンド")

    command_tabs = st.tabs(["起動", "停止", "ログ確認", "データリセット"])

    with command_tabs[0]:
        st.write("**データベース起動:**")
        st.code("docker-compose -f docker-compose.mcp-demo.yml up -d redis postgres elasticsearch qdrant")

        st.write("**MCPサーバー起動:**")
        st.code("docker-compose -f docker-compose.mcp-demo.yml up -d redis-mcp postgres-mcp es-mcp qdrant-mcp")

        st.write("**全サービス起動:**")
        st.code("docker-compose -f docker-compose.mcp-demo.yml up -d")

    with command_tabs[1]:
        st.write("**全サービス停止:**")
        st.code("docker-compose -f docker-compose.mcp-demo.yml down")

        st.write("**ボリューム削除（データも削除）:**")
        st.code("docker-compose -f docker-compose.mcp-demo.yml down -v")

    with command_tabs[2]:
        st.write("**全サービスのログ:**")
        st.code("docker-compose -f docker-compose.mcp-demo.yml logs -f")

        st.write("**特定サービスのログ:**")
        st.code("docker-compose -f docker-compose.mcp-demo.yml logs -f redis-mcp")

    with command_tabs[3]:
        st.write("**テストデータ再投入:**")
        st.code("uv run python scripts/setup_test_data.py")

        st.write("**完全リセット:**")
        st.code("""
# 停止してボリューム削除  
docker-compose -f docker-compose.mcp-demo.yml down -v

# 再起動
docker-compose -f docker-compose.mcp-demo.yml up -d

# データ再投入
uv run python scripts/setup_test_data.py
        """)

    # MCP エンドポイント情報
    st.subheader("🌐 MCP エンドポイント")

    mcp_endpoints = {
        "Redis MCP"        : "http://localhost:8000/mcp",
        "PostgreSQL MCP"   : "http://localhost:8001/mcp",
        "Elasticsearch MCP": "http://localhost:8002/mcp",
        "Qdrant MCP"       : "http://localhost:8003/mcp"
    }

    st.json(mcp_endpoints)

    # トラブルシューティング
    st.subheader("🔧 トラブルシューティング")

    with st.expander("❓ よくある問題と解決方法"):
        st.markdown("""
        **🔴 Redis 接続エラー**
        - Dockerコンテナが起動しているか確認: `docker ps | grep redis`
        - ポート6379が使用中でないか確認: `lsof -i :6379`

        **🟦 PostgreSQL 接続エラー**
        - 認証情報を確認: `testuser/testpass`
        - データベース初期化を確認: `docker-compose logs postgres`

        **🟡 Elasticsearch 接続エラー**
        - メモリ不足の可能性: `docker stats`
        - Java heap size設定を確認: `ES_JAVA_OPTS=-Xms512m -Xmx512m`

        **🟠 Qdrant 接続エラー**
        - コンテナの起動状況: `docker-compose ps qdrant`
        - ヘルスチェック: `curl http://localhost:6333/`

        **🤖 OpenAI API エラー**
        - APIキーの設定確認: `.env`ファイル
        - クォータ制限の確認: OpenAIダッシュボード
        """)

    # アプリ情報
    st.subheader("ℹ️ アプリケーション情報")

    app_info = {
        "バージョン": "1.0.0",
        "作成日"    : "2024-01-15",
        "Python"    : "3.11+",
        "Streamlit" : st.__version__,
        "使用技術"  : ["Docker", "Redis", "PostgreSQL", "Elasticsearch", "Qdrant", "OpenAI API"]
    }

    st.json(app_info)

# フッター
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p><strong>🚀 MCP Demo App</strong> - OpenAI API × MCP サーバー連携のデモンストレーション</p>
    <p>Made with ❤️ using Streamlit</p>
</div>
""", unsafe_allow_html=True)

# streamlit run a_mcp_sample.py --server.port=8501
