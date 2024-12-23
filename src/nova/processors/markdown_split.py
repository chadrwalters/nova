class ThreeFileSplitProcessor:
    """Processor for splitting markdown into three files."""

    def __init__(self, processor_config: Dict[str, Any], nova_config: Dict[str, Any]):
        """Initialize the processor.
        
        Args:
            processor_config: Processor-specific configuration
            nova_config: Global Nova configuration
        """
        self.logger = logging.getLogger(__name__)
        self.processor_config = processor_config
        self.nova_config = nova_config
        
        # Set up output files
        self.output_files = {
            'summary': 'summary.md',
            'raw_notes': 'raw_notes.md',
            'attachments': 'attachments.md'
        }
        if 'output_files' in processor_config:
            self.output_files.update(processor_config['output_files'])
            
        # Set up section markers
        self.section_markers = {
            'summary': '--==SUMMARY==--',
            'raw_notes': '--==RAW NOTES==--',
            'attachments': '--==ATTACHMENTS==--'
        }
        if 'section_markers' in processor_config:
            self.section_markers.update(processor_config['section_markers'])
            
        # Set up attachment markers
        self.attachment_markers = {
            'start': '--==ATTACHMENT_BLOCK: {filename}==--',
            'end': '--==ATTACHMENT_BLOCK_END==--'
        }
        if 'attachment_markers' in processor_config:
            self.attachment_markers.update(processor_config['attachment_markers'])
            
        # Set up content type rules
        self.content_type_rules = {
            'summary': [
                'Contains high-level overviews',
                'Contains key insights and decisions',
                'Contains structured content'
            ],
            'raw_notes': [
                'Contains detailed notes and logs',
                'Contains chronological entries',
                'Contains unstructured content'
            ],
            'attachments': [
                'Contains file references',
                'Contains embedded content',
                'Contains metadata'
            ]
        }
        if 'content_type_rules' in processor_config:
            self.content_type_rules.update(processor_config['content_type_rules'])
            
        # Set up content preservation options
        self.content_preservation = {
            'validate_input_size': True,
            'validate_output_size': True,
            'track_content_markers': True,
            'verify_section_integrity': True
        }
        if 'content_preservation' in processor_config:
            self.content_preservation.update(processor_config['content_preservation'])
            
        # Other options
        self.cross_linking = processor_config.get('cross_linking', True)
        self.preserve_headers = processor_config.get('preserve_headers', True)
        
        # Initialize state
        self.content_markers = set()
        self.section_sizes = {
            'summary': 0,
            'raw_notes': 0,
            'attachments': 0
        }
        
    def process(self, input_file: Path, output_dir: Path) -> Dict[str, Path]:
        """Process input file and split into three files.
        
        Args:
            input_file: Input markdown file
            output_dir: Output directory
            
        Returns:
            Dict mapping section names to output file paths
        """
        try:
            # Read input file
            content = input_file.read_text(encoding='utf-8')
            
            # Split content into sections
            sections = self._split_content(content)
            
            # Create output files
            output_files = {}
            for section_name, section_content in sections.items():
                output_path = output_dir / self.output_files[section_name]
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(section_content, encoding='utf-8')
                output_files[section_name] = output_path
                
            return output_files
            
        except Exception as e:
            raise ProcessingError(f"Failed to process {input_file}: {str(e)}") from e
            
    def _split_content(self, content: str) -> Dict[str, str]:
        """Split content into sections.
        
        Args:
            content: Content to split
            
        Returns:
            Dict mapping section names to content
        """
        sections = {
            'summary': [],
            'raw_notes': [],
            'attachments': []
        }
        
        # Extract sections using markers
        current_section = None
        lines = content.split('\n')
        
        for line in lines:
            # Check for section markers
            for section_name, marker in self.section_markers.items():
                if marker in line:
                    current_section = section_name
                    break
                    
            # Add line to current section
            if current_section:
                sections[current_section].append(line)
                
        # Join sections
        return {
            name: '\n'.join(lines) if lines else ''
            for name, lines in sections.items()
        } 