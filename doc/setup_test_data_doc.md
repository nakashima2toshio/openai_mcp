#### setup_test_data 実行説明
```bash
# テストデータ投入スクリプトを実行
uv run python scripts/setup_test_data.py

# データベース接続確認
# PostgreSQL
docker-compose -f docker-compose.mcp-demo.yml exec postgres psql -U testuser -d testdb -c "SELECT * FROM customers;"

# Redis
docker-compose -f docker-compose.mcp-demo.yml exec redis redis-cli KEYS "*"

# Elasticsearch
curl "http://localhost:9200/blog_articles/_search?pretty"

# Qdrant
curl "http://localhost:6333/collections/product_embeddings/points?limit=5"
```
