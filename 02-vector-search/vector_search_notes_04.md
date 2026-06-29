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