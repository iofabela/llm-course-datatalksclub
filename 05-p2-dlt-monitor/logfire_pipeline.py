"""Logfire -> DuckDB pipeline with the dlt REST API source.

Reads spans/traces (`records`) and `metrics` out of a Logfire project through
the query API (POST /v2/query, bearer read token) and loads them into DuckDB.

The read token comes from `LOGFIRE_READ_TOKEN` in the repo-root `.env` (see
dlt-logfire-hw.md), falling back to dlt secrets
(`[sources.logfire] read_token = ...` in `.dlt/secrets.toml`).

Usage (from the repo root, with the venv active):
    python 05-p2-dlt-monitor/logfire_pipeline.py [--days 30] [--limit 10000]
"""

import argparse
import os
from datetime import datetime, timedelta, timezone

import dlt
from dlt.sources.rest_api import RESTAPIConfig, rest_api_resources
from dotenv import load_dotenv

# Data region of the Logfire project: "logfire-us" or "logfire-eu".
# The read token is region-bound (a token from the wrong region -> 401).
BASE_URL = "https://logfire-eu.pydantic.dev/v1/"
MAX_ROWS = 10_000  # hard row cap of the /v2/query API


@dlt.source(name="logfire")
def logfire_source(
    read_token: str = dlt.secrets.value,
    days: int = 7,
    row_limit: int = MAX_ROWS,
):
    """Logfire query API source: recent `records` (traces) and `metrics`.

    Args:
        read_token: Logfire read token. Auto-loaded from dlt secrets when not
            passed explicitly (local dev uses `LOGFIRE_READ_TOKEN` from `.env`).
        days: how far back to query (`min_timestamp` = now - days).
        row_limit: max rows per table (the API caps this at 10,000).
    """
    min_timestamp = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    limit = min(row_limit, MAX_ROWS)

    config: RESTAPIConfig = {
        "client": {
            "base_url": BASE_URL,
            "auth": {
                "type": "bearer",
                "token": read_token,
            },
            # without an explicit Accept header the API answers in Arrow format
            "headers": {"Accept": "application/json"},
            # one POST returns the whole result set (up to `limit` rows)
            "paginator": {"type": "single_page"},
        },
        "resource_defaults": {
            "write_disposition": "replace",
        },
        "resources": [
            {
                "name": "records",  # spans/traces
                "endpoint": {
                    "path": "/v2/query",
                    "method": "POST",
                    "json": {
                        "sql": "SELECT * FROM records "
                        "ORDER BY start_timestamp DESC "
                        f"LIMIT {limit}",
                        "min_timestamp": min_timestamp,
                        "limit": limit,
                    },
                    # the response JSON keeps the rows under the "data" key
                    "data_selector": "data",
                },
            },
            {
                "name": "metrics",
                "endpoint": {
                    "path": "/v2/query",
                    "method": "POST",
                    "json": {
                        "sql": "SELECT * FROM metrics "
                        "ORDER BY recorded_timestamp DESC "
                        f"LIMIT {limit}",
                        "min_timestamp": min_timestamp,
                        "limit": limit,
                    },
                    "data_selector": "data",
                },
            },
        ],
    }
    yield from rest_api_resources(config)


def get_data(days: int = 7, row_limit: int = MAX_ROWS) -> None:
    load_dotenv()  # local dev: LOGFIRE_READ_TOKEN from the repo-root `.env`

    # Connect to destination
    pipeline = dlt.pipeline(
        pipeline_name="logfire_pipeline",
        destination="duckdb",
        dataset_name="logfire_data",
    )

    # Load the data. Prefer the env var; fall back to dlt secrets.
    read_token = os.environ.get("LOGFIRE_READ_TOKEN")
    source = (
        logfire_source(read_token=read_token, days=days, row_limit=row_limit)
        if read_token
        else logfire_source(days=days, row_limit=row_limit)
    )
    load_info = pipeline.run(source)
    print(load_info)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, help="lookback window in days")
    parser.add_argument("--limit", type=int, default=MAX_ROWS, help="max rows per table")
    args = parser.parse_args()
    get_data(days=args.days, row_limit=args.limit)
