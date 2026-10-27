"""
Main FastAPI server for Encrypted IoT Device Fingerprinting GUI.
Port: 8765 (configurable via .env).
"""
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load .env
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
GUI_DIR = os.path.dirname(BACKEND_DIR)
load_dotenv(os.path.join(GUI_DIR, ".env"))

BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8765))
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

app = FastAPI(
    title="Encrypted IoT Device Fingerprinting API",
    description="Real-time ML backend for encrypted network traffic timing analysis and open-set device fingerprinting.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for flexible local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
from .routes.info import router as info_router
from .routes.predict import router as predict_router
from .routes.stream import router as stream_router
from .routes.spoof import router as spoof_router

app.include_router(info_router, tags=["Information & Evaluation"])
app.include_router(predict_router, tags=["Inference"])
app.include_router(stream_router, tags=["Live Streaming & Replay"])
app.include_router(spoof_router, tags=["Spoofing Detection & Claimed-Identity Verification"])


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "iot-fingerprinting-backend", "port": BACKEND_PORT}


@app.get("/")
def root():
    return {
        "title": "Encrypted IoT Device Fingerprinting API",
        "docs_url": "/docs",
        "health": "/health",
        "model_info": "/model/info",
        "evaluation": "/evaluation",
        "spoof_results": "/spoof/results",
        "spoof_verify": "/spoof/verify",
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host=BACKEND_HOST, port=BACKEND_PORT, reload=True)
