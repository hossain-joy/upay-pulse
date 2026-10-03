"""
upay Pulse - Scam Reporting Service
Handles citizen and agent scam complaints, links reports to money-mule clusters,
and orchestrates automated freeze workflows upon fraud confirmation.
"""

from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.exceptions import AppException
from backend.app.core.events import event_bus
from backend.app.models.user import User
from backend.app.models.scam import ScamReport, ScamReportStatus
from backend.app.models.mule_graph import MuleGraphNode
from backend.app.models.transaction import Transaction
from backend.app.models.audit import AuditLog
from backend.app.schemas.scam import ScamReportCreate, ScamReportResolve
from backend.app.services.freeze_service import FreezeService

class ScamService:

    @classmethod
    def file_report(cls, db: Session, reporter: User, req: ScamReportCreate) -> ScamReport:
        """
        Files a new scam or fraud incident report from a customer or agent.
        Automatically analyzes if the reported account belongs to a known mule syndicate.
        """
        target_account = req.reported_account.strip()

        # Validate linked transaction if provided
        if req.transaction_id:
            txn = db.query(Transaction).filter(Transaction.id == req.transaction_id).first()
            if not txn:
                raise AppException(
                    message="Referenced transaction not found.",
                    code="TRANSACTION_NOT_FOUND",
                    status_code=404
                )

        # Check if the reported account matches any known cluster node
        mule_node = db.query(MuleGraphNode).filter(MuleGraphNode.account_number == target_account).first()
        cluster_id = mule_node.cluster_id if mule_node else None

        report = ScamReport(
            reporter_id=reporter.id,
            reported_account=target_account,
            transaction_id=req.transaction_id,
            reason=req.reason.strip(),
            status=ScamReportStatus.SUBMITTED,
            cluster_id=cluster_id,
            investigation_notes=req.investigation_notes
        )
        db.add(report)
        db.flush()

        # Audit Log
        db.add(AuditLog(
            actor_id=reporter.id,
            actor_role=reporter.role.value if hasattr(reporter.role, 'value') else str(reporter.role),
            action="SCAM_REPORT_FILED",
            resource="SCAM_REPORTS",
            resource_id=report.id,
            details=f'{{"reported_account": "{target_account}", "cluster_id": "{cluster_id}", "reason": "{req.reason}"}}'
        ))

        # Real-time Event Bus alert for Risk Console
        event_bus.publish_sync("security.scam_reported", {
            "report_id": report.id,
            "reporter_phone": reporter.phone,
            "reported_account": target_account,
            "reason": req.reason,
            "cluster_id": cluster_id
        })

        db.commit()
        db.refresh(report)
        return report

    @classmethod
    def list_reports(
        cls,
        db: Session,
        status: Optional[ScamReportStatus] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[int, List[ScamReport]]:
        """
        Lists scam reports with optional status filtering.
        """
        query = db.query(ScamReport)
        if status:
            query = query.filter(ScamReport.status == status)

        total = query.count()
        items = query.order_by(desc(ScamReport.created_at)).offset(skip).limit(limit).all()
        return total, items

    @classmethod
    def get_report(cls, db: Session, report_id: str) -> ScamReport:
        """
        Retrieves a single scam report by ID.
        """
        report = db.query(ScamReport).filter(ScamReport.id == report_id).first()
        if not report:
            raise AppException(
                message=f"Scam report {report_id} not found.",
                code="REPORT_NOT_FOUND",
                status_code=404
            )
        return report

    @classmethod
    def resolve_report(
        cls,
        db: Session,
        report_id: str,
        admin: User,
        req: ScamReportResolve
    ) -> ScamReport:
        """
        Investigator resolves report. If confirmed fraud and auto_freeze is enabled,
        executes Master Freeze on the fraudster's account.
        """
        report = cls.get_report(db, report_id)
        report.status = req.status
        if req.investigation_notes:
            report.investigation_notes = req.investigation_notes

        freeze_executed = False
        frozen_user_id = None

        if req.status == ScamReportStatus.CONFIRMED_FRAUD and req.auto_freeze_account:
            # Look up suspect user by phone or email
            suspect = db.query(User).filter(
                (User.phone == report.reported_account) | (User.email == report.reported_account)
            ).first()

            if suspect and not suspect.is_frozen:
                FreezeService.freeze_account(
                    db=db,
                    user=suspect,
                    reason=f"Scam report {report_id} confirmed fraud by admin {admin.email}",
                    admin_override=True
                )
                freeze_executed = True
                frozen_user_id = suspect.id

        # Audit resolution
        db.add(AuditLog(
            actor_id=admin.id,
            actor_role="ADMIN",
            action="SCAM_REPORT_RESOLVED",
            resource="SCAM_REPORTS",
            resource_id=report.id,
            details=f'{{"status": "{req.status.value}", "freeze_executed": {freeze_executed}, "target_user_id": "{frozen_user_id}"}}'
        ))

        db.commit()
        db.refresh(report)
        return report
