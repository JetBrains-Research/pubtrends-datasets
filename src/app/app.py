"""Flask application for GEOmetadb dataset queries."""

from dataclasses import asdict
from flask import Flask, request, jsonify
import os
import logging
import json
from flasgger import Swagger
from src.db.geometadb_dataset_linker import GEOmetadbDatasetLinker
import requests
from src.db.elink_dataset_linker import ELinkDatasetLinker
from src.db.geometadb_gse_loader import GEOmetadbGSELoader
from src.app.swagger_template import swagger_template
from src.config.config import Config

app = Flask(__name__)
swagger = Swagger(app, template=swagger_template)
CONFIG = Config(test=False)

dataset_linker = GEOmetadbDatasetLinker(CONFIG)
gse_loader = GEOmetadbGSELoader(CONFIG)

# Deployment and development
LOG_PATHS = ['/logs', os.path.expanduser('~/.pubtrends-datasets/logs')]
for p in LOG_PATHS:
    if os.path.isdir(p):
        logfile = os.path.join(p, 'app.log')
        break
else:
    raise RuntimeError('Failed to configure main log file')

logging.basicConfig(filename=logfile,
                    filemode='a',
                    format='[%(asctime)s,%(msecs)03d: %(levelname)s/%(name)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)

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
          dataset_linker = ELinkDatasetLinker(http_session)
          gse_accessions = dataset_linker.link_to_datasets(pubmed_ids)
          
          if not gse_accessions:
              return jsonify([])
          
          # Load the GSE objects
          gse_objects = gse_loader.load_gses(gse_accessions)
          
          result = [asdict(gse) for gse in gse_objects]
          
          return jsonify(result)
    
    except Exception as e:
        logger.error(f'/datasets exception {log_request(request)}')
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)

