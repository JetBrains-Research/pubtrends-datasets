"""Flask application for GEOmetadb dataset queries."""

from flask import Flask, request, jsonify
from typing import List
import os
from flasgger import Swagger
from src.db.GEOmetadb_dataset_linker import GEOmetadbDatasetLinker
from src.db.geometadb_gse_loader import GEOmetadbGSELoader
from src.app.swagger_template import swagger_template

app = Flask(__name__)
swagger = Swagger(app, template=swagger_template)

# Initialize the database connections
# Default to the GEOmetadb.sqlite in the project root
DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "GEOmetadb.sqlite"
)

dataset_linker = GEOmetadbDatasetLinker(GEOmetadb_path=DEFAULT_DB_PATH)
gse_loader = GEOmetadbGSELoader(GEOmetadb_path=DEFAULT_DB_PATH)


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
    pubmed_ids_param = request.args.get('pubmed_ids', '')
    
    if not pubmed_ids_param:
        return jsonify({"error": "pubmed_ids parameter is required"}), 400
    
    # Parse comma-separated pubmed IDs
    pubmed_ids = [pid.strip() for pid in pubmed_ids_param.split(',') if pid.strip()]
    
    if not pubmed_ids:
        return jsonify({"error": "At least one valid PubMed ID is required"}), 400
    
    try:
        # Get GSE accessions for the given PubMed IDs
        gse_accessions = dataset_linker.link_to_datasets(pubmed_ids)
        
        if not gse_accessions:
            return jsonify([])
        
        # Load the GSE objects
        gse_objects = gse_loader.load_gses(gse_accessions)
        
        # Convert to dictionaries for JSON serialization
        result = [gse.to_dict() for gse in gse_objects]
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)

