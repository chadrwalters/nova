def _get_env_path(key: str, default: str = '') -> Path:
    """Get environment variable as Path with proper expansion."""
    value = os.environ.get(key, default)
    expanded = os.path.expandvars(value)
    return Path(expanded)

def _process_attachment(self, attachment_path: Path) -> str:
    """Process an attachment file and return markdown content."""
    if not attachment_path.exists():
        logger.warning(f"Attachment not found: {attachment_path}")
        return f"<!-- Attachment not found: {attachment_path} -->"

    # Skip JSON files
    if attachment_path.suffix.lower() == '.json':
        return ''

    # Get the relative path from the input directory
    input_dir = _get_env_path('NOVA_INPUT_DIR')
    try:
        rel_path = attachment_path.relative_to(input_dir)
    except ValueError:
        logger.warning(f"Attachment not in input directory: {attachment_path}")
        return f"<!-- Attachment not in input directory: {attachment_path} -->"

    # Handle different file types
    suffix = attachment_path.suffix.lower()
    if suffix in ['.jpg', '.jpeg', '.png', '.gif', '.heic']:
        # For HEIC files, use the converted JPG path
        if suffix == '.heic':
            processed_path = _get_env_path('NOVA_PROCESSED_IMAGES_DIR') / rel_path.with_suffix('.jpg')
        else:
            processed_path = _get_env_path('NOVA_PROCESSED_IMAGES_DIR') / rel_path

        # Add image reference
        return f"\n![{attachment_path.stem}]({processed_path})\n"

    elif suffix in ['.pdf', '.docx', '.xlsx', '.txt', '.csv']:
        # For documents, add a link
        return f"\n[{attachment_path.name}]({attachment_path})\n"

    else:
        logger.warning(f"Unsupported attachment type: {attachment_path}")
        return f"<!-- Unsupported attachment type: {attachment_path} -->" 