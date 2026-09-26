from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from pathlib import Path

from intent_router import route_query
from llm_service import llm_service

app = FastAPI(title="SmartMonitor AI Chatbot API", version="1.0.0")

class ChatRequest(BaseModel):
    query: str
    user_id: Optional[str] = "default_user"

class ChatResponse(BaseModel):
    query: str
    intent: str
    context_data: Dict[str, Any]
    response: str

@app.get("/")
def read_root():
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return {"status": "online", "message": "SmartMonitor AI Assistant Service is Running."}

@app.post("/api/v1/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
        
    intent, context_data = route_query(request.query)
    
    answer = llm_service.generate_response(
        query=request.query, 
        intent=intent, 
        context_data=context_data, 
        user_id=request.user_id
    )
    
    return ChatResponse(
        query=request.query,
        intent=intent,
        context_data=context_data,
        response=answer
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)