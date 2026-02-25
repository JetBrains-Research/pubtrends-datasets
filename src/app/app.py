"""Flask application for GEOmetadb dataset queries."""

import json
from dataclasses import asdict

import numpy as np
import requests
from flasgger import Swagger
from flask import Flask, request, jsonify

from src.app.swagger_template import swagger_template
from src.config.config import Config
from src.config.configure_log_file import configure_log_file
from src.db.chained_dataset_linker import ChainedDatasetLinker
from src.db.chained_gse_loader import ChainedGSELoader
from src.db.elink_dataset_linker import ELinkDatasetLinker
from src.db.europepmc_dataset_linker import EuropePMCDatasetLinker
from src.db.gse_repository import GSERepository
from src.db.ncbi_gse_loader import NCBIGSELoader
from src.semantic_search.semantic_search import rank_by_relevance

app = Flask(__name__)
swagger = Swagger(app, template=swagger_template)
CONFIG = Config(test=False)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{CONFIG.geometadb_path}"

gse_repository = GSERepository(CONFIG.geometadb_path)

configure_log_file()

logger = app.logger

def log_request(r):
    return f'addr:{r.remote_addr} args:{json.dumps(r.args)}'


def cosine_similarity(vector, matrix):
    vector_norm = np.linalg.norm(vector)
    matrix_norms = np.linalg.norm(matrix, axis=1)
    if vector_norm == 0:
        return np.zeros(matrix.shape[0])
    safe_norms = np.where(matrix_norms == 0, 1.0, matrix_norms)
    return (matrix @ vector) / (safe_norms * vector_norm)


def fetch_datasets_for_pubmed_ids(pubmed_ids):
    """Core logic for fetching GSE datasets given PubMed IDs."""
    with requests.Session() as http_session:
        europepmc_dataset_linker = EuropePMCDatasetLinker(http_session)
        elink_dataset_linker = ELinkDatasetLinker(http_session)
        dataset_linker = ChainedDatasetLinker(elink_dataset_linker, europepmc_dataset_linker)
        gse_accessions = dataset_linker.link_to_datasets(pubmed_ids)
        gse_accessions = list(filter(lambda acc: acc.startswith("GSE"), gse_accessions))

        if not gse_accessions:
            return []

        chained_loader = ChainedGSELoader(
            gse_repository,
            NCBIGSELoader(http_session, gse_repository)
        )
        return chained_loader.get_gses(gse_accessions)


@app.route('/datasets', methods=['GET', 'POST'])
def get_datasets():
    """
    GET/POST endpoint to retrieve GSE objects by PubMed IDs.
    ---
    summary: Get GSE datasets associated with PubMed IDs
    description: |
      Retrieves Gene Expression Omnibus Series (GSE) datasets that are linked to the provided PubMed IDs.
      For GET requests, provide PubMed IDs as a comma-separated query parameter.
      For POST requests, provide PubMed IDs as a JSON array in the request body.
    parameters:
      - name: pubmed_ids
        in: query
        type: string
        required: false
        description: (GET only) Comma-separated list of PubMed IDs (e.g., "30530648,31018141")
        example: "30530648,31018141"
      - name: body
        in: body
        required: false
        schema:
          type: object
          properties:
            pubmed_ids:
              type: array
              items:
                type: string
              description: (POST only) Array of PubMed IDs
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

    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        pubmed_ids_raw = payload.get('pubmed_ids')

        if not isinstance(pubmed_ids_raw, list) or not pubmed_ids_raw:
            return jsonify({"error": "pubmed_ids must be a non-empty list"}), 400

        pubmed_ids = [str(pid).strip() for pid in pubmed_ids_raw if str(pid).strip()]
    else:
        pubmed_ids_param = request.args.get('pubmed_ids', '')

        if not pubmed_ids_param:
            logger.error(f'/datasets error {log_request(request)}')
            return jsonify({"error": "pubmed_ids parameter is required"}), 400

        pubmed_ids = [pid.strip() for pid in pubmed_ids_param.split(',') if pid.strip()]

    if not pubmed_ids:
        return jsonify({"error": "At least one valid PubMed ID is required"}), 400

    try:
        gse_objects = fetch_datasets_for_pubmed_ids(pubmed_ids)
        result = [asdict(gse) for gse in gse_objects]
        return jsonify(result)

    except Exception as e:
        logger.exception(f'/datasets exception {e}')
        return jsonify({"error": str(e)}), 500


@app.route('/relevant_datasets', methods=['POST'])
def get_relevant_datasets():
    """
    POST endpoint to retrieve most relevant datasets for a query and PubMed IDs.
    ---
    summary: Get relevant GSE datasets for PubMed IDs and query
    description: |
      Retrieves Gene Expression Omnibus Series (GSE) datasets linked to the provided PubMed IDs,
      then ranks them by cosine similarity between the query embedding and dataset text
      (title, summary, overall design).
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            pubmed_ids:
              type: array
              items:
                type: string
            query:
              type: string
          required:
            - pubmed_ids
            - query
    responses:
      200:
        description: Successful response with list of relevant GSE datasets
        schema:
          type: array
          items:
            type: object
            properties:
              gse:
                type: string
              title:
                type: string
              summary:
                type: string
              overall_design:
                type: string
              pubmed_id:
                type: integer
              score:
                type: number
      400:
        description: Bad request - missing or invalid inputs
    """
    logger.info(f'/relevant_datasets {log_request(request)}')
    payload = request.get_json(silent=True) or {}
    pubmed_ids = payload.get('pubmed_ids')
    query = payload.get('query')

    if not isinstance(pubmed_ids, list) or not pubmed_ids:
        return jsonify({"error": "pubmed_ids must be a non-empty list"}), 400
    if not isinstance(query, str) or not query.strip():
        return jsonify({"error": "query must be a non-empty string"}), 400

    pubmed_ids = [str(pid).strip() for pid in pubmed_ids if str(pid).strip()]
    if not pubmed_ids:
        return jsonify({"error": "At least one valid PubMed ID is required"}), 400

    try:
        gses = fetch_datasets_for_pubmed_ids(pubmed_ids)
        return jsonify(rank_by_relevance(gses, query))
    except Exception as e:
        logger.exception(f'/relevant_datasets exception {e}')
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
