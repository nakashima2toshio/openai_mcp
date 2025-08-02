#!/usr/bin/env python3
"""
Qdrant接続診断スクリプト
"""
import requests
import json
import time

def diagnose_qdrant():
    """Qdrant接続の診断"""
    print("🔍 Qdrant接続診断を開始...")

    host = "localhost"
    port = 6333
    base_url = f"http://{host}:{port}"

    # テストするエンドポイント一覧
    endpoints = [
        "/",
        "/health",
        "/collections",
        "/cluster",
        "/telemetry",
        "/metrics"
    ]

    results = {}

    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        print(f"\n📡 テスト中: {url}")

        try:
            response = requests.get(url, timeout=5)
            status_code = response.status_code

            if status_code == 200:
                print(f"✅ 成功: Status {status_code}")
                results[endpoint] = {
                    "status": "success",
                    "code": status_code,
                    "response_size": len(response.text)
                }

                # レスポンスの一部を表示
                try:
                    if response.text:
                        data = response.json()
                        print(f"   📄 レスポンス例: {json.dumps(data, indent=2)[:200]}...")
                except:
                    print(f"   📄 レスポンス例: {response.text[:100]}...")

            else:
                print(f"❌ エラー: Status {status_code}")
                results[endpoint] = {
                    "status": "error",
                    "code": status_code
                }

        except requests.exceptions.ConnectionError as e:
            print(f"❌ 接続エラー: {e}")
            results[endpoint] = {
                "status": "connection_error",
                "error": str(e)
            }
        except requests.exceptions.Timeout as e:
            print(f"❌ タイムアウト: {e}")
            results[endpoint] = {
                "status": "timeout",
                "error": str(e)
            }
        except Exception as e:
            print(f"❌ 予期しないエラー: {e}")
            results[endpoint] = {
                "status": "unexpected_error",
                "error": str(e)
            }

    print("\n" + "="*50)
    print("📋 診断結果サマリー")
    print("="*50)

    working_endpoints = []
    for endpoint, result in results.items():
        if result["status"] == "success":
            working_endpoints.append(endpoint)
            print(f"✅ {endpoint}: OK")
        else:
            print(f"❌ {endpoint}: {result['status']}")

    if working_endpoints:
        print(f"\n🎉 利用可能なエンドポイント: {working_endpoints}")
        print(f"💡 推奨: 最初に成功した '{working_endpoints[0]}' を使用")

        # 修正コード例を出力
        print(f"\n🔧 修正コード例:")
        print(f"response = requests.get('http://localhost:6333{working_endpoints[0]}', timeout=3)")

    else:
        print("\n💥 Qdrantサーバーに接続できません")
        print("🔧 確認事項:")
        print("  1. Dockerコンテナが起動しているか: docker ps | grep qdrant")
        print("  2. ポート6333が利用可能か: lsof -i :6333")
        print("  3. Docker Composeが正常か: docker-compose -f docker-compose.mcp-demo.yml ps")
        print("  4. ログでエラーを確認: docker-compose -f docker-compose.mcp-demo.yml logs qdrant")

if __name__ == "__main__":
    diagnose_qdrant()
