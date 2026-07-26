import dlt
from dlt.hub import run
from dlt.hub.run import trigger
from dlt.sources.rest_api import RESTAPIConfig, rest_api_resources

BASE_URL = "https://test-agent-traces-api-xt2e7ottma-ew.a.run.app"

@dlt.source(name="agent_logs_api")
def agent_logs_source(base_url: str = dlt.config.value, page_size: int = 1000):
    """Agent Logs API — Logfire (OpenTelemetry span) format.

    Args:
        base_url: API base URL. Auto-loaded from config.toml ([sources.agent_logs_api]).
        page_size: records per page for the offset paginator.
    """
    config: RESTAPIConfig = {
        "client": {
            "base_url": base_url,
            "paginator": {
                "type": "offset",
                "limit": page_size,
                "offset": 0,
                "limit_param": "limit",
                "offset_param": "offset",
                "total_path": "total",  # read total record count from the envelope
            },
        },
        "resource_defaults": {
            "write_disposition": "replace",
        },
        "resources": [
            {
                "name": "logs",
                "endpoint": {
                    "path": "/logfire/logs",  # Logfire (OTel span) format
                    "data_selector": "logs",  # records live under the "logs" key
                },
                "primary_key": "index",
            },
        ],
    }
    yield from rest_api_resources(config)


def load(full: bool = False, pages: int = 20) -> None:
    pipeline = dlt.pipeline(
        pipeline_name="agent_traces",
        destination="duckdb",
        dataset_name="logfire_data",  # persistent dataset (distinct from catalog name)
    )
    source = agent_logs_source(base_url=BASE_URL)
    if not full:
        # each page = 1000 records; 20 pages = 20,000 logs. Pass --full for all 1M.
        source.add_limit(pages)
    info = pipeline.run(source)
    print(info)
    print(pipeline.last_trace.last_normalize_info)

@run.pipeline("agent_traces", trigger=trigger.schedule("0 12 * * *"))
def ingest_logs():
    """Runtime job: load 20,000 agent logs from /logs into DuckDB."""
    load(pages=20)

if __name__ == "__main__":
    import sys

    load(full="--full" in sys.argv)