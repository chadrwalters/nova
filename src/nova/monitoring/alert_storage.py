"""Alert storage and retrieval for Nova monitoring."""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Float, Enum
from sqlalchemy.orm import declarative_base, sessionmaker
import enum
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

class AlertStatus(enum.Enum):
    """Alert status enum."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

class AlertSeverity(enum.Enum):
    """Alert severity enum."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

    def __lt__(self, other):
        """Compare severity levels."""
        order = {"critical": 3, "warning": 2, "info": 1}
        return order[self.value] < order[other.value]

    def __gt__(self, other):
        """Compare severity levels."""
        order = {"critical": 3, "warning": 2, "info": 1}
        return order[self.value] > order[other.value]

    def __le__(self, other):
        """Compare severity levels."""
        return self < other or self == other

    def __ge__(self, other):
        """Compare severity levels."""
        return self > other or self == other

@dataclass
class Alert:
    """Alert data class for API responses."""
    alert_id: str
    type: str
    severity: AlertSeverity
    message: str
    component: str
    created_at: datetime
    updated_at: datetime
    status: AlertStatus
    value: float
    alert_metadata: Dict[str, Any]

    @classmethod
    def from_stored_alert(cls, stored_alert: 'StoredAlert') -> 'Alert':
        """Create an Alert instance from a StoredAlert."""
        return cls(
            alert_id=stored_alert.alert_id,
            type=stored_alert.type,
            severity=stored_alert.severity,
            message=stored_alert.message,
            component=stored_alert.component,
            created_at=stored_alert.created_at,
            updated_at=stored_alert.updated_at,
            status=stored_alert.status,
            value=stored_alert.value,
            alert_metadata=stored_alert.alert_metadata
        )

@dataclass
class StoredAlert(Base):
    """Alert storage model."""
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True)
    alert_id = Column(String, unique=True, nullable=False)
    type = Column(String, nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    message = Column(String, nullable=False)
    component = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    status = Column(Enum(AlertStatus), nullable=False, default=AlertStatus.ACTIVE)
    value = Column(Float, nullable=True)
    alert_metadata = Column(JSON, nullable=True)

class AlertStorage:
    """Alert storage manager."""

    def __init__(self, db_url: str = "sqlite:///alerts.db"):
        """Initialize alert storage.

        Args:
            db_url: Database URL for alert storage
        """
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def store_alert(self, alert_id: str, alert_type: str, severity: str,
                   message: str, component: str, value: Optional[float] = None,
                   metadata: Optional[Dict] = None) -> StoredAlert:
        """Store a new alert.

        Args:
            alert_id: Unique alert identifier
            alert_type: Type of alert
            severity: Alert severity
            message: Alert message
            component: Affected component
            value: Alert value if applicable
            metadata: Additional alert metadata

        Returns:
            Stored alert
        """
        session = self.Session()
        try:
            alert = StoredAlert(
                alert_id=alert_id,
                type=alert_type,
                severity=AlertSeverity(severity),
                message=message,
                component=component,
                value=value,
                alert_metadata=metadata
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)  # Refresh to ensure all attributes are loaded
            return alert
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store alert: {e}")
            raise
        finally:
            session.close()

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get an alert by ID."""
        session = self.Session()
        try:
            stored_alert = session.query(StoredAlert).filter(StoredAlert.alert_id == alert_id).first()
            return Alert.from_stored_alert(stored_alert) if stored_alert else None
        finally:
            session.close()

    def get_alerts(self, start_time: Optional[datetime] = None,
                  end_time: Optional[datetime] = None,
                  component: Optional[str] = None,
                  severity: Optional[str] = None,
                  status: Optional[str] = None,
                  limit: int = 100) -> List[Alert]:
        """Get alerts matching the given criteria."""
        session = self.Session()
        try:
            query = session.query(StoredAlert)

            if start_time:
                query = query.filter(StoredAlert.created_at >= start_time)
            if end_time:
                query = query.filter(StoredAlert.created_at <= end_time)
            if component:
                query = query.filter(StoredAlert.component == component)
            if severity:
                query = query.filter(StoredAlert.severity == AlertSeverity(severity.lower()))
            if status:
                query = query.filter(StoredAlert.status == AlertStatus(status.lower()))

            stored_alerts = query.order_by(StoredAlert.created_at.desc()).limit(limit).all()
            return [Alert.from_stored_alert(alert) for alert in stored_alerts]
        finally:
            session.close()

    def get_alert_summary(self) -> Dict[str, int]:
        """Get a summary of alerts by status."""
        session = self.Session()
        try:
            total = session.query(StoredAlert).count()
            active = session.query(StoredAlert).filter(StoredAlert.status == AlertStatus.ACTIVE).count()
            acknowledged = session.query(StoredAlert).filter(StoredAlert.status == AlertStatus.ACKNOWLEDGED).count()
            resolved = session.query(StoredAlert).filter(StoredAlert.status == AlertStatus.RESOLVED).count()

            return {
                "total_alerts": total,
                "active_alerts": active,
                "acknowledged_alerts": acknowledged,
                "resolved_alerts": resolved
            }
        finally:
            session.close()

    def update_alert_status(self, alert_id: str, status: str) -> bool:
        """Update alert status.

        Args:
            alert_id: Alert identifier
            status: New alert status

        Returns:
            True if alert was updated, False otherwise
        """
        session = self.Session()
        try:
            alert = session.query(StoredAlert).filter_by(alert_id=alert_id).first()
            if alert:
                alert.status = AlertStatus(status)
                alert.updated_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(alert)  # Refresh to ensure all attributes are loaded
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update alert status: {e}")
            raise
        finally:
            session.close()

    def delete_old_alerts(self, before_time: datetime) -> int:
        """Delete alerts older than specified time.

        Args:
            before_time: Delete alerts before this time

        Returns:
            Number of alerts deleted
        """
        session = self.Session()
        try:
            deleted = session.query(StoredAlert).filter(
                StoredAlert.created_at < before_time
            ).delete()
            session.commit()
            return deleted
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete old alerts: {e}")
            raise
        finally:
            session.close()
