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
from src.db.chained_dataset_linker import ChainedDatasetLinker
from src.db.chained_gse_loader import ChainedGSELoader
from src.db.elink_dataset_linker import ELinkDatasetLinker
from src.db.europepmc_dataset_linker import EuropePMCDatasetLinker
from src.db.geometadb_update_job_repository import GEOmetadbUpdateJobRepository
from src.db.gse_repository import GSERepository
from src.db.mapper_registry import mapper_registry
from src.db.ncbi_gse_loader import NCBIGSELoader

app = Flask(__name__)
swagger = Swagger(app, template=swagger_template)
CONFIG = Config(test=False)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{CONFIG.geometadb_path}"

db = SQLAlchemy(metadata=mapper_registry.metadata)
db.init_app(app)
migrate = Migrate(app, db)

gse_repository = GSERepository(CONFIG.geometadb_path)
update_job_repository = GEOmetadbUpdateJobRepository(CONFIG.geometadb_path)

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
                gse_repository,
                NCBIGSELoader(http_session, gse_repository)
            )
            gse_objects = chained_loader.get_gses(gse_accessions)

            result = [asdict(gse) for gse in gse_objects]

            return jsonify(result)

    except Exception as e:
        logger.exception(f'/datasets exception {e}')
        return jsonify({"error": str(e)}), 500


@app.route('/update-jobs', methods=['GET'])
def get_update_jobs():
    """
    GET endpoint to retrieve all GEOmetadb update jobs.
    ---
    summary: Get all GEOmetadb update jobs
    description: |
      Retrieves all GEOmetadb update jobs, ordered by date (most recent first).
      Each job contains information about when it was run and its status.
    responses:
      200:
        description: Successful response with list of update jobs
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
                example: 1
              date:
                type: string
                format: date-time
                example: "2026-01-21T10:30:00"
              status:
                type: string
                enum: [in_progress, cancelled, failed, successful]
                example: "successful"
              last_update_date_start:
                type: string
                format: date-time
                example: "2026-01-01T00:00:00"
              last_update_date_end:
                type: string
                format: date-time
                example: "2026-01-10T00:00:00"
        examples:
          application/json:
            - id: 1
              date: "2026-01-21T10:30:00"
              status: "successful"
              last_update_date_start: "2026-01-01T00:00:00"
              last_update_date_end: "2026-01-10T00:00:00"
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    logger.info(f'/update-jobs {log_request(request)}')
    
    try:
        jobs = update_job_repository.get_all_jobs()
        result = [{
            "id": job.id,
            "date": job.date.isoformat() if job.date else None,
            "status": job.status,
            "last_update_date_start": job.last_update_date_start.isoformat() if job.last_update_date_start else None,
            "last_update_date_end": job.last_update_date_end.isoformat() if job.last_update_date_end else None
        } for job in jobs]
        
        return jsonify(result)
        
    except Exception as e:
        logger.exception(f'/update-jobs exception {e}')
        return jsonify({"error": str(e)}), 500


@app.route('/update-jobs/<int:job_id>/updates', methods=['GET'])
def get_job_updates(job_id):
    """
    GET endpoint to retrieve all GSE updates for a specific job.
    ---
    summary: Get GSE updates for a specific update job
    description: |
      Retrieves all GSE accessions that were updated as part of a specific job,
      along with their individual update statuses.
    parameters:
      - name: job_id
        in: path
        type: integer
        required: true
        description: The ID of the update job
        example: 1
    responses:
      200:
        description: Successful response with list of GSE updates
        schema:
          type: array
          items:
            type: object
            properties:
              gse_acc:
                type: string
                example: "GSE12345"
              status:
                type: string
                enum: [pending, failed, successful]
                example: "successful"
        examples:
          application/json:
            - gse_acc: "GSE12345"
              status: "successful"
            - gse_acc: "GSE67890"
              status: "successful"
      404:
        description: Job not found
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Job not found"
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    logger.info(f'/update-jobs/{job_id}/updates {log_request(request)}')
    
    try:
        # Check if job exists
        job = update_job_repository.get_job_by_id(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        updates = update_job_repository.get_job_updates(job_id)
        result = [{
            "gse_acc": update.gse_acc,
            "status": update.status
        } for update in updates]
        
        return jsonify(result)
        
    except Exception as e:
        logger.exception(f'/update-jobs/{job_id}/updates exception {e}')
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
