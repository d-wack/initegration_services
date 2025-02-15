"""
Integration Service - Main Application

This service handles integration between Monday.com and HubSpot.
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
    return {"message": "Integration Service Running"} 