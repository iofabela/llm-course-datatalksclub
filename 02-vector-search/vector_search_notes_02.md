# Embeddings

Before we can do vector search, we need to turn our text into vectors.
We call this process embedding: we embed text into a vector space. The
vectors we get back are also called "embeddings."

## Word embeddings and sentence embeddings

This idea comes from
[word2vec](https://en.wikipedia.org/wiki/Word2vec). The model learns to
place words as points in a multi-dimensional space. Words with similar
meanings land close to each other.

Imagine a 2D space where "enroll" and "join" are near each other and
"Docker" is far away:

```text
        ˣ enroll
       ˣ join
                   ˣ Docker
```

The same idea works for entire sentences:

```text
Q1: "I just discovered the course. Can I still join it?"
Q2: "I just found out about the program. Can I still enroll?"

These two are close - they mean the same thing.

Q3: "How do I run Docker on Windows?"

This one is far away from Q1 and Q2.
```

Now imagine all 1200 documents in our FAQ dataset. Each one becomes a
point in this space. When a user asks a question, we embed it into the
same space and find the closest documents. Those nearest neighbors are
our search results.

The model encodes the whole sentence, not the words in isolation. So it
can tell apart the same word in different contexts.

Take the word "judge." In "the judge ruled out the possibility of crime"
(legal) it gets one vector. In "LLM-as-a-judge approach to evaluate
LLMs" (ML evaluation) it gets a different one. The surrounding context
changes the embedding.

So an embedding model takes text in and returns a fixed-length array of
numbers. We train it so that texts with similar meanings get similar
vectors.

We'll use <u>[sentence-transformers](https://www.sbert.net/)</u>, a popular
open-source library for embeddings. It runs locally on your machine, so
there are no API costs.

> Check the use and code in the notebook : vector_search.ipynb

## Cosine similarity

The `all-MiniLM-L6-v2` model outputs normalized vectors - vectors with
unit length. When both vectors are normalized, the dot product equals
cosine similarity. That's why the model documentation says it "uses
cosine similarity."

Cosine similarity measures the angle between two vectors, ignoring
their length:

- 1.0 = same direction (similar)
- 0.0 = perpendicular (unrelated)
- -1.0 = opposite direction (opposite meaning)

Formally, if `theta` is the angle between two vectors, cosine similarity
is `cos(theta)`:

- `cos(0) = 1` - vectors point in the same direction
- `cos(90) = 0` - vectors are perpendicular
- `cos(180) = -1` - vectors point in opposite directions

Because our vectors are normalized, the dot product gives us cosine
similarity directly. This is why we can use `v1.dot(dv)` to compare
texts.

In practice, we rarely get cosine similarity below 0. The embedding
model maps text to a region of the vector space where most vectors
have positive components. There's no concept of "opposite meaning"
that maps to a vector pointing the other way.

# Embedding Our Dataset

Video: [Watch this lesson](https://www.youtube.com/watch?v=NC89mz1iG4E&list=PL3MmuxUbc_hLZFNgSad56pDBKK8KO0XIv)

In the previous lesson we saw how embeddings work on a couple of
examples. Now we apply them to the whole FAQ dataset.

# Vector Search

Video: [Watch this lesson](https://www.youtube.com/watch?v=h-_tdBc24qc&list=PL3MmuxUbc_hLZFNgSad56pDBKK8KO0XIv)

In the previous lesson we embedded our FAQ dataset into a matrix `X`
with 1208 document vectors. Here we see how vector search works under
the hood.

## Scoring documents

We have a matrix `X` with all document embeddings. We take a query,
compare it against every document, and keep the most similar ones.

<details>
<summary>Click to reveal results</summary>
<pre><code>
0.7629411
{'course': 'data-engineering-zoomcamp', 'section': 'General Course-Related Questions', 'question': 'Course: Can I still join the course after the start date?', 'answer': "Yes, even if you don't register, you're still eligible to submit the homework.\n\nBe aware, however, that there will be deadlines for turning in homeworks and the final projects. So don't leave everything for the last minute.", 'doc_id': '3f1424af17'}

0.7579372
{'course': 'mlops-zoomcamp', 'section': 'General Course-Related Questions', 'question': 'Course - Can I still join the course after the start date?', 'answer': "Yes, even if you don't register, you're still eligible to submit the homeworks as long as the form is still open and accepting submissions.\n\nBe aware, however, that there will be deadlines for turning in the final projects. So don't leave everything to the last minute.", 'doc_id': '2d8b16c2a0'}

0.7192134
{'course': 'machine-learning-zoomcamp', 'section': 'General Course-Related Questions', 'question': 'The course has already started. Can I still join it?', 'answer': 'Yes, you can. Even though you missed the start date, you can register for the course. You won’t be able to submit some of the homeworks, but you can still take part in the course.\n\nIn order to get a certificate, you need to submit 2 out of 3 course projects and review 3 peers by the deadline. It means that if you join the course at the end of November and manage to work on two projects, you will still be eligible for a certificate.', 'doc_id': '41aabbd7c5'}

0.65363127
{'course': 'llm-zoomcamp', 'section': 'General Course-Related Questions', 'question': 'I just discovered the course. Can I still join?', 'answer': 'Yes, but if you want to receive a certificate, you need to submit your project while we’re still accepting submissions.', 'doc_id': '74eb249bbf'}

0.5601
{'course': 'data-engineering-zoomcamp', 'section': 'General Course-Related Questions', 'question': 'Course - Can I follow the course after it finishes?', 'answer': 'Yes, we will keep all the materials available, so you can follow the course at your own pace after it finishes.\n\nYou can also continue reviewing the homeworks and prepare for the next cohort. You can also start working on your final capstone project.', 'doc_id': '068529125b'}
</pre></code>

</details>

# Vector Search with minsearch

Video: [Watch this lesson](https://www.youtube.com/watch?v=E7KdO3xmESg&list=PL3MmuxUbc_hLZFNgSad56pDBKK8KO0XIv)

In the previous section we did vector search by hand with numpy. We
embedded the query, computed dot products, and found the best matches.
Writing the argsort and matrix code every time gets old, and it can't
filter by course. So instead we'll use a library that wraps all of it.

We'll use [minsearch](https://github.com/alexeygrigorev/minsearch), the
small in-memory search library we already used in module 1 for text
search. It has a `VectorSearch` class for vector search.

Both classes share the same API:

- `fit` to index data
- `search` to query
- `filter_dict` in `search` to filter by keyword

It's the simplest way to get started with vector search.