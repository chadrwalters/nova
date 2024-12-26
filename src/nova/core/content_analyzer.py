"""Content analyzer for detecting and categorizing markdown content."""

import re
from typing import Dict, Any, List, Tuple, Optional
from enum import Enum

from .logging import get_logger

logger = get_logger(__name__)

class ContentType(Enum):
    """Types of content that can be detected."""
    SUMMARY = "summary"
    TECHNICAL = "technical"
    REFERENCE = "reference"
    ATTACHMENT = "attachment"
    RAW_NOTE = "raw_note"

class ContentAnalyzer:
    """Analyzes markdown content to determine its type and characteristics."""
    
    def __init__(self):
        """Initialize the content analyzer."""
        self.logger = logger
        
        # Patterns for content type detection
        self.patterns = {
            # Summary patterns
            'summary_patterns': [
                r'^#\s+.*$',  # Top-level headings
                r'^>\s+.*$',  # Blockquotes
                r'^\*\*Key\s+Points?\*\*:?',  # Key points markers
                r'^\*\*Summary\*\*:?',  # Summary markers
                r'^\*\*TL;DR\*\*:?',  # TL;DR markers
                r'^Abstract:?',  # Abstract markers
                r'^Overview:?',  # Overview markers
                r'^Introduction:?',  # Introduction markers
                r'^\*\*Highlights?\*\*:?',  # Highlights markers
                r'^\*\*Main Points?\*\*:?',  # Main points markers
            ],
            
            # Technical patterns
            'technical_patterns': [
                r'^```[\w\-+]*$',  # Code block markers
                r'^\s{4}.*$',  # Indented code
                r'^`.*`$',  # Inline code
                r'^\|\s*[\w\-]+\s*\|',  # Table rows
                r'^[-\d\s.]+\s*[kKmMgGtT][bB]\s*$',  # Size measurements
                r'^https?://',  # URLs
                r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',  # IP addresses
                r'^(?:GET|POST|PUT|DELETE|PATCH)\s+/\w+',  # API endpoints
                r'^(?:SELECT|INSERT|UPDATE|DELETE)\s+',  # SQL queries
                r'^(?:public|private|protected)\s+\w+\s+\w+\(',  # Method signatures
                r'^\s*@\w+(?:\(.*\))?$',  # Annotations/decorators
                r'^\s*<[\w\-]+.*>',  # XML/HTML tags
                r'^\s*\$\s*[\w\-]+\s*=',  # Shell variables
                r'^\s*\[\s*[\w\-]+\s*\]',  # INI section headers
            ],
            
            # Reference patterns
            'reference_patterns': [
                r'^\[.*\]:\s*.*$',  # Reference-style links
                r'^See also:',  # See also sections
                r'^Related:',  # Related sections
                r'^References?:',  # Reference sections
                r'^\d+\.\s+.*$',  # Numbered lists
                r'^Bibliography:',  # Bibliography sections
                r'^Sources?:',  # Sources sections
                r'^Further Reading:',  # Further reading sections
                r'^Citations?:',  # Citations sections
                r'^Links?:',  # Links sections
                r'^\[\^.*\]:',  # Footnote definitions
            ],
            
            # Attachment patterns
            'attachment_patterns': [
                r'!\[.*\]\(.*\)',  # Image references
                r'\[.*\]\(.*(?:\.pdf|\.doc|\.docx|\.xls|\.xlsx|\.zip|\.tar|\.gz|\.7z)\)',  # Document links
                r'--==ATTACHMENT_BLOCK:.*==--',  # Attachment blocks
                r'<iframe.*</iframe>',  # Embedded content
                r'<video.*</video>',  # Video elements
                r'<audio.*</audio>',  # Audio elements
                r'<embed.*>',  # Embedded elements
                r'<object.*</object>',  # Object elements
                r'data:(?:image|video|audio).*',  # Data URLs for media
            ]
        }
        
        # Weights for different indicators
        self.weights = {
            'code_block': 2.0,  # Code blocks are strong technical indicators
            'image': 2.0,  # Images are strong attachment indicators
            'heading': 1.5,  # Headings suggest summary content
            'blockquote': 1.5,  # Blockquotes often indicate important content
            'key_marker': 3.0,  # Key points, summary markers are very strong indicators
            'link': 1.0,  # Links are weak indicators
            'pattern_match': 1.0,  # Base weight for pattern matches
        }
    
    def analyze_content(self, content: str) -> Dict[str, Any]:
        """Analyze content to determine its type and characteristics."""
        if not content:
            return {
                'content_type': ContentType.RAW_NOTE,
                'confidence': 1.0,
                'characteristics': {
                    'has_code': False,
                    'has_images': False,
                    'has_links': False,
                    'structure_level': 0,
                    'technical_density': 0.0,
                    'summary_density': 0.0,
                    'reference_density': 0.0,
                    'attachment_density': 0.0
                }
            }
        
        # Split into lines for analysis
        lines = content.splitlines()
        
        # Initialize characteristics
        characteristics = {
            'has_code': False,
            'has_images': False,
            'has_links': False,
            'structure_level': 0,
            'technical_density': 0.0,
            'summary_density': 0.0,
            'reference_density': 0.0,
            'attachment_density': 0.0
        }
        
        # Track pattern matches
        pattern_matches = {
            'summary': 0,
            'technical': 0,
            'reference': 0,
            'attachment': 0
        }
        
        # Track weighted matches
        weighted_matches = {
            'summary': 0,
            'technical': 0,
            'reference': 0,
            'attachment': 0
        }
        
        # Track code block state
        in_code_block = False
        
        # Analyze each line
        for line in lines:
            # Check for code block boundaries
            if re.match(r'^```', line):
                in_code_block = not in_code_block
                if in_code_block:
                    characteristics['has_code'] = True
                    pattern_matches['technical'] += 1
                    weighted_matches['technical'] += self.weights['code_block']
                continue
            
            # If in code block, count as technical
            if in_code_block:
                pattern_matches['technical'] += 1
                weighted_matches['technical'] += self.weights['pattern_match']
                continue
            
            # Check for images
            if '![' in line and '](' in line:
                characteristics['has_images'] = True
                pattern_matches['attachment'] += 1
                weighted_matches['attachment'] += self.weights['image']
            
            # Check for links
            if '[' in line and '](' in line:
                characteristics['has_links'] = True
                if any(ext in line.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip']):
                    pattern_matches['attachment'] += 1
                    weighted_matches['attachment'] += self.weights['link'] * 1.5
                else:
                    pattern_matches['reference'] += 1
                    weighted_matches['reference'] += self.weights['link']
            
            # Check structure level
            if re.match(r'^#{1,6}\s', line):
                characteristics['structure_level'] += 1
                pattern_matches['summary'] += 1
                weighted_matches['summary'] += self.weights['heading']
            
            # Check for blockquotes
            if line.startswith('>'):
                pattern_matches['summary'] += 1
                weighted_matches['summary'] += self.weights['blockquote']
            
            # Check for key markers with more precise matching
            if re.search(r'(?i)^(?:\*\*)?(?:Key Points?|Summary|TL;DR|Abstract|Overview|Highlights?)(?:\*\*)?:?$', line):
                pattern_matches['summary'] += 1
                weighted_matches['summary'] += self.weights['key_marker']
            
            # Check each pattern type
            for pattern_type, patterns in self.patterns.items():
                base_type = pattern_type.replace('_patterns', '')
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        pattern_matches[base_type] += 1
                        weighted_matches[base_type] += self.weights['pattern_match']
        
        # Calculate densities
        total_lines = len(lines) or 1  # Avoid division by zero
        characteristics['technical_density'] = pattern_matches['technical'] / total_lines
        characteristics['summary_density'] = pattern_matches['summary'] / total_lines
        characteristics['reference_density'] = pattern_matches['reference'] / total_lines
        characteristics['attachment_density'] = pattern_matches['attachment'] / total_lines
        
        # Determine content type based on weighted matches and characteristics
        content_type = ContentType.RAW_NOTE
        confidence = 0.5
        max_weighted = max(weighted_matches.values())
        
        if max_weighted > 0:
            # Find type with highest weighted matches
            for content_type_name, matches in weighted_matches.items():
                if matches == max_weighted:
                    content_type = ContentType[content_type_name.upper()]
                    # Calculate confidence based on multiple factors
                    total_weighted = sum(weighted_matches.values())
                    total_unweighted = sum(pattern_matches.values())
                    
                    if total_weighted > 0:
                        # Base confidence calculation
                        weighted_confidence = matches / total_weighted
                        unweighted_confidence = pattern_matches[content_type_name] / total_unweighted if total_unweighted > 0 else 0.5
                        density_confidence = characteristics[f'{content_type_name}_density']
                        
                        # Combine confidences with weights
                        confidence = (
                            weighted_confidence * 0.5 +
                            unweighted_confidence * 0.3 +
                            density_confidence * 0.2
                        )
                        
                        # Apply characteristic-based adjustments
                        if content_type == ContentType.TECHNICAL and characteristics['has_code']:
                            confidence *= 1.2
                        elif content_type == ContentType.ATTACHMENT and characteristics['has_images']:
                            confidence *= 1.2
                        elif content_type == ContentType.SUMMARY and characteristics['structure_level'] > 0:
                            confidence *= 1.2
                        elif content_type == ContentType.REFERENCE and characteristics['has_links']:
                            confidence *= 1.2
                        
                        # Adjust for mixed content
                        if sum(1 for m in weighted_matches.values() if m > 0) > 1:
                            # If multiple types have significant matches, reduce confidence
                            confidence *= 0.8
                    break
        
        return {
            'content_type': content_type,
            'confidence': min(confidence, 1.0),
            'characteristics': characteristics
        }
    
    def suggest_section(self, content: str) -> Tuple[str, float]:
        """Suggest which section content belongs in.
        
        Args:
            content: Content to analyze
            
        Returns:
            Tuple of (section_name, confidence)
        """
        analysis = self.analyze_content(content)
        
        # Map content types to sections
        type_to_section = {
            ContentType.SUMMARY: 'summary',
            ContentType.TECHNICAL: 'raw_notes',
            ContentType.REFERENCE: 'raw_notes',
            ContentType.ATTACHMENT: 'attachments',
            ContentType.RAW_NOTE: 'raw_notes'
        }
        
        return type_to_section[analysis['content_type']], analysis['confidence'] 