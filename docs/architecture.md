# Nova System Architecture

## Table of Contents
1. [Overview](#overview)
2. [Core Concept & Goals](#core-concept--goals)
3. [Phases & Workflow](#phases--workflow)
    1. [Parse Phase](#parse-phase)
    2. [Split Phase](#split-phase)
    3. [Further Phases (Future Roadmap)](#further-phases-future-roadmap)
4. [Key Components](#key-components)
5. [Directory & Filesystem Structure](#directory--filesystem-structure)
6. [Handler Extension Architecture](#handler-extension-architecture)
7. [Error Handling & Logging](#error-handling--logging)
8. [Data Flow & Caching](#data-flow--caching)
9. [Configuration & Environment Setup](#configuration--environment-setup)
10. [Security & Performance Considerations](#security--performance-considerations)
11. [Testing & CI](#testing--ci)
12. [Future Enhancements & Roadmap](#future-enhancements--roadmap)

---

## Overview
Nova is a document-processing pipeline designed to handle various input file types (e.g., PDF, DOCX, images, text, spreadsheets, HTML) and produce interlinked, consolidated Markdown outputs. The system is organized around a **phase-based** architecture, each phase handling a specific concern such as parsing raw inputs or splitting and organizing the processed content.

Nova’s main goals:
1. **Convert** arbitrary file formats into standardized Markdown representations.
2. **Aggregate** relevant content from these files into structured summary documents.
3. **Enhance** the output with additional context (metadata, image analysis, etc.).

---

## Core Concept & Goals
1. **Phase-Oriented Pipeline**  
   Nova uses distinct phases (currently *parse* and *split*) to separate the tasks of converting source files into Markdown vs. splitting or reorganizing those Markdown files.

2. **Handler-Based Parsing**  
   Each file type (PDF, DOCX, images, spreadsheets, etc.) is parsed by a specialized *handler*, which extracts text or metadata and then writes a `*.parsed.md` file.  

3. **Configurable & Extensible**  
   Handlers, phases, and other features are all made modular so that new file types, additional phases, or advanced AI-based analyses can be integrated with minimal disruption.

---

## Phases & Workflow
Below is a high-level look at how Nova processes content through two primary phases. Additional phases can be added in the future.

```mermaid
flowchart LR
    InputDir((Input Directory)) -->|Raw Files| PhaseParse
    PhaseParse -->|*.parsed.md + metadata| PhaseSplit
    PhaseSplit -->|Summary.md / Raw Notes.md / Attachments.md| OutputDir((Output Directory))

    subgraph "Parse Phase"
      direction TB
      PhaseParse([ParsePhase<br/>Handlers<br/>Markdown Conversion]) --> ParseOutput[(Parsed Files)]
    end

    subgraph "Split Phase"
      direction TB
      PhaseSplit([SplitPhase<br/>Summary/RawNotes/Attachments]) --> SplitOutput[(Consolidated MD Files)]
    end

Parse Phase
	•	Goal: Convert each input file into a *.parsed.md file (plus optional metadata).
	•	Implementation:
	1.	The pipeline enumerates each file in the input directory.
	2.	For each file, a relevant handler is retrieved from the Handler Registry.
	3.	The handler extracts text, metadata, or additional context (e.g., an image description from an AI model) and writes out a filename.parsed.md.
	4.	Any references (attachments, images) are also captured, with links updated in the new Markdown output.
	•	Key Classes:
	•	nova.phases.parse.ParsePhase
	•	nova.handlers.* (e.g., ImageHandler, DocumentHandler, etc.)
	•	DocumentMetadata (tracks data about a file as it passes through)

Split Phase
	•	Goal: Read all *.parsed.md files produced by the Parse Phase, gather them, and split out summary sections, raw notes, and attachments into three consolidated Markdown files: Summary.md, Raw Notes.md, Attachments.md.
	•	Implementation:
	1.	The SplitPhase scans the parse phase output directory (_NovaProcessing/phases/parse) looking for *.parsed.md files.
	2.	For each file, the content is inspected for markers such as --==RAW NOTES==--. Text before the marker is appended to Summary.md, while text after is appended to Raw Notes.md.
	3.	Attachments are extracted by scanning for embedded references, which are then appended to Attachments.md.
	4.	The resulting consolidated files are placed in _NovaProcessing/phases/split/.

Further Phases (Future Roadmap)

Nova is designed to allow additional phases to be appended as the pipeline grows. Examples might include:
	•	Phase: Publish
Generate a final distribution package or upload to a documentation site.
	•	Phase: Index
Produce cross-referenced indexes or tables for easy searching.
	•	Phase: AI Summaries
Summarize Raw Notes.md using advanced AI models for short, bullet-point briefs.

Key Components

Pipeline Runner (run_nova.sh / nova.core.pipeline.NovaPipeline)
	•	Single Entry Point for configuring, instantiating, and running the pipeline from the command line.
	•	Coordinates the phases, loads config, handles logging.

Directory Structure
	1.	_NovaProcessing/
Temporary working area for parsed intermediate files, final consolidated MD, and attachments.
	2.	_NovaInput/
Location for raw input files to be processed.
	3.	_Nova/
Final output directory for Summary.md, Raw Notes.md, and Attachments.md.

Handlers
	•	Overview: Each handler focuses on one file type and knows how to convert that type to Markdown. Examples:
	•	DocumentHandler: PDF, DOCX
	•	ImageHandler: JPG, PNG, HEIC
	•	TextHandler: plain text, JSON, XML
	•	SpreadsheetHandler: CSV, XLSX
	•	Registry: HandlerRegistry automatically picks the right handler based on file extension.

Configuration
	•	nova.config
Manages YAML config files, environment variables, caching directories, and file paths.

Directory & Filesystem Structure

The root project folder typically looks like this (simplified):

nova
├── docs/
│   └── architecture.md     # This file 
├── src/
│   └── nova/
│       ├── phases/
│       │   ├── parse.py    # Parse Phase
│       │   ├── split.py    # Split Phase
│       │   └── base.py
│       ├── handlers/       # All file-type handlers
│       ├── config/         # Configuration management
│       ├── core/           # Core pipeline, logging, metadata, metrics
│       ├── models/         # Pydantic or dataclass-based metadata models
│       └── utils/          # Utility functions 
├── tests/
│   └── integration/        # Integration tests for each phase
└── ...

Key Subfolders:
	•	src/nova/phases/: Phase classes (ParsePhase, SplitPhase) implementing the pipeline steps.
	•	src/nova/handlers/: Specialized classes for each file type.
	•	src/nova/models/: Data structures for metadata, including DocumentMetadata.
	•	src/nova/config/: Config loading, environment setup, and caching parameters.
	•	tests/: Unit and integration tests covering handlers, phases, and system-level tests.

Handler Extension Architecture

Handlers manage “reading -> extracting -> converting” data for a file type. Each inherits from BaseHandler:
	1.	Registration: HandlerRegistry maps file extensions to handlers.
	2.	Processing:
	•	process(...) is invoked with a Path, an output_dir, and a DocumentMetadata.
	•	Handler extracts content, writes a *.parsed.md, and updates metadata.processed = True.
	3.	Fallback: If a file extension isn’t recognized, a default or error path is used, adding a note that no handler was found.

A UML-ish representation:

classDiagram
    class BaseHandler {
        <<abstract>>
        +process(file_path, output_dir, metadata) -> DocumentMetadata?
        +process_impl() -> DocumentMetadata? (override)
        #_safe_read_file()
        #_safe_write_file()
    }
    class DocumentHandler {
        +process_impl() -> DocumentMetadata?
        -_extract_pdf_text()
        -_extract_docx_text()
    }
    class ImageHandler {
        +process_impl() -> DocumentMetadata?
        -_get_image_context()
        -_classify_image_type()
        -_write_markdown()
    }
    BaseHandler <|-- DocumentHandler
    BaseHandler <|-- ImageHandler

Error Handling & Logging
	•	Central Exceptions: nova.core.errors defines NovaError, ProcessingError, etc.
	•	Per-Phase & Per-Handler: Each handler or phase can add errors to a DocumentMetadata record with add_error().
	•	Logging:
	•	Rich / Python Logging used for console output, debug logs, and file logs.
	•	Nova logs to nova.log in the base_dir/logs folder with separate console output for immediate feedback.

Data Flow & Caching
	•	Data Flow:
	1.	Input: Raw files placed in _NovaInput.
	2.	Parse: Writes *.parsed.md into _NovaProcessing/phases/parse/<relative-subfolders>.
	3.	Split: Reads those *.parsed.md files, appending text to Summary.md, Raw Notes.md, and listing references in Attachments.md under _NovaProcessing/phases/split/.
	•	Cache:
	•	nova.cache.manager.CacheManager can store partial results (especially for heavy operations like AI-based image analysis) in _NovaCache.
	•	The pipeline checks if cached results are valid or if input files are newer than the cached output.

Configuration & Environment Setup

Nova’s configuration:
	1.	nova.yaml: main config file in config/.
	2.	Environment Variables:
	•	OPENAI_API_KEY needed for ImageHandler AI features.
	•	NOVA_CONFIG_PATH can override the default config path.
	3.	Auto-Generation: Scripts like install.sh or set_env.sh create .env files or directories if missing.

Sample:

base_dir: "${HOME}/Library/Mobile Documents/com~apple~CloudDocs"
input_dir: "${HOME}/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput"
output_dir: "${HOME}/Library/Mobile Documents/com~apple~CloudDocs/_Nova"
processing_dir: "${HOME}/Library/Mobile Documents/com~apple~CloudDocs/_NovaProcessing"

cache:
  dir: "${HOME}/Library/Mobile Documents/com~apple~CloudDocs/_NovaCache"
  enabled: true
  ttl: 3600

Security & Performance Considerations
	1.	Security:
	•	Paths are sanitized to prevent directory traversal.
	•	Handlers do not execute untrusted code or macros from user documents.
	•	OpenAI calls require API keys stored securely in environment variables.
	2.	Performance:
	•	Large PDFs or image files can be memory-intensive. Handlers may handle them in streaming or partial ways in the future.
	•	Caching is used for repeated AI calls on the same images.
	•	Phase-based structure allows partial or incremental reprocessing if only certain files changed.

Testing & CI
	•	Test Layout:
	•	tests/unit/: Unit tests for handlers and utilities.
	•	tests/integration/: End-to-end tests ensuring parse and split phases produce correct *.parsed.md and consolidated outputs.
	•	tests/performance/: (Optional) checks speed or memory usage for large inputs.
	•	Automated:
	•	run_tests.sh uses pytest with pytest.ini or pyproject.toml for configurations.

Future Enhancements & Roadmap
	•	Additional Phases: “Publish” or “Index” to further structure or upload results.
	•	Improved AI Integrations:
	•	Expand ImageHandler to handle bounding boxes, advanced classification, or OCR layouts.
	•	Add advanced text summarization handlers for large documents.
	•	Granular Caching:
	•	Intelligent re-checking so that only changed pages/images are reprocessed.
	•	Live/Interactive:
	•	Possible integration with a web-based UI or event-based triggers (like dropping new files into _NovaInput).


