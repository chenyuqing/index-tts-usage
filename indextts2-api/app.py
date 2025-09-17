#!/usr/bin/env python3
"""
IndexTTS2 API Service
A simplified RESTful API for voice cloning and TTS
"""

import os
import sys
import logging
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from api.routes import router, setup_cors
from config.settings import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize config
config = get_config()

# Create FastAPI app
app = FastAPI(
    title="IndexTTS2 API",
    description="A simplified RESTful API for voice cloning and text-to-speech",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup CORS
setup_cors(app)

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "error_code": "500"
        }
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "IndexTTS2 API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "IndexTTS2 API",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "app:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level="info"
    )