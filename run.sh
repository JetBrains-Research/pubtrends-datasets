#!/bin/bash
# conda init
conda_install_path=$(conda info | grep -i 'base environment' | awk '{print $4}')
source $conda_install_path/etc/profile.d/conda.sh
conda env update -f environment.yml
conda activate pubtrends_datasets

python -m flask --app src.app.app run --port 5002
