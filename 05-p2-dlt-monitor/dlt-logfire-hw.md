# DLT-LogFire | Homework : DTL - Workshop
dltHub is an agent-native data engineering platform for building, running, and operating production-grade data pipelines. The toolchain is designed to be driven from coding agents. dltHub supports both local and managed cloud development.
In Module 5 we learn about monitoring and observability, and implement our own monitoring solution. 

## Prerequisites

You'll need these accounts and tools:

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/) package manager
- A coding agent: Claude Code [`.claude`]
- A [Logfire](https://logfire.dev) account
- A dltHub Platform account (free): [app.dlthub.com](https://app.dlthub.com/)
- [!NOTE] : for execute the files, make it from the path `~/llm-zoomcamp-code` with the `source .venv/bin/activate` (for Python)
- For the homework, use the `~/llm-zoomcamp-code/05-p2-dlt-monitor/main.py`
- [!NOTE] Requires the next `.env` with the values:
    - `OPENAI_API_KEY` : rest API for the models.
    - `LOGFIRE_TOKEN` & `LOGFIRE_READ_TOKEN` : from [Logfire](https://logfire.dev) for the project to write and read values.

# Question 1. Instrument the agent with Logfire
For the following query

> How do I run Ollama locally?

how many spans does a single agent run produce?

According to `pydantic_ai.all_messages` from the agent:

![logfire_response_span](/05-p2-dlt-monitor/docs/logfire_agent_messages.png)

> Answer : 5 (more or less)

# Question 2. Load traces into DuckDB with dlt

How many tables did dlt create? Check with:

![logfire_table](/05-p2-dlt-monitor/docs/logfire_table.png)

> From the pipeline result: 1

# Question 3. Query traces with an agent

The token counts are stored in the span attributes as
`gen_ai.usage.input_tokens`. Sum them across all LLM calls within the
trace. The number depends on how many searches the agent made, so
report the range it falls into:

> Checking the spans, the result was : 4505 ≈ 5000
> `"gen_ai.aggregated_usage.input_tokens": 4505,`
   