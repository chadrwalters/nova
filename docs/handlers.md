# Nova Handlers

## Overview

Nova's handlers are specialized components responsible for processing different types of files. Each handler inherits from `BaseHandler` and implements specific logic for its supported file types.

## Handler Registry

The `HandlerRegistry` class manages all available handlers and their file type associations. It provides:
- Registration of handlers by file extension
- Handler lookup by file type
- Default handler initialization
- File processing orchestration

### Default Handler Mappings

- **Document Files**: `.txt`, `.docx`, `.doc`, `.rtf`, `.odt`, `.pdf`
- **Image Files**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.heic`, `.webp`
- **Audio Files**: `.mp3`, `.wav`, `.m4a`, `.ogg`
- **Video Files**: `.mp4`, `.mov`, `.avi`, `.mkv`
- **Spreadsheet Files**: `.xlsx`, `.xls`, `.csv`
- **HTML Files**: `.html`, `.htm`
- **Archive Files**: `.zip`, `.tar`, `.gz`, `.7z`
- **Markdown Files**: `.md`, `.markdown`

## Base Handler

### Overview
The `BaseHandler` class (`src/nova/context_processor/handlers/base.py`) provides the foundation for all handlers with common functionality:

- Metadata management
- File processing status tracking
- Error handling
- Output file management

### Core Components

#### ProcessingStatus
Enum-like class defining possible processing states:
- `COMPLETED`: File successfully processed
- `FAILED`: Processing failed with error
- `SKIPPED`: File intentionally skipped
- `UNCHANGED`: File unchanged from previous processing

#### ProcessingResult
Class encapsulating processing results:
- `status`: Current processing status
- `metadata`: Document metadata
- `error`: Error message if any

#### BaseHandler
Base class providing:
- Metadata store initialization
- Metadata validation
- Base metadata updates
- Output file saving
- Error handling

### Key Methods

#### _update_base_metadata
Updates core metadata fields:
- File path and size
- Handler name and version
- Creation and modification timestamps
- Title from filename

#### _save_output
Handles output file saving:
- Validates metadata schema
- Creates output directories
- Writes content
- Updates metadata
- Validates related metadata

## Document Handler

### Overview
The `DocumentHandler` processes various document formats:
- PDF files
- Microsoft Word documents (DOC/DOCX)
- Rich Text Format (RTF)
- OpenDocument Text (ODT)
- Apple Pages documents

### Libraries Used
- `docx2txt`: Word document processing
- `pypdf`: PDF processing
- Custom metadata handling for each format

### Processing Flow
1. Identifies document type
2. Extracts text content
3. Preserves document structure
4. Generates markdown output
5. Handles document metadata

## Markdown Handler

### Overview
The `MarkdownHandler` (`src/nova/context_processor/handlers/markdown.py`) processes markdown files, handling:
- Content processing
- Link updates
- Embedded document processing
- Metadata extraction

### Key Features

#### Link Processing
- Updates relative links to be input-directory relative
- Handles dated directory structures
- Preserves external links
- Updates embedded document references

#### Embedded Documents
- Processes documents marked with `<!-- {"embed": "true"} -->`
- Maintains document hierarchy
- Updates relative paths
- Preserves original links for failed embeds

### Processing Flow

1. **Initialization**
   - Creates metadata if not provided
   - Updates base metadata
   - Initializes markdown writer

2. **Content Processing**
   - Reads markdown content
   - Processes with markdown writer
   - Updates links and references

3. **Embedded Document Processing**
   - Identifies embedded documents
   - Processes each embedded document
   - Updates references and paths
   - Maintains document structure

4. **Output Generation**
   - Creates output markdown file
   - Updates metadata
   - Saves processed content

## Image Handler

### Overview
The `ImageHandler` (`src/nova/context_processor/handlers/image.py`) processes image files with:
- Format conversion
- OpenAI vision analysis
- Metadata extraction
- Markdown output generation

### Supported Formats
- JPEG/JPG
- PNG
- GIF
- BMP
- TIFF
- WebP
- HEIC/HEIF
- SVG

### Key Components

#### Image Conversion
- Converts all formats to JPEG
- Special handling for SVG using CairoSVG
- Alpha channel handling
- DPI preservation
- Format-specific optimizations

#### OpenAI Integration
- Uses gpt-4o model for vision analysis
- Base64 image encoding
- Detailed image description generation
- Error handling and fallbacks

### Processing Flow

1. **Initialization**
   - Creates metadata if not provided
   - Updates base metadata
   - Initializes OpenAI client

2. **Image Processing**
   - Converts to JPEG format
   - Extracts image information
   - Handles alpha channels
   - Preserves quality settings

3. **Image Analysis**
   - Encodes image in base64
   - Sends to OpenAI for analysis
   - Processes response
   - Handles analysis failures

4. **Output Generation**
   - Creates markdown documentation
   - Includes image information
   - Embeds analysis results
   - Adds image reference

### Libraries Used
- Pillow (PIL): Core image processing
- pillow-heif: HEIC/HEIF support
- CairoSVG: SVG conversion
- OpenAI: Image analysis

## Spreadsheet Handler

### Overview
The `SpreadsheetHandler` processes spreadsheet files:
- Excel files (XLSX/XLS)
- CSV files
- OpenDocument Spreadsheets (ODS)

### Libraries Used
- `pandas`: Data processing
- `openpyxl`: Excel file handling
- `tabulate`: Markdown table generation

### Processing Flow
1. Loads spreadsheet data
2. Converts to pandas DataFrame
3. Processes each worksheet
4. Generates markdown tables
5. Preserves data structure

## HTML Handler

### Overview
The `HTMLHandler` processes HTML files:
- HTML documents
- Web pages
- HTML exports

### Libraries Used
- `html2text`: HTML to markdown conversion
- `BeautifulSoup`: HTML parsing
- Custom link handling

### Key Features
- Link preservation
- Image handling
- Table conversion
- Structure preservation

## Archive Handler

### Overview
The `ArchiveHandler` processes archive files:
- ZIP archives
- TAR archives
- 7Z archives
- Compressed files (GZ, BZ2, XZ)

### Processing Flow
1. Archive extraction
2. Content processing
3. Structure preservation
4. Metadata tracking
5. Reference management

## Audio Handler

### Overview
The `AudioHandler` processes audio files:
- MP3 files
- WAV files
- FLAC files
- M4A files
- OGG files
- AAC files

### Features
- Metadata extraction
- Duration analysis
- Format information
- Quality assessment

## Video Handler

### Overview
The `VideoHandler` processes video files:
- MP4 files
- AVI files
- MOV files
- MKV files
- WebM files
- FLV files

### Features
- Video metadata extraction
- Duration analysis
- Resolution information
- Format details
- Thumbnail generation

## Text Handler

### Overview
The `TextHandler` processes plain text files:
- Basic text files
- Character encoding detection
- Line ending normalization
- Content analysis

### Features
- Encoding detection
- Line counting
- Format preservation
- Basic metadata extraction

## Common Handler Patterns

### Metadata Management
All handlers follow consistent metadata patterns:
- Create or update metadata
- Validate schema
- Track processing status
- Store output information

### Error Handling
Handlers implement robust error handling:
- Graceful failure handling
- Detailed error messages
- Status tracking
- Metadata error recording

### Output Generation
Consistent output patterns:
- Structured markdown generation
- Metadata updates
- File organization
- Reference management

## Best Practices

### Handler Development
1. Inherit from `BaseHandler`
2. Implement required methods
3. Handle all error cases
4. Validate metadata
5. Follow output conventions

### Error Management
1. Use try-except blocks
2. Log detailed errors
3. Update metadata
4. Maintain processing state
5. Provide fallback behavior
