# streamlit run openai_api_mcp_sample.py
# 簡素化されたメインファイル（50行程度）
# streamlit run openai_api_mcp_sample_simple.py --server.port=8501

import streamlit as st
import os
from dotenv import load_dotenv

# ヘルパーモジュールからインポート
from helper_mcp import MCPApplication


def main():
    """メインアプリケーション"""

    # 環境変数を読み込み
    load_dotenv()

    # Streamlitページ設定
    st.set_page_config(
        page_title="MCP サーバー デモ",
        page_icon="🤖",
        layout="wide"
    )

    # ヘッダー
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

    # OpenAI APIキーの設定（オプション）
    if os.getenv('OPENAI_API_KEY'):
        try:
            import openai
            openai.api_key = os.getenv('OPENAI_API_KEY')
            client = openai.OpenAI()
        except ImportError:
            st.warning("OpenAIライブラリがインストールされていません")

    # メインアプリケーションの実行
    app = MCPApplication()
    app.run()

    # フッター
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p><strong>🚀 MCP Demo App v2.0</strong> - リファクタリング版</p>
        <p>Made with ❤️ using Streamlit</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

# streamlit run openai_api_mcp_sample.py
