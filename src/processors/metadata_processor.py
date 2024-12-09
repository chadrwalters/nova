import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

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

    def __init__(self):
        # Initialize NLP components
        self.stop_words = set(stopwords.words("english"))
        self.lemmatizer = WordNetLemmatizer()

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
        self.patterns = {
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

    def extract_metadata(
        self, content: str, file_path: Optional[Path] = None
    ) -> ExtractedMetadata:
        """Extract metadata from document content."""
        try:
            # Try frontmatter first
            doc = frontmatter.loads(content)
            metadata = doc.metadata
            clean_content = doc.content

            # If no frontmatter, try other formats
            if not metadata:
                metadata = {}
                clean_content = content

                # Try YAML block
                yaml_match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
                if yaml_match:
                    try:
                        metadata = yaml.safe_load(yaml_match.group(1))
                        clean_content = yaml_match.group(2)
                    except yaml.YAMLError:
                        pass

                # Try JSON block
                if not metadata:
                    json_match = re.match(r"^\{[\s\S]*?\}\n(.*)", content, re.DOTALL)
                    if json_match:
                        try:
                            metadata = json.loads(json_match.group(0))
                            clean_content = json_match.group(1)
                        except json.JSONDecodeError:
                            pass

            # Extract additional metadata from content
            extracted = self._extract_content_metadata(clean_content)

            # Create empty metadata structure
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
                    try:
                        final_metadata.date = datetime.strptime(
                            date_match.group(1), "%Y-%m-%d"
                        )
                    except ValueError:
                        pass

            # Convert date string to datetime if needed
            if isinstance(final_metadata.date, str):
                try:
                    # Try common date formats
                    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"]:
                        try:
                            final_metadata.date = datetime.strptime(
                                final_metadata.date, fmt
                            )
                            break
                        except ValueError:
                            continue
                except Exception:
                    final_metadata.date = datetime.now()

            # Ensure date exists
            if not final_metadata.date:
                final_metadata.date = datetime.now()

            # Convert priority to int if present
            if final_metadata.priority:
                try:
                    final_metadata.priority = int(final_metadata.priority)
                except (ValueError, TypeError):
                    final_metadata.priority = None

            # Ensure lists are unique
            for field in ["tags", "keywords", "references", "related_docs"]:
                value = getattr(final_metadata, field)
                if value:
                    setattr(final_metadata, field, list(set(value)))

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

    def _extract_content_metadata(self, content: str) -> Dict:
        """Extract metadata from content using patterns."""
        metadata = {}

        # Extract using patterns
        for field, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.MULTILINE)
                values = [m.group(1) for m in matches]
                if values:
                    if field == "tags":
                        metadata[field] = list(
                            set(
                                tag.strip("#")
                                for value in values
                                for tag in value.split()
                            )
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
        """Extract keywords from content using NLP."""
        try:
            # Simple word tokenization
            words = re.findall(r"\b\w+\b", content.lower())

            # Remove stop words and lemmatize
            keywords = []
            for word in words:
                if word not in self.stop_words and word.isalnum() and len(word) > 2:
                    lemma = self.lemmatizer.lemmatize(word)
                    keywords.append(lemma)

            # Count frequencies
            from collections import Counter

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

    def _generate_summary(self, content: str) -> Optional[str]:
        """Generate a summary from content."""
        try:
            # Remove markdown formatting
            clean_text = re.sub(r"[#*_~`]", "", content)
            clean_text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", clean_text)

            # Simple sentence splitting
            sentences = re.split(r"[.!?]+\s+", clean_text)

            # Get first few sentences (adjust as needed)
            summary_sentences = sentences[:3]

            if summary_sentences:
                return " ".join(summary_sentences)
            return None

        except Exception as e:
            logger.error("Summary generation failed", error=str(e))
            return None

    def _create_empty_metadata(self) -> DocumentMetadata:
        """Create empty metadata structure."""
        return DocumentMetadata(
            title="",
            date=datetime.now(),
            author=None,
            category="general",
            tags=[],
            summary=None,
            status=None,
            priority=None,
            keywords=[],
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

        return sorted(list(references))

    def find_related_documents(
        self, content: str, metadata: DocumentMetadata, all_docs: List[DocumentMetadata]
    ) -> List[str]:
        """Find related documents based on content similarity."""
        try:
            # Extract keywords from current document
            doc_keywords = set(metadata.keywords)
            doc_tags = set(metadata.tags)

            related = []
            for other in all_docs:
                # Skip self
                if other.title == metadata.title:
                    continue

                # Calculate similarity score
                other_keywords = set(other.keywords)
                other_tags = set(other.tags)

                keyword_similarity = (
                    len(doc_keywords & other_keywords)
                    / len(doc_keywords | other_keywords)
                    if doc_keywords or other_keywords
                    else 0
                )
                tag_similarity = (
                    len(doc_tags & other_tags) / len(doc_tags | other_tags)
                    if doc_tags or other_tags
                    else 0
                )

                # Combine scores (adjust weights as needed)
                similarity = (keyword_similarity * 0.6) + (tag_similarity * 0.4)

                if similarity > 0.3:  # Adjust threshold as needed
                    related.append(other.title)

            return sorted(related)

        except Exception as e:
            logger.error("Related document finding failed", error=str(e))
            return []
