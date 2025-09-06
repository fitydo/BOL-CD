"""Data Retention Policy Management for BOL-CD

Implements automatic data deletion based on retention policies.
Supports different retention periods for different data types and compliance requirements.
"""

from __future__ import annotations

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class RetentionPeriod(Enum):
    """Standard retention periods"""
    DAYS_7 = 7
    DAYS_30 = 30
    DAYS_90 = 90
    DAYS_180 = 180
    DAYS_365 = 365
    DAYS_730 = 730  # 2 years
    DAYS_1095 = 1095  # 3 years
    DAYS_2555 = 2555  # 7 years
    UNLIMITED = -1  # No automatic deletion


class DataType(Enum):
    """Types of data with different retention requirements"""
    ALERTS = "alerts"
    AUDIT_LOGS = "audit_logs"
    METRICS = "metrics"
    REPORTS = "reports"
    USER_DATA = "user_data"
    TEMPORARY = "temporary"
    COMPLIANCE = "compliance"


class RetentionPolicy:
    """Data retention policy configuration"""
    
    def __init__(
        self,
        data_type: DataType,
        retention_period: RetentionPeriod,
        enabled: bool = True,
        archive_before_delete: bool = False,
        compliance_hold: bool = False
    ):
        self.data_type = data_type
        self.retention_period = retention_period
        self.enabled = enabled
        self.archive_before_delete = archive_before_delete
        self.compliance_hold = compliance_hold  # Prevents deletion for legal/compliance reasons
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "data_type": self.data_type.value,
            "retention_days": self.retention_period.value,
            "enabled": self.enabled,
            "archive_before_delete": self.archive_before_delete,
            "compliance_hold": self.compliance_hold
        }


class RetentionManager:
    """Manages data retention policies and automatic deletion"""
    
    def __init__(
        self,
        config_file: Optional[str] = None,
        database_url: Optional[str] = None,
        storage_path: Optional[str] = None
    ):
        self.config_file = config_file or os.getenv("BOLCD_RETENTION_CONFIG", "configs/retention.yaml")
        self.database_url = database_url or os.getenv("BOLCD_DATABASE_URL", "sqlite:///./bolcd.db")
        self.storage_path = Path(storage_path or os.getenv("BOLCD_STORAGE_PATH", "./data"))
        self.archive_path = self.storage_path / "archive"
        self.archive_path.mkdir(parents=True, exist_ok=True)
        
        # Default policies
        self.policies: Dict[DataType, RetentionPolicy] = self._load_default_policies()
        
        # Load custom policies from config
        self._load_config()
        
        # Initialize database connection if needed
        if self.database_url:
            self.engine = create_engine(self.database_url)
            self.SessionLocal = sessionmaker(bind=self.engine)
    
    def _load_default_policies(self) -> Dict[DataType, RetentionPolicy]:
        """Load default retention policies"""
        # Get plan tier from environment
        plan_tier = os.getenv("BOLCD_PLAN_TIER", "standard").lower()
        
        # Default policies based on plan
        if plan_tier == "starter":
            return {
                DataType.ALERTS: RetentionPolicy(DataType.ALERTS, RetentionPeriod.DAYS_90),
                DataType.AUDIT_LOGS: RetentionPolicy(DataType.AUDIT_LOGS, RetentionPeriod.DAYS_90),
                DataType.METRICS: RetentionPolicy(DataType.METRICS, RetentionPeriod.DAYS_30),
                DataType.REPORTS: RetentionPolicy(DataType.REPORTS, RetentionPeriod.DAYS_90),
                DataType.USER_DATA: RetentionPolicy(DataType.USER_DATA, RetentionPeriod.UNLIMITED),
                DataType.TEMPORARY: RetentionPolicy(DataType.TEMPORARY, RetentionPeriod.DAYS_7),
                DataType.COMPLIANCE: RetentionPolicy(DataType.COMPLIANCE, RetentionPeriod.DAYS_365, compliance_hold=True)
            }
        elif plan_tier == "enterprise":
            return {
                DataType.ALERTS: RetentionPolicy(DataType.ALERTS, RetentionPeriod.UNLIMITED),
                DataType.AUDIT_LOGS: RetentionPolicy(DataType.AUDIT_LOGS, RetentionPeriod.DAYS_2555, archive_before_delete=True),
                DataType.METRICS: RetentionPolicy(DataType.METRICS, RetentionPeriod.DAYS_365),
                DataType.REPORTS: RetentionPolicy(DataType.REPORTS, RetentionPeriod.UNLIMITED),
                DataType.USER_DATA: RetentionPolicy(DataType.USER_DATA, RetentionPeriod.UNLIMITED),
                DataType.TEMPORARY: RetentionPolicy(DataType.TEMPORARY, RetentionPeriod.DAYS_7),
                DataType.COMPLIANCE: RetentionPolicy(DataType.COMPLIANCE, RetentionPeriod.UNLIMITED, compliance_hold=True)
            }
        else:  # standard
            return {
                DataType.ALERTS: RetentionPolicy(DataType.ALERTS, RetentionPeriod.DAYS_365),
                DataType.AUDIT_LOGS: RetentionPolicy(DataType.AUDIT_LOGS, RetentionPeriod.DAYS_365, archive_before_delete=True),
                DataType.METRICS: RetentionPolicy(DataType.METRICS, RetentionPeriod.DAYS_90),
                DataType.REPORTS: RetentionPolicy(DataType.REPORTS, RetentionPeriod.DAYS_365),
                DataType.USER_DATA: RetentionPolicy(DataType.USER_DATA, RetentionPeriod.UNLIMITED),
                DataType.TEMPORARY: RetentionPolicy(DataType.TEMPORARY, RetentionPeriod.DAYS_7),
                DataType.COMPLIANCE: RetentionPolicy(DataType.COMPLIANCE, RetentionPeriod.DAYS_730, compliance_hold=True)
            }
    
    def _load_config(self):
        """Load custom retention policies from config file"""
        config_path = Path(self.config_file)
        if not config_path.exists():
            return
        
        try:
            if config_path.suffix == ".yaml":
                import yaml
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
            else:
                with open(config_path, "r") as f:
                    config = json.load(f)
            
            # Override default policies with custom config
            for data_type_str, policy_config in config.get("retention_policies", {}).items():
                try:
                    data_type = DataType(data_type_str)
                    retention_days = policy_config.get("retention_days", 90)
                    
                    # Find matching retention period enum
                    retention_period = RetentionPeriod.DAYS_90  # default
                    for period in RetentionPeriod:
                        if period.value == retention_days:
                            retention_period = period
                            break
                    
                    self.policies[data_type] = RetentionPolicy(
                        data_type=data_type,
                        retention_period=retention_period,
                        enabled=policy_config.get("enabled", True),
                        archive_before_delete=policy_config.get("archive_before_delete", False),
                        compliance_hold=policy_config.get("compliance_hold", False)
                    )
                except ValueError:
                    logger.warning(f"Unknown data type in config: {data_type_str}")
                    
        except Exception as e:
            logger.error(f"Failed to load retention config: {e}")
    
    def apply_retention_policies(self, dry_run: bool = False) -> Dict[str, Any]:
        """Apply retention policies to delete old data"""
        results = {
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "dry_run": dry_run,
            "deleted": {},
            "archived": {},
            "errors": []
        }
        
        for data_type, policy in self.policies.items():
            if not policy.enabled or policy.compliance_hold:
                continue
            
            if policy.retention_period == RetentionPeriod.UNLIMITED:
                continue
            
            try:
                cutoff_date = datetime.now(datetime.UTC) - timedelta(days=policy.retention_period.value)
                
                # Process based on data type
                if data_type == DataType.ALERTS:
                    count = self._clean_alerts(cutoff_date, dry_run, policy.archive_before_delete)
                    results["deleted"][data_type.value] = count
                    
                elif data_type == DataType.AUDIT_LOGS:
                    count = self._clean_audit_logs(cutoff_date, dry_run, policy.archive_before_delete)
                    results["deleted"][data_type.value] = count
                    
                elif data_type == DataType.METRICS:
                    count = self._clean_metrics(cutoff_date, dry_run, policy.archive_before_delete)
                    results["deleted"][data_type.value] = count
                    
                elif data_type == DataType.REPORTS:
                    count = self._clean_reports(cutoff_date, dry_run, policy.archive_before_delete)
                    results["deleted"][data_type.value] = count
                    
                elif data_type == DataType.TEMPORARY:
                    count = self._clean_temporary_files(cutoff_date, dry_run)
                    results["deleted"][data_type.value] = count
                    
            except Exception as e:
                logger.error(f"Error applying retention for {data_type.value}: {e}")
                results["errors"].append({
                    "data_type": data_type.value,
                    "error": str(e)
                })
        
        return results
    
    def _clean_alerts(self, cutoff_date: datetime, dry_run: bool, archive: bool) -> int:
        """Clean old alert data"""
        count = 0
        
        # Clean from database
        if self.database_url:
            with self.SessionLocal() as session:
                # Count records to delete
                result = session.execute(
                    text("SELECT COUNT(*) FROM alerts WHERE created_at < :cutoff"),
                    {"cutoff": cutoff_date}
                )
                count = result.scalar() or 0
                
                if not dry_run and count > 0:
                    if archive:
                        # Archive before deletion
                        self._archive_database_records("alerts", cutoff_date)
                    
                    # Delete old records
                    session.execute(
                        text("DELETE FROM alerts WHERE created_at < :cutoff"),
                        {"cutoff": cutoff_date}
                    )
                    session.commit()
        
        # Clean from filesystem
        alerts_path = self.storage_path / "alerts"
        if alerts_path.exists():
            for file_path in alerts_path.glob("*.jsonl"):
                # Check file modification time
                if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_date:
                    count += 1
                    if not dry_run:
                        if archive:
                            self._archive_file(file_path)
                        file_path.unlink()
        
        return count
    
    def _clean_audit_logs(self, cutoff_date: datetime, dry_run: bool, archive: bool) -> int:
        """Clean old audit logs"""
        count = 0
        
        # Clean audit log files
        audit_path = self.storage_path / "audit"
        if audit_path.exists():
            for file_path in audit_path.glob("*.jsonl"):
                if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_date:
                    count += 1
                    if not dry_run:
                        if archive:
                            self._archive_file(file_path)
                        file_path.unlink()
        
        return count
    
    def _clean_metrics(self, cutoff_date: datetime, dry_run: bool, archive: bool) -> int:
        """Clean old metrics data"""
        count = 0
        
        # Clean metrics files
        metrics_path = self.storage_path / "metrics"
        if metrics_path.exists():
            for file_path in metrics_path.glob("*.json"):
                if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_date:
                    count += 1
                    if not dry_run:
                        if archive:
                            self._archive_file(file_path)
                        file_path.unlink()
        
        return count
    
    def _clean_reports(self, cutoff_date: datetime, dry_run: bool, archive: bool) -> int:
        """Clean old reports"""
        count = 0
        
        # Clean report files
        reports_path = self.storage_path / "reports"
        if reports_path.exists():
            for file_path in reports_path.glob("*"):
                if file_path.is_file() and datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_date:
                    count += 1
                    if not dry_run:
                        if archive:
                            self._archive_file(file_path)
                        file_path.unlink()
        
        return count
    
    def _clean_temporary_files(self, cutoff_date: datetime, dry_run: bool) -> int:
        """Clean temporary files"""
        count = 0
        
        # Clean tmp directory
        tmp_path = self.storage_path / "tmp"
        if tmp_path.exists():
            for file_path in tmp_path.glob("*"):
                if file_path.is_file() and datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_date:
                    count += 1
                    if not dry_run:
                        file_path.unlink()
        
        return count
    
    def _archive_file(self, file_path: Path):
        """Archive a file before deletion"""
        # Create archive subdirectory based on date
        archive_date = datetime.fromtimestamp(file_path.stat().st_mtime)
        archive_subdir = self.archive_path / archive_date.strftime("%Y/%m")
        archive_subdir.mkdir(parents=True, exist_ok=True)
        
        # Move file to archive
        archive_file = archive_subdir / file_path.name
        file_path.rename(archive_file)
        
        # Compress if large
        if archive_file.stat().st_size > 1024 * 1024:  # > 1MB
            import gzip
            with open(archive_file, "rb") as f_in:
                with gzip.open(f"{archive_file}.gz", "wb") as f_out:
                    f_out.writelines(f_in)
            archive_file.unlink()
    
    def _archive_database_records(self, table: str, cutoff_date: datetime):
        """Archive database records before deletion"""
        with self.SessionLocal() as session:
            # Export to JSON
            result = session.execute(
                text(f"SELECT * FROM {table} WHERE created_at < :cutoff"),
                {"cutoff": cutoff_date}
            )
            
            # Save to archive
            archive_date = cutoff_date.strftime("%Y%m%d")
            archive_file = self.archive_path / f"{table}_{archive_date}.jsonl"
            
            with open(archive_file, "w") as f:
                for row in result:
                    f.write(json.dumps(dict(row), default=str) + "\n")
    
    def get_retention_status(self) -> Dict[str, Any]:
        """Get current retention policy status"""
        status = {
            "policies": {},
            "storage_usage": {},
            "next_cleanup": None
        }
        
        # Add policy details
        for data_type, policy in self.policies.items():
            status["policies"][data_type.value] = policy.to_dict()
        
        # Calculate storage usage
        for data_type in DataType:
            path = self.storage_path / data_type.value
            if path.exists():
                total_size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                status["storage_usage"][data_type.value] = {
                    "size_bytes": total_size,
                    "size_mb": round(total_size / (1024 * 1024), 2)
                }
        
        return status
    
    def set_compliance_hold(self, data_type: DataType, enabled: bool = True):
        """Set or remove compliance hold on data type"""
        if data_type in self.policies:
            self.policies[data_type].compliance_hold = enabled
            logger.info(f"Compliance hold {'enabled' if enabled else 'disabled'} for {data_type.value}")
