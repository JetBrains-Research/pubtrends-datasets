#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Error: Input file path is required"
    exit 1
fi

test_db_dump="$1"

if [ ! -f "$test_db_dump" ] || [ ! -r "$test_db_dump" ]; then
    echo "Error: File '$test_db_dump' does not exist or is not readable"
    exit 1
fi

test_geometadb_path=~/geodatasets/testgeometadb.sqlite
mkdir -p ~/geodatasets
rm -f "$test_geometadb_path"
sqlite3 "$test_geometadb_path" < "$test_db_dump"
