#!/bin/bash
echo '1. Setting up conda environment'
conda env create -f environment.yml
conda activate pubtrends_datasets
echo '2. Downloading GEOmetadb SQLite database'
wget -O GEOmetadb.sqlite 'https://gbnci.cancer.gov/geo/GEOmetadb.sqlite.gz'

