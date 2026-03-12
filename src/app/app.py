"""Flask application for GEOmetadb dataset queries."""

import json
from dataclasses import asdict

import requests
from flasgger import Swagger
from flask import Flask, request, jsonify
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from src.app.swagger_template import swagger_template
from src.config.config import Config
from src.config.configure_log_file import configure_log_file
from src.db.linkers.chained_dataset_linker import ChainedDatasetLinker
from src.db.loaders.chained_gse_loader import ChainedGSELoader
from src.db.loaders.chained_gsm_loader import ChainedGSMLoader
from src.db.linkers.elink_dataset_linker import ELinkDatasetLinker
from src.db.linkers.europepmc_dataset_linker import EuropePMCDatasetLinker
from src.db.models.gse import GSE_DTO
from src.db.models.gsm import GSM
from src.db.repositories.gse_repository import GSERepository
from src.db.repositories.gsm_repository import GSMRepository
from src.db.models.mapper_registry import mapper_registry
from src.db.loaders.ncbi_gse_loader import NCBIGSELoader
from src.db.loaders.ncbi_gsm_loader import NCBIGSMLoader

app = Flask(__name__)
swagger = Swagger(app, template=swagger_template)
CONFIG = Config(test=False)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{CONFIG.geometadb_path}"

db = SQLAlchemy(metadata=mapper_registry.metadata)
db.init_app(app)
migrate = Migrate(app, db)

gse_repository = GSERepository(CONFIG.geometadb_path)
gsm_repository = GSMRepository(CONFIG.geometadb_path)

configure_log_file()

logger = app.logger


def log_request(r):
    return f'addr:{r.remote_addr} args:{json.dumps(r.args)}'


def _link_pubmed_to_gse(pubmed_ids: list[str], http_session) -> dict[str, list[str]]:
    """
    Helper function to link PubMed IDs to GSE accessions.

    :param pubmed_ids: List of PubMed IDs
    :param http_session: HTTP session to use for requests
    :return: Dictionary mapping PubMed IDs to GSE accessions
    """
    europepmc_dataset_linker = EuropePMCDatasetLinker(http_session)
    elink_dataset_linker = ELinkDatasetLinker(http_session)
    dataset_linker = ChainedDatasetLinker(elink_dataset_linker, europepmc_dataset_linker)

    pubmed_to_gse = dataset_linker.link_to_datasets_mapped(pubmed_ids)

    filtered_result = {
        pubmed_id: [acc for acc in accessions if acc.startswith("GSE")]
        for pubmed_id, accessions in pubmed_to_gse.items()
    }

    return filtered_result


def _get_gse_details(gse_accessions: list[str], http_session) -> list[GSE]:
    """
    Helper function to retrieve GSE details by accession numbers.

    :param gse_accessions: List of GSE accession numbers
    :param http_session: HTTP session to use for requests
    :return: List of GSE objects
    """
    chained_loader = ChainedGSELoader(
        gse_repository,
        NCBIGSELoader(http_session, gse_repository)
    )
    return chained_loader.get_gses(gse_accessions)


def _get_gsm_details(gsm_accessions: list[str], http_session) -> list[GSM]:
    """
    Helper function to retrieve GSM details by accession numbers.

    :param gsm_accessions: List of GSM accession numbers
    :param http_session: HTTP session to use for requests
    :return: List of GSM objects
    """
    chained_loader = ChainedGSMLoader(
        gsm_repository,
        NCBIGSMLoader(http_session, gsm_repository)
    )
    return chained_loader.get_gsms(gsm_accessions)


@app.route('/pubmed-to-gse', methods=['GET', 'POST'])
def get_pubmed_to_gse():
    """
    GET/POST endpoint to retrieve GSE accession numbers associated with PubMed IDs.
    ---
    summary: Get GSE accession numbers for PubMed IDs
    description: |
      Retrieves a mapping of PubMed IDs to their associated Gene Expression Omnibus Series (GSE) accession numbers.
      For GET: provide comma-separated PubMed IDs in query parameter.
      For POST: provide JSON array of PubMed IDs in request body.
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
        description: (POST only) JSON array of PubMed IDs
        schema:
          type: object
          properties:
            pubmed_ids:
              type: array
              items:
                type: string
          example:
            pubmed_ids: ["30530648", "31018141"]
    responses:
      200:
        description: Successful response with mapping of PubMed IDs to GSE accessions
        schema:
          type: object
          additionalProperties:
            type: array
            items:
              type: string
        examples:
          application/json:
            "30530648": ["GSE116672"]
            "31018141": ["GSE127884", "GSE127892", "GSE127893"]
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
    logger.info(f'/pubmed-to-gse {log_request(request)}')

    if request.method == 'POST':
        data = request.get_json()
        if not data or 'pubmed_ids' not in data:
            logger.error(f'/pubmed-to-gse error {log_request(request)}')
            return jsonify({"error": "pubmed_ids parameter is required"}), 400
        pubmed_ids = data['pubmed_ids']
        if not isinstance(pubmed_ids, list):
            return jsonify({"error": "pubmed_ids must be an array"}), 400
        pubmed_ids = [str(pid).strip() for pid in pubmed_ids if str(pid).strip()]
    else:
        pubmed_ids_param = request.args.get('pubmed_ids', '')
        if not pubmed_ids_param:
            logger.error(f'/pubmed-to-gse error {log_request(request)}')
            return jsonify({"error": "pubmed_ids parameter is required"}), 400
        pubmed_ids = [pid.strip() for pid in pubmed_ids_param.split(',') if pid.strip()]

    if not pubmed_ids:
        return jsonify({"error": "At least one valid PubMed ID is required"}), 400

    try:
        with requests.Session() as http_session:
            pubmed_to_gse = _link_pubmed_to_gse(pubmed_ids, http_session)
            return jsonify(pubmed_to_gse)

    except Exception as e:
        logger.exception(f'/pubmed-to-gse exception {e}')
        return jsonify({"error": str(e)}), 500


@app.route('/gse-details', methods=['GET', 'POST'])
def get_gse_details():
    """
    GET/POST endpoint to retrieve detailed GSE objects by GSE accession numbers.
    ---
    summary: Get detailed GSE information by accession numbers
    description: |
      Retrieves detailed Gene Expression Omnibus Series (GSE) dataset information for the provided GSE accession numbers.
      For GET: provide comma-separated GSE accessions in query parameter.
      For POST: provide JSON array of GSE accessions in request body.
    parameters:
      - name: gse_accessions
        in: query
        type: string
        required: false
        description: (GET only) Comma-separated list of GSE accession numbers (e.g., "GSE116672,GSE127884")
        example: "GSE116672,GSE127884"
      - name: body
        in: body
        required: false
        description: (POST only) JSON array of GSE accessions
        schema:
          type: object
          properties:
            gse_accessions:
              type: array
              items:
                type: string
          example:
            gse_accessions: ["GSE116672", "GSE127884"]
    responses:
      200:
        description: Successful response with list of detailed GSE datasets
        schema:
          type: array
          items:
            $ref: '#/definitions/GSE'
        examples:
          application/json:
            - gse: "GSE116672"
              title: "Gene expression analysis"
              status: "Public on Jan 01 2020"
              pubmed_id: 30530648
            - gse: "GSE127884"
              title: "Another dataset"
              status: "Public on Feb 01 2020"
              pubmed_id: 31018141
      400:
        description: Bad request - missing or invalid GSE accessions
        schema:
          type: object
          properties:
            error:
              type: string
              example: "gse_accessions parameter is required"
        examples:
          application/json:
            error: "gse_accessions parameter is required"
    """
    logger.info(f'/gse-details {log_request(request)}')

    if request.method == 'POST':
        data = request.get_json()
        if not data or 'gse_accessions' not in data:
            logger.error(f'/gse-details error {log_request(request)}')
            return jsonify({"error": "gse_accessions parameter is required"}), 400
        gse_accessions = data['gse_accessions']
        if not isinstance(gse_accessions, list):
            return jsonify({"error": "gse_accessions must be an array"}), 400
        gse_accessions = [str(acc).strip() for acc in gse_accessions if str(acc).strip()]
    else:
        gse_accessions_param = request.args.get('gse_accessions', '')
        if not gse_accessions_param:
            logger.error(f'/gse-details error {log_request(request)}')
            return jsonify({"error": "gse_accessions parameter is required"}), 400
        gse_accessions = [acc.strip() for acc in gse_accessions_param.split(',') if acc.strip()]

    if not gse_accessions:
        return jsonify({"error": "At least one valid GSE accession is required"}), 400

    try:
        with requests.Session() as http_session:
            gse_objects = _get_gse_details(gse_accessions, http_session)
            result = [asdict(GSE_DTO(gse)) for gse in gse_objects]
            return jsonify(result)

    except Exception as e:
        logger.exception(f'/gse-details exception {e}')
        return jsonify({"error": str(e)}), 500


@app.route('/gsm-details', methods=['GET', 'POST'])
def get_gsm_details():
    """
    GET/POST endpoint to retrieve detailed GSM objects by GSM accession numbers.
    ---
    summary: Get detailed GSM information by accession numbers
    description: |
      Retrieves detailed Gene Expression Omnibus Sample (GSM) information for the provided GSM accession numbers.
      For GET: provide comma-separated GSM accessions in query parameter.
      For POST: provide JSON array of GSM accessions in request body.
    parameters:
      - name: gsm_accessions
        in: query
        type: string
        required: false
        description: (GET only) Comma-separated list of GSM accession numbers (e.g., "GSM123456,GSM789012")
        example: "GSM123456,GSM789012"
      - name: body
        in: body
        required: false
        description: (POST only) JSON array of GSM accessions
        schema:
          type: object
          properties:
            gsm_accessions:
              type: array
              items:
                type: string
          example:
            gsm_accessions: ["GSM123456", "GSM789012"]
    responses:
      200:
        description: Successful response with list of detailed GSM samples
        schema:
          type: array
          items:
            $ref: '#/definitions/GSM'
        examples:
          application/json:
            - gsm: "GSM123456"
              title: "Sample 1"
              series_id: "GSE12345"
              status: "Public on Jan 01 2020"
            - gsm: "GSM789012"
              title: "Sample 2"
              series_id: "GSE78901"
              status: "Public on Feb 01 2020"
      400:
        description: Bad request - missing or invalid GSM accessions
        schema:
          type: object
          properties:
            error:
              type: string
              example: "gsm_accessions parameter is required"
        examples:
          application/json:
            error: "gsm_accessions parameter is required"
    """
    logger.info(f'/gsm-details {log_request(request)}')

    if request.method == 'POST':
        data = request.get_json()
        if not data or 'gsm_accessions' not in data:
            logger.error(f'/gsm-details error {log_request(request)}')
            return jsonify({"error": "gsm_accessions parameter is required"}), 400
        gsm_accessions = data['gsm_accessions']
        if not isinstance(gsm_accessions, list):
            return jsonify({"error": "gsm_accessions must be an array"}), 400
        gsm_accessions = [str(acc).strip() for acc in gsm_accessions if str(acc).strip()]
    else:
        gsm_accessions_param = request.args.get('gsm_accessions', '')
        if not gsm_accessions_param:
            logger.error(f'/gsm-details error {log_request(request)}')
            return jsonify({"error": "gsm_accessions parameter is required"}), 400
        gsm_accessions = [acc.strip() for acc in gsm_accessions_param.split(',') if acc.strip()]

    if not gsm_accessions:
        return jsonify({"error": "At least one valid GSM accession is required"}), 400

    try:
        with requests.Session() as http_session:
            gsm_objects = _get_gsm_details(gsm_accessions, http_session)
            result = [asdict(gsm) for gsm in gsm_objects]
            return jsonify(result)

    except Exception as e:
        logger.exception(f'/gsm-details exception {e}')
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
