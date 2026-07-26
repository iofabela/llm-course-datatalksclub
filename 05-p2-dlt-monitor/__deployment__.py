"""Deployment manifest — import the pipelines and notebooks you want to deploy and list them in __all__."""

# from pipeline import my_pipeline
# from notebook import my_notebook
from rest_api_pipeline import ingest_logs

__all__: list[str] = ["ingest_logs"]
