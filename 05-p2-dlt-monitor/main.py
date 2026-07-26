import logfire
from dotenv import load_dotenv
from openai import OpenAI
from agent import faq_agent, SearchDeps
from filesystem_pipeline import load as load_traces
from ingest import build_index, load_faq_data
from rest_api_post_sample import agent_output_source, make_payload, save_output

OpenAI()
load_dotenv()
logfire.configure()
logfire.instrument_pydantic_ai()



def save_run(output: str, question: str, same_time: bool = False, sample: bool = True) -> None:
    """Persist the run into duckdb (pipeline `agent_traces`, dataset `logfire_data`).

    1. POST `result.output` via the REST API sample  -> table `agent_outputs`
       (requires `python receiver_api.py` running on localhost:8787).
    2. Load the local agent session traces           -> table `log_records`.

    same_time=False: two CONSECUTIVE `pipeline.run` calls on the same pipeline.
    same_time=True:  a SINGLE `pipeline.run` with all resources at the same time.
    """
    if same_time:
        load_traces(
            sample=sample,
            extra_resources=[agent_output_source(make_payload(question, output))],
        )
    else:
        save_output(output, question)
        load_traces(sample=sample)


def main():
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

    # Save the answer (POST sample) and the agent traces into duckdb
    save_run(result.output, question)


if __name__ == '__main__':
    main()
