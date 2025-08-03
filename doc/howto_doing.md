### 1. 環境セットアップ
```bash
# プロジェクト作成
mkdir mcp-streamlit-demo && cd mcp-streamlit-demo
uv init streamlit-mcp-app && cd streamlit-mcp-app

# パッケージインストール
uv add streamlit openai python-dotenv pandas numpy requests redis psycopg2-binary elasticsearch qdrant-client

# 環境変数設定（.envファイル作成）
# OPENAI_API_KEY を実際のキーに設定
```
### 2. データベース起動
```bash
# Docker Compose設定をコピーして配置
# データベース群を起動
docker-compose -f docker-compose.mcp-demo.yml up -d redis postgres elasticsearch qdrant

# 起動確認
docker-compose -f docker-compose.mcp-demo.yml ps
```
### 3. テストデータ投入
```bash
# スクリプトファイルを作成・配置
# テストデータ投入実行
uv run python scripts/setup_test_data.py
```
### 4. Streamlitアプリ起動
```bash
# アプリファイルを作成・配置
### # アプリ起動
uv run streamlit run app.py
```
### 5. MCPサーバー起動（オプション）
```bash
# 実際のMCP機能を使用したい場合
docker-compose -f docker-compose.mcp-demo.yml up -d redis-mcp postgres-mcp es-mcp qdrant-mcp
```

