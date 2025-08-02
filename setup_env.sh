#!/bin/bash
# setup_env.sh - MCP Streamlitアプリ環境セットアップスクリプト

set -e  # エラーで停止

echo "🚀 MCP Streamlit アプリ環境をセットアップ中..."

# 1. 現在の環境確認
echo "📋 現在の環境を確認中..."
echo "Python: $(python --version)"
echo "pip: $(pip --version)"

# uvがインストールされているかチェック
if command -v uv &> /dev/null; then
    echo "uv: $(uv --version)"
    USE_UV=true
else
    echo "uv: インストールされていません (pipを使用)"
    USE_UV=false
fi

# 2. requirements.txtの作成
echo "📝 requirements.txt を作成中..."
cat > requirements.txt << 'EOF'
# Core packages
streamlit>=1.28.0
openai>=1.3.0
python-dotenv>=1.0.0

# Data processing
pandas>=2.0.0
numpy>=1.24.0
requests>=2.31.0

# Database clients
redis>=5.0.0
psycopg2-binary>=2.9.0
elasticsearch>=8.10.0
qdrant-client>=1.6.0

# Optional performance packages
watchdog>=3.0.0
EOF

# 3. パッケージのインストール
echo "📦 パッケージをインストール中..."

if [ "$USE_UV" = true ]; then
    echo "uvを使用してインストール..."

    # uvプロジェクトを初期化（既存の場合はスキップ）
    if [ ! -f "pyproject.toml" ]; then
        uv init .
    fi

    # 依存関係を追加
    uv add streamlit openai python-dotenv pandas numpy requests redis psycopg2-binary elasticsearch qdrant-client watchdog

    echo "✅ uvでインストール完了"
else
    echo "pipを使用してインストール..."
    pip install -r requirements.txt
    echo "✅ pipでインストール完了"
fi

# 4. .envファイルのテンプレート作成
echo "🔧 .env テンプレートを作成中..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# OpenAI API Key (必須)
OPENAI_API_KEY=your-openai-api-key-here

# Database URLs
REDIS_URL=redis://localhost:6379/0
PG_CONN_STR=postgresql://testuser:testpass@localhost:5432/testdb
ELASTIC_URL=http://localhost:9200
QDRANT_URL=http://localhost:6333

# Optional API Keys
PINECONE_API_KEY=your-pinecone-api-key-here
SEARCH_API_KEY=your-search-api-key-here
EOF
    echo "⚠️  .env ファイルを作成しました。OPENAI_API_KEY を設定してください。"
else
    echo "✅ .env ファイルは既に存在します"
fi

# 5. インストール確認
echo "🔍 インストールを確認中..."

# 重要なパッケージの確認
packages=("streamlit" "openai" "redis" "psycopg2" "pandas")
missing_packages=()

for package in "${packages[@]}"; do
    if python -c "import $package" 2>/dev/null; then
        echo "✅ $package: インストール済み"
    else
        echo "❌ $package: インストールされていません"
        missing_packages+=("$package")
    fi
done

# 6. エラーチェック
if [ ${#missing_packages[@]} -gt 0 ]; then
    echo "🚨 以下のパッケージが不足しています:"
    printf '%s\n' "${missing_packages[@]}"
    echo ""
    echo "手動でインストールしてください:"
    if [ "$USE_UV" = true ]; then
        echo "uv add ${missing_packages[*]}"
    else
        echo "pip install ${missing_packages[*]}"
    fi
    exit 1
fi

# 7. Streamlitアプリの存在確認
if [ -f "a_mcp_sample.py" ]; then
    echo "✅ Streamlitアプリファイル (a_mcp_sample.py) が見つかりました"

    # 8. アプリ起動テスト
    echo "🧪 アプリの構文チェック中..."
    if python -m py_compile openai_api_mcp_sample.py; then
        echo "✅ 構文チェック完了"
    else
        echo "❌ 構文エラーがあります"
        exit 1
    fi
else
    echo "⚠️  Streamlitアプリファイル (a_mcp_sample.py) が見つかりません"
    echo "app.py として作成してください"
fi

# 9. 起動コマンドの提示
echo ""
echo "🎉 環境セットアップ完了！"
echo ""
echo "次のステップ:"
echo "1. .env ファイルで OPENAI_API_KEY を設定"
echo "2. Dockerでデータベースを起動:"
echo "   docker-compose -f docker-compose.mcp-demo.yml up -d"
echo "3. テストデータを投入:"
echo "   python scripts/setup_test_data.py"
echo "4. Streamlitアプリを起動:"

if [ "$USE_UV" = true ]; then
    echo "   uv run streamlit run a_mcp_sample.py --server.port=8501"
else
    echo "   streamlit run a_mcp_sample.py --server.port=8501"
fi

echo ""
echo "🌐 ブラウザで http://localhost:8501 にアクセス"
echo ""
