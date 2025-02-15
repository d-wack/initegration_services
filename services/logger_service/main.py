"""
Logger Service - Main Application

This service handles centralized logging for all other services.
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
    return {"message": "Logger Service Running"} 