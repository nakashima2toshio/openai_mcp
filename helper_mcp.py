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

# 必要なライブラリの確認
try:
    import requests
except ImportError:
    st.error("requests ライブラリが必要です: pip install requests")

try:
    import pandas as pd
except ImportError:
    st.error("pandas ライブラリが必要です: pip install pandas")


# ==================================================
# ユーティリティ関数
# ==================================================
def safe_get_secret(key: str, default: Any = None) -> Any:
    """Streamlit secretsから安全に値を取得"""
    try:
        return st.secrets.get(key, default)
    except Exception:
        # secrets.toml が存在しない場合は環境変数を使用
        return os.getenv(key, default)


def safe_format_number(value: Any, use_comma: bool = True) -> str:
    """数値を安全にフォーマット"""
    try:
        if value is None:
            return "0"

        # 数値型に変換を試行
        if isinstance(value, (int, float)):
            num_value = value
        else:
            # 文字列から数値への変換を試行
            num_value = float(value)

        # カンマ区切りフォーマット
        if use_comma:
            # 小数点以下がある場合の処理
            if isinstance(num_value, float) and num_value != int(num_value):
                return f"{num_value:,.0f}"
            else:
                return f"{int(num_value):,}"
        else:
            return str(int(num_value))

    except (ValueError, TypeError):
        # 変換に失敗した場合は文字列として返す
        return str(value) if value is not None else "N/A"


def safe_format_metric(label: str, value: Any, suffix: str = "", prefix: str = "", use_comma: bool = True) -> None:
    """Streamlitメトリクスを安全に表示"""
    try:
        formatted_value = safe_format_number(value, use_comma)
        display_value = f"{prefix}{formatted_value}{suffix}"
        st.metric(label, display_value)
    except Exception as e:
        st.metric(label, f"エラー: {e}")


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
        self.host = safe_get_secret('REDIS_HOST', 'localhost')
        self.port = int(safe_get_secret('REDIS_PORT', 6379))
        self.db = int(safe_get_secret('REDIS_DB', 0))

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
        # secrets.toml が存在しない場合のエラーを回避
        self.conn_str = safe_get_secret('PG_CONN_STR', os.getenv('PG_CONN_STR'))

    def check_connection(self) -> Dict[str, str]:
        """PostgreSQL接続状態をチェック"""
        if not self.conn_str:
            return {"status": "🔴 接続NG", "details": "接続文字列が設定されていません"}

        try:
            conn = psycopg2.connect(self.conn_str, connect_timeout=3)
            conn.close()
            return {"status": "🟢 接続OK", "details": "正常"}
        except Exception as e:
            return {"status": f"🔴 接続NG", "details": str(e)[:50]}

    def get_data_summary(self) -> Dict[str, Any]:
        """PostgreSQLデータの概要取得"""
        if not self.conn_str:
            return {"table_count": "?", "status": "error", "message": "接続文字列未設定"}

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
        if not self.conn_str:
            st.error("PostgreSQL接続文字列が設定されていません")
            return {}

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
        self.url = safe_get_secret('ELASTIC_URL', os.getenv('ELASTIC_URL', 'http://localhost:9200'))

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
        self.url = safe_get_secret('QDRANT_URL', os.getenv('QDRANT_URL', 'http://localhost:6333'))

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

    def _render_elasticsearch_details(self):
        """Elasticsearch詳細表示"""
        st.subheader("🟡 Elasticsearch データ")
        if st.button("Elasticsearch データを表示", key="show_elasticsearch"):
            es_manager = self.status_manager.get_manager('Elasticsearch')
            status = es_manager.check_connection()

            if "🟢" in status["status"]:
                with st.spinner("Elasticsearchデータを取得中..."):
                    try:
                        # インデックス一覧を取得
                        response = requests.get(f'{es_manager.url}/_cat/indices?format=json', timeout=5)
                        if response.status_code == 200:
                            indices_data = response.json()

                            st.write("**📋 インデックス一覧:**")
                            if indices_data:
                                df_indices = pd.DataFrame(indices_data)
                                # 主要な列のみ表示
                                display_columns = ['index', 'docs.count', 'store.size', 'status']
                                available_columns = [col for col in display_columns if col in df_indices.columns]
                                if available_columns:
                                    st.dataframe(df_indices[available_columns], use_container_width=True)
                                else:
                                    st.dataframe(df_indices, use_container_width=True)
                            else:
                                st.info("インデックスが見つかりませんでした")

                        # サンプル検索（blog_articlesインデックスがある場合）
                        search_response = requests.get(f'{es_manager.url}/blog_articles/_search?size=5', timeout=5)
                        if search_response.status_code == 200:
                            search_data = search_response.json()
                            hits = search_data.get('hits', {}).get('hits', [])

                            if hits:
                                st.write("**📝 サンプル記事データ:**")
                                for i, hit in enumerate(hits, 1):
                                    source = hit.get('_source', {})
                                    with st.expander(f"記事 {i}: {source.get('title', 'タイトル不明')}"):
                                        col1, col2 = st.columns([2, 1])
                                        with col1:
                                            st.write(f"**内容:** {source.get('content', 'N/A')}")
                                            st.write(f"**カテゴリ:** {source.get('category', 'N/A')}")
                                        with col2:
                                            st.write(f"**著者:** {source.get('author', 'N/A')}")
                                            st.write(f"**閲覧数:** {source.get('view_count', 'N/A')}")
                                            st.write(f"**公開日:** {source.get('published_date', 'N/A')}")
                            else:
                                st.info("blog_articlesインデックスにデータが見つかりませんでした")
                        else:
                            st.warning("blog_articlesインデックスが存在しないか、アクセスできません")

                    except Exception as e:
                        st.error(f"Elasticsearch詳細データ取得エラー: {e}")
            else:
                st.warning("Elasticsearchサーバーに接続できません")
                st.write(f"状態: {status['status']}")
                st.write(f"詳細: {status['details']}")

    def _render_qdrant_details(self):
        """Qdrant詳細表示"""
        st.subheader("🟠 Qdrant データ")
        if st.button("Qdrant データを表示", key="show_qdrant"):
            qdrant_manager = self.status_manager.get_manager('Qdrant')
            status = qdrant_manager.check_connection()

            if "🟢" in status["status"]:
                with st.spinner("Qdrantデータを取得中..."):
                    try:
                        # コレクション一覧を取得
                        response = requests.get(f'{qdrant_manager.url}/collections', timeout=5)
                        if response.status_code == 200:
                            collections_data = response.json()
                            collections = collections_data.get('result', {}).get('collections', [])

                            st.write("**📚 コレクション一覧:**")
                            if collections:
                                collection_info = []
                                for collection in collections:
                                    # 各コレクションの詳細を取得
                                    detail_response = requests.get(
                                        f'{qdrant_manager.url}/collections/{collection["name"]}',
                                        timeout=5
                                    )
                                    if detail_response.status_code == 200:
                                        detail_data = detail_response.json()
                                        result = detail_data.get('result', {})
                                        config = result.get('config', {})

                                        collection_info.append({
                                            '名前'        : collection['name'],
                                            'ベクトル数'  : result.get('points_count', 0),
                                            'ベクトル次元': config.get('params', {}).get('vectors', {}).get('size',
                                                                                                            'N/A'),
                                            '距離計算'    : config.get('params', {}).get('vectors', {}).get('distance',
                                                                                                            'N/A'),
                                            'ステータス'  : result.get('status', 'unknown')
                                        })
                                    else:
                                        collection_info.append({
                                            '名前'        : collection['name'],
                                            'ベクトル数'  : 'N/A',
                                            'ベクトル次元': 'N/A',
                                            '距離計算'    : 'N/A',
                                            'ステータス'  : 'unknown'
                                        })

                                df_collections = pd.DataFrame(collection_info)
                                st.dataframe(df_collections, use_container_width=True)
                            else:
                                st.info("コレクションが見つかりませんでした")

                        # サンプルデータ取得（最初のコレクションから）
                        if collections:
                            collection_name = collections[0]['name']

                            # ポイントを取得
                            points_response = requests.post(
                                f'{qdrant_manager.url}/collections/{collection_name}/points/scroll',
                                json={"limit": 5, "with_payload": True, "with_vector": False},
                                headers={'Content-Type': 'application/json'},
                                timeout=5
                            )

                            if points_response.status_code == 200:
                                points_data = points_response.json()
                                points = points_data.get('result', {}).get('points', [])

                                if points:
                                    st.write(f"**🔍 {collection_name} サンプルデータ:**")
                                    sample_data = []
                                    for point in points:
                                        payload = point.get('payload', {})
                                        sample_data.append({
                                            'ID': point.get('id', 'N/A'),
                                            **{k: str(v)[:50] + ('...' if len(str(v)) > 50 else '')
                                               for k, v in payload.items()}
                                        })

                                    if sample_data:
                                        df_samples = pd.DataFrame(sample_data)
                                        st.dataframe(df_samples, use_container_width=True)

                        # クラスター情報
                        st.write("**🏥 クラスター情報:**")
                        try:
                            cluster_response = requests.get(f'{qdrant_manager.url}/cluster', timeout=5)

                            if cluster_response.status_code == 200:
                                cluster_data = cluster_response.json()
                                result = cluster_data.get('result', {})

                                # クラスター機能の状態をチェック
                                cluster_status = result.get('status')

                                if cluster_status == 'disabled':
                                    # クラスター機能が無効の場合（単一ノード構成）
                                    st.info("クラスター機能は無効です（単一ノード構成）")

                                    # Telemetry情報から代替情報を取得
                                    try:
                                        telemetry_response = requests.get(f'{qdrant_manager.url}/telemetry', timeout=5)
                                        if telemetry_response.status_code == 200:
                                            telemetry_data = telemetry_response.json()
                                            telemetry_result = telemetry_data.get('result', {})

                                            col1, col2 = st.columns(2)
                                            with col1:
                                                st.write(f"**ノードID:** {telemetry_result.get('id', 'N/A')}")
                                                collections_count = len(telemetry_result.get('collections', {}))
                                                st.write(f"**コレクション数:** {collections_count}")
                                            with col2:
                                                app_info = telemetry_result.get('app', {})
                                                st.write(f"**バージョン:** {app_info.get('version', 'N/A')}")
                                                st.write(f"**構成モード:** スタンドアローン")

                                    except Exception as telemetry_error:
                                        st.warning(f"Telemetry情報の取得に失敗: {telemetry_error}")
                                        st.write("**構成:** 単一ノード（詳細情報取得不可）")

                                elif cluster_status == 'enabled' or 'peers' in result:
                                    # クラスター機能が有効の場合（複数ノード構成）
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        peers = result.get('peers', [])
                                        st.write(f"**ピア数:** {len(peers)}")
                                        st.write(f"**ローカルピアID:** {result.get('peer_id', 'N/A')}")
                                    with col2:
                                        consensus_thread = result.get('consensus_thread_status', {})
                                        st.write(f"**リーダー:** {consensus_thread.get('is_leader', False)}")
                                        st.write(f"**クラスター状態:** {cluster_status or '有効'}")

                                else:
                                    # 不明な状態
                                    st.warning(f"不明なクラスター状態: {cluster_status}")
                                    st.write("**構成:** 不明")

                                # デバッグ情報（展開可能）
                                with st.expander("🔍 詳細なクラスター情報", expanded=False):
                                    st.json(cluster_data)

                            else:
                                st.warning(f"クラスター情報の取得に失敗 (Status: {cluster_response.status_code})")

                        except requests.exceptions.RequestException as e:
                            st.warning(f"クラスター情報の取得でネットワークエラー: {e}")

                    except Exception as e:
                        st.error(f"Qdrant詳細データ取得エラー: {e}")
            else:
                st.warning("Qdrantサーバーに接続できません")
                st.write(f"状態: {status['status']}")
                st.write(f"詳細: {status['details']}")


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
        api_key = safe_get_secret('OPENAI_API_KEY', os.getenv('OPENAI_API_KEY'))
        if not api_key:
            st.error("🔑 OPENAI_API_KEY が設定されていません。.envファイルまたはsecrets.tomlを確認してください。")

            # 設定方法を表示
            with st.expander("🔧 設定方法", expanded=True):
                st.markdown("""
                **方法1: 環境変数（推奨）**
                ```bash
                export OPENAI_API_KEY="sk-..."
                ```

                **方法2: .envファイル**
                ```
                OPENAI_API_KEY=sk-...
                ```

                **方法3: secrets.tomlファイル**
                ```toml
                # .streamlit/secrets.toml
                OPENAI_API_KEY = "sk-..."
                ```
                """)
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


class DataAnalysisPage(PageManager):
    """データ分析ダッシュボードページ"""

    def render(self):
        st.header("📈 データ分析とダッシュボード")

        # 必要なサーバーの確認
        status = self.status_manager.check_all_servers()
        required_servers = ['PostgreSQL', 'Redis']
        servers_ready = all("🟢" in status[server]["status"] for server in required_servers)

        if not servers_ready:
            st.warning("データ分析には PostgreSQL と Redis の接続が必要です")
            return

        try:
            self._render_sales_analysis()
            self._render_redis_statistics()
        except Exception as e:
            st.error(f"データ分析エラー: {e}")

    def _render_sales_analysis(self):
        """売上分析"""
        st.subheader("💰 売上分析")

        engine = sqlalchemy.create_engine(os.getenv('PG_CONN_STR'))

        col1, col2, col3 = st.columns(3)

        # 総売上
        total_sales = pd.read_sql("SELECT SUM(price * quantity) as total FROM orders", engine).iloc[0]['total']
        with col1:
            safe_format_metric("総売上", total_sales, prefix="¥")

        # 平均注文価格
        avg_order = pd.read_sql("SELECT AVG(price * quantity) as avg FROM orders", engine).iloc[0]['avg']
        with col2:
            safe_format_metric("平均注文価格", avg_order, prefix="¥")

        # 注文数
        order_count = pd.read_sql("SELECT COUNT(*) as count FROM orders", engine).iloc[0]['count']
        with col3:
            safe_format_metric("総注文数", order_count, suffix="件", use_comma=False)

        engine.dispose()

    def _render_redis_statistics(self):
        """Redis統計"""
        st.subheader("🔴 Redis 統計")

        try:
            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

            col1, col2, col3 = st.columns(3)

            with col1:
                active_sessions = len(r.keys('session:*'))
                safe_format_metric("アクティブセッション", active_sessions, use_comma=False)

            with col2:
                page_views = r.get('counter:page_views') or 0
                safe_format_metric("ページビュー", page_views)

            with col3:
                search_count = r.llen('search:recent')
                safe_format_metric("検索履歴数", search_count, use_comma=False)

            # Redis詳細統計
            st.write("**Redis詳細統計**")

            # メモリ使用量（info commandの結果をパース）
            redis_info = r.info()

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                used_memory = redis_info.get('used_memory_human', 'N/A')
                st.metric("使用メモリ", used_memory)

            with col2:
                connected_clients = redis_info.get('connected_clients', 0)
                safe_format_metric("接続クライアント数", connected_clients, use_comma=False)

            with col3:
                total_commands = redis_info.get('total_commands_processed', 0)
                safe_format_metric("総コマンド数", total_commands)

            with col4:
                uptime_days = redis_info.get('uptime_in_days', 0)
                safe_format_metric("稼働日数", uptime_days, "日", use_comma=False)

        except Exception as e:
            st.error(f"Redis統計取得エラー: {e}")


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
        try:
            from helper_mcp_pages import DirectQueryPage, SettingsPage
            return {
                0: DataViewPage("データ確認", self.status_manager),
                1: AIChatPage("AIチャット", self.status_manager),
                2: DirectQueryPage("直接クエリ", self.status_manager),
                3: DataAnalysisPage("データ分析", self.status_manager),
                4: SettingsPage("設定", self.status_manager),
            }
        except ImportError:
            # helper_mcp_pages.py が存在しない場合の簡易版
            return {
                0: DataViewPage("データ確認", self.status_manager),
                1: AIChatPage("AIチャット", self.status_manager),
                2: None,  # 簡易版では未実装
                3: DataAnalysisPage("データ分析", self.status_manager),
                4: None,  # 簡易版では未実装
            }

    def run(self):
        """アプリケーションの実行"""
        # セッション初期化
        MCPSessionManager.init_session()

        # 環境変数の確認と警告表示
        self._check_environment()

        # サイドバー描画
        self.sidebar_manager.render_server_status()
        self.sidebar_manager.render_quick_actions()
        current_tab = self.sidebar_manager.render_navigation(self.tab_names)

        # 現在のページ表示
        st.markdown(f"### 現在のページ: {self.tab_names[current_tab]}")

        # ページコンテンツの描画
        if current_tab in self.pages and self.pages[current_tab] is not None:
            self.pages[current_tab].render()
        else:
            st.warning(f"ページ {current_tab} は実装中です")
            self._render_setup_instructions()

    def _check_environment(self):
        """環境設定のチェックと警告表示"""
        missing_vars = []

        # 必要な環境変数をチェック
        required_vars = {
            'OPENAI_API_KEY': 'OpenAI APIキー',
            'PG_CONN_STR'   : 'PostgreSQL接続文字列'
        }

        for var, description in required_vars.items():
            if not safe_get_secret(var, os.getenv(var)):
                missing_vars.append(f"**{var}**: {description}")

        if missing_vars:
            with st.sidebar.expander("⚠️ 設定不備", expanded=True):
                st.warning("以下の設定が不足しています:")
                for var in missing_vars:
                    st.write(f"- {var}")

                st.info("設定方法は「⚙️ 設定」タブを参照してください")

    def _render_setup_instructions(self):
        """セットアップ手順の表示"""
        st.markdown("""
        ## 🚀 セットアップ手順

        ### 1. 環境変数の設定
        以下の環境変数を設定してください：

        ```bash
        # OpenAI API キー（必須）
        export OPENAI_API_KEY="sk-..."

        # PostgreSQL接続文字列（オプション）
        export PG_CONN_STR="postgresql://user:pass@localhost:5432/dbname"
        ```

        ### 2. Dockerサービス起動（オプション）
        ```bash
        docker-compose -f docker-compose.mcp-demo.yml up -d
        ```

        ### 3. テストデータ投入（オプション）
        ```bash
        uv run python scripts/setup_test_data.py
        ```
        """)


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
    'DataAnalysisPage',
    'safe_get_secret',
    'safe_format_number',
    'safe_format_metric',
]
