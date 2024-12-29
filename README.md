Nova Document Processing System

Nova is a multi-phase document processing pipeline that converts various file formats into structured Markdown outputs. The system has evolved through several versions, each adding key features and improvements:
	•	V1: Generated PDFs from Markdown files, then merged them into a single PDF document.
	•	V1.5: Began splitting output into three Markdown files—Summary, Raw Notes, and Attachments—but the codebase had limited reliability and clarity.
	•	V2 (Current): Complete rewrite using a phase-based architecture with caching. We can easily add new phases without regenerating all outputs, saving time when files are unchanged.

Key Features
	1.	Phase-Based Pipeline
	•	Parse Phase: Converts original documents into .parsed.md files while preserving original data.
	•	Split Phase: Generates three consolidated files from the parsed outputs: Summary.md, Raw Notes.md, and Attachments.md.
	•	Additional phases (like image classification, audio processing, or custom tasks) can be added to src/nova/phases as needed.
	2.	Caching & Reprocessing
	•	Checks if input files (or their relevant metadata) have changed before regenerating output.
	•	Skips processing for unchanged files, speeding up repeated runs.
	3.	Handlers for Multiple Formats
	•	Document Handler (Word, PDF, etc.)
	•	Image Handler (JPEG, PNG, HEIC, etc.)
	•	Audio Handler (MP3, WAV, etc.)
	•	Spreadsheet Handler (XLSX, CSV, etc.)
	•	Markdown Handler (MD files themselves)
	•	Archive Handler (ZIP archives)
Each handler converts an input into .parsed.md, often including AI-assisted transformations where possible.
	4.	Extensible Configuration
	•	YAML-based config (e.g., nova.yaml), supplemented by environment variables.
	•	Allows custom directory locations for input, output, cache, and processing directories.
	•	Flexible to add new phases or modify existing ones with minimal disruption.
	5.	Advanced Logging & Metrics
	•	Rich logs for debugging (via rich and custom formatting).
	•	Optionally track performance metrics (timings, memory usage, etc.) in JSON logs.
	6.	Pluggable Phase Architecture
	•	Implementation in src/nova/phases/<phase>.py.
	•	Each phase can read or write .parsed.md files, generate or update metadata, and place new output in the pipeline’s processing directory.

How Nova Works
	1.	Input Directory
Place all source files (PDFs, images, spreadsheets, etc.) in the configured input_dir (by default _NovaInput in iCloud).
	2.	Parse Phase
Each file is assigned a handler based on extension. The handler produces a .parsed.md file in phases/parse/. Example:

└── parse/
    ├── MyDocument.parsed.md
    ├── MyImage.parsed.md
    └── ...


	3.	Split Phase
Collects all .parsed.md files, locates the raw notes marker (--==RAW NOTES==--), extracts a short “summary” block, and populates three consolidated outputs:
	1.	Summary.md (30-40% of content)
	2.	Raw Notes.md (50-60% of content)
	3.	Attachments.md (5-10% listing and linking attachments)
	4.	Caching
	•	Each file’s modification time is tracked; if it’s the same, we skip reprocessing.
	•	Caches AI calls (e.g., image recognition or text extraction) to avoid repetitive API usage.
	5.	Output
Final processed Markdown files end up in the phases/split/ directory, and optionally in the main _Nova directory if desired.

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

