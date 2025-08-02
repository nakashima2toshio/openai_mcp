# データセットアップ用のサンプルスクリプト
# setup_sample_data.py

import requests
import json
import time


def setup_elasticsearch_data():
    """Elasticsearchにサンプルデータを投入"""
    es_url = "http://localhost:9200"

    # インデックス作成
    index_config = {
        "mappings": {
            "properties": {
                "title"         : {"type": "text", "analyzer": "standard"},
                "content"       : {"type": "text", "analyzer": "standard"},
                "category"      : {"type": "keyword"},
                "author"        : {"type": "keyword"},
                "published_date": {"type": "date"},
                "view_count"    : {"type": "integer"},
                "tags"          : {"type": "keyword"}
            }
        }
    }

    # インデックスの作成
    try:
        response = requests.put(f"{es_url}/blog_articles", json=index_config)
        print(f"Index creation: {response.status_code}")
    except Exception as e:
        print(f"Error creating index: {e}")
        return

    # サンプル記事データ
    sample_articles = [
        {
            "title"         : "Pythonプログラミング入門",
            "content"       : "Pythonは初心者にも学びやすいプログラミング言語です。文法がシンプルで、豊富なライブラリが特徴です。",
            "category"      : "プログラミング",
            "author"        : "田中太郎",
            "published_date": "2024-01-15",
            "view_count"    : 1250,
            "tags"          : ["Python", "入門", "プログラミング"]
        },
        {
            "title"         : "機械学習の基礎",
            "content"       : "機械学習は人工知能の一分野で、データからパターンを学習してモデルを構築する技術です。",
            "category"      : "AI・機械学習",
            "author"        : "佐藤花子",
            "published_date": "2024-01-20",
            "view_count"    : 890,
            "tags"          : ["機械学習", "AI", "データサイエンス"]
        },
        {
            "title"         : "Docker入門ガイド",
            "content"       : "Dockerはコンテナ技術を使ってアプリケーションを効率的にデプロイできるツールです。",
            "category"      : "インフラ",
            "author"        : "山田次郎",
            "published_date": "2024-01-25",
            "view_count"    : 650,
            "tags"          : ["Docker", "コンテナ", "DevOps"]
        },
        {
            "title"         : "Streamlitでダッシュボード作成",
            "content"       : "Streamlitを使うと簡単にWebアプリケーションやダッシュボードを作成できます。",
            "category"      : "プログラミング",
            "author"        : "鈴木三郎",
            "published_date": "2024-02-01",
            "view_count"    : 430,
            "tags"          : ["Streamlit", "Python", "ダッシュボード"]
        },
        {
            "title"         : "ElasticsearchとKibanaで分析",
            "content"       : "ElasticsearchとKibanaを組み合わせることで強力なデータ分析環境を構築できます。",
            "category"      : "データ分析",
            "author"        : "高橋四郎",
            "published_date": "2024-02-05",
            "view_count"    : 720,
            "tags"          : ["Elasticsearch", "Kibana", "データ分析"]
        }
    ]

    # データの投入
    for i, article in enumerate(sample_articles, 1):
        try:
            response = requests.post(f"{es_url}/blog_articles/_doc/{i}", json=article)
            print(f"Article {i}: {response.status_code}")
        except Exception as e:
            print(f"Error inserting article {i}: {e}")

    # インデックスをリフレッシュ
    try:
        requests.post(f"{es_url}/blog_articles/_refresh")
        print("Index refreshed")
    except Exception as e:
        print(f"Error refreshing index: {e}")


def setup_qdrant_data():
    """Qdrantにサンプルデータを投入"""
    qdrant_url = "http://localhost:6333"

    # コレクション作成
    collection_config = {
        "vectors": {
            "size"    : 384,  # sentence-transformersの一般的なサイズ
            "distance": "Cosine"
        }
    }

    try:
        response = requests.put(f"{qdrant_url}/collections/product_embeddings", json=collection_config)
        print(f"Collection creation: {response.status_code}")
    except Exception as e:
        print(f"Error creating collection: {e}")
        return

    # サンプル商品データ（ベクトルはダミー）
    import random

    sample_products = [
        {
            "id"     : 1,
            "payload": {
                "name"       : "ワイヤレスヘッドホン",
                "description": "高音質のBluetoothワイヤレスヘッドホン。ノイズキャンセリング機能付き。",
                "category"   : "エレクトロニクス",
                "price"      : 15800,
                "brand"      : "TechSound"
            },
            "vector" : [random.uniform(-1, 1) for _ in range(384)]
        },
        {
            "id"     : 2,
            "payload": {
                "name"       : "コーヒーメーカー",
                "description": "自動ドリップ式コーヒーメーカー。タイマー機能付きで朝の準備が楽に。",
                "category"   : "キッチン家電",
                "price"      : 8900,
                "brand"      : "BrewMaster"
            },
            "vector" : [random.uniform(-1, 1) for _ in range(384)]
        },
        {
            "id"     : 3,
            "payload": {
                "name"       : "ランニングシューズ",
                "description": "軽量で通気性の良いランニングシューズ。長距離走に最適。",
                "category"   : "スポーツ",
                "price"      : 12500,
                "brand"      : "RunFast"
            },
            "vector" : [random.uniform(-1, 1) for _ in range(384)]
        },
        {
            "id"     : 4,
            "payload": {
                "name"       : "ビジネスバッグ",
                "description": "耐久性の高いナイロン製ビジネスバッグ。PC収納スペース付き。",
                "category"   : "ファッション",
                "price"      : 6800,
                "brand"      : "ProBag"
            },
            "vector" : [random.uniform(-1, 1) for _ in range(384)]
        },
        {
            "id"     : 5,
            "payload": {
                "name"       : "スマートウォッチ",
                "description": "健康管理機能付きスマートウォッチ。心拍数や歩数を測定。",
                "category"   : "エレクトロニクス",
                "price"      : 22000,
                "brand"      : "HealthTech"
            },
            "vector" : [random.uniform(-1, 1) for _ in range(384)]
        }
    ]

    # データの投入
    points_data = {
        "points": sample_products
    }

    try:
        response = requests.put(f"{qdrant_url}/collections/product_embeddings/points", json=points_data)
        print(f"Points insertion: {response.status_code}")
    except Exception as e:
        print(f"Error inserting points: {e}")


if __name__ == "__main__":
    print("🚀 サンプルデータをセットアップ中...")

    print("\n📄 Elasticsearchデータセットアップ")
    setup_elasticsearch_data()

    print("\n🔍 Qdrantデータセットアップ")
    setup_qdrant_data()

    print("\n✅ セットアップ完了!")
    print("\n💡 使用方法:")
    print("1. Dockerサービスを起動: docker-compose -f docker-compose.mcp-demo.yml up -d")
    print("2. このスクリプトを実行: python setup_sample_data.py")
    print("3. Streamlitアプリを起動: streamlit run openai_api_mcp_sample.py")

