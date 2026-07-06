# Homework # 3 | AI Orchestration with Kestra

In this module, we learn how to orchestrate AI workflows using [Kestra](https://kestra.io/), an open-source orchestration platform.
We start from the context problem that makes generic AI assistants unreliable, and end with autonomous multi-agent systems that can research, reason, and act without a fixed predetermined sequence of steps.

> This module is created and taught by [Will Russell](https://www.linkedin.com/in/wrussell1999/) from [Kestra](https://kestra.io/).


## Question 1: Context Engineering

> Try the following experiment:

1. Open ChatGPT in a private browser window: https://chatgpt.com
2. Enter this prompt: "Create a Kestra flow that loads NYC taxi data from CSV to BigQuery"
3. Then, use Kestra's AI Copilot with the same prompt

> After trying the same prompt in ChatGPT vs Kestra's AI Copilot, what is the primary reason AI Copilot generates better Kestra flows?

<h3>First result in OpenAI</h3>

<details>
<summary>&ensp;Click to expand</summary>
Below is a complete Kestra flow that:
Downloads the NYC Taxi CSV file.
Uploads the CSV to Google Cloud Storage.
Creates the BigQuery dataset (if it doesn't exist).
Loads the CSV from GCS into BigQuery.
Replace the placeholder values (`YOUR_PROJECT_ID`, `YOUR_BUCKET`, etc.) with your own.

```YAML
id: nyc_taxi_to_bigquery
namespace: company.team

inputs:
  - id: taxi_file
    type: STRING
    defaults: yellow_tripdata_2023-01.csv.gz

variables:
  project_id: YOUR_PROJECT_ID
  dataset: nyc_taxi
  table: yellow_tripdata
  bucket: YOUR_BUCKET
  location: US

tasks:
  - id: download_csv
    type: io.kestra.plugin.core.http.Download
    uri: https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/{{ inputs.taxi_file }}

  - id: upload_to_gcs
    type: io.kestra.plugin.gcp.gcs.Upload
    from: "{{ outputs.download_csv.uri }}"
    to: gs://{{ vars.bucket }}/nyc_taxi/{{ inputs.taxi_file }}

  - id: create_dataset
    type: io.kestra.plugin.gcp.bigquery.Query
    projectId: "{{ vars.project_id }}"
    sql: |
      CREATE SCHEMA IF NOT EXISTS `{{ vars.project_id }}.{{ vars.dataset }}`
      OPTIONS(location="{{ vars.location }}");

  - id: load_to_bigquery
    type: io.kestra.plugin.gcp.bigquery.LoadFromGcs
    projectId: "{{ vars.project_id }}"
    destinationTable: "{{ vars.project_id }}.{{ vars.dataset }}.{{ vars.table }}"
    sourceUris:
      - gs://{{ vars.bucket }}/nyc_taxi/{{ inputs.taxi_file }}
    format: CSV
    compression: GZIP
    autodetect: true
    skipLeadingRows: 1
    writeDisposition: WRITE_TRUNCATE

  - id: verify_load
    type: io.kestra.plugin.gcp.bigquery.Query
    projectId: "{{ vars.project_id }}"
    fetch: true
    sql: |
      SELECT COUNT(*) AS total_rows
      FROM `{{ vars.project_id }}.{{ vars.dataset }}.{{ vars.table }}`;
```

Prerequisites
Configure a Google Cloud credentials file or service account in Kestra with permissions for:
Cloud Storage (`Storage Object Admin` or equivalent)
BigQuery (`BigQuery Data Editor` and `BigQuery Job User`)
Also ensure:
The GCS bucket (`YOUR_BUCKET`) already exists.
The required GCP credentials are configured as a Kestra secret or plugin default.
The CSV filename matches the download URL (for example, yellow_tripdata_2023-01.csv.gz).
This workflow provides a simple ELT pipeline where the CSV is extracted from a public source, staged in Google Cloud Storage, and then loaded directly into BigQuery using schema autodetection.
</details>

<h3>New results in Kestra</h3>


<details>
<summary>Click to expand</summary>

```YAML
id: rabbit_274011
namespace: company.team
inputs:
  - id: fileUrl
    type: STRING
    description: The URL of the file to download
    required: true

tasks:
  - id: downloadNycTaxiData
    type: io.kestra.plugin.core.http.Download
    uri: "{{ inputs.fileUrl }}"
    # If the CSV has a specific filename, you can specify it here
    # saveAs: nyc_taxi_data.csv

  - id: uploadToGCS
    type: io.kestra.plugin.gcp.gcs.Upload
    # This will take the URI of the downloaded file from the previous task
    from: "{{ outputs.downloadNycTaxiData.uri }}"
    # Replace 'your_bucket_name' and adjust the path as needed
    to: gs://your_bucket_name/nyc_taxi_data.csv

  - id: loadToBigQuery
    type: io.kestra.plugin.gcp.bigquery.Load
    # This will take the URI of the uploaded file from the previous task
    from: "{{ outputs.uploadToGCS.uri }}"
    # Replace 'your_project', 'your_dataset', and 'nyc_taxi_data_table' with your BigQuery details
    destinationTable: your_project.your_dataset.nyc_taxi_data_table
    format: CSV
    csvOptions:
      # Set to true if your CSV has a header row
      skipLeadingRows: 1
      # Adjust if your CSV uses a different delimiter (e.g., ';')
      fieldDelimiter: ","
    # Set to true if BigQuery should infer the schema
    autodetect: true
    # Configure createDisposition and writeDisposition as needed
    createDisposition: CREATE_IF_NEEDED
    writeDisposition: WRITE_TRUNCATE
```

</details>

Kestra has access to plugin documentation.
Looking at the two outputs, this shows up concretely:
- ChatGPT invents a task type `io.kestra.plugin.gcp.bigquery.LoadFromGcs`, this isn't an actual Kestra plugin task. It's a plausible-sounding name based on general pattern-matching (since it's loading "from GCS"), but it's not something that exists in Kestra's plugin ecosystem.
- Kestra's Copilot uses `io.kestra.plugin.gcp.bigquery.Load` with a from property and proper `csvOptions nested structure`, this matches the actual plugin schema.

This isn't really about model size, token budget, or general internet access, a general-purpose LLM can have both of those and still hallucinate plugin-specific details it was never trained on (especially since plugins evolve over time and niche YAML schemas are underrepresented in general training data). Direct access to up-to-date, tool-specific documentation is what closes that gap.

> Response : AI Copilot has access to current Kestra plugin documentation

## Question 2: RAG vs No RAG

Run both `1_chat_without_rag.yaml` and `2_chat_with_rag.yaml` in the Kestra UI. Read the execution logs for each.

The non-RAG response about Kestra 1.1 features is best described as:

<h4>With-Rag:</h4>
<details>

```
INFO 2026-07-06T03:13:58.813469Z ✅ RAG Response (with retrieved context):
Kestra 1.1 introduced several major features. Here are at least 5 with brief descriptions:

1.  **New Filters**: Redesigned UI filters for improved usability, offering explicit filter options, single-click resets, saved filter combinations, and customizable table columns.
2.  **No-Code Dashboard Editor**: Extended the no-code, multi-panel editor to custom dashboards, allowing users to build and customize dashboards directly from the UI without writing YAML.
3.  **Human Task**: Introduced "human-in-the-loop" workflows for Enterprise Edition users, allowing executions to be paused and resumed only after manual approval by specific users or groups.
4.  **Multi-Agent AI Systems**: Enabled AI agents to use other AI agents as tools, facilitating sophisticated multi-agent orchestration workflows where a primary agent can delegate subtasks to specialized expert agents.
5.  **Fix with AI**: Provided AI-powered suggestions to help diagnose and resolve issues when task runs fail, offering intelligent recommendations for fixes.
6.  **Dozens of New Plugins**: Expanded integration capabilities with new plugins for various tools and platforms, including Liquibase, dlt, Airtable, Flink, Stripe, YouTube, Odoo, and many more.

🎉 Note that this response is detailed, accurate, and grounded in the actual release documentation. Compare this with the output from 1_chat_without_rag.yaml!
```

</details>

<h4>Without-Rag:</h4>

<details>

```
INFO 2026-07-06T01:56:10.210736Z ❌ Response WITHOUT RAG (no retrieved context):
Kestra 1.1 introduced several exciting new features and improvements. Here are at least 5 major features with brief descriptions:

1.  **Event-Driven Flows (Triggers and Listeners):**
    *   **Description:** This was a significant enhancement, making Kestra more reactive and allowing for truly event-driven architectures. Users could now define triggers that would start a flow based on an external event (e.g., a file landing in S3, a message in Kafka, a webhook call) or an internal event (e.g., another flow completing). Conversely, listeners allowed flows to react to specific events happening within Kestra itself (e.g., a task failing, a flow completing). This dramatically expanded Kestra's capabilities beyond simple scheduled orchestrations.

2.  **Plugin System Revamp and New Plugins:**
    *   **Description:** Kestra 1.1 came with a refactored and more robust plugin system, making it easier for developers to create and maintain custom tasks. Alongside this, several important new plugins were released or significantly improved, including:
        *   **HTTP Trigger & Tasks:** Enabled easy interaction with web services, sending and receiving HTTP requests.
        *   **AWS Plugins:** Expanded support for various AWS services like S3 (triggers, list, upload, download), Lambda, SQS, SNS, and more.
        *   **Kafka Plugin:** Facilitated integration with Kafka, allowing flows to produce and consume messages.
        *   **GCP Plugins (Initial Release/Improvements):** Expanded support for Google Cloud services.
        *   **Database Plugins (Improvements):** Enhanced connectivity and task options for various databases.

3.  **UI/UX Improvements and Observability:**
    *   **Description:** The user interface received significant updates to enhance user experience and observability. This included:
        *   **Improved Flow Visualization:** Clearer visual representation of flow execution, making it easier to understand the state and progress of complex workflows.
        *   **Enhanced Task Logs:** Better accessibility and filtering of task logs for easier debugging.
        *   **New Navigation and Layout:** A more intuitive layout for navigating through flows, executions, and other Kestra entities.
        *   **Better Error Reporting:** More informative error messages and stack traces to aid in troubleshooting.

4.  **Templating and Dynamic Flow Generation:**
    *   **Description:** Kestra 1.1 greatly improved its templating capabilities, allowing for more dynamic and reusable flow definitions. This involved:
        *   **Enhanced Jinja2 Support:** Deeper integration and more powerful use of Jinja2 for parameterizing flows, tasks, and creating dynamic content.
        *   **Subflows with Parameters:** Making it easier to create reusable components (subflows) that could accept parameters, promoting modularity and reducing duplication. This was crucial for building complex, maintainable orchestrations.

5.  **Simplified Configuration and Deployment:**
    *   **Description:** Efforts were made to streamline the configuration and deployment process for Kestra itself. This included:
        *   **Improved Docker Images:** More optimized and easier-to-use Docker images for deploying Kestra.
        *   **Clearer Documentation:** Enhanced documentation around setup, configuration, and best practices.
        *   **Initial Kubernetes Helm Chart (or significant improvements):** While a basic Helm chart might have existed before, 1.1 often brought significant improvements or a more official/robust version, simplifying Kubernetes deployments.

These features collectively made Kestra 1.1 a major release, significantly expanding its capabilities for building complex, reactive, and scalable data orchestration pipelines.

🤔 Did you notice that this response seems to be:
- Incorrect?
- Vague/generic?
- Listing features that haven't been added in exactly this version but rather a long time ago?

👉 This is why context matters! Run `2_chat_with_rag.yaml` to see the accurate, context-grounded response.

```
</details>

> RESPONSE: Vague, generic, or fabricated — the model guesses from training data

## Question 3: Token usage — short summary

Run `4_simple_agent.yaml` with `summary_length = short` (leave the other inputs as defaults).

Open the execution logs and find the token usage logged by the `log_token_usage` task.

What is the approximate **output** token count for `multilingual_agent`?

```
INFO 2026-07-06T21:46:53.756418Z 📊 Token Usage Summary:

Multilingual Agent:
- Input tokens: 282
- Output tokens: 68
- Total tokens: 350

English Brevity Agent:
- Input tokens: 83
- Output tokens: 35
- Total tokens: 118

💡 Tip: Monitor token usage to understand costs and optimize prompts!
```

> RESPONSE : 60-100 tokens

## Question 4: Token usage — long summary

Run `4_simple_agent.yaml` again with `summary_length = long`.

Compare the `multilingual_agent` output token count to your result from Question 3. Roughly how many times more output tokens does the long summary use?

<details>
<summary>Results</summary>

```
INFO 2026-07-06T21:56:42.421882Z 📊 Token Usage Summary:

Multilingual Agent:
- Input tokens: 282
- Output tokens: 191
- Total tokens: 473

English Brevity Agent:
- Input tokens: 206
- Output tokens: 60
- Total tokens: 266

💡 Tip: Monitor token usage to understand costs and optimize prompts!
```

</details>

> RESPONSE :  2-5x more

## Question 5: Modifying a flow

Open `4_simple_agent.yaml` in the Kestra flow editor. Find the `english_brevity` task and change its prompt from asking for exactly **1 sentence** to asking for exactly **3 sentences**.

Save the flow, then run it with `summary_length = long`.

Compare the `english_brevity` output token count to the original 1-sentence version (also with `summary_length = long`). How do they compare?

<details>
<summary>Results</summary>

```
INFO 2026-07-06T22:18:54.442925Z 📊 Token Usage Summary:

Multilingual Agent:
- Input tokens: 282
- Output tokens: 179
- Total tokens: 461

English Brevity Agent:
- Input tokens: 194
- Output tokens: 68
- Total tokens: 262

💡 Tip: Monitor token usage to understand costs and optimize prompts!

```

</details>

> RESPONSE :  2-4x more

## Question 6: Best Practices

Based on what you learned in this module, for production workflows requiring deterministic, repeatable results with strict compliance requirements (e.g., financial reporting, workflows in highly regulated industries), which approach is most appropriate?

- Always use AI agents for maximum flexibility and adaptation
- Use traditional task-based workflows for predictability and auditability
- Use only RAG without agents for better performance
- Use web search tools exclusively to ensure current data

> RESPONSE : Use traditional task-based workflows for predictability and auditability