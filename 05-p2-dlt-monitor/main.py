import logfire
from dotenv import load_dotenv
from openai import OpenAI
from agent import faq_agent, SearchDeps
from filesystem_pipeline import save_agent_run
from ingest import build_index, load_faq_data

OpenAI()
load_dotenv()
logfire.configure()
logfire.instrument_pydantic_ai()


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

    # Save the agent's answer (via the REST API POST source -> `agent_outputs`)
    # and the session traces (-> `log_records`) in one pipeline.run.
    # Requires `python receiver_api.py` running on localhost:8787.
    save_agent_run(question, result.output)


if __name__ == '__main__':
    main()
