# Dagan - Agentic RAG System

An intelligent Retrieval-Augmented Generation (RAG) system powered by a ReAct agent for answering questions about administrative procedures in Togo. Built with LangGraph, OpenAI, and pgvector.

## Overview

Dagan is an **Agentic RAG** system that autonomously decides the best strategy to answer user questions by combining:
- **Vector search** across a curated knowledge base of Togolese administrative documents
- **Web search** using Tavily API for real-time information
- **LLM-based reranking** to prioritize official government sources (.gouv.tg)

Unlike traditional CRAG (Corrective RAG) systems with fixed pipelines, Dagan uses a **ReAct agent** that dynamically chooses which tools to use and when, providing more flexible and contextual responses.

## Key Features

- **Autonomous Agent**: ReAct agent with ZERO_SHOT_REACT_DESCRIPTION strategy
- **Hybrid Search**: Combines vector similarity search (PGVector) and web search (Tavily)
- **Intelligent Reranking**: GPT-4o-mini reranks results with multi-criteria evaluation (relevance 40%, officiality 30%, reliability 20%, quality 10%)
- **Source Tracking**: Complete traceability of information sources with URLs
- **Streaming Support**: Server-Sent Events (SSE) for real-time response streaming
- **Document Vectorization**: Automatic chunking and embedding of web content
- **Official Source Priority**: Strongly prioritizes .gouv.tg domains

## Architecture

```
User Question
      |
      v
[Validate Domain] --> Out-of-scope handler
      |
      v
[Agent RAG - ReAct]
      |
      +-- [Vector Search Tool]
      |     |
      |     +-> PGVector (cosine similarity >= 0.8)
      |     +-> LLM Reranking (top 20 -> top 5)
      |
      +-- [Web Search Tool]
            |
            +-> Tavily API (max 10 results)
            +-> LLM Reranking (top 10 -> top 5)
      |
      v
[Generate Response with Sources]
```

## Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **Agent**: LangChain + LangGraph
- **LLM**: OpenAI GPT-4o-mini
- **Embeddings**: OpenAI text-embedding-3-large (2000 dimensions)
- **Vector Database**: PostgreSQL + pgvector (Supabase)
- **Web Search**: Tavily API
- **Crawling**: Tavily Crawl API

## Installation

### Prerequisites

- Python 3.11 or higher
- PostgreSQL with pgvector extension (or Supabase account)
- OpenAI API key
- Tavily API key

### Setup

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/dagan.git
cd dagan
```

2. **Create and activate virtual environment**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

5. **Set up the database**

Execute the SQL script in your Supabase SQL Editor or PostgreSQL:

```bash
psql -d your_database -f database/supabase_script.sql
```

Or use the Supabase dashboard to run `database/supabase_script.sql`.

6. **Run the server**

```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at `http://127.0.0.1:8000`

## API Usage

### Health Check

```bash
GET /health
```

**Response:**
```json
{
  "status": "everything is ok"
}
```

### Vectorize Documents

Add web content to the knowledge base:

```bash
POST /vectorize
Content-Type: application/json

{
  "url": "https://service-public.gouv.tg/service/creation-entreprise"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully vectorized 15 chunks from https://...",
  "documents_count": 15,
  "chunks_info": {
    "chunk_size": 4000,
    "chunk_overlap": 800,
    "total_chunks": 15
  }
}
```

### Query (Non-Streaming)

Ask a question:

```bash
POST /crag/query
Content-Type: application/json

{
  "question": "Comment créer une entreprise au Togo?",
  "conversation_id": "optional-thread-id"
}
```

**Response:**
```json
{
  "success": true,
  "conversation_id": "uuid-123",
  "question": "Comment créer une entreprise au Togo?",
  "answer": "Pour créer une entreprise au Togo, vous devez...",
  "sources": [
    {
      "url": "https://service-public.gouv.tg/...",
      "content": "...",
      "similarity_score": 0.92,
      "rerank_score": 9.5
    }
  ],
  "metadata": {
    "workflow": "agent_rag",
    "messages_count": 5,
    "sources_count": 5
  }
}
```

### Query (Streaming)

Real-time streaming with Server-Sent Events:

```bash
POST /crag/stream
Content-Type: application/json

{
  "question": "Quels documents pour créer une entreprise?",
  "conversation_id": "optional-thread-id"
}
```

**Response (SSE):**
```json
{"type": "node_start", "node": "validate_domain"}
{"type": "node_end", "node": "validate_domain", "is_valid": true}
{"type": "node_start", "node": "agent_rag"}
{"type": "message_chunk", "content": "Pour créer..."}
{"type": "message_chunk", "content": " une entreprise..."}
{"type": "node_end", "node": "agent_rag"}
{"type": "complete", "answer": "...", "sources": [...]}
```

## Project Structure

```
dagan/
├── app.py                      # FastAPI application and endpoints
├── crag_graph.py              # LangGraph workflow definition
├── nodes/
│   ├── agent_rag.py           # ReAct agent node
│   ├── validate_context.py    # Domain validation node
│   └── deprecated/            # Archived obsolete nodes (7 nodes)
├── tools/
│   ├── vector_search.py       # Vector search tool with reranking
│   ├── web_search.py          # Web search tool with reranking
│   └── reranker.py            # LLM-based reranking module
├── database/
│   └── supabase_script.sql    # Database schema and functions
├── docs/
│   └── README.md
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
└── README.md                  # This file
```

## Configuration

Key configuration variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `CRAG_TOP_K` | 20 | Number of candidates for vector search |
| `EMBEDDING_DIMENSIONS` | 2000 | Embedding vector dimensions |
| `LLM_MODEL` | gpt-4o-mini | Model for agent and reranking |
| `LLM_TEMPERATURE` | 0.7 | Temperature for response generation |
| `DOCUMENTS_COLLECTION` | crawled_documents | Collection name in database |



## Contributing

We welcome contributions! Here's how you can help:

### Ways to Contribute

1. **Bug Reports**: Open an issue describing the bug and how to reproduce it
2. **Feature Requests**: Suggest new features or improvements
3. **Code Contributions**: Submit pull requests for bug fixes or new features
4. **Documentation**: Improve documentation, add examples, fix typos
5. **Testing**: Write tests, report edge cases

### Pull Request Process

1. **Fork the repository**

```bash
git clone https://github.com/yourusername/dagan.git
cd dagan
git checkout -b feature/your-feature-name
```

2. **Make your changes**

- Follow the existing code style
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass

3. **Commit your changes**

```bash
git add .
git commit -m "feat: add your feature description"
```

Use conventional commits:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation
- `refactor:` for code refactoring
- `test:` for adding tests

4. **Push and create PR**

```bash
git push origin feature/your-feature-name
```

Then open a Pull Request on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots/examples if applicable


### Areas for Contribution

- [ ] Add support for more embedding models
- [ ] Implement cross-encoder reranking (faster alternative)
- [ ] Create a web UI
- [ ] Add more comprehensive tests
- [ ] Optimize vector search performance
- [ ] Add support for more data sources
- [ ] Implement caching layer
- [ ] Add metrics and observability
- [ ] Create Docker deployment setup

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [LangChain](https://www.langchain.com/) and [LangGraph](https://langchain-ai.github.io/langgraph/)
- Vector search powered by [pgvector](https://github.com/pgvector/pgvector)
- Web search via [Tavily](https://tavily.com/)
- Hosted on [Supabase](https://supabase.com/)

## Citation

If you use Dagan in your research or project, please cite:

```bibtex
@software{dagan2025,
  title={Dagan: Agentic RAG System for Administrative Procedures},
  author={Novatekis},
  year={2025},
  url={https://github.com/yourusername/dagan}
}
```

## Roadmap

- [x] Core RAG functionality
- [x] ReAct agent integration
- [x] LLM-based reranking
- [x] Streaming support
- [ ] Web UI
- [ ] Docker deployment
- [ ] API authentication
- [ ] Rate limiting
- [ ] Metrics dashboard

---

**Status**: Production Ready | **Version**: 2.0.0 | **Last Updated**: October 2025
