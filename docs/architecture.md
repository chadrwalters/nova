# Nova Architecture

This document describes the overall architecture of the Nova system. It explains how the system is organized (directories, modules, classes) and how key components—such as phases, handlers, and Markdown generation—interact with each other. It also covers how to add new phases or extend Nova with new file handlers. The purpose is to ensure that both human developers and large language models (LLMs) can fully understand the flow of control, data, and the constraints in this system.

---

## Table of Contents
1. [High-Level Overview](#high-level-overview)
2. [System Layout](#system-layout)
3. [Phases & Pipeline](#phases--pipeline)
   - [Adding a New Phase](#adding-a-new-phase)
   - [Phase Implementation Rules](#phase-implementation-rules)
4. [Handlers & File Processing](#handlers--file-processing)
   - [Adding a New Handler](#adding-a-new-handler)
   - [Handler Responsibilities](#handler-responsibilities)
5. [Markdown Generation](#markdown-generation)
6. [Configuration Management](#configuration-management)
7. [Metadata & References](#metadata--references)
8. [Logging & Debugging](#logging--debugging)
9. [Utility Modules](#utility-modules)
10. [Extending or Customizing Nova](#extending-or-customizing-nova)

---

## 1. High-Level Overview

Nova is a system for taking various input files (documents, images, archives, spreadsheets, etc.) and running them through multiple *phases* of processing (Parse, Disassemble, Split, Finalize, etc.). The final output typically includes structured Markdown (`.parsed.md`, `Summary.md`, `Attachments.md`, etc.) along with metadata (`.metadata.json`). The goal is to provide a flexible pipeline that can be extended with new phases or new file handlers while maintaining consistent output.

A typical run might:
1. Read a directory of input files.
2. For each file, the **Parse** phase creates normalized Markdown (`.parsed.md`).
3. **Disassemble** takes those `.parsed.md` files, splitting them into summary vs. raw notes.
4. **Split** aggregates or organizes them further (e.g., into consolidated `Summary.md`, `Raw Notes.md`, or `Attachments.md`).
5. **Finalize** may do link validation, attachments copying, or final housekeeping tasks.

---

## 2. System Layout

Below is a general outline of the `src/nova` folder:

- **config/**  
  Manages loading and validating the system’s YAML config files (e.g. `default.yaml`). Exposes `ConfigManager`.

- **core/**  
  - **markdown/**: Houses the `MarkdownWriter` class and templates (`base.md`, `image.md`) for generating consistent Markdown.  
  - **logging.py**: Defines `NovaLogger`, `NovaFormatter`, and `LoggingManager`, centralizing logging setup.  
  - **metadata.py**, **serialization.py**, **reference_manager.py**, etc.: Core classes and utilities around storing metadata, referencing attachments, and so on.  
  - **pipeline.py**: The main `NovaPipeline` orchestration that runs the phases in order and tracks state.  
  - **progress.py**: Tracks progress across phases and files.

- **handlers/**  
  Each file in `handlers/` processes a specific file type (e.g. `image.py`, `document.py`, `archive.py`).  
  `HandlerRegistry` maps file extensions to the correct handler.

- **phases/**  
  Each sub-phase logic is in its own file: `parse.py`, `disassemble.py`, `split.py`, `finalize.py`.  
  A base class `base.py` gives common scaffolding for phase classes.

- **models/**  
  Contains `document.py`, `links.py`, `link_map.py`, `metadata.py`, etc. These define pydantic models (e.g. `LinkContext`, `LinkRelationshipMap`), data classes, and typed structures for references and link states.

- **processor/**  
  Additional specialized code for advanced processing steps (like `markdown_processor.py`).

- **ui/**  
  - `visualization.py`: Link graph visualization (uses D3.js).  
  - `navigation.py`: Renders navigation elements in HTML.  
  - `progress.py`: Enhanced progress display with `rich`.

- **utils/**  
  Reusable functions and classes that are not core but used across the codebase (`file_utils.py`, `output_manager.py`, `path_utils.py`, etc.).

- **cli.py**  
  The command-line entry point that sets up arguments, logging, and calls `NovaPipeline`.

---

## 3. Phases & Pipeline

### The `NovaPipeline` Class

`core/pipeline.py` defines a `NovaPipeline` that:
- Is constructed with a `ConfigManager`.
- Has an internal dictionary of phases, e.g. `{"parse": ParsePhase(...), "disassemble": DisassemblyPhase(...), ...}`.
- Calls `process_directory()` to run the pipeline across all files in the input directory.
- For each phase, it gathers the relevant files (e.g. for parse, it uses the original input dir; for disassemble, it uses the parse output dir, etc.) and calls `phase.process_file(file_path, output_dir)`.
- Maintains global pipeline state in `self.state[phase_name]`.

**Key points**  
- Each phase can read or write to `self.state[phase]`, allowing high-level tracking of `successful_files`, `failed_files`, etc.  
- The pipeline also checks timestamps in `needs_reprocessing()` (for parse) to skip or reprocess files.

#### Phase Execution Flow

1. **Parse** phase enumerates all input files and calls `ParsePhase.process_file()`.  
2. **Disassemble** reads parse-phase output (`*.parsed.md`) and splits them into `.summary.md` / `.rawnotes.md`.  
3. **Split** further consolidates and creates `Summary.md`, `Raw Notes.md`, `Attachments.md`.  
4. **Finalize** might do link validation, copy attachments, or anything that needs a final pass.

### Adding a New Phase

1. **Create a new file** in `nova/phases/` (e.g. `myphase.py`).  
2. **Inherit** from `Phase`:  

class MyPhase(Phase):
async def process_impl(self, file_path: Path, output_dir: Path, metadata=None):
# Implement your logic

3. **Register** it in `NovaPipeline` by adding to `self.phases` in the constructor or in `get_phase_instance()`:

self.phases[“myphase”] = MyPhase(config, self)

4. **Include** it in your config’s `pipeline.phases` list (or override phases at runtime) so it runs in the correct order.

### Phase Implementation Rules

- Each phase has a `process_impl(file_path, output_dir, metadata=...)` coroutine that returns updated metadata or `None`.
- **File Discovery**: Typically each phase looks for specific file patterns from the previous phase’s output. For example, `disassemble` looks in `parse_dir/*.parsed.md`.
- **Output**: The phase decides what to write (e.g., `.summary.md`, `.rawnotes.md`, `.md`, `.metadata.json`) and updates the pipeline’s `self.state["myphase"]` sets for success/failure/unchanged.
- **Finalize** can run a final `phase.finalize()` to do any summary, cleanup, or logs.

---

## 4. Handlers & File Processing

Handlers are specialized classes in `nova/handlers/` that parse and convert specific file types into a standardized output. For instance:

- `DocumentHandler`: `.docx`, `.pdf`, `.odt`  
- `ImageHandler`: `.jpg`, `.svg`, `.heic`, etc.  
- `SpreadsheetHandler`: `.xlsx`, `.csv`  
- `MarkdownHandler`: `.md`  
- `AudioHandler`: `.mp3`, `.wav`  
- `VideoHandler`: `.mp4`, `.mov`  

The `HandlerRegistry` in `registry.py`:
- Maintains a dictionary of `file_type -> handler_instance`.
- Looks up the appropriate handler based on a file’s extension.
- If no handler is found, the file is marked as “skipped” or “unsupported.”

Within the **Parse** phase:
1. For each file, we do `handler = handler_registry.get_handler(file_path)`  
2. `handler.process_impl(file_path, metadata)` returns updated DocumentMetadata.

### Adding a New Handler

1. **Create** a new file in `nova/handlers/` (e.g. `ppt_handler.py`).  
2. **Subclass** `BaseHandler`, specify:

class PptHandler(BaseHandler):
name = “ppt”
version = “0.1.0”
file_types = [“ppt”]  # or anything else

3. **Implement** `process_impl(self, file_path, metadata)`. Usually:
   - Read the file (or call specialized libs).
   - Produce `.parsed.md`.
   - Populate `metadata`.
   - Possibly do partial conversions or add attachments.  
4. **Register** it in `HandlerRegistry` (the `_register_default_handlers()` method) or dynamically so the system knows to use it for `.ppt`.

### Handler Responsibilities

- **Validate** the file if needed (some do a `validate_file()` internally).  
- **Read** the file’s contents and convert to a standard textual form if possible (like `.parsed.md` or code blocks).  
- Use the **unified Markdown** approach via `MarkdownWriter` to generate `.parsed.md`.  
- **Save** updated metadata (`.metadata.json`) referencing the handler name, version, and output files.

---

## 5. Markdown Generation

Nova uses a single **MarkdownWriter** (in `core/markdown/writer.py`) to ensure consistent `.parsed.md` content:
- `write_document(title, content, metadata, file_path, output_path)` is the typical entry point to produce a full Markdown file from templates.
- **Templates**:
  - `base.md` for standard doc structure
  - `image.md` for image-specific structure
- Handlers call `markdown_writer.write_document(...)` or `markdown_writer.write_image(...)`. This eliminates ad-hoc string building in each handler.
- **Benefits**:  
  - Central location to tweak heading styles, front matter, or reference syntax.  
  - Minimizes duplication across different handlers.

---

## 6. Configuration Management

- The **ConfigManager** in `nova/config/manager.py` loads `default.yaml` (or an override path).  
- The loaded config is stored in a `NovaConfig` pydantic model with sub-sections like `cache`, `logging`, `pipeline`, `debug`, etc.  
- `Nova` or `NovaPipeline` references `config.pipeline.phases` to decide which phases to run.  
- The logging config portion is used by `LoggingManager` to set up console/file loggers.

**Highlights**:
- You can set environment variables (e.g. `NOVA_LOG_LEVEL=DEBUG`) to override part of the config dynamically.  
- Paths in the config are typically expanded and validated, ensuring they exist if `create_dirs=True`.

---

## 7. Metadata & References

**FileMetadata / DocumentMetadata**:
- Each file or document that passes through the pipeline has associated metadata (e.g. `metadata['file_path']`, `output_files`, `errors` array).
- The metadata is often saved to `.metadata.json` in the same subdirectory as the `.parsed.md`.

**ReferenceManager** (in `core/reference_manager.py`):
- Used to track references in Markdown text, e.g. `[ATTACH:IMAGE:foo]`, `[NOTE:bar]`, etc.
- `extract_references(content, source_file)` can find these references for subsequent link validation or attachment embedding.

**LinkRelationshipMap**:
- Handles cross-file linking with `direct_relationships`, `reverse_relationships`, `navigation_paths`, etc.
- The `Finalize` phase or visualization modules can produce link graphs to show broken references or highlight “bidirectional” link usage.

---

## 8. Logging & Debugging

### Logging

- Implemented in `core/logging.py`:  
  - `NovaLogger` extends Python’s `logging.Logger` with fields like `.phase`, `.handler`, etc.  
  - `LoggingManager` sets up console and file handlers, using `NovaFormatter` for a uniform log format.
- The code references these logs from every major piece (phases, handlers, pipeline). This ensures logs are consistent across modules.

### Debugging

- Optional advanced debugging can be enabled in config (`debug.enabled: true`).  
- A `DebugManager` can track extra details like memory usage, pipeline state snapshots, or break on error if `break_on_error` is set.  
- Phase states (`self.state`) can be dumped to JSON for later analysis if `dump_state` is enabled.

---

## 9. Utility Modules

**utils/output_manager.py**:
- The `OutputManager` helps unify how we construct output paths for each phase. For example, `.parsed.md` or `.metadata.json` with the same relative structure as input.  
- Example usage:  

output_path = self.output_manager.get_output_path_for_phase(
file_path,
“parse”,
“.parsed.md”
)

**utils/file_utils.py**:
- Has a `safe_write_file()` function that only overwrites a file if content changes. This helps avoid rewriting timestamps unnecessarily.

**utils/path_utils.py**:
- Functions to sanitize filenames (e.g. removing special characters), get relative paths, or build `.metadata.json` filenames consistently.

---

## 10. Extending or Customizing Nova

1. **New Phases**: Create a `MyPhase` class extending `Phase`, override `process_impl()`, register it, and add it to `config.pipeline.phases`.  
2. **New Handlers**: Create `MyHandler`, specify file extensions, implement `process_impl()`, and register in `HandlerRegistry`.  
3. **Additional Markdown Templates**: If you need specialized formatting, add `.md` files under `core/markdown/templates`. Then call `markdown_writer.write_from_template("mytemplate", **kwargs)`.  
4. **Link or UI Enhancements**: If you want custom link visualizations, see `ui/visualization.py` for D3-based graph creation or `navigation.py` for nav headers.  
5. **Logging**: Modify or expand `logging` config in `default.yaml` to add new log levels, separate files, or structured logging fields.  
6. **Reference Management**: If new reference types are needed (`[VIDEO:...], [SHEET:...]`), update `ReferenceManager` to handle them and revise phases or `Finalize` logic to validate them.

---

## Conclusion

With the revised architecture, Nova has:
- A consistent pipeline that organizes the entire flow from raw input to final outputs.
- A single point of logging configuration (eliminating multiple ad hoc logger settings).
- Centralized, consistent Markdown generation.
- A flexible approach for adding new phases or handlers.
- Strong references/metadata management to keep track of attachments, links, and sections.

This structure should make the system easier to maintain and expand as new features, file types, or phases are introduced.