"""Visualization utilities for monitoring data."""

import io
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure

logger = logging.getLogger(__name__)

def create_tag_cloud(tags: Dict[str, int], max_words: int = 50) -> bytes:
    """Create a word cloud visualization of tags.

    Args:
        tags: Dictionary of tag frequencies
        max_words: Maximum number of words to include

    Returns:
        PNG image bytes
    """
    try:
        try:
            from wordcloud import WordCloud
        except ImportError:
            logger.warning("wordcloud package not installed, falling back to bar chart")
            return create_tag_barchart(tags, max_words)

        # Create word cloud
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            max_words=max_words
        ).generate_from_frequencies(tags)

        # Convert to image
        fig = plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')

        return _fig_to_png(fig)
    except Exception as e:
        logger.error(f"Failed to create tag cloud: {e}")
        return b""

def create_tag_barchart(tags: Dict[str, int], max_tags: int = 50) -> bytes:
    """Create a bar chart visualization of tags.

    Args:
        tags: Dictionary of tag frequencies
        max_tags: Maximum number of tags to include

    Returns:
        PNG image bytes
    """
    try:
        # Sort tags by frequency and take top N
        sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:max_tags]
        labels, values = zip(*sorted_tags)

        # Create bar chart
        fig, ax = plt.subplots(figsize=(12, 6))
        plt.bar(labels, values)
        plt.title("Tag Frequencies")
        plt.xlabel("Tags")
        plt.ylabel("Frequency")
        plt.xticks(rotation=45, ha='right')

        return _fig_to_png(fig)
    except Exception as e:
        logger.error(f"Failed to create tag bar chart: {e}")
        return b""

def create_attachment_pie(attachment_types: Dict[str, float]) -> bytes:
    """Create a pie chart of attachment type distribution.

    Args:
        attachment_types: Dictionary of type percentages

    Returns:
        PNG image bytes
    """
    try:
        # Convert dict_keys to list
        labels = list(attachment_types.keys())
        values = list(attachment_types.values())

        # Create pie chart
        fig, ax = plt.subplots(figsize=(8, 8))
        plt.pie(
            values,
            labels=labels,
            autopct='%1.1f%%',
            startangle=90
        )
        plt.title("Attachment Types Distribution")

        return _fig_to_png(fig)
    except Exception as e:
        logger.error(f"Failed to create attachment pie chart: {e}")
        return b""

def create_date_timeline(date_data: List[Dict[str, Any]]) -> bytes:
    """Create a timeline visualization of document dates.

    Args:
        date_data: List of date and count dictionaries

    Returns:
        PNG image bytes
    """
    try:
        # Convert to DataFrame
        df = pd.DataFrame(date_data)
        df['date'] = pd.to_datetime(df['date'])

        # Create timeline
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.lineplot(data=df, x='date', y='count')
        plt.title("Document Timeline")
        plt.xlabel("Date")
        plt.ylabel("Number of Documents")
        plt.xticks(rotation=45)

        return _fig_to_png(fig)
    except Exception as e:
        logger.error(f"Failed to create date timeline: {e}")
        return b""

def create_search_trends(performance_data: List[Dict[str, Any]]) -> bytes:
    """Create a visualization of search performance trends.

    Args:
        performance_data: List of performance metrics over time

    Returns:
        PNG image bytes
    """
    try:
        # Convert to DataFrame
        df = pd.DataFrame(performance_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Create multi-line plot
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.lineplot(data=df, x='timestamp', y='response_time', label='Response Time (ms)')
        sns.lineplot(data=df, x='timestamp', y='results_count', label='Results Count')

        plt.title("Search Performance Trends")
        plt.xlabel("Time")
        plt.ylabel("Value")
        plt.xticks(rotation=45)
        plt.legend()

        return _fig_to_png(fig)
    except Exception as e:
        logger.error(f"Failed to create search trends: {e}")
        return b""

def create_error_trends(error_data: List[Dict[str, Any]]) -> bytes:
    """Create a visualization of error trends.

    Args:
        error_data: List of error counts over time

    Returns:
        PNG image bytes
    """
    try:
        # Convert to DataFrame
        df = pd.DataFrame(error_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Create stacked area plot
        fig, ax = plt.subplots(figsize=(12, 6))
        df.plot(
            x='timestamp',
            y=['error_count', 'warning_count'],
            kind='area',
            stacked=True,
            ax=ax
        )

        plt.title("Error and Warning Trends")
        plt.xlabel("Time")
        plt.ylabel("Count")
        plt.xticks(rotation=45)
        plt.legend(['Errors', 'Warnings'])

        return _fig_to_png(fig)
    except Exception as e:
        logger.error(f"Failed to create error trends: {e}")
        return b""

def _fig_to_png(fig: Figure) -> bytes:
    """Convert matplotlib figure to PNG bytes.

    Args:
        fig: Matplotlib figure

    Returns:
        PNG image bytes
    """
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
