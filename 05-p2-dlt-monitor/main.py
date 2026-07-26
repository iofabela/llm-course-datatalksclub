import os
import dlt
from dotenv import load_dotenv
import logfire
from openai import OpenAI
from dlt.hub import run
from agent import faq_agent, SearchDeps
from filesystem_pipeline import save_agent_output, save_agent_run
from ingest import build_index, load_faq_data

load_dotenv()  # local dev: fill env vars from `.env` (absent on dltHub Runtime)
OpenAI()
logfire.configure()
logfire.instrument_pydantic_ai()

def _bridge_secret(env_name: str, key: str) -> None:
    """Expose a dlt secret as an env var (no-op if the env var is already set).

    Locally the values come from `.env` (via `load_dotenv`). On dltHub Runtime
    there is no `.env` — synced profile secrets (`.dlt/prod.secrets.toml`) are
    resolved through dlt's config system instead, so bridge them into the env
    vars that `openai`/`pydantic-ai` and `logfire` read at import/configure
    time. Must run BEFORE importing `agent` or calling `logfire.configure()`.
    """
    if not os.environ.get(env_name):
        value = dlt.secrets.get(key)
        if value:
            os.environ[env_name] = value


_bridge_secret("OPENAI_API_KEY", "openai_api_key")
_bridge_secret("LOGFIRE_TOKEN", "logfire_token")


def main(save=save_agent_run):
    # Download the FAQ and build the search index
    documents = load_faq_data()
    index = build_index(documents)

    # Inject the index into the agent via the dependency container
    deps = SearchDeps(index=index)

    # Ask a question. run_sync blocks until the agent is done;
    # the agent may call search multiple times before answering.
    question = 'How do I run Ollama locally?'
    result = faq_agent.run_sync(question, deps=deps)

    print(result.output)

    # Save the agent's answer (-> `agent_outputs`) and the session traces
    # (-> `log_records`) in one pipeline.run.
    save(question, result.output)


# no `trigger=`: a manual trigger is added automatically (run on demand only)
@run.pipeline("agent_traces")
def faq_agent_job():
    """Runtime job: run the FAQ agent on dltHub.

    Telemetry (traces/metrics) goes to Logfire; the answer + session traces
    are saved directly into duckdb (`save_agent_output`) — the local receiver
    API used by `save_agent_run` does not exist on a remote runner.
    """
    main(save=save_agent_output)


if __name__ == '__main__':
    main()
