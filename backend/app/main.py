import json
import logging
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent import run_agent

app = FastAPI(title="Backend Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("api")

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    async def event_stream():
        try:
            async for chunk in run_agent(req.message):
                yield f"data: {chunk}\n"
        except Exception as e:
            logger.exception("Agent execution failed.")
            error_payload = json.dumps({
                "type": "error", 
                "content": "An internal error occurred. Please try again later."
            })
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
