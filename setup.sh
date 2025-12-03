#!/bin/bash
echo '1. Setting up conda environment'
conda env create -f environment.yml
conda activate pubtrends_datasets
echo '2. Generating test sample of GEOmetadb'
mkdir -p ~/geodatasets
sqlite3 ~/geodatasets/testgeometadb.sqlite < src/test/db/testgeometadb.sql
echo '3. Downloading GEOmetadb SQLite database'
wget -O ~/geodatasets/geometadb.sqlite.gz 'https://gbnci.cancer.gov/geo/GEOmetadb.sqlite.gz'
gunzip ~/geodatasets/geometadb.sqlite.gz
echo '4. Creating ~/.pubtrends-datasets directory'
mkdir -p ~/.pubtrends-datasets
mkdir -p ~/.pubtrends-datasets/logs
echo 'Setup finished'
echo 'Please edit the config.properties file and copy it to ~/.pubtrends-datasets before running the app'
