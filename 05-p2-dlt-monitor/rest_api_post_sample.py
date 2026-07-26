"""Sample: POST the agent's answer (`result.output` from `main.py`) through a
dlt REST API source and save it into DuckDB.

Mirror of `rest_api_pipeline.py`, but instead of GET-ing logs it POSTs one
record — the FAQ agent's answer — to the local receiver API (`receiver_api.py`,
started with `python receiver_api.py`). The receiver stores the payload in
`data/agent_outputs.jsonl` and returns the stored record, which dlt loads into
the `agent_outputs` table of the same pipeline/dataset as the traces:

    pipeline_name="agent_traces", destination="duckdb", dataset_name="logfire_data"

Usage:
    python receiver_api.py            # terminal 1: start the receiver
    python rest_api_post_sample.py    # terminal 2: POST a demo answer
"""

from typing import Any, Dict, Optional

import dlt
from dlt.sources.rest_api import RESTAPIConfig, rest_api_resources

BASE_URL = "http://localhost:8787"


def _escape_braces(value: Any) -> Any:
    """Escape literal `{`/`}` by doubling them.

    dlt treats `{...}` inside `json` values as placeholder expressions (e.g.
    `{resources.parent.id}`) and rejects anything else. Agent answers routinely
    contain literal braces (code fences, JSON snippets), so escape them — dlt
    collapses `{{`/`}}` back to single braces when sending the request.
    """
    if isinstance(value, str):
        return value.replace("{", "{{").replace("}", "}}")
    if isinstance(value, dict):
        return {k: _escape_braces(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_escape_braces(v) for v in value]
    return value


def make_payload(question: Optional[str], output: str) -> Dict[str, Any]:
    """The record we POST: the question asked in `main.py` and `result.output`."""
    return _escape_braces({"question": question, "output": output})


@dlt.source(name="agent_output_api")
def agent_output_source(payload: Dict[str, Any], base_url: str = BASE_URL):
    """Agent output API — POST one answer, load the acknowledged record.

    Args:
        payload: JSON body sent with the POST (see `make_payload`).
        base_url: receiver API base URL (`receiver_api.py`).
    """
    config: RESTAPIConfig = {
        "client": {
            "base_url": base_url,
            # a POST returns a single response, not pages
            "paginator": {"type": "single_page"},
        },
        "resource_defaults": {
            "write_disposition": "append",  # accumulate answers across runs
        },
        "resources": [
            {
                "name": "agent_outputs",
                "endpoint": {
                    "path": "/outputs",
                    "method": "POST",  # send the payload instead of only reading
                    "json": payload,  # request body = the agent's answer
                    # no data_selector: the response IS the stored record (one row)
                },
            },
        ],
    }
    yield from rest_api_resources(config)


def save_output(output: str, question: Optional[str] = None) -> None:
    """POST one agent answer and save it into duckdb (consecutive mode helper)."""
    pipeline = dlt.pipeline(
        pipeline_name="agent_traces",
        destination="duckdb",
        dataset_name="logfire_data",  # same dataset as the traces
    )
    info = pipeline.run(agent_output_source(make_payload(question, output)))
    print(info)
    print(pipeline.last_trace.last_normalize_info)


if __name__ == "__main__":
    save_output(
        output="You can run Ollama locally with `ollama run <model>`.",
        question="How do I run Ollama locally?",
    )
