# Nova Core Dependencies

## ⚠️ DEPENDENCY CHANGE POLICY ⚠️

All dependencies listed in this document are CORE to the system's functionality and have been carefully selected. 
**DO NOT MODIFY OR UPGRADE these dependencies without explicit approval from the project owner.**

## System Dependencies (Homebrew)

### Core Brew Packages
```bash
# Image Processing
imagemagick@6      # Specific version for image conversion compatibility
ghostscript        # PDF processing and image handling
tesseract         # OCR capabilities

# Development Tools
python@3.9        # Core Python version - DO NOT UPGRADE without approval
poetry            # Package management
git              # Version control

# System Utilities
coreutils         # Required for file operations
findutils         # Enhanced file search capabilities
gnu-sed          # Required for text processing
```

### Installation Command
```bash
brew install imagemagick@6 ghostscript tesseract python@3.9 poetry git coreutils findutils gnu-sed
```

## Python Dependencies

### Core Processing Libraries
```toml
[tool.poetry.dependencies]
python = "^3.9"
markitdown = "0.0.1a3"          # Custom markdown processing - DO NOT CHANGE
pillow = "9.5.0"                # Image processing - Version locked for ImageMagick compatibility
python-magic = "0.4.27"         # File type detection
pyyaml = "6.0.1"                # Configuration handling
click = "8.1.7"                 # CLI framework
```

### AI and Machine Learning
```toml
openai = "1.3.5"                # OpenAI API integration - Version locked for stability
tiktoken = "0.5.1"              # Token counting for OpenAI
```

### Development Dependencies
```toml
[tool.poetry.dev-dependencies]
pytest = "^7.4.3"
mypy = "^1.7.1"
black = "^23.11.0"
isort = "^5.12.0"
```

## Dependency Change Protocol

1. **Change Request**
   - Document the need for change
   - Provide compatibility analysis
   - Test impact on existing functionality
   - Get explicit approval from project owner

2. **Testing Requirements**
   - Full test suite must pass
   - Performance benchmarks must be maintained
   - No regression in image processing quality
   - All phases must complete successfully

3. **Version Control**
   - Lock all dependency versions
   - Document any version changes
   - Keep change history
   - Maintain compatibility matrix

4. **Compatibility Requirements**
   - ImageMagick version must remain at 6.x
   - Python version must remain at 3.9.x
   - Core libraries must maintain API compatibility
   - System utilities must preserve current behavior

## Critical Dependencies (DO NOT MODIFY)

These dependencies have been extensively tested and are critical for system stability:

1. **markitdown==0.0.1a3**
   - Custom markdown processing
   - Core to document handling
   - Extensively tested version
   - API stability required

2. **imagemagick@6**
   - Image processing backbone
   - Version 6 required for compatibility
   - Specific conversion features
   - Performance optimized

3. **python@3.9**
   - System baseline version
   - Compatibility verified
   - Performance optimized
   - Library compatibility assured

4. **openai==1.3.5**
   - API stability required
   - Rate limiting tested
   - Error handling verified
   - Performance benchmarked

## Dependency Update Process

1. **Request Phase**
   - Submit detailed change request
   - Include compatibility analysis
   - Provide performance impact
   - Document security implications

2. **Review Phase**
   - Technical review required
   - Performance testing required
   - Security audit required
   - Owner approval required

3. **Testing Phase**
   - Full regression testing
   - Performance benchmarking
   - Integration testing
   - Error handling verification

4. **Implementation Phase**
   - Staged rollout
   - Rollback plan required
   - Documentation updates
   - Monitoring plan 