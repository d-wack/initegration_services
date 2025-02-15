"""
Webhook Service - Main Application

This service handles webhook reception and processing from third-party services.
"""

from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Webhook Service Running"} 