# helper_mcp.py
# MCP（Model Context Protocol）関連のヘルパー関数とクラス
# データベース管理、UI管理、ページ管理を含む

import streamlit as st
import redis
import psycopg2
import sqlalchemy
import requests
import pandas as pd
import json
import time
import traceback
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod


# ==================================================
# 設定とセッション管理
# ==================================================
class MCPSessionManager:
    """MCPアプリケーション用のセッション管理"""

    @staticmethod
    def init_session():
        """セッション状態の初期化"""
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'selected_tab_index' not in st.session_state:
            st.session_state.selected_tab_index = 0
        if 'auto_process_question' not in st.session_state:
            st.session_state.auto_process_question = False
        if 'server_status_cache' not in st.session_state:
            st.session_state.server_status_cache = {}
        if 'last_status_check' not in st.session_state:
            st.session_state.last_status_check = 0


# ==================================================
# データベース管理クラス群
# ==================================================
class DatabaseManager(ABC):
    """データベース管理の基底クラス"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def check_connection(self) -> Dict[str, str]:
        """接続状態をチェック"""
        pass

    @abstractmethod
    def get_data_summary(self) -> Dict[str, Any]:
        """データの概要を取得"""
        pass


class RedisManager(DatabaseManager):
    """Redis管理クラス"""

    def __init__(self):
        super().__init__("Redis")
        self.host = 'localhost'
        self.port = 6379
        self.db = 0

    def check_connection(self) -> Dict[str, str]:
        """Redis接続状態をチェック"""
        try:
            r = redis.Redis(host=self.host, port=self.port, db=self.db, socket_connect_timeout=3)
            r.ping()
            return {"status": "🟢 接続OK", "details": "正常"}
        except Exception as e:
            return {"status": f"🔴 接続NG", "details": str(e)[:50]}

    def get_data_summary(self) -> Dict[str, Any]:
        """Redisデータの概要取得"""
        try:
            r = redis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)

            # キー数を安全に取得
            count = 0
            for _ in r.scan_iter():
                count += 1
                if count > 1000:
                    return {"key_count": f"{count}+", "status": "partial"}

            return {
                "key_count"    : str(count),
                "status"       : "complete",
                "session_count": len(r.keys('session:*')),
                "counter_count": len(r.keys('counter:*'))
            }
        except Exception:
            return {"key_count": "?", "status": "error"}

    def get_detailed_data(self) -> Dict[str, Any]:
        """Redis詳細データ取得"""
        try:
            r = redis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)

            # セッションデータ
            session_keys = list(r.scan_iter('session:*'))
            session_data = []
            for key in sorted(session_keys):
                data = r.hgetall(key)
                data['session_key'] = key
                session_data.append(data)

            # カウンタデータ
            counter_keys = list(r.scan_iter('counter:*'))
            counter_data = {}
            for key in sorted(counter_keys):
                counter_data[key.replace('counter:', '')] = r.get(key)

            # その他のデータ
            categories = list(r.smembers('categories:all'))
            search_history = r.lrange('search:recent', 0, -1)

            return {
                "sessions"      : session_data,
                "counters"      : counter_data,
                "categories"    : categories,
                "search_history": search_history
            }
        except Exception as e:
            st.error(f"Redis詳細データ取得エラー: {e}")
            return {}


class PostgreSQLManager(DatabaseManager):
    """PostgreSQL管理クラス"""

    def __init__(self):
        super().__init__("PostgreSQL")
        self.conn_str = st.secrets.get('PG_CONN_STR') or os.getenv('PG_CONN_STR')

    def check_connection(self) -> Dict[str, str]:
        """PostgreSQL接続状態をチェック"""
        try:
            conn = psycopg2.connect(self.conn_str, connect_timeout=3)
            conn.close()
            return {"status": "🟢 接続OK", "details": "正常"}
        except Exception as e:
            return {"status": f"🔴 接続NG", "details": str(e)[:50]}

    def get_data_summary(self) -> Dict[str, Any]:
        """PostgreSQLデータの概要取得"""
        try:
            engine = sqlalchemy.create_engine(self.conn_str)

            # テーブル数と基本統計
            customers = pd.read_sql("SELECT COUNT(*) as count FROM customers", engine).iloc[0]['count']
            orders = pd.read_sql("SELECT COUNT(*) as count FROM orders", engine).iloc[0]['count']
            products = pd.read_sql("SELECT COUNT(*) as count FROM products", engine).iloc[0]['count']

            engine.dispose()
            return {
                "table_count": 3,
                "customers"  : customers,
                "orders"     : orders,
                "products"   : products,
                "status"     : "complete"
            }
        except Exception:
            return {"table_count": "?", "status": "error"}

    def get_detailed_data(self) -> Dict[str, Any]:
        """PostgreSQL詳細データ取得"""
        try:
            engine = sqlalchemy.create_engine(self.conn_str)

            # 各テーブルのデータ
            customers = pd.read_sql("SELECT * FROM customers ORDER BY id LIMIT 10", engine)
            orders = pd.read_sql("""
                                 SELECT o.*, c.name as customer_name
                                 FROM orders o
                                          JOIN customers c ON o.customer_id = c.id
                                 ORDER BY o.order_date DESC
                                 LIMIT 10
                                 """, engine)
            products = pd.read_sql("SELECT * FROM products ORDER BY id", engine)

            # 統計情報
            total_sales = pd.read_sql("SELECT SUM(price * quantity) as total FROM orders", engine).iloc[0]['total']

            engine.dispose()
            return {
                "customers"  : customers,
                "orders"     : orders,
                "products"   : products,
                "total_sales": total_sales
            }
        except Exception as e:
            st.error(f"PostgreSQL詳細データ取得エラー: {e}")
            return {}


class ElasticsearchManager(DatabaseManager):
    """Elasticsearch管理クラス"""

    def __init__(self):
        super().__init__("Elasticsearch")
        self.url = 'http://localhost:9200'

    def check_connection(self) -> Dict[str, str]:
        """Elasticsearch接続状態をチェック"""
        try:
            response = requests.get(f'{self.url}/_cluster/health', timeout=3)
            if response.status_code == 200:
                return {"status": "🟢 接続OK", "details": "正常"}
            else:
                return {"status": f"🔴 接続NG", "details": f"Status: {response.status_code}"}
        except Exception as e:
            return {"status": f"🔴 接続NG", "details": str(e)[:50]}

    def get_data_summary(self) -> Dict[str, Any]:
        """Elasticsearchデータの概要取得"""
        try:
            response = requests.get(f'{self.url}/blog_articles/_count', timeout=3)
            if response.status_code == 200:
                count = response.json()['count']
                return {"document_count": count, "status": "complete"}
            else:
                return {"document_count": "?", "status": "error"}
        except Exception:
            return {"document_count": "?", "status": "error"}

    def search_articles(self, term: str, field: str = "全フィールド") -> List[Dict]:
        """記事検索"""
        try:
            if field == "全フィールド":
                query = {
                    "query"    : {
                        "multi_match": {
                            "query" : term,
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
                            field: term
                        }
                    },
                    "highlight": {
                        "fields": {
                            field: {}
                        }
                    }
                }

            response = requests.post(
                f'{self.url}/blog_articles/_search',
                json=query,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                return response.json()['hits']['hits']
            return []
        except Exception as e:
            st.error(f"Elasticsearch検索エラー: {e}")
            return []


class QdrantManager(DatabaseManager):
    """Qdrant管理クラス"""

    def __init__(self):
        super().__init__("Qdrant")
        self.url = 'http://localhost:6333'

    def check_connection(self) -> Dict[str, str]:
        """Qdrant接続状態をチェック"""
        try:
            response = requests.get(f'{self.url}/', timeout=3)
            if response.status_code == 200:
                return {"status": "🟢 接続OK", "details": "正常"}
            else:
                return {"status": f"🔴 接続NG", "details": f"Status: {response.status_code}"}
        except Exception as e:
            return {"status": f"🔴 接続NG", "details": str(e)[:50]}

    def get_data_summary(self) -> Dict[str, Any]:
        """Qdrantデータの概要取得"""
        try:
            response = requests.get(f'{self.url}/collections', timeout=3)
            if response.status_code == 200:
                collections = response.json().get('result', {}).get('collections', [])
                return {
                    "collection_count": len(collections),
                    "collections"     : [col['name'] for col in collections],
                    "status"          : "complete"
                }
            return {"collection_count": "?", "status": "error"}
        except Exception:
            return {"collection_count": "?", "status": "error"}


# ==================================================
# サーバー状態管理
# ==================================================
class ServerStatusManager:
    """全サーバーの状態管理"""

    def __init__(self):
        self.managers = {
            'Redis'        : RedisManager(),
            'PostgreSQL'   : PostgreSQLManager(),
            'Elasticsearch': ElasticsearchManager(),
            'Qdrant'       : QdrantManager()
        }

    @st.cache_data(ttl=30)
    def check_all_servers(_self) -> Dict[str, Dict[str, str]]:
        """全サーバーの状態をチェック（キャッシュ付き）"""
        status = {}
        for name, manager in _self.managers.items():
            status[name] = manager.check_connection()
        return status

    def get_connected_count(self) -> int:
        """接続済みサーバー数を取得"""
        status = self.check_all_servers()
        return sum(1 for s in status.values() if "🟢" in s["status"])

    def get_manager(self, name: str) -> Optional[DatabaseManager]:
        """指定されたデータベースマネージャーを取得"""
        return self.managers.get(name)


# ==================================================
# UI管理クラス
# ==================================================
class SidebarManager:
    """サイドバーの管理"""

    def __init__(self, status_manager: ServerStatusManager):
        self.status_manager = status_manager

    def render_server_status(self):
        """サーバー状態の表示"""
        st.sidebar.header("📊 MCP サーバー状態")

        if st.sidebar.button("🔄 状態更新"):
            st.cache_data.clear()

        status = self.status_manager.check_all_servers()
        for server, state in status.items():
            st.sidebar.markdown(f"**{server}**: {state['status']}")

        connected_count = self.status_manager.get_connected_count()
        st.sidebar.markdown(f"**接続済み**: {connected_count}/4 サーバー")

    def render_quick_actions(self):
        """クイックアクションの表示"""
        st.sidebar.markdown("---")
        st.sidebar.header("⚡ クイックアクション")

        if st.sidebar.button("🚀 Docker起動"):
            st.sidebar.code("docker-compose -f docker-compose.mcp-demo.yml up -d")

        if st.sidebar.button("📊 データ再投入"):
            st.sidebar.code("uv run python scripts/setup_test_data.py")

    def render_navigation(self, tab_names: List[str]) -> int:
        """ナビゲーションの表示"""
        st.sidebar.markdown("---")
        st.sidebar.header("📋 ページ選択")

        current_tab = st.session_state.selected_tab_index

        for i, tab_name in enumerate(tab_names):
            # 現在のタブかどうかで表示を変える
            if i == current_tab:
                st.sidebar.markdown(f"**▶ {tab_name}**")
            else:
                if st.sidebar.button(tab_name, key=f"tab_btn_{i}"):
                    st.session_state.selected_tab_index = i
                    st.rerun()

        return current_tab


# ==================================================
# ページ管理クラス群
# ==================================================
class PageManager(ABC):
    """ページ管理の基底クラス"""

    def __init__(self, name: str, status_manager: ServerStatusManager):
        self.name = name
        self.status_manager = status_manager

    @abstractmethod
    def render(self):
        """ページの描画"""
        pass


class DataViewPage(PageManager):
    """データ確認ページ"""

    def render(self):
        st.write("📊 投入されたテストデータの確認")

        # データ概要カード
        self._render_summary_metrics()

        st.markdown("---")

        # データ詳細表示
        self._render_detailed_data()

    def _render_summary_metrics(self):
        """概要メトリクスの表示"""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            redis_manager = self.status_manager.get_manager('Redis')
            redis_summary = redis_manager.get_data_summary()
            st.metric(
                label="Redis Keys",
                value=redis_summary.get('key_count', '?'),
                help="Redisに保存されているキーの総数"
            )

        with col2:
            pg_manager = self.status_manager.get_manager('PostgreSQL')
            pg_summary = pg_manager.get_data_summary()
            st.metric(
                label="PostgreSQL Tables",
                value=pg_summary.get('table_count', '?'),
                help="customers, orders, products"
            )

        with col3:
            es_manager = self.status_manager.get_manager('Elasticsearch')
            es_summary = es_manager.get_data_summary()
            st.metric(
                label="ES Documents",
                value=es_summary.get('document_count', '?'),
                help="ブログ記事のドキュメント数"
            )

        with col4:
            qdrant_manager = self.status_manager.get_manager('Qdrant')
            qdrant_summary = qdrant_manager.get_data_summary()
            st.metric(
                label="Qdrant Collections",
                value=qdrant_summary.get('collection_count', '?'),
                help="ベクトルコレクション数"
            )

    def _render_detailed_data(self):
        """詳細データの表示"""
        col1, col2 = st.columns(2)

        with col1:
            self._render_redis_details()

        with col2:
            self._render_postgresql_details()

        # 他のデータベースも同様に
        st.markdown("---")
        self._render_elasticsearch_details()
        self._render_qdrant_details()

    def _render_redis_details(self):
        """Redis詳細表示"""
        st.subheader("🔴 Redis データ")
        if st.button("Redis データを表示", key="show_redis"):
            redis_manager = self.status_manager.get_manager('Redis')
            with st.spinner("Redisデータを取得中..."):
                data = redis_manager.get_detailed_data()

                if data.get('sessions'):
                    st.write("**🔑 セッションデータ:**")
                    df_sessions = pd.DataFrame(data['sessions'])
                    st.dataframe(df_sessions, use_container_width=True)

                if data.get('counters'):
                    st.write("**📊 カウンタデータ:**")
                    counter_cols = st.columns(2)
                    for i, (key, value) in enumerate(data['counters'].items()):
                        with counter_cols[i % 2]:
                            st.metric(key.replace('_', ' ').title(), value)

                # その他のデータも表示

    def _render_postgresql_details(self):
        """PostgreSQL詳細表示"""
        st.subheader("🟦 PostgreSQL データ")
        if st.button("PostgreSQL データを表示", key="show_postgres"):
            pg_manager = self.status_manager.get_manager('PostgreSQL')
            with st.spinner("PostgreSQLデータを取得中..."):
                data = pg_manager.get_detailed_data()

                if 'customers' in data:
                    st.write("**👥 顧客データ:**")
                    st.dataframe(data['customers'], use_container_width=True)

                if 'orders' in data:
                    st.write("**🛒 注文データ:**")
                    st.dataframe(data['orders'], use_container_width=True)

                # その他のデータも表示

    def _render_elasticsearch_details(self):
        """Elasticsearch詳細表示"""
        st.subheader("🟡 Elasticsearch データ")
        if st.button("Elasticsearch データを表示", key="show_elasticsearch"):
            # 実装は元のコードと同様
            pass

    def _render_qdrant_details(self):
        """Qdrant詳細表示"""
        st.subheader("🟠 Qdrant データ")
        if st.button("Qdrant データを表示", key="show_qdrant"):
            # 実装は元のコードと同様
            pass


class AIChatPage(PageManager):
    """AIチャットページ"""

    def render(self):
        st.header("🤖 AI アシスタント（MCP経由）")

        # サーバー状態チェック
        if not self._check_servers():
            return

        # API キーチェック
        if not self._check_api_key():
            return

        # サンプル質問
        self._render_sample_questions()

        # チャット履歴
        self._render_chat_history()

        # チャット入力
        self._handle_chat_input()

    def _check_servers(self) -> bool:
        """サーバー状態チェック"""
        status = self.status_manager.check_all_servers()
        servers_ready = all("🟢" in s["status"] for s in status.values())

        if not servers_ready:
            st.warning("⚠️ 一部のサーバーに接続できません。MCPサーバーを起動してください。")
            st.code("""
# MCPサーバーを起動
docker-compose -f docker-compose.mcp-demo.yml up -d redis-mcp postgres-mcp es-mcp qdrant-mcp
            """)
            return False
        return True

    def _check_api_key(self) -> bool:
        """API キーチェック"""
        import os
        if not os.getenv('OPENAI_API_KEY'):
            st.error("🔑 OPENAI_API_KEY が設定されていません。.envファイルを確認してください。")
            return False
        return True

    def _render_sample_questions(self):
        """サンプル質問の表示"""
        st.subheader("💡 サンプル質問")
        sample_questions = [
            "Redisに保存されているセッション数を教えて",
            "PostgreSQLの顧客テーブルから東京在住の顧客を検索して",
            "Elasticsearchで「Python」に関する記事を検索して",
            "Qdrantの商品ベクトルから類似商品を見つけて",
            "今日の売上データを分析して"
        ]

        selected_question = st.selectbox(
            "質問を選択（または下のチャットに直接入力）:",
            ["選択してください..."] + sample_questions,
            key="question_selector"
        )

        if selected_question != "選択してください..." and st.button("この質問を使用", key="use_question_btn"):
            st.session_state.messages.append({"role": "user", "content": selected_question})
            st.session_state.auto_process_question = True
            st.session_state.selected_tab_index = 1  # AIチャットページを維持
            st.rerun()

    def _render_chat_history(self):
        """チャット履歴の表示"""
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    def _handle_chat_input(self):
        """チャット入力の処理"""
        prompt = st.chat_input("何か質問してください")

        if st.session_state.auto_process_question or prompt:
            if st.session_state.auto_process_question:
                st.session_state.auto_process_question = False
                if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                    current_prompt = st.session_state.messages[-1]["content"]
                else:
                    current_prompt = None
            else:
                current_prompt = prompt
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.write(prompt)

            if current_prompt:
                self._generate_ai_response(current_prompt)

        # チャット履歴クリア
        if st.button("🗑️ チャット履歴をクリア", key="clear_chat"):
            st.session_state.messages = []
            st.rerun()

    def _generate_ai_response(self, prompt: str):
        """AI応答の生成"""
        with st.chat_message("assistant"):
            response_placeholder = st.empty()

            try:
                with st.spinner("AI が回答を生成中..."):
                    # 実際のMCP処理はここに実装
                    response_text = self._create_demo_response(prompt)

                    # タイプライター効果
                    full_response = ""
                    for word in response_text.split():
                        full_response += word + " "
                        response_placeholder.markdown(full_response + "▌")
                        time.sleep(0.05)

                    response_placeholder.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})

            except Exception as e:
                error_msg = f"❌ エラーが発生しました: {e}"
                response_placeholder.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

    def _create_demo_response(self, prompt: str) -> str:
        """デモ用レスポンス生成"""
        return f"""
🤖 **AI Assistant Response**

質問: "{prompt}"

申し訳ございませんが、現在MCPサーバーとの連携機能は開発中です。
代わりに、利用可能なデータについて説明いたします：

**📊 利用可能なデータ:**
- **Redis**: セッション管理、カウンタ、検索履歴
- **PostgreSQL**: 顧客情報、注文データ、商品カタログ
- **Elasticsearch**: ブログ記事、全文検索
- **Qdrant**: 商品ベクトル、推薦システム

**💡 現在できること:**
- "📊 直接クエリ" タブで各データベースに直接アクセス
- "🔍 データ確認" タブでテストデータの確認
        """


# ==================================================
# メインアプリケーション管理
# ==================================================
class MCPApplication:
    """MCPアプリケーションのメイン管理クラス"""

    def __init__(self):
        self.status_manager = ServerStatusManager()
        self.sidebar_manager = SidebarManager(self.status_manager)

        # ページ定義
        self.tab_names = ["🔍 データ確認", "🤖 AI チャット", "📊 直接クエリ", "📈 データ分析", "⚙️ 設定"]
        self.pages = self._initialize_pages()

    def _initialize_pages(self):
        """ページの初期化"""
        from helper_mcp_pages import DirectQueryPage, DataAnalysisPage, SettingsPage

        return {
            0: DataViewPage("データ確認", self.status_manager),
            1: AIChatPage("AIチャット", self.status_manager),
            2: DirectQueryPage("直接クエリ", self.status_manager),
            3: DataAnalysisPage("データ分析", self.status_manager),
            4: SettingsPage("設定", self.status_manager),
        }

    def run(self):
        """アプリケーションの実行"""
        # セッション初期化
        MCPSessionManager.init_session()

        # サイドバー描画
        self.sidebar_manager.render_server_status()
        self.sidebar_manager.render_quick_actions()
        current_tab = self.sidebar_manager.render_navigation(self.tab_names)

        # 現在のページ表示
        st.markdown(f"### 現在のページ: {self.tab_names[current_tab]}")

        # ページコンテンツの描画
        if current_tab in self.pages:
            self.pages[current_tab].render()
        else:
            st.warning(f"ページ {current_tab} は実装中です")


# ==================================================
# エクスポート
# ==================================================
__all__ = [
    'MCPApplication',
    'MCPSessionManager',
    'ServerStatusManager',
    'RedisManager',
    'PostgreSQLManager',
    'ElasticsearchManager',
    'QdrantManager',
    'SidebarManager',
    'DataViewPage',
    'AIChatPage',
]
