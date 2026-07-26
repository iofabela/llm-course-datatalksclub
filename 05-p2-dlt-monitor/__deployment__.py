"""Deployment manifest — import the pipelines and notebooks you want to deploy and list them in __all__."""

from main import faq_agent_job
from rest_api_pipeline import ingest_logs

__all__: list[str] = ["ingest_logs", "faq_agent_job"]
