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

This script will create a conda environment called `pubtrends_datasets` and install the prerequisite packages.

After the script finishes, please edit and copy the `config.properties` file to `~/.pubtrends-datasets/config.properties`.

## Launch instructions

First make sure that the `pubtrends_datasets` conda environment is active. You can activate the environment by running this command:
```
conda activate pubtrends_datasets
```

Then run the `run.sh` script. The app should now be running on port 5002.

## API Documentation

The API documentation is available at `http://localhost:5002/apidocs`.

## Testing

You can launch the unit tests by running this command:
```
python -m unittest discover src/test
```