"""
OAuth Service - Main Application

This service handles OAuth authentication for third-party providers.
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
    return {"message": "OAuth Service Running"} 