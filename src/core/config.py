from typing import List, Optional, Dict, Any, ClassVar
from pathlib import Path
from pydantic import BaseModel, Field, validator
from enum import Enum
import yaml
import os
import psutil
import re
from .base_config import LoggingConfig, ErrorSeverity

# Get a basic logger for config initialization
import structlog
logger = structlog.get_logger(__name__)

class ProcessingPhase(str, Enum):
    """Processing pipeline phases."""
    MARKDOWN_PARSE = "markdown_parse"
    MARKDOWN_CONSOLIDATE = "markdown_consolidate"
    PDF_GENERATE = "pdf_generate"

class MarkdownConfig(BaseModel):
    """Configuration for markdown processing."""
    
    METADATA_REQUIREMENTS: ClassVar[Dict] = {
        "date": {
            "required": True,
            "format": "YYYY-MM-DD",
            "source": ["filename", "frontmatter"]
        },
        "title": {
            "required": True,
            "source": ["h1_header", "filename", "frontmatter"]
        }
    }
    
    typographer: bool = True
    linkify: bool = True
    breaks: bool = True
    plugins: List[str] = Field(
        default=["table", "strikethrough", "taskList", "linkify", "image", "footnote"]
    )

    class Config:
        validate_assignment = True

class ProcessingConfig(BaseModel):
    error_tolerance: str = "lenient"
    max_retries: int = 3
    delay_between_retries: int = 1
    max_file_size: int = 10
    max_total_size: int = 50
    concurrent_processes: int = 4
    input_dir: Path = Field(default_factory=lambda: Path(os.getenv("NOVA_INPUT_DIR", "")))
    processing_dir: Path = Field(default_factory=lambda: Path(os.getenv("NOVA_PROCESSING_DIR", "")))
    phase_markdown_parse: Path = Field(default_factory=lambda: Path(os.getenv("NOVA_PHASE_MARKDOWN_PARSE", "")))
    phase_markdown_consolidate: Path = Field(default_factory=lambda: Path(os.getenv("NOVA_PHASE_MARKDOWN_CONSOLIDATE", "")))
    phase_pdf_generate: Path = Field(default_factory=lambda: Path(os.getenv("NOVA_PHASE_PDF_GENERATE", "")))
    temp_dir: Path = Field(default_factory=lambda: Path(os.getenv("NOVA_TEMP_DIR", "")))

    class Config:
        arbitrary_types_allowed = True

    def model_post_init(self, __context):
        """Convert path strings to Path objects after env var expansion."""
        # Expand environment variables before converting to Path
        for field in ['input_dir', 'processing_dir', 'phase_markdown_parse', 
                     'phase_markdown_consolidate', 'phase_pdf_generate', 'temp_dir']:
            value = getattr(self, field)
            if isinstance(value, (str, Path)):
                # Convert to string, expand vars, then convert to Path
                expanded = os.path.expandvars(str(value))
                setattr(self, field, Path(expanded))

class PDFPageConfig(BaseModel):
    """PDF page configuration."""
    format: str
    orientation: str

class PDFMarginsConfig(BaseModel):
    """PDF margins configuration."""
    top: int
    right: int
    bottom: int
    left: int

class PDFHeadersConfig(BaseModel):
    """PDF headers configuration."""
    h1_size: int
    h2_size: int
    h3_size: int
    h4_size: int
    font_family: str

class PDFCodeConfig(BaseModel):
    """PDF code block configuration."""
    font_family: str
    font_size: int
    background: str

class PDFHRConfig(BaseModel):
    """PDF horizontal rule configuration."""
    width: int = Field(
        default=1,
        description="Line width in points",
        ge=1,
        le=5
    )
    color: str = Field(
        default="#000000",
        description="Line color in hex format"
    )

    @validator('width')
    def validate_width(cls, v):
        if isinstance(v, (int, float)):
            value = int(v)
            if value < 1:
                return 1
            if value > 5:
                return 5
            return value
        if isinstance(v, str):
            try:
                # Remove any units and convert
                clean_value = v.lower().strip()
                # Handle relative units by converting to base value
                for unit in ['r', 'pt', 'px', 'em', 'rem', '%']:
                    if clean_value.endswith(unit):
                        clean_value = clean_value[:-len(unit)].strip()
                        break
                if not clean_value:
                    return 1  # Default width
                value = int(float(clean_value))
                if value < 1:
                    return 1
                if value > 5:
                    return 5
                return value
            except (ValueError, TypeError):
                return 1  # Default to 1 on conversion error
        return 1  # Default for any other type

    @validator('color')
    def validate_color(cls, v):
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError(f"Invalid color format: {v}. Must be hex color (e.g., #000000)")
        return v

class PDFStyleConfig(BaseModel):
    """PDF styling configuration."""
    font_family: str = Field(
        default="Noto Sans, STHeiti Light, Arial Unicode MS",
        description="Font stack with Unicode support"
    )
    fallback_fonts: list[str] = Field(
        default=["STHeiti Light", "Arial Unicode MS"],
        description="Fallback fonts for Unicode characters"
    )
    font_size: int = Field(
        default=11,
        description="Base font size in points",
        ge=6,
        le=72
    )
    line_height: float = Field(
        default=1.5,
        description="Line height multiplier",
        ge=1.0,
        le=3.0
    )
    margins: PDFMarginsConfig
    page: PDFPageConfig
    headers: PDFHeadersConfig
    code: PDFCodeConfig
    hr: PDFHRConfig

    @validator('font_size')
    def validate_font_size(cls, v):
        if isinstance(v, str):
            # Strip 'pt' or 'px' if present
            v = v.lower().replace('pt', '').replace('px', '').strip()
            try:
                return int(v)
            except ValueError:
                raise ValueError(f"Invalid font size: {v}")
        return v

class OutputConfig(BaseModel):
    """Output configuration."""
    format: str = "pdf"
    style: PDFStyleConfig = Field(default_factory=lambda: PDFStyleConfig(
        font_family="Helvetica",
        fallback_fonts=["Courier", "Times"],
        font_size=11,
        line_height=1.5,
        margins=PDFMarginsConfig(
            top=25,
            right=20,
            bottom=25,
            left=20
        ),
        page=PDFPageConfig(
            format="A4",
            orientation="P"
        ),
        headers=PDFHeadersConfig(
            h1_size=24,
            h2_size=20,
            h3_size=16,
            h4_size=14,
            font_family="Helvetica"
        ),
        code=PDFCodeConfig(
            font_family="Courier",
            font_size=9,
            background="#f6f8fa"
        ),
        hr=PDFHRConfig(
            width=1,
            color="#000000"
        )
    ))
    page_size: str = "A4"
    margin: str = "2.5cm 1.5cm"

    class Config:
        arbitrary_types_allowed = True

class SecurityConfig(BaseModel):
    allow_external_refs: bool = False
    sanitize_html: bool = True
    allowed_domains: List[str] = Field(default_factory=list)
    max_image_size: int = 5242880

class ResourceManagementConfig(BaseModel):
    """Resource management configuration."""
    max_memory_mb: int = 256
    cleanup_interval: int = 300
    batch_size: int = 1

class OfficeFormatConfig(BaseModel):
    """Office format configuration."""
    extensions: List[str]
    metadata: List[str]
    elements: List[str]

class OfficeProcessingConfig(BaseModel):
    """Office processing configuration."""
    tool: str = "markitdown"
    powerpoint: Dict[str, Any] = Field(default_factory=lambda: {
        "slide_separator": "---",
        "include_notes": True
    })
    excel: Dict[str, Any] = Field(default_factory=lambda: {
        "sheet_separator": "## Sheet:",
        "max_rows": 1000
    })
    pdf: Dict[str, Any] = Field(default_factory=lambda: {
        "extract_images": True,
        "ocr_enabled": True
    })

class DocumentHandlingConfig(BaseModel):
    """Document handling configuration."""
    allowed_types: List[str] = Field(default_factory=lambda: [
        ".md", ".markdown", ".docx", ".doc", ".pdf", ".pptx", ".ppt"
    ])
    max_size: int = 10485760  # 10MB
    embed_options: List[str] = Field(default_factory=lambda: [
        "images", "tables", "code"
    ])
    embedded_document_template: str = """
---
## Embedded Document: {title}

<!-- Document Info:
Type: {doc_type}
Source: {source}
Embedded In: {parent}
Processed: {timestamp}
Processor: {processor}
Original Metadata:
{original_metadata}
-->

{content}

<!-- End of embedded document: {source} -->
---
"""
    office_formats: Dict[str, OfficeFormatConfig] = Field(default_factory=lambda: {
        "word": OfficeFormatConfig(
            extensions=[".docx", ".doc"],
            metadata=["author", "title", "created", "modified"],
            elements=["tables", "images", "headers", "lists"]
        ),
        "powerpoint": OfficeFormatConfig(
            extensions=[".pptx", ".ppt"],
            metadata=["author", "title", "created", "slides", "notes"],
            elements=["slides", "notes", "images", "diagrams"]
        ),
        "pdf": OfficeFormatConfig(
            extensions=[".pdf"],
            metadata=["title", "author", "keywords"],
            elements=["text", "images", "forms", "tables"],
            preview_support=True
        )
    })
    office_processing: OfficeProcessingConfig = Field(default_factory=OfficeProcessingConfig)
    word_processing: Dict[str, Any] = Field(default_factory=lambda: {
        "image_output_dir": "",
        "preserve_images": True,
        "ocr_enabled": True,
        "max_image_size": 5242880
    })

class MetadataConfig(BaseModel):
    """Metadata configuration."""
    required_fields: List[str] = Field(default_factory=lambda: [
        'filename',
        'date',
        'title',
        'toc',
        'processed_timestamp'
    ])
    date_format: str = '%Y-%m-%d'
    filename_pattern: str = r'^\d{8}\s*-\s*.+\.md$'

class NovaConfig(BaseModel):
    """Main configuration class."""
    markdown: MarkdownConfig = Field(default_factory=MarkdownConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    document_handling: DocumentHandlingConfig = Field(default_factory=DocumentHandlingConfig)
    resource_management: Optional[ResourceManagementConfig] = Field(
        default_factory=lambda: ResourceManagementConfig(
            max_memory_mb=256,
            cleanup_interval=300,
            batch_size=1
        )
    )
    _memory_warning_logged: bool = False
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    
    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True
    }
    
    def validate_system_resources(self):
        """Validate system resources with fallback options"""
        required_memory = self.resource_management.max_memory_mb if self.resource_management else 256
        available_memory = psutil.virtual_memory().available // (1024 * 1024)
        
        if available_memory < (required_memory / 2) and not self._memory_warning_logged:
            logger.warning(
                "Low memory available",
                required=f"{required_memory}MB",
                available=f"{available_memory}MB"
            )
            self.processing.concurrent_processes = 1
            self._memory_warning_logged = True
            
        return True

    def __init__(self, config_path: Optional[Path] = None, **data):
        if config_path:
            # Convert Typer Option to Path if needed
            if hasattr(config_path, 'default'):
                config_path = None
            elif config_path:
                config_path = Path(str(config_path))
            
            # Load config file if it exists
            if config_path and config_path.exists():
                with open(config_path) as f:
                    config_data = yaml.safe_load(f)
                data.update(config_data)
        super().__init__(**data)

def load_config(config_path: Path) -> NovaConfig:
    """Load configuration from YAML file."""
    try:
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
            
        # Expand environment variables in paths
        for key in ['input_dir', 'processing_dir', 'phase_markdown_parse', 
                   'phase_markdown_consolidate', 'phase_pdf_generate', 'temp_dir']:
            if key in config_data['processing']:
                config_data['processing'][key] = os.path.expandvars(
                    config_data['processing'][key]
                )
            
        logger.debug("config_loaded", config=config_data)
        
        # Validate config
        config = NovaConfig(**config_data)
        logger.debug("config_validated", config=config.model_dump())
        
        return config
        
    except Exception as e:
        logger.error("config_load_failed", error=str(e))
        raise ConfigError(f"Failed to load config: {str(e)}")