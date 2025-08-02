# qdrant_diagnostic.py
# Qdrantの状態を詳細に診断するスクリプト

import requests
import json


def diagnose_qdrant(url="http://localhost:6333"):
    """Qdrantの詳細診断"""
    print(f"🔍 Qdrant診断開始: {url}")
    print("=" * 50)

    # 1. 基本接続テスト
    print("\n1. 基本接続テスト")
    try:
        response = requests.get(f"{url}/", timeout=5)
        print(f"✅ 基本接続: OK (Status: {response.status_code})")
        if response.status_code == 200:
            data = response.json()
            print(f"   バージョン: {data.get('title', 'unknown')} {data.get('version', 'unknown')}")
    except Exception as e:
        print(f"❌ 基本接続: NG ({e})")
        return

    # 2. コレクション一覧
    print("\n2. コレクション一覧")
    try:
        response = requests.get(f"{url}/collections", timeout=5)
        if response.status_code == 200:
            data = response.json()
            collections = data.get('result', {}).get('collections', [])
            print(f"✅ コレクション数: {len(collections)}")
            for collection in collections:
                print(f"   - {collection['name']}")
        else:
            print(f"❌ コレクション取得失敗 (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ コレクション取得エラー: {e}")

    # 3. クラスター情報
    print("\n3. クラスター情報")
    try:
        response = requests.get(f"{url}/cluster", timeout=5)
        print(f"   クラスターエンドポイント: Status {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ クラスター機能: 有効")
            print(f"   レスポンス: {json.dumps(data, indent=2, ensure_ascii=False)}")
        elif response.status_code == 404:
            print("⚠️  クラスター機能: 無効（単一ノード構成）")
        else:
            print(f"❌ クラスター情報取得失敗")
            print(f"   レスポンス: {response.text[:200]}")
    except Exception as e:
        print(f"❌ クラスター情報エラー: {e}")

    # 4. Telemetry情報（代替）
    print("\n4. Telemetry情報")
    try:
        response = requests.get(f"{url}/telemetry", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Telemetry: 利用可能")
            result = data.get('result', {})

            # 基本情報
            print(f"   ノードID: {result.get('id', 'N/A')}")
            app_info = result.get('app', {})
            print(f"   バージョン: {app_info.get('version', 'N/A')}")
            print(f"   Git SHA: {app_info.get('commit', 'N/A')}")

            # コレクション情報
            collections_info = result.get('collections', {})
            print(f"   管理コレクション数: {len(collections_info)}")

        else:
            print(f"❌ Telemetry取得失敗 (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ Telemetry取得エラー: {e}")

    # 5. 各エンドポイントのテスト
    print("\n5. 利用可能エンドポイント")
    endpoints = [
        "/",
        "/collections",
        "/cluster",
        "/telemetry",
        "/metrics"
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(f"{url}{endpoint}", timeout=3)
            status = "✅" if response.status_code == 200 else "❌" if response.status_code >= 400 else "⚠️"
            print(f"   {status} {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"   ❌ {endpoint}: Error ({type(e).__name__})")

    print("\n" + "=" * 50)
    print("🏁 診断完了")

    # 推奨設定
    print("\n💡 推奨設定:")
    print("   - Qdrantがローカルで動作している場合は単一ノード構成が一般的です")
    print("   - クラスター機能が不要な場合は、telemetry情報で十分です")
    print("   - Dockerで起動している場合: docker run -p 6333:6333 qdrant/qdrant")


if __name__ == "__main__":
    diagnose_qdrant()

