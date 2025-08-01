# 🧪 a10_00_openai_skeleton.py テスト計画書

## 🌟 テスト概要

現在のプロジェクト構成に基づく、a10_00_openai_skeleton.py の包括的テスト計画です。

| 項目 | 内容 |
|------|------|
| **テスト対象** | a10_00_openai_skeleton.py |
| **関連ファイル** | helper.py, config.yaml |
| **プロジェクト構成** | 既存のディレクトリ構造を維持 |
| **テスト配置** | ルートディレクトリにテストファイル作成 |

### 📁 現在のプロジェクト構成

```
プロジェクトルート/
├── a10_00_openai_skeleton.py    # ← テスト対象
├── helper.py                    # ← 依存ファイル
├── config.yaml                  # ← 設定ファイル
├── tests/                       # ← 新規作成（テスト専用）
├── doc/                         # 既存ドキュメント
├── data/                        # 既存データ
└── requirements.txt             # 既存依存関係
```

---

## 🛠️ 1. テスト環境作成（修正版）

### ⚠️ エラー対応

`pytest-streamlit` パッケージは存在しないため、実用的なStreamlitテスト手法を採用します。

### 💻 1.1 環境構築手順（修正版）

#### Step 1: 現在の環境確認

```bash
# 現在のディレクトリ確認
pwd
ls -la | grep -E "(a10_00_openai_skeleton|helper|config)"

# Python環境確認
python --version
pip list | grep -E "(streamlit|openai|tiktoken|yaml)"
```

#### Step 2: テスト専用ディレクトリ作成

```bash
# テストディレクトリ作成
mkdir -p tests
mkdir -p tests/fixtures
mkdir -p tests/data
mkdir -p tests/utils
mkdir -p coverage
mkdir -p logs/test

# テスト用設定ディレクトリ
mkdir -p config
```

#### Step 3: テスト依存関係追加（修正版）

```bash
# requirements-test.txt 作成（実在するパッケージのみ）
cat > requirements-test.txt << EOF
# 基本テスト
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.1
pytest-asyncio>=0.21.1

# Webテスト（Streamlit E2Eテスト用）
selenium>=4.15.0
webdriver-manager>=4.0.0

# APIモック
responses>=0.23.3
requests-mock>=1.11.0

# 日時モック
freezegun>=1.2.2

# パフォーマンステスト
pytest-benchmark>=4.0.0
memory-profiler>=0.60.0

# コード品質
flake8>=6.0.0
black>=23.0.0
mypy>=1.5.0

# 追加ユーティリティ
psutil>=5.9.0
timeout-decorator>=0.5.0
EOF

# 段階的インストール
echo "🔄 基本テストツールをインストール..."
pip install pytest pytest-cov pytest-mock pytest-asyncio

echo "🔄 モックライブラリをインストール..."
pip install responses requests-mock freezegun

echo "🔄 パフォーマンス・品質ツールをインストール..."
pip install pytest-benchmark memory-profiler flake8 black mypy

echo "🔄 ユーティリティをインストール..."
pip install psutil timeout-decorator

# オプション: Webテストツール（必要な場合のみ）
echo "🔄 Webテストツール（オプション）..."
read -p "Selenium E2Eテストをインストールしますか？ (y/n): " install_selenium
if [[ $install_selenium == "y" ]]; then
    pip install selenium webdriver-manager
    echo "✅ Seleniumインストール完了"
else
    echo "⏭️ Seleniumはスキップしました"
fi
```

#### Step 4: 簡易動作確認

```bash
# インストール確認
echo "📋 インストール確認..."
python -c "
import pytest
import pytest_cov
import responses
print('✅ 基本テストツール: OK')

try:
    import selenium
    print('✅ Selenium: OK')
except ImportError:
    print('⏭️ Selenium: スキップ')

print('🎉 テスト環境準備完了！')
"
```

### 🔧 1.2 Streamlitテスト戦略

Streamlitアプリのテストは以下の3段階アプローチを採用：

| レベル | 手法 | 対象 | 実装難易度 |
|--------|------|------|------------|
| **Level 1** | ロジック単体テスト | helper.py、ビジネスロジック | 低 |
| **Level 2** | モックベーステスト | Streamlitコンポーネント | 中 |
| **Level 3** | E2Eテスト | 完全なUIフロー | 高 |

#### Level 1: ロジック単体テスト（推奨開始点）

```python
# tests/test_logic_only.py
"""Streamlit以外のロジック部分のテスト"""

def test_helper_functions():
    """helper.pyの関数テスト（Streamlit非依存）"""
    from helper import TokenManager, ConfigManager

    # TokenManagerのテスト
    token_count = TokenManager.count_tokens("テストテキスト", "gpt-4o-mini")
    assert isinstance(token_count, int)
    assert token_count > 0

    # ConfigManagerのテスト
    config = ConfigManager("config.yaml")
    default_model = config.get("models.default", "gpt-4o-mini")
    assert isinstance(default_model, str)
```

#### Level 2: モックベーステスト

```python
# tests/test_streamlit_mock.py
"""Streamlit要素のモックテスト"""

import pytest
from unittest.mock import Mock, patch
import sys

# Streamlitモックの設定
sys.modules['streamlit'] = Mock()

def test_demo_logic_with_mock():
    """デモロジックのモックテスト"""
    with patch('streamlit.selectbox') as mock_selectbox:
        mock_selectbox.return_value = "gpt-4o-mini"

        # テスト対象のインポート（モック後）
        from a10_00_openai_skeleton import SimpleChatDemo

        demo = SimpleChatDemo("test_chat", "テストチャット")
        assert demo.demo_name == "test_chat"
```

#### Level 3: E2Eテスト（オプション）

```python
# tests/test_e2e.py
"""E2Eテスト（Seleniumを使用）"""

import pytest
import subprocess
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

@pytest.mark.e2e
def test_app_startup():
    """アプリ起動テスト"""
    # Streamlitアプリを別プロセスで起動
    process = subprocess.Popen([
        "streamlit", "run", "a10_00_openai_skeleton.py",
        "--server.port=8502", "--server.headless=true"
    ])

    time.sleep(5)  # 起動待機

    try:
        # ブラウザ設定
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)

        # アプリにアクセス
        driver.get("http://localhost:8502")
        time.sleep(3)

        # タイトル確認
        title = driver.find_element(By.TAG_NAME, "h1").text
        assert "OpenAI" in title

        driver.quit()
    finally:
        process.terminate()
```

### 🚀 1.3 段階的テスト実行

#### Phase 1: 基本テスト環境確認

```bash
# Phase 1: 基本動作確認
echo "🧪 Phase 1: 基本テスト環境確認"

# pytest動作確認
pytest --version

# 簡単なテスト実行
python -c "
import helper
import a10_00_openai_skeleton
print('✅ モジュールインポート: OK')
"

# 設定ファイル確認
python -c "
from helper import ConfigManager
config = ConfigManager('config.yaml')
print(f'✅ 設定読み込み: {config.get(\"models.default\")}')
"
```

#### Phase 2: ロジックテスト実行

```bash
# Phase 2: ロジック部分のテスト
echo "🧪 Phase 2: ロジックテスト"

# helper.pyのロジックテスト
pytest tests/test_helper.py -v --tb=short

# 基本的な動作確認
pytest tests/test_logic_only.py -v
```

#### Phase 3: モックテスト実行

```bash
# Phase 3: Streamlitモックテスト
echo "🧪 Phase 3: モックテスト"

# Streamlitをモックしたテスト
pytest tests/test_streamlit_mock.py -v
```

#### Phase 4: 総合テスト（オプション）

```bash
# Phase 4: E2Eテスト（Seleniumが必要）
echo "🧪 Phase 4: E2Eテスト"

# E2Eテスト実行（時間がかかります）
pytest tests/test_e2e.py -v -m e2e
```

#### Step 3: テスト依存関係追加

```bash
# requirements-test.txt 作成（修正版）
cat > requirements-test.txt << EOF
# 基本テスト
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.1
pytest-asyncio>=0.21.1

# Streamlitテスト（実在するパッケージ）
selenium>=4.15.0
webdriver-manager>=4.0.0

# APIモック
responses>=0.23.3
requests-mock>=1.11.0

# 日時モック
freezegun>=1.2.2

# パフォーマンステスト
pytest-benchmark>=4.0.0
memory-profiler>=0.60.0

# コード品質
flake8>=6.0.0
black>=23.0.0
mypy>=1.5.0

# 追加ユーティリティ
psutil>=5.9.0
timeout-decorator>=0.5.0
EOF

# インストール
pip install -r requirements-test.txt
```

### 🔧 1.2 テスト設定ファイル作成

#### pytest設定

```bash
# pytest.ini 作成
cat > pytest.ini << 'EOF'
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
    --disable-warnings
markers =
    unit: 単体テスト
    integration: 統合テスト
    ui: UIテスト
    functional: 機能テスト
    performance: パフォーマンステスト
    slow: 実行時間の長いテスト
    api: API呼び出しテスト
EOF
```

#### テスト用設定ファイル

```bash
# config/config_test.yaml 作成
cat > config/config_test.yaml << 'EOF'
models:
  default: "gpt-4o-mini"
  available:
    - "gpt-4o-mini"
    - "gpt-4o"

api:
  timeout: 10
  max_retries: 2

ui:
  page_title: "Test OpenAI API Demo"
  layout: "wide"
  message_display_limit: 10

app:
  demo_categories:
    - name: "基本機能"
      demos: ["simple_chat", "token_counter"]
    - name: "応用機能"
      demos: ["structured_output"]

  demo_titles:
    simple_chat: "テストチャット"
    structured_output: "テスト構造化出力"
    token_counter: "テストトークンカウンター"

experimental:
  debug_mode: true
  performance_monitoring: true

cache:
  enabled: false
  ttl: 60
  max_size: 10

model_pricing:
  gpt-4o-mini:
    input: 0.00015
    output: 0.0006
  gpt-4o:
    input: 0.005
    output: 0.015
EOF
```

### 🔑 1.3 環境変数設定

```bash
# .env.test ファイル作成
cat > .env.test << 'EOF'
# テスト用OpenAI API Key
OPENAI_API_KEY=sk-test-dummy-key-for-testing
OPENAI_API_KEY_TEST=sk-test-dummy-key-for-testing

# テスト用設定
PYTHONPATH=.
STREAMLIT_SERVER_PORT=8502
STREAMLIT_SERVER_HEADLESS=true

# テスト用ログレベル
LOG_LEVEL=DEBUG
TEST_MODE=true
EOF

# 環境変数読み込み
source .env.test
```

---

## 🧪 2. テストの準備

### 📋 2.1 テストファイル構成

| ファイル | 対象 | 内容 |
|----------|------|------|
| `tests/conftest.py` | 共通設定 | fixtureやpytest設定 |
| `tests/test_helper.py` | helper.py | 各クラス・関数の単体テスト |
| `tests/test_skeleton.py` | a10_00_openai_skeleton.py | メインアプリのテスト |
| `tests/test_integration.py` | 連携テスト | API連携・E2Eテスト |
| `tests/test_ui.py` | UIテスト | Streamlit UI動作テスト |
| `tests/fixtures/` | テストデータ | モックデータ・サンプル |

### 🔧 2.2 基本テストファイル作成

#### conftest.py（共通設定）

```python
# tests/conftest.py
import pytest
import os
import sys
from unittest.mock import Mock, patch
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def mock_openai_client():
    """OpenAI クライアントのモック"""
    with patch('openai.OpenAI') as mock:
        client = Mock()

        # モックレスポンス
        response = Mock()
        response.id = "resp_test_123"
        response.model = "gpt-4o-mini"
        response.output = [
            Mock(
                type="message",
                content=[
                    Mock(type="output_text", text="テスト応答")
                ]
            )
        ]
        response.usage = Mock(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15
        )

        client.responses.create.return_value = response
        mock.return_value = client
        yield client

@pytest.fixture
def test_config_path():
    """テスト用設定ファイルパス"""
    return "config/config_test.yaml"

@pytest.fixture
def sample_text():
    """テスト用サンプルテキスト"""
    return {
        "short": "これは短いテストです。",
        "medium": "これは中程度の長さのテストテキストです。" * 10,
        "long": "これは長いテストテキストです。" * 100,
        "json_request": "以下の商品を分析してください：素晴らしい商品でした！"
    }

@pytest.fixture(scope="session")
def setup_test_environment():
    """テスト環境のセットアップ"""
    # テスト用ディレクトリ作成
    os.makedirs("logs/test", exist_ok=True)
    os.makedirs("tests/fixtures", exist_ok=True)

    # 環境変数設定
    os.environ["TEST_MODE"] = "true"
    os.environ["OPENAI_API_KEY"] = "sk-test-dummy"

    yield

    # クリーンアップ
    # テスト後の清掃処理
```

### 📊 2.3 テストデータ準備

#### モックレスポンス

```python
# tests/fixtures/mock_responses.py
"""OpenAI API モックレスポンス定義"""

MOCK_CHAT_RESPONSE = {
    "id": "resp_test_123",
    "model": "gpt-4o-mini",
    "created_at": "2025-01-01T00:00:00Z",
    "output": [
        {
            "type": "message",
            "content": [
                {
                    "type": "output_text",
                    "text": "これはテスト用の応答メッセージです。"
                }
            ]
        }
    ],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 8,
        "total_tokens": 18
    }
}

MOCK_JSON_RESPONSE = {
    "id": "resp_test_456",
    "model": "gpt-4o-mini",
    "output": [
        {
            "type": "message",
            "content": [
                {
                    "type": "output_text",
                    "text": '{"評価": 5, "良い点": ["高品質", "使いやすい"], "改善点": ["価格"]}'
                }
            ]
        }
    ],
    "usage": {
        "prompt_tokens": 25,
        "completion_tokens": 15,
        "total_tokens": 40
    }
}

MOCK_ERROR_RESPONSE = {
    "error": {
        "type": "invalid_request_error",
        "message": "Invalid API key provided",
        "code": "invalid_api_key"
    }
}
```

#### テスト用データ

```python
# tests/fixtures/test_data.py
"""テスト用データ定義"""

# テキストサンプル
TEXT_SAMPLES = {
    "empty": "",
    "short": "短い",
    "medium": "これは中程度の長さのテストテキストです。" * 5,
    "long": "これは長いテストテキストです。" * 50,
    "japanese": "これは日本語のテストです。OpenAI APIを使用しています。",
    "english": "This is an English test. We are using OpenAI API.",
    "mixed": "This is 混合 text with English and 日本語.",
    "special_chars": "特殊文字：!@#$%^&*()[]{}|;':\",./<>?",
    "unicode": "🚀🤖🧪✅❌⚡📊🎯🔧"
}

# メッセージサンプル
MESSAGE_SAMPLES = [
    {"role": "user", "content": "こんにちは"},
    {"role": "assistant", "content": "こんにちは！どのようにお手伝いできますか？"},
    {"role": "user", "content": "天気を教えて"},
    {"role": "assistant", "content": "申し訳ございませんが、リアルタイムの天気情報は提供できません。"}
]

# 構造化出力テストケース
STRUCTURED_OUTPUT_CASES = [
    {
        "task": "商品レビューの分析",
        "input": "この商品は素晴らしいです。品質が高く、使いやすいです。ただし、価格がもう少し安ければと思います。",
        "expected_keys": ["評価", "良い点", "改善点"]
    },
    {
        "task": "テキストの要約",
        "input": "人工知能（AI）は、人間の知能を模倣する技術です。機械学習、深層学習、自然言語処理などの分野があります。近年、ChatGPTなどの大規模言語モデルが注目されています。",
        "expected_keys": ["タイトル", "要点", "結論"]
    },
    {
        "task": "感情分析",
        "input": "今日はとても楽しい一日でした！友達と会って美味しい食事をして、映画も見ました。",
        "expected_keys": ["感情", "強度", "理由"]
    }
]
```

## 🧪 3. テスト実施手順（実用版）

### 📋 3.1 即座に実行可能なテスト手順

#### 🚀 Quick Start（5分で開始）

```bash
# 1. 基本テストディレクトリ作成
mkdir -p tests

# 2. 最小限のテスト依存関係インストール
pip install pytest pytest-cov pytest-mock

# 3. 基本動作確認テスト作成
cat > tests/test_basic.py << 'EOF'
"""基本動作確認テスト"""
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """基本インポートテスト"""
    try:
        import helper
        print("✅ helper.py インポート成功")
    except ImportError as e:
        print(f"❌ helper.py インポート失敗: {e}")
        raise

    try:
        import a10_00_openai_skeleton
        print("✅ skeleton.py インポート成功")
    except ImportError as e:
        print(f"❌ skeleton.py インポート失敗: {e}")
        raise

def test_config_file():
    """設定ファイル確認"""
    import os
    assert os.path.exists("config.yaml"), "config.yaml が見つかりません"
    print("✅ config.yaml 存在確認")

def test_helper_basic():
    """helper.py基本機能テスト"""
    from helper import ConfigManager, TokenManager

    # ConfigManager基本テスト
    config = ConfigManager("config.yaml")
    default_model = config.get("models.default", "gpt-4o-mini")
    assert isinstance(default_model, str)
    print(f"✅ デフォルトモデル: {default_model}")

    # TokenManager基本テスト
    text = "これはテストです。"
    tokens = TokenManager.count_tokens(text, default_model)
    assert isinstance(tokens, int)
    assert tokens > 0
    print(f"✅ トークン計算: {tokens}")

if __name__ == "__main__":
    test_imports()
    test_config_file()
    test_helper_basic()
    print("🎉 基本テスト完了!")
EOF

# 4. 基本テスト実行
echo "🧪 基本テスト実行..."
python tests/test_basic.py

# 5. pytest実行
echo "🧪 pytest実行..."
pytest tests/test_basic.py -v
```

#### 🔧 段階的テスト構築

##### Stage 1: ファイル存在・インポート確認

```bash
# tests/test_stage1_existence.py 作成
cat > tests/test_stage1_existence.py << 'EOF'
"""Stage 1: ファイル存在・インポート確認"""
import sys
import os
import pytest

# パス設定
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestFileExistence:
    """ファイル存在確認"""

    def test_main_files_exist(self):
        """メインファイル存在確認"""
        assert os.path.exists("a10_00_openai_skeleton.py")
        assert os.path.exists("helper.py")
        assert os.path.exists("config.yaml")

    def test_import_helper(self):
        """helper.py インポート"""
        import helper
        assert hasattr(helper, 'ConfigManager')
        assert hasattr(helper, 'TokenManager')
        assert hasattr(helper, 'MessageManager')

    def test_import_skeleton(self):
        """skeleton.py インポート"""
        import a10_00_openai_skeleton
        assert hasattr(a10_00_openai_skeleton, 'OpenAISkeletonApp')
        assert hasattr(a10_00_openai_skeleton, 'SimpleChatDemo')
EOF

# Stage 1実行
pytest tests/test_stage1_existence.py -v
```

##### Stage 2: helper.pyロジックテスト

```bash
# tests/test_stage2_helper.py 作成
cat > tests/test_stage2_helper.py << 'EOF'
"""Stage 2: helper.py ロジックテスト"""
import sys
import os
import pytest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestConfigManager:
    """ConfigManager テスト"""

    def test_config_loading(self):
        """設定読み込みテスト"""
        from helper import ConfigManager
        config = ConfigManager("config.yaml")

        # 基本取得
        default_model = config.get("models.default")
        assert default_model is not None

        # デフォルト値
        non_existent = config.get("non.existent.key", "default_value")
        assert non_existent == "default_value"

class TestTokenManager:
    """TokenManager テスト"""

    def test_token_counting(self):
        """トークンカウントテスト"""
        from helper import TokenManager

        # 基本テキスト
        tokens = TokenManager.count_tokens("Hello world", "gpt-4o-mini")
        assert isinstance(tokens, int)
        assert tokens > 0

        # 日本語テキスト
        tokens_jp = TokenManager.count_tokens("こんにちは世界", "gpt-4o-mini")
        assert isinstance(tokens_jp, int)
        assert tokens_jp > 0

        # 空文字
        tokens_empty = TokenManager.count_tokens("", "gpt-4o-mini")
        assert tokens_empty >= 0

    def test_cost_estimation(self):
        """コスト推定テスト"""
        from helper import TokenManager

        cost = TokenManager.estimate_cost(100, 50, "gpt-4o-mini")
        assert isinstance(cost, float)
        assert cost >= 0

    def test_model_limits(self):
        """モデル制限テスト"""
        from helper import TokenManager

        limits = TokenManager.get_model_limits("gpt-4o-mini")
        assert isinstance(limits, dict)
        assert "max_tokens" in limits
        assert "max_output" in limits

class TestMessageManager:
    """MessageManager テスト"""

    @patch('streamlit.session_state', {})
    def test_message_management(self):
        """メッセージ管理テスト"""
        from helper import MessageManager

        # モックセッションステート
        import streamlit as st
        st.session_state = {}

        manager = MessageManager("test_messages")

        # メッセージ追加
        manager.add_message("user", "テストメッセージ")
        messages = manager.get_messages()

        # 確認
        user_messages = [m for m in messages if m.get('role') == 'user']
        assert len(user_messages) > 0
        assert any("テストメッセージ" in str(m.get('content', '')) for m in user_messages)
EOF

# Stage 2実行
pytest tests/test_stage2_helper.py -v
```

##### Stage 3: skeleton.pyロジックテスト

```bash
# tests/test_stage3_skeleton.py 作成
cat > tests/test_stage3_skeleton.py << 'EOF'
"""Stage 3: skeleton.py ロジックテスト"""
import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Streamlitモック設定
streamlit_mock = MagicMock()
streamlit_mock.session_state = {}
sys.modules['streamlit'] = streamlit_mock

class TestDemoClasses:
    """デモクラステスト"""

    def test_simple_chat_demo_creation(self):
        """SimpleChatDemo作成テスト"""
        from a10_00_openai_skeleton import SimpleChatDemo

        demo = SimpleChatDemo("test_chat", "テストチャット")
        assert demo.demo_name == "test_chat"
        assert demo.title == "テストチャット"
        assert hasattr(demo, 'run')

    def test_structured_output_demo_creation(self):
        """StructuredOutputDemo作成テスト"""
        from a10_00_openai_skeleton import StructuredOutputDemo

        demo = StructuredOutputDemo("test_structured", "テスト構造化")
        assert demo.demo_name == "test_structured"
        assert hasattr(demo, 'run')

    def test_token_counter_demo_creation(self):
        """TokenCounterDemo作成テスト"""
        from a10_00_openai_skeleton import TokenCounterDemo

        demo = TokenCounterDemo("test_token", "テストトークン")
        assert demo.demo_name == "test_token"
        assert hasattr(demo, 'run')

class TestDemoManager:
    """DemoManager テスト"""

    def test_demo_manager_creation(self):
        """DemoManager作成テスト"""
        from a10_00_openai_skeleton import DemoManager

        manager = DemoManager()
        assert hasattr(manager, 'demos')
        assert hasattr(manager, 'run_demo')

        # 基本デモの存在確認
        assert 'simple_chat' in manager.demos
        assert 'structured_output' in manager.demos
        assert 'token_counter' in manager.demos

class TestMainApp:
    """メインアプリテスト"""

    def test_app_creation(self):
        """アプリ作成テスト"""
        from a10_00_openai_skeleton import OpenAISkeletonApp

        app = OpenAISkeletonApp()
        assert hasattr(app, 'demo_manager')
        assert hasattr(app, 'run')
EOF

# Stage 3実行
pytest tests/test_stage3_skeleton.py -v
```

### 📊 3.2 実行結果確認表

#### テスト実行マトリックス

| Stage | テスト内容 | 実行コマンド | 期待結果 | 実行時間 |
|-------|------------|--------------|----------|----------|
| **Quick Start** | 基本動作確認 | `python tests/test_basic.py` | 全て✅ | 10秒 |
| **Stage 1** | ファイル存在・インポート | `pytest tests/test_stage1_existence.py -v` | 3/3 PASSED | 5秒 |
| **Stage 2** | helper.pyロジック | `pytest tests/test_stage2_helper.py -v` | 全テストPASSED | 15秒 |
| **Stage 3** | skeleton.pyロジック | `pytest tests/test_stage3_skeleton.py -v` | 全テストPASSED | 10秒 |
| **All Tests** | 全体テスト | `pytest tests/ -v` | 全テストPASSED | 30秒 |

#### 実行コマンド一覧

```bash
# 🚀 全体実行スクリプト
echo "🧪 段階的テスト実行開始"

# Stage 1: 基本確認
echo "📋 Stage 1: ファイル存在・インポート確認"
pytest tests/test_stage1_existence.py -v || exit 1

# Stage 2: helper.pyテスト
echo "🔧 Stage 2: helper.pyロジックテスト"
pytest tests/test_stage2_helper.py -v || exit 1

# Stage 3: skeleton.pyテスト
echo "🎮 Stage 3: skeleton.pyロジックテスト"
pytest tests/test_stage3_skeleton.py -v || exit 1

# カバレッジ測定
echo "📊 カバレッジ測定"
pytest tests/ --cov=. --cov-include="*.py" --cov-exclude="tests/*" --cov-report=term

echo "✅ 全テスト完了！"
```

#### 問題発生時のデバッグ

```bash
# 詳細エラー情報
pytest tests/ -v -s --tb=long

# 特定テストのみ実行
pytest tests/test_stage2_helper.py::TestTokenManager::test_token_counting -v -s

# テスト失敗時の対話デバッグ
pytest tests/ --pdb

# 実行時間測定
pytest tests/ --durations=10
```

### 🎯 3.3 成功基準チェックリスト

| 項目 | 確認内容 | 完了 |
|------|----------|------|
| **環境** | Python、pip、依存関係インストール | ☐ |
| **ファイル** | a10_00_openai_skeleton.py、helper.py、config.yaml存在 | ☐ |
| **インポート** | モジュールが正常にインポートできる | ☐ |
| **設定** | config.yamlが正常に読み込める | ☐ |
| **ロジック** | helper.pyの各クラスが動作する | ☐ |
| **デモ** | skeleton.pyのデモクラスが作成できる | ☐ |
| **統合** | 全体が連携して動作する | ☐ |

この段階的アプローチにより、確実にテストを構築・実行できます！🎯

---

## 📊 4. テスト実施表

### 🎯 4.1 テスト実行マトリックス

| テスト種別 | ファイル | 実行時間 | カバレッジ目標 | 合格基準 |
|------------|----------|----------|----------------|----------|
| **単体テスト** | test_helper.py | ~30s | 95% | 全ケース成功 |
| **アプリテスト** | test_skeleton.py | ~45s | 90% | 全ケース成功 |
| **統合テスト** | test_integration.py | ~60s | 85% | 全ケース成功 |
| **UIテスト** | test_ui.py | ~90s | 80% | 全ケース成功 |
| **総合テスト** | 全テスト | ~3-5分 | 88% | 95%以上成功 |

### 📈 4.2 品質指標

| 指標 | 目標値 | 測定方法 | 判定基準 |
|------|--------|----------|----------|
| **テスト成功率** | 95%以上 | pytest結果 | PASSED/TOTAL |
| **コードカバレッジ** | 88%以上 | pytest-cov | ライン+ブランチ |
| **実行時間** | 5分以内 | タイマー測定 | 総実行時間 |
| **メモリ使用量** | 100MB以内 | memory-profiler | ピークメモリ |

### 🔧 4.3 実行スクリプト

#### 統合テスト実行スクリプト

```bash
#!/bin/bash
# run_all_tests.sh

echo "🧪 a10_00_openai_skeleton.py テスト実行開始"
echo "============================================"

# 環境確認
echo "📋 環境確認..."
python --version
echo "現在のディレクトリ: $(pwd)"
echo "ファイル確認:"
ls -la | grep -E "(a10_00_openai_skeleton|helper|config)"

# 依存関係確認
echo "📦 依存関係確認..."
pip list | grep -E "(streamlit|openai|pytest)" || {
    echo "❌ 必要な依存関係が不足しています"
    exit 1
}

# テスト環境変数設定
echo "🔧 環境変数設定..."
export TEST_MODE=true
export OPENAI_API_KEY=sk-test-dummy
export PYTHONPATH=.

# 1. 単体テスト
echo "🔬 1. helper.py 単体テスト..."
pytest tests/test_helper.py -v --tb=short || {
    echo "❌ helper.py テスト失敗"
    exit 1
}

# 2. アプリテスト
echo "🎮 2. skeleton.py アプリテスト..."
pytest tests/test_skeleton.py -v --tb=short || {
    echo "❌ skeleton.py テスト失敗"
    exit 1
}

# 3. 統合テスト
echo "🔗 3. 統合テスト..."
pytest tests/test_integration.py -v --tb=short || {
    echo "❌ 統合テスト失敗"
    exit 1
}

# 4. UIテスト
echo "🎨 4. UIテスト..."
pytest tests/test_ui.py -v --tb=short || {
    echo "❌ UIテスト失敗"
    exit 1
}

# 5. カバレッジ測定
echo "📊 5. カバレッジ測定..."
pytest tests/ --cov=. --cov-include="*.py" --cov-exclude="tests/*" \
    --cov-report=html --cov-report=term \
    --cov-fail-under=85 || {
    echo "⚠️ カバレッジが目標値を下回りました"
}

# 6. パフォーマンステスト
echo "⚡ 6. パフォーマンステスト..."
pytest tests/ -m performance --durations=10 || {
    echo "⚠️ パフォーマンステストで警告"
}

echo "✅ 全テスト完了！"
echo "📊 カバレッジレポート: coverage/index.html"
echo "📝 テスト結果: pytest レポートを確認してください"
```

#### 簡易テスト実行

```bash
# 簡易テスト（重要テストのみ）
pytest tests/test_helper.py::TestConfigManager::test_load_config \
       tests/test_skeleton.py::TestSimpleChatDemo::test_basic_chat \
       tests/test_integration.py::test_api_integration \
       -v

# 失敗時のデバッグ実行
pytest tests/ -v -s --tb=long --pdb
```

### 📋 4.4 テスト結果チェックリスト

| 項目 | 確認内容 | 完了 |
|------|----------|------|
| **環境** | Python、依存関係、ディレクトリ構成 | ☐ |
| **設定** | config.yaml、環境変数、テスト設定 | ☐ |
| **単体** | helper.py 全クラスの動作確認 | ☐ |
| **アプリ** | skeleton.py 全デモの動作確認 | ☐ |
| **統合** | API連携、エラーハンドリング | ☐ |
| **UI** | Streamlit要素の動作確認 | ☐ |
| **品質** | カバレッジ、パフォーマンス | ☐ |
| **レポート** | テスト結果、ログ、カバレッジ | ☐ |

このテスト計画により、現在のプロジェクト構成に適合したテストが実施できます！🎯