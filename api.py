from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List
import logging
import os
import json
import asyncio
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check for required environment variables
if not os.getenv("GITHUB_TOKEN"):
    raise ValueError("GITHUB_TOKEN not found in environment variables")
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment variables")

from previewer.orchestrator import PRReviewOrchestrator
from previewer.agents.base import Message

app = FastAPI(title="PReviewer API")

# Add CORS middleware with more permissive settings for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

class PRReviewRequest(BaseModel):
    pr_url: str = Field(..., description="GitHub PR URL", min_length=1)

    class Config:
        json_schema_extra = {
            "example": {
                "pr_url": "https://github.com/owner/repo/pull/123"
            }
        }

class PRReviewResponse(BaseModel):
    success: bool
    message: str
    steps: List[str]
    report: Optional[str] = None
    error: Optional[str] = None

async def log_message(message: str, message_type: str = "progress"):
    return f"data: {json.dumps({'type': message_type, 'message': message})}\n\n"

async def review_pr_stream(request: PRReviewRequest):
    try:
        # Initialize the review process
        yield await log_message("Initializing PR Review")
        
        # Run the review process
        orchestrator = PRReviewOrchestrator()
        async for step in orchestrator.review_pr(request.pr_url):
            yield await log_message(step)
            
        # Send completion message
        yield await log_message("Review completed successfully", "complete")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in review process: {error_msg}", exc_info=True)
        yield await log_message(f"Error: {error_msg}", "error")

@app.post("/api/review/stream")
async def review_pr_stream_endpoint(request: Request):
    try:
        raw_data = await request.body()
        logger.info(f"Raw request body: {raw_data}")
        
        try:
            json_data = await request.json()
            logger.info(f"Parsed JSON data: {json_data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

        try:
            review_request = PRReviewRequest(**json_data)
            logger.info(f"Validated request data: {review_request.dict()}")
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise HTTPException(status_code=422, detail=str(e))

        return StreamingResponse(
            review_pr_stream(review_request),
            media_type="text/event-stream"
        )
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
        raise

@app.post("/api/review", response_model=PRReviewResponse)
async def review_pr(request: PRReviewRequest):
    try:
        logger.info(f"Received review request for PR: {request.pr_url}")
        
        # Initialize orchestrator
        orchestrator = PRReviewOrchestrator()
        
        # Create response object to track progress
        response = PRReviewResponse(
            success=True,
            message="Processing PR review",
            steps=["Initializing PR Review"],
            report=None
        )
        
        # Review PR
        try:
            orchestrator.review_pr(request.pr_url)
            
            # Get the final report from the orchestrator's state
            if orchestrator.state.report_analyzer and orchestrator.state.report_analyzer.state.final_reports:
                pr_number = orchestrator.state.pr_number
                final_report = orchestrator.state.report_analyzer.state.final_reports.get(pr_number, "No report generated")
            else:
                final_report = "No report generated"
            
            response.steps.extend([
                "PR Review Completed",
                "Report Generated"
            ])
            response.report = final_report
            response.message = "PR review completed successfully"
            
        except Exception as e:
            logger.error(f"Error during PR review: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error during PR review: {str(e)}"
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
