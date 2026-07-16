# Querying Data

We're saving conversations now, so the next step is reading them back.
That's what the dashboard runs on. Normally I'd open a Jupyter notebook
here and poke at the data first. I'd try a few queries to see what the
rows look like. Our data is small and simple, so we skip that and go
straight to a script.

Create `db_query.py`.

Connect to the same database:

```python
from dataclasses import dataclass

from db_init import get_db_connection
from metrics import LLMCallRecord
```

## Fetching conversations

A query returns each row as a plain tuple. You have to remember that
column 4 is the model and column 6 is the prompt. That's no fun to work
with. So we convert each row back into the `LLMCallRecord` dataclass we
already use for live calls.

A helper to convert a database row into an `LLMCallRecord`:

```python
def row_to_record(row):
    return LLMCallRecord(
        model=row[4],
        prompt=row[6],
        instructions=row[5],
        answer=row[2],
        prompt_tokens=row[7],
        completion_tokens=row[8],
        total_tokens=row[9],
        response_time=row[10],
        cost=row[11],
        timestamp=row[12],
    )
```

Now update `get_conversations` to use it:

```python
def get_conversations(limit=10):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, question, answer, course, model,
                       instructions, prompt,
                       prompt_tokens, completion_tokens, total_tokens,
                       response_time, cost, timestamp
                FROM conversations
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [row_to_record(row) for row in rows]
```

We order by `timestamp` to get the most recent calls. One thing to keep
in mind as the table grows: there's no index on `timestamp`, but there
is one on `id`. Since ids increase over time anyway, ordering by `id`
would be faster - or you add an index on `timestamp`. With a handful of
rows it doesn't matter, so we leave it simple for now.

Test it:

```python
if __name__ == "__main__":
    records = get_conversations()
    for record in records:
        print(record)
```

Run it:

```bash
uv run python db_query.py
```

The output is a wall of text, not something you'd want to read all day.
Still, it proves we can pull the data back out of the database. Now we
put it in front of a dashboard.


# Streamlit Dashboard


Before we reach for Grafana, let's build a quick dashboard right in
Streamlit. For a lot of projects this is all you need. When you're
getting started, seeing latency, cost, and recent conversations in one
place is already enough. You often don't need Grafana at all.

If you stop here, you don't even need Postgres. You could swap it for
SQLite and skip Docker entirely. We're on Postgres only because Grafana
connects to it more easily than to SQLite, which matters later. For a
lightweight project, SQLite plus a Streamlit dashboard is a perfectly
good place to stop.

I'm not a Streamlit expert. When I build these pages, I describe what I
want to ChatGPT or a coding assistant. Then I let it write the layout. I
kept this one simple on purpose, so you can read it top to bottom and
follow what's happening.

First, add aggregate queries to `db_query.py`.

Add a `Stats` dataclass to `db_query.py`:

```python
@dataclass
class Stats:
    total: int
    avg_response_time: float
    total_cost: float
    avg_tokens: float
```

A function to compute aggregate stats:

```python
def get_stats():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*),
                    AVG(response_time),
                    SUM(cost),
                    AVG(total_tokens)
                FROM conversations
            """)
            row = cur.fetchone()
    finally:
        conn.close()

    return Stats(
        total=row[0],
        avg_response_time=row[1],
        total_cost=row[2],
        avg_tokens=row[3],
    )
```

Create `dashboard.py`:

```python
import streamlit as st
from dataclasses import asdict
import pandas as pd
from db_query import get_conversations, get_stats
```

At the top we show four summary numbers, the ones most worth watching
when you're getting started. You can show far more, but these are a good
starting point.

Show the summary metrics:

```python
st.title("Course Assistant Dashboard")

stats = get_stats()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total conversations", stats.total)
col2.metric("Avg response time", f"{stats.avg_response_time:.2f}s")
col3.metric("Total cost", f"${stats.total_cost:.4f}")
col4.metric("Avg tokens", f"{stats.avg_tokens:.0f}")
```

For the time charts we pull the last 100 conversations and let Streamlit
plot them. This isn't the most efficient way to do it. We fetch whole
records just to chart two columns. A leaner version would query only the
timestamp and the value we want. With our volume it's fine, so we keep it
short.

Charts for cost and response time over time:

```python
records = get_conversations(limit=100)
df = pd.DataFrame([asdict(r) for r in records])

st.subheader("Cost over time")
st.line_chart(df, x="timestamp", y="cost")

st.subheader("Response time over time")
st.line_chart(df, x="timestamp", y="response_time")
```

Recent conversations:

```python
st.subheader("Recent conversations")
records = get_conversations(limit=20)

for record in records:
    st.write(f"**{record.prompt[:80]}...**")
    st.write(f"{record.answer[:200]}...")
    st.write(f"Time: {record.response_time:.2f}s | Cost: ${record.cost:.4f}")
    st.divider()
```

Run it.

The port 8501 is already in use (by the chat app), so we will use a
different port:

```bash
uv run streamlit run dashboard.py --server.port 8502
```

We didn't even use a table for the conversations - plain text is enough
to make the point. This simple dashboard already gives us real
visibility into the system. Later we set up Grafana for a more powerful
view, with alerting and richer panels.
