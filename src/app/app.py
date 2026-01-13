"""Flask application for GEOmetadb dataset queries."""

import json
import logging
import os
from dataclasses import asdict

import requests
from flasgger import Swagger
from flask import Flask, request, jsonify

from src.app.swagger_template import swagger_template
from src.config.config import Config
from src.db.chained_dataset_linker import ChainedDatasetLinker
from src.db.elink_dataset_linker import ELinkDatasetLinker
from src.db.europepmc_dataset_linker import EuropePMCDatasetLinker
from src.db.geometadb_gse_loader import GEOmetadbGSELoader
from src.db.ncbi_gse_loader import NCBIGSELoader
from src.db.chained_gse_loader import ChainedGSELoader
from src.db.gse_repository import GSERepository
from src.config.configure_log_file import configure_log_file

app = Flask(__name__)
swagger = Swagger(app, template=swagger_template)
CONFIG = Config(test=False)

repository = GSERepository(CONFIG.geometadb_path)
geometadb_gse_loader = GEOmetadbGSELoader(repository)

configure_log_file()

logger = app.logger


def log_request(r):
    return f'addr:{r.remote_addr} args:{json.dumps(r.args)}'


@app.route('/datasets', methods=['GET'])
def get_datasets():
    """
    GET endpoint to retrieve GSE objects by PubMed IDs.
    ---
    summary: Get GSE datasets associated with PubMed IDs
    description: |
      Retrieves Gene Expression Omnibus Series (GSE) datasets that are linked to the provided PubMed IDs.
      The PubMed IDs should be provided as a comma-separated list in the query parameter.
    parameters:
      - name: pubmed_ids
        in: query
        type: string
        required: true
        description: Comma-separated list of PubMed IDs (e.g., "30530648,31018141")
        example: "30530648,31018141"
    responses:
      200:
        description: Successful response with list of GSE datasets
        schema:
          type: array
          items:
            $ref: '#/definitions/GSE'
        examples:
          application/json:
            - gse: "GSE12345"
              title: "Gene expression analysis"
              status: "Public on Jan 01 2020"
              pubmed_id: 30530648
            - gse: "GSE67890"
              title: "Another dataset"
              status: "Public on Feb 01 2020"
              pubmed_id: 31018141
      400:
        description: Bad request - missing or invalid PubMed IDs
        schema:
          type: object
          properties:
            error:
              type: string
              example: "pubmed_ids parameter is required"
        examples:
          application/json:
            error: "pubmed_ids parameter is required"
    """
    logger.info(f'/datasets {log_request(request)}')
    pubmed_ids_param = request.args.get('pubmed_ids', '')

    if not pubmed_ids_param:
        logger.error(f'/datasets error {log_request(request)}')
        return jsonify({"error": "pubmed_ids parameter is required"}), 400

    pubmed_ids = [pid.strip() for pid in pubmed_ids_param.split(',') if pid.strip()]

    if not pubmed_ids:
        return jsonify({"error": "At least one valid PubMed ID is required"}), 400

    try:
        with requests.Session() as http_session:
            europepmc_dataset_linker = EuropePMCDatasetLinker(http_session)
            elink_dataset_linker = ELinkDatasetLinker(http_session)
            dataset_linker = ChainedDatasetLinker(elink_dataset_linker, europepmc_dataset_linker)
            gse_accessions = dataset_linker.link_to_datasets(pubmed_ids)
            gse_accessions = list(filter(lambda acc: acc.startswith("GSE"), gse_accessions))

            if not gse_accessions:
                return jsonify([])

            # Load the GSE objects using a chain: GEOmetadb first, then NCBI for missing ones
            chained_loader = ChainedGSELoader(
                geometadb_gse_loader,
                NCBIGSELoader(http_session, repository)
            )
            gse_objects = chained_loader.load_gses(gse_accessions)

            result = [asdict(gse) for gse in gse_objects]

            return jsonify(result)

    except Exception as e:
        logger.exception(f'/datasets exception {e}')
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
