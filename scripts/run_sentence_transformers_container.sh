docker run -d \
  --name pubtrends-embeddings \
  --restart always \
  -v  ./resources/docker/sentence_transformers/config.properties:/config/config.properties:ro \
  -v ~/.pubtrends-datasets/logs:/logs \
  -v ~/.pubtrends-datasets/sentence-transformers:/sentence-transformers \
  -v ~/.pubtrends-datasets/nltk_data:/home/user/nltk_data \
  -p 5001:5001 \
  --health-cmd='python3 -c "import urllib.request; urllib.request.urlopen(\"http://localhost:5001\")"' \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --health-start-period=60s \
  biolabs/sentence-transformers