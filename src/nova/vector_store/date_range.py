from dataclasses import dataclass
from datetime import datetime


@dataclass
class DateRange:
    """Class to represent a date range for filtering vector store results."""

    start_date: datetime
    end_date: datetime
    weekdays: list[str] | None = None
