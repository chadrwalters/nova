# Troubleshooting Guide

This guide covers common issues that may arise when using the Nova document processing pipeline, along with their solutions.

## Common Issues

### Attachment Handling

#### Missing Attachments
**Problem**: Attachments are not appearing in the output files.

**Possible Causes**:
1. Incorrect attachment block markers
2. Unclosed attachment blocks
3. Nested attachment blocks

**Solutions**:
1. Ensure attachment blocks use the correct markers:
   ```
   --==ATTACHMENT_BLOCK: filename==--
   [Content]
   --==ATTACHMENT_BLOCK_END==--
   ```
2. Check that every block has both start and end markers
3. Avoid nesting attachment blocks inside each other

#### Duplicate Attachments
**Problem**: Error about duplicate attachment names.

**Solution**:
- Use unique filenames for each attachment
- If multiple versions are needed, add a suffix (e.g., `file-v1.txt`, `file-v2.txt`)

### Cross-References

#### Broken References
**Problem**: Warnings about missing reference targets.

**Possible Causes**:
1. Referenced content doesn't exist
2. Case mismatch in reference names
3. Special characters in references

**Solutions**:
1. Ensure all referenced content exists
2. Match case exactly (references are case-sensitive)
3. Use simple reference names without special characters

#### Circular References
**Problem**: Warning about circular reference chains.

**Solution**:
- Review reference chain and break the cycle
- Use unidirectional references where possible

### Content Distribution

#### Unbalanced Distribution
**Problem**: Content not split as expected between files.

**Possible Causes**:
1. Missing section headers
2. Incorrect content structure
3. Large attachments

**Solutions**:
1. Add clear section headers
2. Structure content with proper headings
3. Consider splitting large attachments

### Performance Issues

#### Slow Processing
**Problem**: Processing takes longer than expected.

**Possible Causes**:
1. Very large files
2. Many small attachments
3. Complex reference chains

**Solutions**:
1. Split large files into smaller documents
2. Combine small attachments where appropriate
3. Simplify reference structure

#### High Memory Usage
**Problem**: Process uses excessive memory.

**Solutions**:
1. Process files in smaller batches
2. Reduce attachment sizes
3. Use concurrent processing for multiple files

### File Operations

#### Permission Errors
**Problem**: Cannot write output files.

**Solutions**:
1. Check file permissions
2. Ensure output directory exists and is writable
3. Close any open file handles

#### Invalid Paths
**Problem**: Error about invalid file paths.

**Solutions**:
1. Use correct path separators for your OS
2. Ensure paths are relative to workspace root
3. Avoid special characters in filenames

## Best Practices

### Content Organization
1. Use clear, hierarchical headings
2. Keep attachments at a reasonable size
3. Use descriptive filenames
4. Place related content in the same section

### Reference Management
1. Use meaningful reference names
2. Keep reference chains short
3. Document reference relationships
4. Validate references before processing

### Performance Optimization
1. Process files in parallel when possible
2. Monitor memory usage
3. Use appropriate batch sizes
4. Clean up temporary files

## Logging and Debugging

### Debug Mode
Enable debug logging for more detailed information:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Log Analysis
Common log messages and their meanings:
- "Unclosed attachment block": Check for missing end markers
- "Missing reference target": Reference points to non-existent content
- "Invalid metadata": Check YAML syntax in metadata block
- "Permission denied": Check file system permissions

### Performance Metrics
Monitor these metrics for optimization:
- Processing time per file
- Memory usage trends
- Content distribution ratios
- Reference chain depths

## Getting Help

If you encounter issues not covered in this guide:

1. Check the latest documentation
2. Review the test cases for examples
3. Enable debug logging for more information
4. File an issue with:
   - Full error message
   - Sample content that reproduces the issue
   - System information
   - Log output 