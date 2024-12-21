def process_markdown(self, content: str, source_path: Path) -> str:
    """Process markdown content.
    
    Args:
        content: Markdown content to process
        source_path: Path to source file
        
    Returns:
        Processed markdown content
    """
    try:
        self.logger.info(f"Processing markdown file: {source_path}")
        
        # Initialize stats for this file
        file_stats = {
            'images': {
                'total': 0,
                'processed': 0,
                'with_description': 0,
                'failed': 0,
                'heic_converted': 0,
                'total_original_size': 0,
                'total_processed_size': 0
            }
        }
        
        # Check if we have image processor
        if not self.image_processor:
            self.logger.warning("No image processor available - skipping image processing")
            return content
        
        # Process images in the content
        self.logger.info("Processing images in markdown content")
        
        # Regular expression to find image references
        image_pattern = r'!\[(.*?)\]\(([^)]+)\)(?:\s*<!--\s*(\{.*?\})\s*-->)?'
        
        def process_image_match(match) -> str:
            """Process a single image match and return updated markdown."""
            file_stats['images']['total'] += 1
            
            alt_text, image_path, metadata_json = match.groups()
            console.print(f"[info]Processing image:[/] [path]{image_path}[/]")
            
            metadata = json.loads(metadata_json) if metadata_json else {}
            
            # Resolve image path relative to markdown file
            full_image_path = source_path.parent / image_path
            if not full_image_path.exists():
                error = f"Image not found: {full_image_path}"
                console.print(f"[warning]{error}[/]")
                file_stats['images']['failed'] += 1
                return match.group(0)
            
            try:
                # Track original size
                file_stats['images']['total_original_size'] += full_image_path.stat().st_size
                
                # Process image
                metadata = self.image_processor.process_image(
                    input_path=full_image_path,
                    output_dir=self.config.image.processed_dir
                )
                
                if metadata:
                    file_stats['images']['processed'] += 1
                    file_stats['images']['total_processed_size'] += metadata.size
                    
                    if metadata.description:
                        file_stats['images']['with_description'] += 1
                        # Generate markdown with description
                        processed_path = Path(metadata.processed_path).relative_to(self.config.output_dir)
                        return f"![{metadata.description}]({processed_path})"
                    else:
                        # Keep original alt text if no description
                        processed_path = Path(metadata.processed_path).relative_to(self.config.output_dir)
                        return f"![{alt_text}]({processed_path})"
                else:
                    file_stats['images']['failed'] += 1
                    return match.group(0)
                
            except Exception as e:
                error = f"Failed to process {full_image_path}: {str(e)}"
                console.print(f"[warning]{error}[/]")
                file_stats['images']['failed'] += 1
                return match.group(0)
        
        # Process all images
        content = re.sub(image_pattern, process_image_match, content)
        
        return content, file_stats
        
    except Exception as e:
        self.logger.error(f"Failed to process {source_path}: {e}")
        raise MarkdownProcessingError(f"Failed to process {source_path}: {e}") from e