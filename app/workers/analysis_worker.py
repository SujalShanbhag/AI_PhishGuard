import logging
from concurrent.futures import ThreadPoolExecutor
from app.database import SessionLocal
from app.models.database_models import Analysis
from app.services.image_analysis import image_analysis_service

logger = logging.getLogger("phishguard_worker")

# Worker thread pool for background media forensics
executor = ThreadPoolExecutor(max_workers=4)

def run_analysis_task(analysis_id: str, media_type: str = "IMAGE"):
    """Executes asynchronous image and document media analysis in worker thread."""
    db = SessionLocal()
    try:
        logger.info(f"Starting background forensics job {analysis_id} (Type: {media_type})")
        image_analysis_service.analyze_image(analysis_id, db)
        logger.info(f"Completed background forensics job {analysis_id}")
    except Exception as e:
        logger.error(f"Error in background task {analysis_id}: {e}", exc_info=True)
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if analysis:
            analysis.status = "FAILED"
            analysis.error_message = f"Background processing error: {str(e)}"
            db.commit()
    finally:
        db.close()

def dispatch_analysis(analysis_id: str, media_type: str):
    """Dispatches media processing job to thread pool."""
    executor.submit(run_analysis_task, analysis_id, media_type)
