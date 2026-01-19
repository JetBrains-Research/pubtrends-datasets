[![JetBrains Research](https://jb.gg/badges/research.svg)](https://confluence.jetbrains.com/display/ALL/JetBrains+on+GitHub)

[![license](https://img.shields.io/github/license/mashape/apistatus.svg)](https://opensource.org/licenses/MIT)

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
/bin/bash -c "cd /pubtrends-datasets; uv sync --locked; uv run pytest src"
```
