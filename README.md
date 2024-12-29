Nova Document Processing System

Nova is a multi-phase document processing pipeline that converts various file formats into structured Markdown outputs. The system has evolved through several versions, each adding key features and improvements:
	•	V1: Generated PDFs from Markdown files, then merged them into a single PDF document.
	•	V1.5: Began splitting output into three Markdown files—Summary, Raw Notes, and Attachments—but the codebase had limited reliability and clarity.
	•	V2 (Current): Complete rewrite using a phase-based architecture with caching. We can easily add new phases without regenerating all outputs, saving time when files are unchanged.

Key Features
	1.	Phase-Based Pipeline
	•	Parse Phase: Converts original documents into .parsed.md files with rich metadata and asset extraction
	•	Split Phase: Intelligently organizes content using section markers (--==SUMMARY==-- etc.)
	•	Finalize Phase: Ensures proper link resolution and creates clean output structure
	•	Additional phases can be added to src/nova/phases as needed

	2.	Rich Metadata & Asset Handling
	•	Extracts and preserves document metadata (creation date, author, etc.)
	•	Manages assets in structured directories (images, attachments)
	•	AI-powered image analysis and description generation
	•	Smart cross-referencing between documents

	3.	Handlers for Multiple Formats
	•	Document Handler: PDF (text + images), DOCX (with styles), RTF
	•	Image Handler: JPEG, PNG, HEIC with AI-powered descriptions
	•	Audio Handler: MP3, WAV with metadata extraction
	•	Spreadsheet Handler: XLSX, CSV with table formatting
	•	Markdown Handler: Direct MD processing
	•	Archive Handler: ZIP with nested content support
	•	HTML Handler: Web page conversion with styling

	4.	Intelligent Processing
	•	Section detection and organization
	•	Smart link resolution between documents
	•	Asset deduplication and path normalization
	•	Configurable content splitting rules

	5.	Progress Tracking & Logging
	•	Rich console interface with progress bars
	•	Color-coded status messages
	•	Detailed logging with configurable verbosity
	•	Error tracking with context

How Nova Works

1. Input Organization
	•	Place source files in _NovaInput/
	•	Supports nested directory structure
	•	Maintains relative paths in output
	•	Handles duplicate file names

2. Parse Phase
Each file is processed by its appropriate handler:

_NovaProcessing/phases/parse/
├── documents/
│   ├── report.parsed.md
│   ├── report.metadata.json
│   └── report.assets/
├── images/
│   ├── diagram.parsed.md
│   └── diagram.metadata.json
└── spreadsheets/
    └── data.parsed.md

3. Split Phase
Processes all parsed files and generates three main outputs:

_NovaProcessing/phases/split/
├── Summary.md       # Key points and highlights
├── Raw Notes.md     # Detailed content and notes
├── Attachments.md   # Asset catalog and references
└── assets/         # Consolidated attachments

4. Finalize Phase
Creates the final output structure:

_Nova/
├── Summary.md
├── Raw Notes.md
├── Attachments.md
└── assets/
    ├── images/
    ├── documents/
    └── other/

5. Content Markers
Nova uses special markers to organize content:
```
--==SUMMARY==--
Key points and highlights go here

--==RAW NOTES==--
Detailed notes and content go here

--==ATTACHMENTS==--
List of attachments and references
```

Installation & Setup
	1.	Install Dependencies

./install.sh

Installs Tesseract, libheif, FFmpeg, ImageMagick (and more), plus Python dependencies.

	2.	Configure
	•	Duplicate config/nova.template.yaml to config/nova.yaml.
	•	Update api_key fields if using AI/vision modules.
	•	Adjust directory paths for input_dir, output_dir, etc.
	3.	Run Nova

./run_nova.sh

By default, Nova looks for files in _NovaInput and outputs to _NovaProcessing (intermediate) and _Nova (final).

Usage Examples

Processing a Single File

poetry run python3 -m nova.cli --input-dir ~/Documents/TestFile.pdf --phases parse

Processes only the parse phase for a single file.

Processing Entire Directory

poetry run python3 -m nova.cli --input-dir ~/Documents/NovaDemos --phases parse split

Runs both parse and split phases, generating .parsed.md files and the three consolidated Markdown outputs.

