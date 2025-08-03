### pip と uv は、共存できます。
##### pip で、venvを作成、運用後にuvをインストールして、運用する方法
uv をインストール（例）
```bash
brew install uv
```
- Windows: winget install astral-sh.uv
- 既存の Python や venv はそのままで OK。
- 既存 venv をアクティブ化してから uv を使う

```bash
# 例: 既存の .venv を使う
source .venv/bin/activate        # Windows: .\.venv\Scripts\activate
uv pip list                      # その venv の中身が見える
uv pip install -r requirements.txt
uv pip install "fastapi[standard]" uvicorn
```
- venv を有効化しない場合は、対象の Python を明示できます：

```bash
uv pip install --python .venv/bin/python -r requirements.txt
```
- いつでも pip も併用可能

```bash
pip list
pip uninstall <pkg>
uv pip uninstall <pkg>   # どちらで入れても同じ環境に反映されます
```
- そのまま運用する／段階的に移行する選択肢
"""
A. 今まで通り requirements.txt 運用（手間最少）
置き換えポイントは pip install → uv pip install だけ。
CI でも同様にコマンドを置き換えるだけで高速化できます。
B. pyproject.toml＋ロックファイル（uv 流儀）へ移行（管理性↑）
"""
```bash
uv init                        # プロジェクト作成（既存でもOK）
uv add fastapi uvicorn         # 依存を追加（pyproject と uv.lock を更新）
uv sync                        # ロックに従ってインストール
uv run python app.py           # 依存を解決して実行
```