# Nova Personal and Professional Assistant 

## Overview

Nova is an advanced AI assistant designed to be your personal analytics and growth partner. This repository contains both the Nova system prompt and a set of tools designed to help prepare your personal data for use with Nova.

The primary workflow involves:
1. Converting PDFs to markdown (if needed)
2. Exporting markdown files from Bear.app (or similar note-taking apps)
3. Consolidating these files into a single markdown document
4. Converting the consolidated markdown into a PDF
5. Using the PDF with the Nova prompt in your preferred AI platform

This workflow helps overcome file number limitations in AI platforms while maintaining the context and structure of your personal data.

## Core Components

### Nova AI Assistant Prompt

The Nova prompt (`prompts/Nova.prompt`) is designed to:
- Process personal data (notes, journals, conversations)
- Provide data-backed personal insights
- Track emotional and behavioral patterns
- Maintain contextual awareness across conversations
- Generate quantifiable metrics and progress tracking

### Supporting Tools

#### PDF to Markdown Converter
- Extracts text and images from PDF files
- Performs OCR on images to extract text
- Saves images to a media directory
- Maintains directory structure and relationships

#### Markdown Consolidator and PDF Generator
- Combines multiple markdown files into a single document
- Handles image processing and path resolution
- Converts markdown to professionally formatted PDF
- Configurable styling and layout options

#### Automation Script
- Streamlines the entire conversion and consolidation process
- Handles cleanup and organization of files
- Maintains consistent directory structure
- Processes both PDF and markdown inputs

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/chadwalt/nova.git
   cd nova
   ```

2. Install system dependencies:

   On macOS:
   ```bash
   brew install tesseract  # For OCR support
   brew install python@3.11
   ```

   On Ubuntu/Debian:
   ```bash
   sudo apt-get update
   sudo apt-get install -y \
       tesseract-ocr \
       python3.11 \
       python3-pip \
       build-essential \
       python3-dev \
       python3-setuptools \
       python3-wheel \
       python3-cffi \
       libcairo2 \
       libpango-1.0-0 \
       libpangocairo-1.0-0 \
       libgdk-pixbuf2.0-0 \
       libffi-dev \
       shared-mime-info
   ```

   On Windows:
   - Install Python 3.11+ from python.org
   - Install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki
   - Add Tesseract to your system PATH

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment:
   ```bash
   cp .env.template .env
   ```

5. Edit `.env` file with your paths:
   ```bash
   # Example .env configuration
   SYNC_BASE="/Users/username/path/to/your/synced/folder"
   NOVA_INPUT_DIR="${SYNC_BASE}/_NovaIndividualMarkdown"
   NOVA_CONSOLIDATED_DIR="${SYNC_BASE}/_NovaConsolidatedMarkdown"
   NOVA_OUTPUT_DIR="${SYNC_BASE}/_Nova"
   ```

6. Create required directories:
   ```bash
   mkdir -p "$NOVA_INPUT_DIR" "$NOVA_CONSOLIDATED_DIR" "$NOVA_OUTPUT_DIR"
   ```

## Usage

### Converting PDFs to Markdown

1. Place your PDF files in the input directory (`$NOVA_INPUT_DIR`)
2. Run the consolidation script:
   ```bash
   ./consolidate.sh
   ```
   The script will:
   - Find all PDF files in the input directory
   - Convert them to markdown with images in `_media` directory
   - Maintain the original directory structure
   - Extract text from images using OCR when possible

### Processing Markdown Files

1. Export your markdown files to your configured input directory (`$NOVA_INPUT_DIR`)
2. Run the consolidation script:
   ```bash
   ./consolidate.sh
   ```

### Output Files

After running the script, you'll find:
- Converted markdown files: In the same directory as the source PDFs
- Media files: In `_media` directory within the input directory
- Consolidated markdown: `$NOVA_CONSOLIDATED_DIR/output.md`
- Final PDF: `$NOVA_OUTPUT_DIR/output.pdf`

## Project Structure
```
.
├── prompts/
│   └── Nova.prompt                 # Core Nova AI system prompt
├── config/
│   └── default_config.yaml         # PDF configuration
├── styles/
│   └── default_style.css           # PDF styling
├── templates/
│   └── default_template.html       # HTML template
├── pdf_to_markdown_converter.py    # PDF to Markdown conversion script
├── markdown_to_pdf_converter.py    # PDF generation script
├── markdown_consolidator.py        # Markdown consolidation script
├── consolidate.sh                 # Main automation script
├── .env.template                  # Environment template
├── .env                          # Local environment configuration (not in git)
└── requirements.txt              # Python dependencies
```

## Requirements

### System Requirements
- Python 3.11+
- Tesseract OCR
- Cairo graphics library
- Pango text layout engine
- GDK-PixBuf image loading library

### Python Dependencies
- PyMuPDF (for PDF processing)
- pytesseract (for OCR)
- Pillow (for image processing)
- Click (for CLI interface)
- WeasyPrint (for PDF generation)
- Rich (for console output)
- Additional dependencies in `requirements.txt`

## Troubleshooting

### PDF Conversion Issues
- Ensure Tesseract is properly installed and in your PATH
- Check PDF permissions and accessibility
- Verify sufficient disk space for image extraction
- Look for errors in the conversion log

### Image Processing Issues
- Verify image file permissions
- Check available memory for large images
- Ensure media directory is writable
- Review image optimization settings if needed

### General Issues
- Check log files for detailed error messages
- Verify all dependencies are installed
- Ensure proper file permissions
- Confirm sufficient disk space

## Using Nova with Claude

### Initial Setup in Claude

1. Create a new project:
   - Open Claude
   - Click "Create Project"
   - Name it "Nova"

2. Add the Nova prompt:
   - Go to Custom Instructions in the project settings
   - Copy the entire contents of `prompts/Nova.prompt`
   - Paste it into the Custom Instructions field
   - Save the changes

3. Add your consolidated data:
   - Go to Project Files
   - Upload your generated PDF (`_Nova/output.pdf`)

### Updating Your Data

When you have new notes or journal entries:

1. Generate new consolidated PDF:
   ```bash
   ./consolidate.sh
   ```

2. Update Claude project:
   - Open your Nova project in Claude
   - Go to Project Files
   - Delete the existing PDF
   - Upload the new PDF from `_Nova/output.pdf`

### Best Practices

- Keep your data current by updating regularly
- Remove old PDFs before uploading new ones
- Verify PDF upload was successful
- Maintain consistent markdown formatting in your notes
- Use clear section headers for better organization
- Consider weekly updates or when significant content is added

### Troubleshooting

If Nova seems to be missing context:
- Confirm the PDF was successfully uploaded
- Verify the old PDF was completely removed
- Check that the consolidation process completed without errors
- Review the PDF content to ensure all data was included
- Try clearing Claude's conversation history

## Configuration

### Environment Setup
The following environment variables must be configured in your `.env` file:

- `SYNC_BASE`: Base path to your synced notes or cloud storage directory
- `NOVA_INPUT_DIR`: Where your markdown files are stored
- `NOVA_CONSOLIDATED_DIR`: Where the consolidated markdown will be saved
- `NOVA_OUTPUT_DIR`: Where the final PDF will be generated

### Sync Setup
Nova is designed to work with markdown files that are synced across your devices. This allows you to write notes on your phone, tablet, or computer and have them automatically available for processing.

Popular note-taking apps that support this workflow include:
- Bear (uses iCloud for sync)
- Obsidian (can use iCloud, Dropbox, or other cloud storage)
- Typora (when used with a cloud-synced folder)
- Any text editor when used with a synced folder (iCloud Drive, Dropbox, Google Drive, etc.)

Ensure your chosen note-taking app is set up to save files in the directory specified by `NOVA_INPUT_DIR`.

### Styling Options
- `config/default_config.yaml`: PDF configuration options
- `styles/default_style.css`: PDF styling
- `templates/default_template.html`: HTML template structure

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

Copyright 2024 Chad Walters

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
