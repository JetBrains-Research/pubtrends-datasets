swagger_template = {
    "definitions": {
        "GSE": {
            "type": "object",
            "properties": {
                "gse": {
                    "type": "string",
                    "description": "GSE accession number",
                    "example": "GSE12345"
                },
                "title": {
                    "type": "string",
                    "description": "Title of the dataset",
                    "example": "Gene expression analysis of sample"
                },
                "status": {
                    "type": "string",
                    "description": "Status of the dataset",
                    "example": "Public on Jan 01 2020"
                },
                "submission_date": {
                    "type": "string",
                    "description": "Date when the dataset was submitted",
                    "example": "2019-12-15"
                },
                "last_update_date": {
                    "type": "string",
                    "description": "Date when the dataset was last updated",
                    "example": "2020-01-01"
                },
                "pubmed_id": {
                    "type": "integer",
                    "description": "Associated PubMed ID",
                    "example": 30530648
                },
                "summary": {
                    "type": "string",
                    "description": "Summary of the goals and objectives of the study",
                    "example": "This dataset contains..."
                },
                "type": {
                    "type": "string",
                    "description": "Type of the dataset",
                    "example": "Expression profiling by array"
                },
                "contributor": {
                    "type": "string",
                    "description": "Contributor information",
                    "example": "Smith, John"
                },
                "web_link": {
                    "type": "string",
                    "description": "Web link to the dataset",
                    "example": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE12345"
                },
                "overall_design": {
                    "type": "string",
                    "description": "Description of the experimental design",
                    "example": "Comparison of treatment vs control"
                },
                "repeats": {
                    "type": "string",
                    "description": "Information about experimental repeats",
                    "example": "3 biological replicates"
                },
                "repeats_sample_list": {
                    "type": "string",
                    "description": "List of samples used for repeats",
                    "example": "GSM123, GSM124, GSM125"
                },
                "variable": {
                    "type": "string",
                    "description": "Variable types investigated in the study",
                    "example": "disease state"
                },
                "variable_description": {
                    "type": "string",
                    "description": "Description of the variable",
                    "example": "Treatment condition"
                },
                "contact": {
                    "type": "string",
                    "description": "Contact information",
                    "example": "john.smith@example.com"
                },
                "supplementary_file": {
                    "type": "string",
                    "description": "Information about supplementary files",
                    "example": "ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE12nnn/GSE12345/suppl/"
                },
                "publication_year": {
                    "type": "string",
                    "description": "Year of publication",
                    "example": "2026"
                }
            }
        },
        "ScoredGSE": {
            "type": "object",
            "properties": {
                "gse_accession": {
                    "type": "string",
                    "description": "Dataset GSE accession number",
                    "example": "GSE12345"
                },
                "score": {
                    "type": "number",
                    "format": "float",
                    "description": "Cosine similarity score between query and dataset text",
                    "example": 0.8123
                }
            },
            "required": ["gse", "score"]
        },
        "PaginatedDatasets": {
            "type": "object",
            "properties": {
                "total": {
                    "type": "integer",
                    "description": "The total number of datasets matching the query",
                    "example": 100
                },
                "gse_accessions": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "The list of GSE accession numbers for the requested page",
                    "example": ["GSE116672", "GSE127884"]
                },
                "page": {
                    "type": "integer",
                    "description": "The current page of results",
                    "example": 1
                },
                "total_pages": {
                    "type": "integer",
                    "description": "The total number of pages of results",
                    "example": 10
                }
            }
        }
    }
}
