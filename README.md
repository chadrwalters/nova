# Nova Document Processing System

A powerful document processing pipeline that converts various file formats into structured Markdown outputs, with support for AI-powered analysis and rich metadata extraction.

## Overview

Nova processes your documents through a configurable pipeline, organizing content into structured Markdown files with intelligent section splitting, asset management, and metadata preservation.

## Features

### 🔄 Phase-Based Pipeline
- **Parse Phase**: Converts documents to intermediate Markdown with metadata
- **Split Phase**: Organizes content into structured sections
- **Finalize Phase**: Creates clean output with resolved links
- Extensible architecture - easily add new phases

### 📄 Format Support
- **Documents**: PDF, DOCX, RTF
- **Images**: JPEG, PNG, HEIC (with AI descriptions)
- **Audio**: MP3, WAV
- **Data**: XLSX, CSV
- **Web**: HTML
- **Archives**: ZIP (with nested content)

### 🧠 Intelligent Processing
- AI-powered image analysis and descriptions
- Smart section detection and organization
- Automatic link resolution
- Asset deduplication
- Rich metadata extraction

### 📊 Progress & Logging
- Real-time progress tracking
- Detailed logging with configurable levels
- Color-coded console output
- Comprehensive error reporting

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/nova.git
cd nova
```

2. Run the installation script:
```bash
./install.sh
```

This will install required system dependencies:
- Tesseract (OCR)
- libheif (HEIC support)
- FFmpeg (audio processing)
- ImageMagick (image processing)
- Python dependencies via Poetry

## Configuration

1. Create your config file:
```bash
cp config/nova.template.yaml config/nova.yaml
```

2. Configure your settings:
```yaml
base_dir: "${HOME}/Library/Mobile Documents/com~apple~CloudDocs"
input_dir: "${HOME}/Library/Mobile Documents/com~apple~CloudDocs/_NovaInput"
output_dir: "${HOME}/Library/Mobile Documents/com~apple~CloudDocs/_Nova"
processing_dir: "${HOME}/Library/Mobile Documents/com~apple~CloudDocs/_NovaProcessing"

# Configure pipeline phases
pipeline:
  phases:
    - parse
    - split
    - finalize
```

3. Optional environment variables:
- `NOVA_CONFIG_PATH`: Override default config location
- `NOVA_LOG_LEVEL`: Set logging verbosity (DEBUG, INFO, etc.)
- `OPENAI_API_KEY`: Required for AI image analysis

## Usage

### Basic Usage
```bash
./run_nova.sh
```

This will process files from `_NovaInput` through all configured phases.

### Advanced Usage
```bash
# Process specific phases
./run_nova.sh --phases parse split

# Process a single file
./run_nova.sh --input-dir ~/Documents/file.pdf

# Enable debug logging
./run_nova.sh --debug
```

## Directory Structure

### Input
Place your files in the configured input directory:
```
_NovaInput/
├── Documents/
│   └── report.pdf
├── Images/
│   └── diagram.png
└── Data/
    └── spreadsheet.xlsx
```

### Processing
Files are processed through phases:
```
_NovaProcessing/
├── phases/
│   ├── parse/
│   │   └── *.parsed.md
│   └── split/
│       ├── Summary.md
│       ├── Raw Notes.md
│       └── Attachments.md
└── cache/
```

### Output
Final output is organized as:
```
_Nova/
├── Summary.md
├── Raw Notes.md
├── Attachments.md
└── assets/
    ├── images/
    ├── documents/
    └── other/
```

## Content Organization

Nova uses special markers and reference formats to organize content:

### Section Markers
```markdown
--==SUMMARY==--
High-level summary content

--==RAW NOTES==--
Detailed content and notes

--==ATTACHMENTS==--
Referenced attachments and their content
```

### Reference Format
Nova uses a consistent reference system across files:

- **Attachments**: `[ATTACH:TYPE:ID]`
  ```markdown
  [ATTACH:PDF:20240118-document-name]
  [ATTACH:JPG:20240118-screenshot]
  ```

- **Notes**: `[NOTE:ID]`
  ```markdown
  [NOTE:20240118-meeting-notes]
  ```

IDs are generated from filenames and include date prefixes when available.

### Output Structure
Content is organized into three main files:

1. **Summary.md**
   - High-level summaries
   - References to attachments using `[ATTACH:type:id]`
   - Links to raw notes

2. **Raw Notes.md**
   - Detailed notes organized by `[NOTE:id]` sections
   - References to attachments
   - Original content structure preserved

3. **Attachments.md**
   - Attachments grouped by type
   - Each attachment has its own `[ATTACH:type:id]` section
   - Preserves metadata and content from source files


