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
    sources (e.g. the POST sample) in a single run without run-level hints
    overriding every resource's table.
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


def build_resources(sample: bool = False):
    """One `filesystem | raw_reader` pipe per available agent log directory."""
    resources = []
    for agent, (bucket_url, file_glob) in SOURCES.items():
        # skip local dirs that don't exist on this machine (e.g. ~/.zlaude)
        path = urlparse(bucket_url).path
        if bucket_url.startswith("file://") and not os.path.isdir(path):
            print(f"skipping {agent}: {path} does not exist")
            continue
        files = filesystem(
            bucket_url=bucket_url,
            file_glob=file_glob,
            files_per_page=1 if sample else 100,
        )
        if sample:
            files = files.add_limit(1)  # one file per source for a quick verify
        resources.append(files | raw_reader(agent))
    return resources


def load(
    sample: bool = False,
    extra_resources: Optional[List] = None,
    dev_mode: bool = False,
) -> None:
    """Save the agent traces into the `logfire_data` dataset.

    Args:
        sample: load only one file per source (quick verify).
        extra_resources: additional dlt sources/resources (e.g. the POST sample
            `agent_output_source`) to load AT THE SAME TIME, in a single
            `pipeline.run`. Omit it to load only the traces — callers can then
            run other pipelines CONSECUTIVELY on the same pipeline name.
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
    resources = build_resources(sample=sample)
    if extra_resources:
        # same time: one run for everything. No run-level table_name /
        # write_disposition here — those would override the per-resource
        # settings (table name + replace/append) of every resource.
        resources = [*extra_resources, *resources]
    info = pipeline.run(resources)
    print(info)
    print(pipeline.last_trace.last_normalize_info)


if __name__ == "__main__":
    import sys

    load(sample="--sample" in sys.argv)