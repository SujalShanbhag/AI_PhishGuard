import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.database_models import User, Analysis, Report
from app.security.authentication import get_current_user
from app.services.report_generation import report_generation_service

router = APIRouter(prefix="/api/reports", tags=["Forensic Reports"])

@router.post("/{analysis_id}/generate")
def generate_report(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis record not found.")

    report = report_generation_service.generate_pdf_report(analysis_id, db)
    if not report:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to compile PDF report.")

    return {
        "report_id": report.id,
        "analysis_id": analysis.id,
        "message": "Forensic PDF report generated successfully.",
        "download_url": f"/api/reports/{report.id}/download"
    }

@router.get("/{report_id}")
def get_report_metadata_or_json(
    report_id: str,
    format: Optional[str] = Query("meta", description="Options: 'meta' or 'json'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(Report).filter(Report.id == report_id, Report.user_id == current_user.id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report record not found.")

    if format == "json":
        json_data = report_generation_service.export_json_report(report.analysis_id, db)
        if not json_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis details not found.")
        return json_data

    return {
        "report_id": report.id,
        "analysis_id": report.analysis_id,
        "report_type": report.report_type,
        "created_at": report.created_at,
        "download_url": f"/api/reports/{report.id}/download"
    }

@router.get("/{report_id}/download")
def download_pdf_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(Report).filter(Report.id == report_id, Report.user_id == current_user.id).first()
    if not report or not os.path.exists(report.report_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file not found or unauthorized.")

    filename = Path(report.report_path).name
    return FileResponse(
        report.report_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.delete("/{report_id}")
def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(Report).filter(Report.id == report_id, Report.user_id == current_user.id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    if os.path.exists(report.report_path):
        try:
            os.remove(report.report_path)
        except Exception:
            pass

    db.delete(report)
    db.commit()
    return {"message": "Report deleted successfully."}
