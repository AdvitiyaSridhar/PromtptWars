import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db
from app.routers import auth, shifts, fatigue, earnings, safety, disputes, evidence

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is initialized
    init_db()
    # Ensure local upload directory exists
    os.makedirs(settings.LOCAL_UPLOAD_DIR, exist_ok=True)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="FairShift worker protection platform for work/rest rules, attendance, earnings, safety and disputes.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.LOCAL_UPLOAD_DIR, exist_ok=True)

# Include Core API Routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(shifts.router, prefix=settings.API_V1_PREFIX)
app.include_router(fatigue.router, prefix=settings.API_V1_PREFIX)
app.include_router(earnings.router, prefix=settings.API_V1_PREFIX)
app.include_router(safety.router, prefix=settings.API_V1_PREFIX)
app.include_router(disputes.router, prefix=settings.API_V1_PREFIX)
app.include_router(evidence.router, prefix=settings.API_V1_PREFIX)

@app.get("/healthz", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "storage_backend": settings.STORAGE_BACKEND
    }

# Check if frontend production dist directory exists for single-container deployment
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="static-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found.")
        file_path = os.path.abspath(os.path.join(frontend_dist, full_path))
        try:
            is_frontend_file = os.path.commonpath([frontend_dist, file_path]) == frontend_dist
        except ValueError:
            is_frontend_file = False
        if is_frontend_file and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))
