#!/bin/bash
# At the time of writing, the Wayback Machine link is faster than the official link
GEOMETADB_DOWNLOAD_LINK='https://web.archive.org/web/20250222142049/https://gbnci.cancer.gov/geo/GEOmetadb.sqlite.gz'

# conda init
conda_install_path=$(conda info | grep -i 'base environment' | awk '{print $4}')
source $conda_install_path/etc/profile.d/conda.sh

echo '1. Setting up conda environment'
if conda env list | grep -q "pubtrends_datasets"; then
    echo "Environment exists, updating..."
    conda env update -f environment.yml
else
    echo "Creating new environment..."
    conda env create -f environment.yml
fi
conda activate pubtrends_datasets

echo '2. Generating test sample of GEOmetadb'
test_geometadb_path=~/geodatasets/testgeometadb.sqlite
mkdir -p ~/geodatasets
rm -f "$test_geometadb_path"
sqlite3 "$test_geometadb_path" < src/test/db/testgeometadb.sql
sed -i "s|^test_geometadb_path\\s*=\\s*.*|test_geometadb_path=${test_geometadb_path}|" config.properties

echo '3. Setting up GEOmetadb SQLite database'
read -rp "Do you want to download GEOmetadb (D) or provide path to an existing GEOmetadb file (P)? [D/P]: " choice
if [[ $choice == "P" || $choice == "p" ]]; then
    while true; do
        read -rp "Enter path to existing GEOmetadb file: " geometadb_path
        geometadb_path="${geometadb_path/#~/$HOME}"
        if [ -f "$geometadb_path" ]; then
            if file "$geometadb_path" | grep -q "sqlite"; then
                break
            else
                echo "Error: File is not a valid SQLite database"
            fi
        else
            echo "Error: File does not exist"
        fi
    done
else
    read -rp "Enter installation path or press Enter for default (~/geodatasets/geometadb.sqlite): " geometadb_path
    if [ -z "$geometadb_path" ]; then
        geometadb_path=~/geodatasets/geometadb.sqlite
    fi
    wget -O "${geometadb_path}.gz" "$GEOMETADB_DOWNLOAD_LINK"
    gunzip "${geometadb_path}.gz"
fi
sed -i "s|^geometadb_path = .*|geometadb_path = ${geometadb_path}|" config.properties

echo '4. Creating ~/.pubtrends-datasets directory'
mkdir -p ~/.pubtrends-datasets/logs
echo 'Setup finished'
echo 'Please copy the config.properties file to ~/.pubtrends-datasets before running the app'
