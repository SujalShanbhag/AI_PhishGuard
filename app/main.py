import os
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings, BASE_DIR
from app.database import engine, Base
import app.models.database_models  # Ensure tables are registered

# Import API Routers
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.analysis import router as analysis_router
from app.api.identity import router as identity_router
from app.api.evidence import router as evidence_router
from app.api.reports import router as reports_router
from app.api.privacy_guard import router as privacy_router
from app.api.gemini_copilot import router as copilot_router
from app.api.datasets import router as datasets_router
from app.api.ml_models import router as ml_router

# Initialize database schema
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI PhishGuard — Advanced Multimodal Deepfake, Phishing Defense "
        "and Privacy-Preserving Identity Protection Platform."
    ),
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Secure exception handler - Never expose internal paths or stack traces
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.APP_DEBUG:
        error_msg = str(exc)
    else:
        error_msg = "An unexpected server error occurred during processing. Please try again."
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": error_msg, "status": "ERROR"}
    )

# Register API Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(analysis_router)
app.include_router(identity_router)
app.include_router(evidence_router)
app.include_router(reports_router)
app.include_router(privacy_router)
app.include_router(copilot_router)
app.include_router(datasets_router)
app.include_router(ml_router)

# Mount Static Files
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
async def serve_index():
    index_file = BASE_DIR / "static" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": f"Welcome to {settings.APP_NAME} API v{settings.APP_VERSION}. Visit /docs for OpenAPI specs."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.APP_DEBUG)
