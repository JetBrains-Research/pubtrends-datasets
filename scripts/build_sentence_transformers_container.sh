TMP_DIR=$(mktemp -d)
git clone https://github.com/jetBrains-Research/pubtrends "$TMP_DIR"
cd "$TMP_DIR" || exit 1
docker build -f pysrc/endpoints/embeddings/sentence_transformer/Dockerfile -t biolabs/sentence-transformers --platform linux/amd64 .
