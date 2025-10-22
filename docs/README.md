# Documentation

Welcome to the Dagan documentation! This folder contains comprehensive guides, architecture details, and migration notes.

## Key Concepts

### System Type

**Dagan is an Agentic RAG**, not a traditional CRAG:
- Uses a ReAct agent that autonomously decides its strategy
- No fixed pipeline (RETRIEVE → GRADE → DECIDE)
- Dynamic tool selection based on context

See [IS_IT_STILL_CRAG.md](IS_IT_STILL_CRAG.md) for detailed comparison.

### Architecture

```
User Question → Validate Domain → Agent RAG → Response
                                      |
                                      +-- Vector Search Tool
                                      +-- Web Search Tool
```


### Reranking System

Two-stage reranking:
1. **Vector Search**: 20 candidates → 5 best (semantic relevance)
2. **Web Search**: 10 candidates → 5 best (multi-criteria)


## Database Schema

Single table design:
- **langchain_pg_embedding**: Stores document embeddings
- 3 indexes: IVFFlat (vectors), BTree (collection), GIN (metadata)
- 3 utility functions: search, delete, stats

## Migration History

Major changes documented:

1. CRAG → Agentic RAG 
2. Added LLM Reranking 
3. Fixed parsing errors 
4. UUID → TEXT migration
5. Fixed embedding dimensions 
6. Fixed vector dtype issue
7. Cleaned obsolete nodes 
8. Cleaned database schema 

## Questions?

- **General questions**: Open a GitHub Discussion
- **Bug reports**: Open a GitHub Issue
- **Documentation issues**: Open a PR or Issue
- **Feature requests**: Open a GitHub Issue with [Feature Request] tag