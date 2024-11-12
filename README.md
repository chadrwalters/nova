# Nova Personal and Professional Assistant 

## Overview

Nova is an advanced AI assistant designed to be your personal analytics and growth partner. This repository contains both the Nova system prompt and a set of tools designed to help prepare your personal data for use with Nova.

The primary workflow involves:
1. Exporting markdown files from Bear.app (or similar note-taking apps)
2. Consolidating these files into a single markdown document
3. Converting the consolidated markdown into a PDF
4. Using the PDF with the Nova prompt in your preferred AI platform

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

#### Markdown Consolidator and PDF Generator
- Combines multiple markdown files into a single document
- Handles image processing and path resolution
- Converts markdown to professionally formatted PDF
- Configurable styling and layout options

#### Automation Script
- Streamlines the consolidation and conversion process
- Handles cleanup and organization of files
- Maintains consistent directory structure

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

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/chadrwalters/nova.git
   cd nova
   ```

2. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Directory Setup
Edit `consolidate.sh` to configure your directories:
```bash
NOVA_INPUT_DIR="/path/to/your/markdown/files"
NOVA_CONSOLIDATED_DIR="/path/to/consolidated/output"
NOVA_OUTPUT_DIR="/path/to/final/output"
```

### Styling Options
- `config/default_config.yaml`: PDF configuration options
- `styles/default_style.css`: PDF styling
- `templates/default_template.html`: HTML template structure

## Usage

1. Export your markdown files to the input directory

2. Run the consolidation script:
   ```bash
   ./consolidate.sh
   ```

3. Find your output files:
   - Consolidated markdown: `_NovaConsolidatedMarkdown/output.md`
   - Final PDF: `_Nova/output.pdf`

4. Use the generated PDF with the Nova prompt in your AI platform

## Project Structure
```
.
├── prompts/
│   └── Nova.prompt              # Core Nova AI system prompt
├── config/
│   └── default_config.yaml      # PDF configuration
├── styles/
│   └── default_style.css        # PDF styling
├── templates/
│   └── default_template.html    # HTML template
├── markdown_to_pdf_converter.py # PDF conversion script
├── consolidate.sh              # Main automation script
└── requirements.txt            # Python dependencies
```

## Requirements

- Python 3.11+
- Dependencies listed in `requirements.txt`
- Unix-like environment (for shell script)

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
