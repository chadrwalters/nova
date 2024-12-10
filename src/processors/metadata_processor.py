import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import frontmatter
import nltk
import structlog
import yaml
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import sent_tokenize, word_tokenize

from src.core.types import DocumentMetadata, ExtractedMetadata

# Download required NLTK data
try:
    nltk.data.find("tokenizers/punkt")
    nltk.data.find("corpora/stopwords")
    nltk.data.find("corpora/wordnet")
except LookupError:
    nltk.download("punkt")
    nltk.download("stopwords")
    nltk.download("wordnet")

logger = structlog.get_logger(__name__)


class MetadataProcessor:
    """Processes and extracts metadata from documents."""

    def __init__(self) -> None:
        """Initialize the metadata processor."""
        # Initialize NLP components
        self.stop_words: Set[str] = set(stopwords.words("english"))
        self.lemmatizer: WordNetLemmatizer = WordNetLemmatizer()

        # Add domain-specific stop words
        self.stop_words.update(
            {
                "document",
                "file",
                "section",
                "chapter",
                "page",
                "version",
                "draft",
                "final",
                "update",
                "revision",
                "todo",
                "note",
                "important",
                "warning",
                "info",
                "example",
                "reference",
                "see",
                "cf",
                "e.g",
                "i.e",
            }
        )

        # Common metadata patterns
        self.patterns: Dict[str, List[str]] = {
            "title": [r"^#\s+(.+)$", r"^Title:\s*(.+)$", r"@title\s+(.+)"],
            "date": [
                r"^Date:\s*(.+)$",
                r"@date\s+(.+)",
                r"\d{4}-\d{2}-\d{2}",
                r"\d{2}/\d{2}/\d{4}",
            ],
            "author": [r"^Author:\s*(.+)$", r"@author\s+(.+)", r"By:\s*(.+)"],
            "category": [r"^Category:\s*(.+)$", r"@category\s+(.+)", r"Type:\s*(.+)"],
            "tags": [r"^Tags:\s*(.+)$", r"@tags\s+(.+)", r"#(\w+)"],
            "status": [r"^Status:\s*(.+)$", r"@status\s+(.+)"],
            "priority": [r"^Priority:\s*(\d+)$", r"@priority\s+(\d+)"],
        }

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string into datetime.

        Args:
            date_str: Date string to parse

        Returns:
            Parsed datetime or None
        """
        if not date_str:
            return None

        # Try common date formats
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def _normalize_metadata(self, metadata: DocumentMetadata) -> None:
        """Normalize metadata fields.

        Args:
            metadata: Metadata to normalize
        """
        # Ensure date exists
        if not metadata.date:
            metadata.date = datetime.now()

        # Convert priority to int if present
        if metadata.priority:
            try:
                metadata.priority = int(metadata.priority)
            except (ValueError, TypeError):
                metadata.priority = None

        # Ensure lists are unique
        for field in ["tags", "keywords", "references", "related_docs"]:
            value = getattr(metadata, field)
            if value:
                setattr(metadata, field, sorted(set(value)))

    def _parse_frontmatter(self, content: str) -> tuple[Dict[str, Any], str]:
        """Parse frontmatter from content.

        Args:
            content: Content to parse

        Returns:
            Tuple of (metadata dict, clean content)
        """
        # Try frontmatter first
        doc = frontmatter.loads(content)
        if doc.metadata:
            return doc.metadata, doc.content

        # Try YAML block
        yaml_match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
        if yaml_match:
            try:
                return yaml.safe_load(yaml_match.group(1)), yaml_match.group(2)
            except yaml.YAMLError:
                pass

        # Try JSON block
        json_match = re.match(r"^\{[\s\S]*?\}\n(.*)", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0)), json_match.group(1)
            except json.JSONDecodeError:
                pass

        return {}, content

    def extract_metadata(
        self, content: str, file_path: Optional[Path] = None
    ) -> ExtractedMetadata:
        """Extract metadata from document content.

        Args:
            content: The content to extract metadata from
            file_path: Optional path to the source file

        Returns:
            ExtractedMetadata containing the extracted metadata and content
        """
        try:
            # Parse frontmatter and get clean content
            metadata, clean_content = self._parse_frontmatter(content)

            # Extract additional metadata from content
            extracted = self._extract_content_metadata(clean_content)

            # Create metadata structure
            final_metadata = self._create_empty_metadata()

            # Update with extracted metadata
            for key, value in extracted.items():
                setattr(final_metadata, key, value)

            # Update with explicit metadata
            for key, value in metadata.items():
                if hasattr(final_metadata, key):
                    setattr(final_metadata, key, value)
                else:
                    final_metadata.custom_fields[key] = value

            # Extract date from filename if not present
            if not final_metadata.date and file_path:
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", file_path.stem)
                if date_match:
                    parsed_date = self._parse_date(date_match.group(1))
                    if parsed_date:
                        final_metadata.date = parsed_date

            # Parse date string if needed
            if isinstance(final_metadata.date, str):
                parsed_date = self._parse_date(final_metadata.date)
                final_metadata.date = parsed_date or datetime.now()

            # Normalize metadata fields
            self._normalize_metadata(final_metadata)

            return ExtractedMetadata(
                metadata=final_metadata,
                content=clean_content,
                is_valid=True,
                error=None,
            )

        except Exception as e:
            logger.error(
                "Metadata extraction failed",
                error=str(e),
                file=str(file_path) if file_path else None,
            )
            return ExtractedMetadata(
                metadata=self._create_empty_metadata(),
                content=content,
                is_valid=False,
                error=str(e),
            )

    def _extract_content_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from content using patterns.

        Args:
            content: The content to extract metadata from

        Returns:
            Dictionary of extracted metadata
        """
        metadata: Dict[str, Any] = {}

        # Extract using patterns
        for field, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.MULTILINE)
                values = [m.group(1) for m in matches]
                if values:
                    if field == "tags":
                        metadata[field] = list(
                            {
                                tag.strip("#")
                                for value in values
                                for tag in value.split()
                            }
                        )
                    elif field in ["date", "priority"]:
                        metadata[field] = values[0]  # Use first match
                    else:
                        metadata[field] = values[0].strip()

        # Extract keywords
        metadata["keywords"] = self._extract_keywords(content)

        # Extract summary
        metadata["summary"] = self._generate_summary(content)

        return metadata

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content using NLP.

        Args:
            content: The content to extract keywords from

        Returns:
            List of extracted keywords
        """
        try:
            # Simple word tokenization
            words = re.findall(r"\b\w+\b", content.lower())

            # Remove stop words and lemmatize
            keywords: List[str] = []
            for word in words:
                if word not in self.stop_words and word.isalnum() and len(word) > 2:
                    lemma = self.lemmatizer.lemmatize(word)
                    keywords.append(lemma)

            # Count frequencies
            keyword_freq = Counter(keywords)

            # Get top keywords (adjust threshold as needed)
            top_keywords = [
                word
                for word, count in keyword_freq.most_common(20)
                if count > 1  # Minimum frequency threshold
            ]

            return top_keywords

        except Exception as e:
            logger.error("Keyword extraction failed", error=str(e))
            return []

    def _generate_summary(self, content: str) -> str:
        """Generate a summary from content.

        Args:
            content: The content to generate summary from

        Returns:
            Generated summary
        """
        try:
            # Remove markdown formatting
            clean_content = re.sub(r"#+ ", "", content)
            clean_content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean_content)
            clean_content = re.sub(r"[*_~`]", "", clean_content)

            # Split into sentences
            sentences = sent_tokenize(clean_content)

            # Get first few sentences (adjust as needed)
            summary_sentences = sentences[:3]

            return " ".join(summary_sentences).strip()

        except Exception as e:
            logger.error("Summary generation failed", error=str(e))
            return ""

    def _create_empty_metadata(self) -> DocumentMetadata:
        """Create an empty metadata structure.

        Returns:
            Empty DocumentMetadata instance
        """
        return DocumentMetadata(
            title="",
            date=datetime.now(),  # Default to current time
            author="",
            category="",
            tags=[],
            status="",
            priority=None,
            keywords=[],
            summary="",
            references=[],
            related_docs=[],
            custom_fields={},
        )

    def extract_references(self, content: str) -> List[str]:
        """Extract document references from content."""
        references = set()

        # Find markdown links
        link_matches = re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", content)
        for match in link_matches:
            text, url = match.groups()
            if not url.startswith(("http://", "https://", "mailto:")):
                references.add(url)

        # Find citations
        citation_matches = re.finditer(r"@cite\{([^}]+)\}", content)
        references.update(m.group(1) for m in citation_matches)

        # Find footnote references
        footnote_matches = re.finditer(r"\[\^([^\]]+)\]", content)
        references.update(m.group(1) for m in footnote_matches)

        return sorted(references)

    def find_related_documents(
        self, content: str, metadata: DocumentMetadata, all_docs: List[DocumentMetadata]
    ) -> List[str]:
        """Find related documents based on content similarity."""
        try:
            # Extract keywords from current document
            doc_keywords = set(metadata.keywords)
            doc_tags = set(metadata.tags)

            related = set()
            for other in all_docs:
                # Skip self
                if other.title == metadata.title:
                    continue

                # Calculate similarity score
                other_keywords = set(other.keywords)
                other_tags = set(other.tags)

                # Calculate keyword similarity
                keyword_union = doc_keywords | other_keywords
                keyword_intersection = doc_keywords & other_keywords
                keyword_similarity = (
                    len(keyword_intersection) / len(keyword_union)
                    if keyword_union
                    else 0
                )

                # Calculate tag similarity
                tag_union = doc_tags | other_tags
                tag_intersection = doc_tags & other_tags
                tag_similarity = (
                    len(tag_intersection) / len(tag_union) if tag_union else 0
                )

                # Combine scores (adjust weights as needed)
                similarity = (keyword_similarity * 0.6) + (tag_similarity * 0.4)

                if similarity > 0.3:  # Adjust threshold as needed
                    related.add(other.title)

            return sorted(related)

        except Exception as e:
            logger.error("Related document finding failed", error=str(e))
            return []
