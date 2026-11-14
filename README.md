# my_rag

A fully local Retrieval-Augmented Generation (RAG) chatbot that answers questions
about the paper *"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"*
(Lewis et al., 2020), with inline source citations.

> **About this project**
> This is my first RAG project. I built it as a learning exercise, following a
> learn-by-doing approach: each component (ingestion, embedding, retrieval,
> generation, API, UI) was implemented step by step to understand how the pieces
> fit together. Feedback and suggestions are very welcome.

## Features

- **Hybrid retrieval**: dense and sparse (BM25) search in Qdrant, combined with rank fusion
- **Grounded answers**: the model answers only from retrieved context and cites sources as `[1]`, `[2]`, …
- **Streaming responses**: answers appear token by token via Server-Sent Events
- **Source viewer**: click a citation to see the exact passage and its section
- **Local and private**: runs on your machine with Ollama, no external LLM API
- **Friendly error handling**: clear messages when Qdrant or Ollama is unavailable, plus rate limiting

## Tech stack

| Layer | Technology |
|---|---|
| LLM | Ollama |
| Vector database | Qdrant |
| Backend | FastAPI (Python) |
| Frontend | React + Vite |
| Testing | pytest |

## What I learned

- Designing a retrieval pipeline: chunking, embeddings, hybrid search, fusion
- Prompting a small local model to stay grounded and cite its sources
- Separating core logic from interfaces so the CLI and web app share one pipeline
- Streaming LLM output end to end, from Ollama to the browser
