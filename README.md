[![JetBrains Research](https://jb.gg/badges/research.svg)](https://confluence.jetbrains.com/display/ALL/JetBrains+on+GitHub)
[![license](https://img.shields.io/github/license/mashape/apistatus.svg)](https://opensource.org/licenses/MIT)
[![Build Status](http://teamcity.jetbrains.com/app/rest/builds/buildType:(id:BioLabs_PubtrendsDB_DockerTests)/statusIcon.svg)](http://teamcity.jetbrains.com/viewType.html?buildTypeId=BioLabs_PubtrendsDB_DockerTests&guest=1)

# pubtrends-datasets
Datasets integration for PubTrends

## Prerequisites

- Python 3
- Conda

## Setup instructions

To set up the project, run the `setup.sh` script:
```
./setup.sh
```

This script will install the prerequisite packages using the [uv](https://github.com/astral-sh/uv) package manager and configure the project.

After the script finishes, please edit and copy the `config.properties` file to `~/.pubtrends-datasets/config.properties`.

## GEO dataset downloading and processing

Use the geometadb backfilling tool to synchronize the database with currently available GEO datasets:
```aiignore
# Backfill from March 6, 2024 (geometadb cutoff date), to the current date
uv run python -m src.db.backfill_geometadb 2024-03-06 --ignore-failures
```
Positional arguments:
- `start_date` - Start of the date range for which to download datasets
- `end_date` - End of the date range for which to download datasets (default: today)
 
Flags:
- `--ignore-failures` - Continue processing even if dataset updates fail.
- `--skip-existing` - Skip datasets already present in the local database

### Configuration
Tweak these properties in `config.properties` to optimize performance on your hardware:
  - `max_ncbi_connections` - Maximum concurrent connections to NCBI's FTP server
  - `dataset_parser_workers` - Number of parallel worker processes for parsing

>[!WARNING]
> RAM Management: `High dataset_parser_workers` counts can lead to RAM exhaustion when parsing large files. It is recommended to start with one or two workers and monitor usage before scaling up.
 
To customize the backfilling process, change these properties:
  - `dataset_download_folder` - Path for storing downloaded datasets
  - `show_backfill_progress` - Boolean to toggle the CLI progress bar.

## Database migration

Database migrations are managed using `flask-migrate`. To migrate the database to the newest version, run:
```aiignore
uv run flask --app src.app.app db upgrade
```

## Launch instructions

You can start the app using this command:
```aiignore
uv run -- flask --app src.app.app run --port 5002
```

The app will be available at `http://localhost:5002`.

## API Documentation

The API documentation is available at `http://localhost:5002/apidocs`.

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
-i -t biolabs/pubtrends-datasets-test \
/bin/bash -c "cd /pubtrends-datasets; uv sync --locked; uv run python -m unittest discover src/test"
```
