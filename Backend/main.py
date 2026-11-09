import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import STATIC_DIR, CORS_ORIGINS, HOST, PORT
from app.api.routes import router

app = FastAPI(
    title="FootfallCam Vision Detection API",
    description="Video-analysis backend service for person detection, tracking, and staff tag verification",
    version="2.3.1"
)

# CORS middleware for Angular UI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static evidence and uploads directories
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include API routes
app.include_router(router)

@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "FootfallCam Vision Detection Backend",
        "version": "2.3.1",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, reload=True)

