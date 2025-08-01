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
        'page_views'        : 1250,
        'user_registrations': 89,
        'sales_today'       : 15,
        'active_sessions'   : 3
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
            'name'            : '田中太郎',
            'preferences'     : ['エレクトロニクス', 'ガジェット'],
            'purchase_history': [{'product': 'ノートPC', 'date': '2024-01-10'}]
        },
        'profile:2': {
            'name'            : '佐藤花子',
            'preferences'     : ['キッチン家電', 'ファッション'],
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
                "title"         : {"type": "text", "analyzer": "standard"},
                "content"       : {"type": "text", "analyzer": "standard"},
                "category"      : {"type": "keyword"},
                "author"        : {"type": "keyword"},
                "published_date": {"type": "date"},
                "tags"          : {"type": "keyword"},
                "view_count"    : {"type": "integer"}
            }
        }
    }

    # インデックス作成
    requests.put(f"{es_url}/blog_articles", json=index_mapping)

    # テストドキュメント
    articles = [
        {
            "title"         : "Python機械学習入門",
            "content"       : "Pythonを使った機械学習の基礎について説明します。scikit-learnやpandasを使って実際にデータ分析を行ってみましょう。",
            "category"      : "技術",
            "author"        : "山田太郎",
            "published_date": "2024-01-15",
            "tags"          : ["Python", "機械学習", "データサイエンス"],
            "view_count"    : 1250
        },
        {
            "title"         : "Dockerコンテナ活用術",
            "content"       : "Dockerを使ったアプリケーション開発とデプロイメントの実践的な方法を紹介します。Docker Composeも含めて解説。",
            "category"      : "技術",
            "author"        : "鈴木花子",
            "published_date": "2024-01-12",
            "tags"          : ["Docker", "DevOps", "コンテナ"],
            "view_count"    : 980
        },
        {
            "title"         : "リモートワークの効率化",
            "content"       : "在宅勤務で生産性を向上させるための具体的な方法とツールを紹介します。コミュニケーション改善のコツも。",
            "category"      : "ビジネス",
            "author"        : "田中一郎",
            "published_date": "2024-01-10",
            "tags"          : ["リモートワーク", "生産性", "働き方改革"],
            "view_count"    : 1580
        },
        {
            "title"         : "Streamlit Web アプリ開発",
            "content"       : "StreamlitでインタラクティブなWebアプリケーションを作成する方法を実例とともに解説します。",
            "category"      : "技術",
            "author"        : "佐藤美香",
            "published_date": "2024-01-08",
            "tags"          : ["Streamlit", "Python", "Webアプリ"],
            "view_count"    : 750
        },
        {
            "title"         : "AI活用ビジネス事例",
            "content"       : "企業でのAI導入成功事例と失敗事例を分析し、効果的なAI活用のポイントを解説します。",
            "category"      : "ビジネス",
            "author"        : "高橋健太",
            "published_date": "2024-01-05",
            "tags"          : ["AI", "DX", "ビジネス戦略"],
            "view_count"    : 2100
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
            "id"         : 1,
            "name"       : "高性能ノートPC",
            "category"   : "エレクトロニクス",
            "description": "プログラミングやデザイン作業に最適な高性能ノートパソコン",
            "price"      : 89800,
            "vector"     : np.random.rand(384).tolist()
        },
        {
            "id"         : 2,
            "name"       : "ワイヤレスイヤホン",
            "category"   : "エレクトロニクス",
            "description": "ノイズキャンセリング機能付きの高音質ワイヤレスイヤホン",
            "price"      : 12800,
            "vector"     : np.random.rand(384).tolist()
        },
        {
            "id"         : 3,
            "name"       : "全自動コーヒーメーカー",
            "category"   : "キッチン家電",
            "description": "豆から挽ける全自動タイプのコーヒーメーカー",
            "price"      : 15600,
            "vector"     : np.random.rand(384).tolist()
        },
        {
            "id"         : 4,
            "name"       : "レザービジネスバッグ",
            "category"   : "ファッション",
            "description": "本革製の高級ビジネスバッグ、ノートPCも収納可能",
            "price"      : 8900,
            "vector"     : np.random.rand(384).tolist()
        },
        {
            "id"         : 5,
            "name"       : "ランニングシューズ",
            "category"   : "スポーツ",
            "description": "軽量で通気性の良いランニング専用シューズ",
            "price"      : 9800,
            "vector"     : np.random.rand(384).tolist()
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
                    "name"       : product["name"],
                    "category"   : product["category"],
                    "description": product["description"],
                    "price"      : product["price"]
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
        # print("- PostgreSQL: 顧客、注文、商品データ")
        print("- Elasticsearch: ブログ記事5件")
        print("- Qdrant: 商品ベクトル5件")

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return False

    return True


if __name__ == "__main__":
    main()
