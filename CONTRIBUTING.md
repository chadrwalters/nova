# Contributing to Nova

## Development Guidelines

### Code Organization
- Use clear module separation
- Follow Python package structure
- Keep processors focused and single-purpose
- Use base classes for common functionality

### Processing Rules

#### Phase 1: Markdown Parse

1. **File Handling**
   - Use pathlib.Path for all file operations
   - Handle UTF-8 encoding properly
   - Validate file permissions
   - Clean up temporary files

2. **State Management**
   - Track file processing state
   - Handle incremental updates
   - Preserve processing history
   - Clean state on force processing

#### Image Processing

1. **Temporary Files**
   - Use stable, predictable filenames for temporary conversions
   - Track temporary files explicitly for cleanup
   - Only clean up files we create temporarily
   - Don't delete original or processed output files

2. **File Organization**
   - Original files go in `${NOVA_ORIGINAL_IMAGES_DIR}`
   - Processed files go in `${NOVA_PROCESSED_IMAGES_DIR}`
   - Metadata goes in `${NOVA_IMAGE_METADATA_DIR}`
   - Cache files go in `${NOVA_IMAGE_CACHE_DIR}`

3. **HEIC Handling**
   - Convert HEIC to JPG before processing
   - Use stable filenames for converted files
   - Clean up intermediate conversion files

#### Office Document Processing

1. **Content Extraction**
   - Try multiple methods to extract content:
     - `text_content` attribute
     - `markdown` attribute
     - `text` attribute
     - Direct dictionary access
   - Log available attributes when extraction fails
   - Include technical details in output for debugging

2. **Output Format**
   - Include YAML frontmatter with metadata
   - Use consistent document structure:
     - Title
     - Content (if available)
     - Technical Details (if extraction fails)
     - Document Information

3. **Error Handling**
   - Log detailed error information
   - Include available attributes in output
   - Provide useful fallback content
   - Track conversion statistics

### Testing

1. **Unit Tests**
   - Test each processor independently
   - Mock external services
   - Test error conditions
   - Verify cleanup operations

2. **Integration Tests**
   - Test full processing pipeline
   - Verify file organization
   - Check metadata generation
   - Validate cleanup

### Logging

1. **Standard Format**
   - Use structured logging
   - Include context information
   - Log appropriate levels
   - Track processing statistics

2. **Error Reporting**
   - Log full stack traces
   - Include relevant file info
   - Track error patterns
   - Report API failures

## Pull Request Process

1. Create feature branch from main
2. Follow code style guidelines
3. Add/update tests
4. Update documentation
5. Submit PR with clear description

## Code Style

- Follow PEP 8
- Use type hints
- Document classes and methods
- Keep functions focused and small