"""dlt filesystem pipeline: load raw AI-agent session logs into DuckDB.

Sources: Claude Code (`~/.claude`), a Claude variant (`~/.zlaude`), Codex
(`~/.codex`), and a Codex variant (`~/.zodex`). Every source stores sessions as
JSONL transcripts with heterogeneous per-line records, so we keep each line
verbatim in a `data` column and pull a few lightweight fields up for
convenience. All four sources land in one unified table, `log_records`,
discriminated by an `agent` column. Model later with DuckDB's JSON functions.
"""

import json
import os
from pathlib import Path
from typing import Iterator, List, Optional
from urllib.parse import urlparse

import dlt
from dlt.sources import TDataItems
from dlt.sources.filesystem import FileItemDict, filesystem

from rest_api_post_sample import agent_output_source, make_payload

HOME = str(Path.home())

# agent name -> (bucket_url, file_glob). Claude-style layouts keep sessions
# under projects/; Codex-style layouts keep them under sessions/YYYY/MM/DD/.
SOURCES = {
    "claude": (f"file://{HOME}/.claude", "projects/**/*.jsonl"),
    "zlaude": (f"file://{HOME}/.zlaude", "projects/**/*.jsonl"),
    "codex": (f"file://{HOME}/.codex", "sessions/**/*.jsonl"),
    "zodex": (f"file://{HOME}/.zodex", "sessions/**/*.jsonl"),
}

TABLE_NAME = "log_records"


def _session_id_from_name(file_name: str) -> str:
    """The session id lives in the filename for every source.

    Claude/zlaude: '<uuid>.jsonl'. Codex/zodex: 'rollout-<ts>-<uuid>.jsonl',
    where the uuid is the trailing five dash-joined groups.
    """
    stem = file_name[:-6] if file_name.endswith(".jsonl") else file_name
    if stem.startswith("rollout-"):
        parts = stem.split("-")
        if len(parts) >= 5:
            return "-".join(parts[-5:])
    return stem


def raw_reader(agent: str):
    """Build a transformer that turns each JSONL line into a raw record row.

    `write_disposition` and the table name travel with the resource (instead of
    being passed to `pipeline.run`), so the traces can be combined with other
    sources (e.g. the REST API POST source) in a single run without run-level
    hints overriding every resource's table.
    """

    @dlt.transformer(name=f"read_{agent}", write_disposition="replace")
    def _read(items: Iterator[FileItemDict]) -> Iterator[TDataItems]:
        for file_obj in items:
            file_name = file_obj["file_name"]
            session_id = _session_id_from_name(file_name)
            rows = []
            with file_obj.open() as f:  # binary; decode per line, tolerate bad utf-8
                for line_no, raw in enumerate(f):
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8", errors="replace")
                    line = raw.strip()
                    if not line:
                        continue
                    rec_type: Optional[str] = None
                    ts: Optional[str] = None
                    try:
                        rec = json.loads(line)
                        if isinstance(rec, dict):
                            rec_type = rec.get("type")
                            t = rec.get("timestamp")
                            ts = t if isinstance(t, str) else (str(t) if t is not None else None)
                    except json.JSONDecodeError:
                        pass
                    rows.append(
                        {
                            "agent": agent,
                            "session_id": session_id,
                            "line_no": line_no,
                            "type": rec_type,
                            "timestamp": ts,
                            "data": line,
                        }
                    )
            if rows:
                # dispatch every batch to the unified table explicitly
                yield dlt.mark.with_table_name(rows, TABLE_NAME)

    return _read


def build_resources():
    """One `filesystem | raw_reader` pipe per available agent log directory."""
    resources = []
    for agent, (bucket_url, file_glob) in SOURCES.items():
        files = filesystem(
            bucket_url=bucket_url,
            file_glob=file_glob,
            files_per_page=1,
        )
        
        resources.append(files | raw_reader(agent))
    return resources


def load(
    extra_resources: Optional[List] = None,
    dev_mode: bool = False,
) -> None:
    """Save the agent traces into the `logfire_data` dataset.

    Args:
        extra_resources: additional dlt sources/resources (e.g. the REST API
            POST source `agent_output_source`) to load AT THE SAME TIME, in a
            single `pipeline.run`. Omit it to load only the traces — callers
            can then run other pipelines CONSECUTIVELY on the same pipeline
            name.
        dev_mode: opt-in throwaway dataset (`logfire_data_<ts>`) for
            experiments. Off by default so data lands in `logfire_data`.
    """
    pipeline = dlt.pipeline(
        # The duckdb catalog (db file) name derives from pipeline_name, so it
        # MUST differ from dataset_name (the schema). If both are
        # "temp_agent_logs", duckdb sees a catalog and a schema with the same
        # name and raises "Ambiguous reference to catalog or schema". Keep the
        # catalog distinct ("temp_agent_logs_store") from the dataset schema
        # ("temp_agent_logs"). The dashboard reads this same db + schema.
        pipeline_name="agent_traces",
        destination="duckdb",
        dataset_name="logfire_data",
        dev_mode=dev_mode,
    )
    resources = build_resources()
    if extra_resources:
        # same time: one run for everything. No run-level table_name /
        # write_disposition here — those would override the per-resource
        # settings (table name + replace/append) of every resource.
        resources = [*extra_resources, *resources]
    info = pipeline.run(resources)
    print(info)
    print(pipeline.last_trace.last_normalize_info)


def save_agent_run(question: str, output: str, dev_mode: bool = False) -> None:
    """Save a full agent run: the agent's answer + the session traces.

    POSTs `result.output` (from `faq_agent.run_sync(question, deps=deps)`)
    via the REST API source (`agent_outputs` table) and loads the local
    session traces (`log_records` table) in ONE `pipeline.run` — the pattern
    from `rest_api_post_sample`:

        pipeline.run(agent_output_source(make_payload(question, output)))

    Args:
        question: the question asked in `main.py`.
        output: the agent's answer (`result.output`).
        dev_mode: opt-in throwaway dataset (`logfire_data_<ts>`).

    Requires the receiver API (`receiver_api.py`) on localhost:8787.
    """
    load(
        extra_resources=[agent_output_source(make_payload(question, output))],
        dev_mode=dev_mode,
    )


@dlt.resource(name="agent_outputs", write_disposition="append")
def agent_output_resource(question: str, output: str):
    """The agent's answer as a plain dlt resource — no receiver API needed."""
    yield {"question": question, "output": output}


def save_agent_output(question: str, output: str, dev_mode: bool = False) -> None:
    """Save a full agent run WITHOUT the receiver API (e.g. on dltHub Runtime).

    Same as `save_agent_run`, but loads `result.output` directly into the
    `agent_outputs` table instead of POSTing it through the local receiver
    (which does not exist on a remote runner).

    Args:
        question: the question asked in `main.py`.
        output: the agent's answer (`result.output`).
        dev_mode: opt-in throwaway dataset (`logfire_data_<ts>`).
    """
    load(
        extra_resources=[agent_output_resource(question, output)],
        dev_mode=dev_mode,
    )


if __name__ == "__main__":
    load()