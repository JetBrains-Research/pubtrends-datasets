[![JetBrains Research](https://jb.gg/badges/research.svg)](https://confluence.jetbrains.com/display/ALL/JetBrains+on+GitHub)
[![license](https://img.shields.io/github/license/mashape/apistatus.svg)](https://opensource.org/licenses/MIT)
[![Build Status](http://teamcity.jetbrains.com/app/rest/builds/buildType:(id:BioLabs_PubtrendsDB_DockerTests)/statusIcon.svg)](http://teamcity.jetbrains.com/viewType.html?buildTypeId=BioLabs_PubtrendsDB_DockerTests&guest=1)

# pubtrends-datasets

Datasets integration for PubTrends

## Getting started

### Prerequisites

- Python 3
- uv

### General Setup

To set up the project, run the `setup.sh` script:

```
scripts/setup.sh
```

This script will install the prerequisite packages using the [uv](https://github.com/astral-sh/uv) package manager and
configure the project.

After the script finishes, copy the `config.properties` file to
`~/.pubtrends-datasets/config.properties`. Feel free to edit this file if you need to override the default configurations.

### Sentence-Transformers Service

The app uses this service to generate text embeddings for the Relevant Datasets feature.

#### Prerequisites for GPU Acceleration:

To use the --gpu flag, you must have a CUDA-capable GPU and
the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
installed.

#### Deployment steps:

1. Build the sentence-transformers container:
   ```scripts/build_sentence_transformers_container.sh```
2. Run the container:
   ```scripts/run_sentence_transformers_container.sh```

Once started, the `pubtrends-embeddings` container will be available on port 5001.

#### Configuration

The Relevant Datasets feature supports the following properties in `config.properties`:
- `embeddings_service_url` - Base URL of the sentence-transformers embeddings service
- `max_tokens_per_chunk` - Maximum number of tokens per semantic-search text chunk
- `overlap_sentences` - Number of overlapping sentences between consecutive chunks
- `chunking_workers` - Number of worker processes used for text chunking

## Running the Application

You can start the app using this command:

```aiignore
uv run -- flask --app src.app.app run --port 5002
```

The app will be available at `http://localhost:5002`.

### API Documentation

The API documentation is available at `http://localhost:5002/apidocs`.

## GEO Dataset Downloading and Processing

Use the geometadb backfilling tool to synchronize the database with currently available GEO datasets:

```aiignore
# Backfill from March 6, 2024 (geometadb cutoff date), to the current date
uv run python -m src.db.utils.backfill_geometadb 2024-03-06 --ignore-failures
```

Positional arguments:

- `start_date` - Start of the date range for which to download datasets
- `end_date` - End of the date range for which to download datasets (default: today)

Flags:

- `--ignore-failures` - Continue processing even if dataset updates fail.
- `--skip-existing` - Skip datasets already present in the local database (default behavior is to process them)
- `--dont-redownload` - Prevents dataset archive files that were downloaded from being redownloaded. However, they will
  still be processed.

To keep the database up to date, we suggest adding the following cron job via `crontab -e`:

```aiignore
0 23 * * * cd <path to this repository> && /home/<username>/.local/bin/uv run python -m src.db.utils.backfill_geometadb --ignore-failures $(date -d "now-2 days" "+\%Y-\%m-\%d")
```

> [!NOTE]
> It seems that GEO datasets published within the last 24 hours are not indexed by ESearch. As a result, these datasets
> cannot be downloaded using the backfilling tool.

### Configuration

Tweak these properties in `config.properties` to optimize performance on your hardware:

- `max_ncbi_connections` - Maximum concurrent connections to NCBI's GEO download host
- `big_gzip_threshold_mb` - Threshold for determining whether a dataset is large (larger than this size in MB)
- `big_dataset_parser_workers` - Number of parallel worker processes for parsing large datasets.
- `small_dataset_parser_workers` - Number of parallel worker processes for parsing small datasets.
- `archive_parser_chunk_size ` - The number of small datasets to process at a time in a single worker process.

> [!WARNING]
> RAM Management: `High big_dataset_parser_workers` counts can lead to RAM exhaustion when parsing large files. It is
> recommended to start with one or two workers and monitor usage before scaling up.

To customize the backfilling process, change these properties:

- `dataset_download_folder` - Path for storing downloaded datasets
- `show_backfill_progress` - Boolean to toggle the CLI progress bar.

## Testing

1. Build the docker image for testing:

```aiignore
docker build -f resources/docker/test/Dockerfile -t biolabs/pubtrends-datasets-test --platform linux/amd64 .
```

2. Run the tests:

```aiignore
docker run --rm --platform linux/amd64 \
--name pubtrends-datasets-test \
--volume=$(pwd)/src:/pubtrends-datasets/src \
--volume=$(pwd)/pyproject.toml:/pubtrends-datasets/pyproject.toml \
--volume=$(pwd)/uv.lock:/pubtrends-datasets/uv.lock \
--volume=$(pwd)/resources/docker/test/test.config.properties:/home/user/.pubtrends-datasets/config.properties \
-i -t biolabs/pubtrends-datasets-test \
/bin/bash -c "cd /pubtrends-datasets; uv sync --locked; uv run python -m unittest discover src/test"
```
