# Nova V1: Product Requirements Document (PRD)

## 1. Introduction

### Product Name
Nova

### Purpose
- Ingest and unify Bear.app notes and attachments (using EasyOCR)
- Provide a semantic chunking and embedding layer for retrieving relevant data
- Use Anthropic's Claude with the official Model-Context Protocol (MCP) SDK for structured RAG queries
- Offer a minimal web interface to monitor or inspect system status (performance, logs, chunk stats)

### Scope
1. Local or optional cloud deployment
2. Ephemeral data handling and minimal logging
3. uv-based environment and dependency management

## 2. Objectives

1. **Consistent Data Consolidation**
   - Pull all Bear.app notes + attachments into a single repository
   - Reference attachments inline or place them near parent notes

2. **MCP-Driven Claude Queries**
   - Leverage official MCP SDK for structured data handling
   - Manage ephemeral data, system instructions, and user content

3. **Simple Monitoring Web App**
   - Show system metrics (chunk counts, conversion logs, recent requests)
   - Provide read-only interface

4. **Security & Ephemeral Data**
   - Enforce ephemeral boundaries in memory or short-lived caches
   - Ensure no long-term retention of ephemeral content

## 3. User Stories

1. As a user, I export my Bear.app notes, run Nova's ingestion pipeline, and query my notes via Claude while Nova retrieves relevant information through an MCP-compliant RAG pipeline.

2. As a user, I open a local web dashboard to check processed attachments, OCR errors, and vector store chunk counts.

3. As a user, I trust that ephemeral data won't leak or remain stored in logs or monitoring UI.

## 4. Functional Requirements

### 4.1 Bear Export & File Conversion [IMPLEMENTED]
- EasyOCR-based text extraction:
  - Multiple OCR configurations for quality/speed tradeoff
  - Confidence threshold validation (50%)
  - Automatic fallback for low confidence results
- Placeholder system for failed OCR:
  - JSON-based placeholder format
  - Error tracking and timestamps
  - 30-day retention policy
  - Automatic cleanup
- Structured output in .nova directory:
  - Organized by processing type
  - Clear separation of placeholders and logs
  - Configurable cleanup policies

### 4.2 Vector Store Layer [IMPLEMENTED]
- Hybrid chunking combining:
  - Heading-based segmentation with hierarchy preservation
  - Semantic content splitting with word boundary detection
  - Configurable chunk sizes (min=100, max=512, overlap=50)
- Sentence transformer embeddings:
  - all-MiniLM-L6-v2 model
  - 384-dimensional vectors
  - MPS acceleration on macOS
  - Batch processing (size=32)
- Local caching system:
  - Model-specific caching
  - Cache key generation
  - Storage in .nova/vector_store/cache
- Integration scripts:
  - Standalone vector processing
  - Bear note integration
  - Detailed logging and error handling

### 4.3 MCP Integration with Claude [IN PROGRESS]
- Official MCP SDK integration
- Ephemeral data handling in memory only
- Structured context blocks and system instructions

### 4.4 RAG Orchestrator [IN PROGRESS]
- Similarity search from vector store
- MCP payload construction
- Claude API integration

### 4.5 Monitoring Web App [PLANNED]
- Read-only dashboard for system metrics
- Local-first deployment
- Optional cloud deployment with authentication

## 5. Non-Functional Requirements

1. **Performance**
   - Few seconds response time for typical queries
   - Stable performance with thousands of notes

2. **Scalability**
   - Handle large note collections efficiently
   - Maintain performance with growing data

3. **Reliability**
   - Graceful handling of conversion failures
   - Robust ephemeral data management

4. **Security**
   - No sensitive data exposure
   - Proper ephemeral data handling

## 6. Assumptions

1. Bear.app exports follow consistent structure
2. Valid Anthropic API key availability
3. Official MCP SDK compatibility
4. Local deployment capability

## 7. Constraints

1. Local-first deployment focus
2. Optional cloud deployment with security measures
3. Strict ephemeral data handling

## 8. Future Enhancements

1. Direct Bear database integration
2. Multi-LLM support
3. Advanced monitoring features
4. Multi-user capabilities

## 9. Success Metrics

1. User satisfaction and trust
2. Sub-5-second query performance
3. Effective monitoring capabilities
4. Modular and maintainable code
