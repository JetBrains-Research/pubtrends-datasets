GPU_ARGS=()

if [[ "${1:-}" == "--gpu" ]]; then
  GPU_ARGS=(--gpus all)
fi

docker run \
  -d \
  "${GPU_ARGS[@]}" \
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
  biolabs/sentence-transformers \
  /bin/bash -c '/bin/bash ~/pubtrends/scripts/nlp.sh \
   && gunicorn --bind 0.0.0.0:5001 --workers 1 --threads 1 --worker-class=gthread \
       --limit-request-line 0 --timeout=600 \
       --log-level=info --log-file=/logs/sentence_transformer_gunicorn.log \
       "pysrc.endpoints.embeddings.sentence_transformer.sentence_transformer_app:get_app()"'
