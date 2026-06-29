# Vector Search with PGVector

Video: [Watch this lesson](https://www.youtube.com/watch?v=0P54MFyz-mc&list=PL3MmuxUbc_hLZFNgSad56pDBKK8KO0XIv)

Many real databases can do vector search. Elasticsearch has it, and
there are dedicated stores like Qdrant and Chroma. We'll go with
Postgres. Most of us already run it at work, and the data engineering
course uses it too. The concept is the same as with sqlitesearch, only
the database under the hood changes.

[pgvector](https://github.com/pgvector/pgvector) is the PostgreSQL
extension that makes this work. Install it and Postgres can do vector
similarity search. On top of that you get the usual production features,
like concurrent access, transactions, and large datasets.

We'll run Postgres with pgvector in Docker.

## Using PGVector

Here's how PGVector compares with the two tools we used earlier:

- minsearch: no setup, in-memory, best for notebooks and experiments
- sqlitesearch: no setup, SQLite file persistence, best for pet projects
- PGVector: requires Docker, Postgres database with concurrent access,
  handles millions of records, best for production systems

Reach for PGVector when you need production features:

- concurrent reads and writes
- transactions
- integration with an existing Postgres-based application

Hybrid search

Both vector and text search have their strengths and weaknesses. Vector
search matches by meaning, so it finds relevant pages even when they use
words different from the query. But it can miss exact terms like names,
codes, or rare keywords. Text search is the opposite: it nails exact words
but misses paraphrases and synonyms.

We don't have to pick one or the other - we can use both and merge their
results. This approach is called "hybrid search".

Each search produces its own ranked list, so we need a way to combine them
into one. In this homework we use Reciprocal Rank Fusion (RRF). It ignores
the raw scores from each method, which live on different scales and aren't
directly comparable. Instead, it looks only at the position of each
document in each list.

Every document scores by its position (`rank`, starting at 0) in each
list, and we sum the scores across lists with a constant `k = 60`:

```text
RRF(d) = sum over lists of  1 / (k + rank(d))
```

"Sum over lists" means we go through every ranked list and, for each list
where the document appears, add its `1 / (k + rank)` contribution. A
document found by both searches collects a score from each list, while one
found by only a single search collects just one.

The constant `k` controls how much the exact rank matters. A larger `k`
flattens the gap between positions, so the difference between rank 0 and
rank 5 counts for less. A smaller `k` does the opposite: it sharpens that
gap, so being at the top of a list matters much more.

The value 60 comes from the original RRF paper and is the usual default.
You rarely need to tune it. Lower it when only the top results matter.
Raise it to reward documents that appear across many lists, even when they
never quite reach the top.

A document that ranks well in both lists ends up higher than one that's
only strong in a single list.

```python
def rrf(result_lists, k=60, num_results=5):
    scores = {}
    docs = {}

    for results in result_lists:
        for rank, doc in enumerate(results):
            key = (doc["filename"], doc["start"])
            scores[key] = scores.get(key, 0) + 1 / (k + rank)
            docs[key] = doc

    ranked = sorted(scores, key=scores.get, reverse=True)
    return [docs[key] for key in ranked[:num_results]]
```

Now run the query `"How do I give the model access to tools?"`
with vector and text search and fuse the results with `rrf`:

```python
results = rrf([vector_results, text_results])
```