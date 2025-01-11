Below is a **final PRD** and **Technical Design** that merges all previous feedback, incorporates your critiques and recommendations, and integrates the **MCP (Model-Context Protocol) SDK** from the [modelcontextprotocol GitHub](https://github.com/modelcontextprotocol). The goal is to create a clear, end-to-end plan for Nova—your personal knowledge management system—while using Anthropic’s Claude as your LLM and leveraging MCP for structured context handling.

# Final Product Requirements Document (PRD)

### 1. Introduction
	* 	**Product Name**: Nova
	* 	**Purpose**:
	* 	Consolidate Bear.app notes and attachments into a single repository using Docling for file conversion
	* 	Provide semantic chunking and embedding of all content
	* 	Employ a Retrieval-Augmented Generation (RAG) pipeline that sends structured MCP requests to Anthropic’s Claude
	* 	Preserve ephemeral data boundaries and metadata using the **MCP SDK**
	* 	**Scope**:
	1.	Ingest notes and attachments (PDF, images, Word docs, etc.)
	2.	Convert attachments to Markdown or text
	3.	Chunk and embed data in a vector DB
	4.	Retrieve relevant context at query time and send it via an MCP-compliant payload to Claude

### 2. Objectives
	1.	**Unified Data Consolidation**
Aggregate all Bear.app exports into a single store, ensuring no data is lost or unlinked.
	2.	**Model-Context Protocol (MCP) Integration**
Use the official MCP SDK to build structured requests to Claude.
	3.	**Reliable Conversion & Fallback**
Use Docling for robust file conversion; provide fallback or placeholders on partial failures.
	4.	**Local vs. Cloud Flexibility**
Keep designs simple for local single-user usage, while allowing an upgrade path for cloud deployment (token-based auth, TLS).
	5.	**Security & Ephemeral Data**
Respect ephemeral data by isolating or discarding it after usage, ensure minimal logging of sensitive content.

### 3. User Stories
	1.	**As a user**, I can ask Claude about my notes, and Claude references relevant text from Nova without mixing ephemeral or private content across multiple sessions.
	2.	**As a user**, I can rely on Docling to handle even partially scanned documents or images (with fallback placeholders if OCR fails).
	3.	**As a user**, I can run Nova locally with minimal overhead, and optionally deploy to the cloud with a simple token-based auth if needed.

### 4. Functional Requirements

### 4.1 Bear.app Export Handling
* **Directory Structure**:
  * Each note has its own Markdown file (`.md`) in the export root
  * Each note has a corresponding directory with the same name (minus `.md`) containing its attachments
  * No global `assets` directory is required

* **Note Processing**:
  * Extracts title from first heading or first non-empty line
  * Parses Bear-style tags (#tag, #tag/subtag)
  * Preserves creation and modification timestamps
  * Handles both inline and heading-based titles

* **Attachment Processing**:
  * **Images**: Processes `![title](path)` syntax
    * Supports HEIC, JPEG, PNG, and GIF formats
    * Handles both titled and untitled images
    * Preserves original filenames and paths

  * **Embedded Files**: Processes `[title](path)<!-- {"embed":"true"} -->` syntax
    * Supports common document formats (PDF, DOCX, XLSX, etc.)
    * Preserves original filenames and metadata
    * Handles text files (TXT, JSON, etc.)

* **Robustness**:
  * Gracefully handles missing attachments
  * Skips invalid note files
  * Supports notes without attachments
  * Maintains correct path resolution for attachments

* **Output**:
  * Returns a `MarkdownCorpus` containing all processed notes
  * Each note includes its metadata, tags, and processed attachments
  * Attachments include content type and source information
  * All paths are properly resolved relative to the export directory

### 4.2 File Conversion (Docling)
	* 	**Primary Tool**: [Docling](https://github.com/docling/docling) for PDFs, DOCX, PPTX, images, etc.
	* 	**Fallback**: For failures or partial OCR, insert placeholders so the user knows which attachments need manual review

### 4.3 Chunking & Embedding
	* 	**Hybrid Chunking**: Combine heading-based splits with semantic segmentation; possibly weight headings more heavily
	* 	**Embeddings**:
	* 	**Local**: Sentence Transformers (all-MiniLM-L6-v2) for privacy
	* 	**Optional Cloud**: If needed, e.g., OpenAI embeddings (with user consent)
	* 	**Vector Database**: FAISS or Chroma for local usage; store chunk text, metadata, ephemeral flags

### 4.4 Retrieval-Augmented Generation (RAG)
	* 	**Retrieval**: Vector similarity search for top-K chunks
	* 	**MCP Payload Construction**: Build structured messages using the **MCP SDK** to separate user messages, system/developer instructions, ephemeral blocks, etc.
	* 	**LLM Call**: Send the MCP payload to Claude’s API, respecting ephemeral or sensitive data

### 4.5 Ephemeral Data Management
	* 	**Isolation**: Keep ephemeral content in memory or ephemeral ephemeral DB entries that expire quickly
	* 	**Discard Policy**: Purge ephemeral logs or references after each request if not needed for further context

### 4.6 Minimal Logging & Security
	* 	**Logging**: Only log high-level events (e.g., “5 chunks retrieved”); avoid storing user query text or chunk content in logs
	* 	**Auth**: For local usage, minimal or no auth is fine. For cloud deployment, add a token-based or basic auth layer plus TLS

### 5. Non-Functional Requirements
	1.	**Performance**: Typical retrieval + generation under ~5 seconds for moderate data sets
	2.	**Scalability**: Capable of indexing thousands of notes while maintaining responsiveness
	3.	**Reliability**: Graceful fallback for Docling errors, partial OCR issues
	4.	**Usability**: A frictionless experience for personal usage (i.e., minimal setup, straightforward usage in the Claude UI)

### 6. Assumptions
	1.	Bear.app exports are performed manually by the user
	2.	Docling supports all relevant attachment file types, or placeholders are acceptable for unsupported formats
	3.	Anthropic API keys and environment for Claude are valid
	4.	The user is comfortable managing ephemeral data locally

### 7. Constraints
	1.	**Local Deployment**: Nova runs on a personal machine by default
	2.	**Claude Access**: Must have reliable internet access to call Anthropic’s API
	3.	**No Direct Bear DB**: Real-time direct integration with Bear’s SQLite DB is planned for future, not V1

### 8. Future Enhancements
	1.	**Direct Bear DB Integration**: Eliminate the manual export step
	2.	**Multi-LLM Routing**: Expand beyond Claude if needed
	3.	**Daily Summaries**: Automated generation of highlight updates or status briefs
	4.	**Multi-User Auth**: If extended to multiple collaborators

### 9. Success Metrics
	1.	**User Satisfaction**: The system reliably retrieves relevant chunks that Claude weaves into high-quality answers
	2.	**Security**: No accidental logging or retention of sensitive ephemeral data
	3.	**Performance**: Sub-5-second queries for typical usage
	4.	**Future-Readiness**: Modular code that can handle expansions without major refactoring
