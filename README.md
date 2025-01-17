# Nova: Building a Personal "Second Brain"

Welcome to the Nova repository! This project has two main goals:

## 1. Streamlined Note Management & RAG Integration
Nova began as a way to convert my meeting notes and attachments into PDFs so I could interact with them in Claude or ChatGPT. Over time, I discovered the limitations of uploading large PDFs and grew curious about more advanced approaches. This led me to explore RAG (Retrieval-Augmented Generation) pipelines, vector stores, and MCP integrations—ultimately transforming Nova into a "second brain" architecture that can easily recall and reference my notes.

## 2. Learning & Growing as a Developer (Again)
Although I was a developer long ago, I now serve as an engineering executive. Building Nova has been a hands-on way to re-learn the fundamentals of coding and explore the power of AI-assisted development. Without these new tools, I simply could not have built something of this scope in such a short time—version 3 came together over about 1.5 weeks of nights and weekend sessions. I often chose the "longer way" on purpose to refine my process and learn how best to manage AI coding assistants. My hope is to share these insights with the community and apply them to professional environments.

# Current Status (V3)

This is what I consider a non-optimized V3: a new architecture that sets the foundation for Nova as a personal second brain. Much of my next work will be focused on improving:

- Speed & Performance: Making the RAG pipeline faster and more efficient
- Effectiveness of Retrieval: Optimizing how Nova integrates multiple data sources
- Processing & Scaling: Ensuring Nova can handle expanding content while still performing reliably

# Future Plans

From here on, I plan to keep pushing Nova's capabilities, focusing on features like:

- Efficient data integration: Automating how different data sources feed into Nova.
- Better contextual advice: Teaching Nova to reason more deeply about various topics, referencing new external documents.
- Scaling for my workflow: Ensuring Nova scales smoothly from a single user—me—to potential broader use cases.

By continuing to build and refactor, I aim to make Nova more useful over time and share my learnings with the community. Thank you for stopping by, and I look forward to collaborating on this journey!

### Core Features
- Document Processing: Multi-format support with rich metadata extraction
- Vector Store: Semantic chunking and embeddings for efficient retrieval
- Search: Semantic similarity search with metadata filtering
- Claude Desktop Integration: READ-ONLY tools for search and monitoring

### Document Processing Features
- Format Support:
  - Text Formats:
    - Markdown (.md) - Native format with full metadata preservation
    - Plain text (.txt) - Direct conversion with basic metadata
    - HTML (.html, .htm) - Converted via html2text with link preservation
    - reStructuredText (.rst) - Converted via docutils with structure preservation
    - AsciiDoc (.adoc, .asciidoc) - Converted via asciidoc with formatting
    - Org Mode (.org) - Converted via pandoc with hierarchy preservation
    - Wiki (.wiki) - Converted via pandoc with basic formatting
    - LaTeX (.tex) - Converted via pandoc with math support
  - Office Formats:
    - Word (.docx) - Converted via pandoc with style preservation
    - Excel (.xlsx) - Converted via pandoc with table structure
    - PowerPoint (.pptx) - Converted via pandoc with slide structure
  - Other Formats:
    - PDF (.pdf) - Converted via pandoc with layout preservation

- Bear Note Processing:
  - Title Date Extraction:
    - Supports formats: YYYYMMDD, YYYY-MM-DD
    - Extracts date components (year, month, day)
    - Adds weekday information
    - Preserves original title
  - Tag Handling:
    - Extracts #tags and #nested/tags
    - Preserves tag hierarchy
    - Maintains tag relationships
  - Metadata Extraction:
    - Creation date from title
    - Modified date from file
    - Tag collection and hierarchy
    - Note title and subtitle
    - Attachment references

- Processing Features:
  - Automatic format detection via MIME types
  - Fallback to extension-based detection
  - Rich metadata extraction
  - Structure preservation
  - Error recovery with detailed logging
  - Progress tracking and reporting

### Monitoring Features
- Session Monitoring:
  - Real-time performance tracking
  - Health checks during sessions
  - Error tracking and reporting
  - Resource usage monitoring

- Persistent Monitoring:
  - Cross-session metrics storage
  - Performance trend analysis
  - Error pattern detection
  - System health tracking

- Log Management:
  - Automated log rotation
  - Log archival and cleanup
  - Structured log parsing
  - Log analysis tools

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/nova.git
cd nova

# Create and activate virtual environment using uv
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

## Usage

### CLI Commands

```bash
# Process notes
nova process-notes --input-dir /path/to/notes --output-dir .nova/processing

# Process vectors
nova process-bear-vectors --input-dir .nova/processing --output-dir .nova/vectors

# Search notes
nova search "your query here" --limit 5

# Monitor system
nova monitor health  # Check system health
nova monitor stats  # View statistics
nova monitor logs   # View recent logs
nova monitor errors # View error summary

# Clean up
nova clean-processing --force  # Clean processed notes
nova clean-vectors --force     # Clean vector store
```

### Claude Desktop Integration

1. Configure Claude Desktop with Nova:
```json
{
  "mcpServers": {
    "nova": {
      "command": "/path/to/nova/scripts/start_nova_mcp.sh",
      "cwd": "/path/to/nova"
    }
  }
}
```

2. Start a conversation in Claude Desktop with:
"I'm using Nova for semantic search and monitoring. Please use port 8765 for all operations."

3. Available tools:
- search_tool: Semantic search with configurable limits and similarity scoring
- monitor_tool: System health checks, statistics, and log analysis

## Directory Structure

```
.nova/
├── processing/  # Processed documents
├── vectors/     # Vector store data
├── logs/        # System logs
│   └── archive/ # Archived logs
└── metrics/     # Persistent metrics
```

## Configuration

Nova uses a centralized `.nova` directory for all system files:
- Input files: Configurable location (default: iCloud Drive/_NovaInput)
- System files: Always in `.nova` directory
- Logs: Rotated at 10MB, archived after 7 days
- Metrics: SQLite database for persistent monitoring

## Monitoring

### Session Monitoring
- Real-time performance tracking
- Component health checks
- Error detection and reporting
- Resource usage monitoring

### Persistent Monitoring
- Cross-session metrics storage
- Performance trend analysis
- Error pattern detection
- System health tracking

### Log Management
- Automatic log rotation (10MB)
- Log archival (7 days)
- Structured parsing
- Analysis tools

## Development

```bash
# Run tests
uv run pytest -v

# Run type checking
uv run mypy src/nova

# Run linting
uv run ruff src/nova
```

## License
