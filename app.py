import uuid
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.pipeline import ChatPipeline
from src.database import SessionLocal, init_db, UserForm

# Initialize database
init_db()

# Initialize FastAPI app
app = FastAPI(title="Kerajaan Agency Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ChatPipeline
pipeline = ChatPipeline()

# Ensure static directory exists
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Models
class SessionCreateRequest(BaseModel):
    customer_name: str
    customer_phone: str

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: str
    show_cta: bool = False
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    is_fallback: bool = False
    rag_sources: Optional[List[str]] = None

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/api/session")
async def get_session(x_session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    session_id = x_session_id
    if not session_id:
        return {"authenticated": False}
        
    db = SessionLocal()
    try:
        user_form = db.query(UserForm).filter(UserForm.session_id == session_id).first()
        if user_form:
            return {
                "authenticated": True,
                "user": {
                    "id": user_form.id,
                    "name": user_form.name,
                    "phone": user_form.phone
                }
            }
    finally:
        db.close()
        
    return {"authenticated": False}

@app.post("/api/session/new")
async def new_session(request: SessionCreateRequest):
    db = SessionLocal()
    try:
        existing_user = db.query(UserForm).filter(UserForm.phone == request.customer_phone).first()
        
        if existing_user:
            session_id = existing_user.session_id
            session = pipeline.conv_manager.get_session(session_id)
            session["customer_name"] = existing_user.name
            session["customer_phone"] = existing_user.phone
        else:
            session_id = str(uuid.uuid4())
            session = pipeline.conv_manager.get_session(session_id)
            session["customer_name"] = request.customer_name
            session["customer_phone"] = request.customer_phone
            
            new_form = UserForm(
                session_id=session_id,
                name=request.customer_name,
                phone=request.customer_phone
            )
            db.add(new_form)
            db.commit()
            
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        print(f"[ERROR] Saving user form: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()

@app.post("/api/logout")
async def logout():
    return {"authenticated": False}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, x_session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    session_id = x_session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        
    db = SessionLocal()
    try:
        response = pipeline.chat(
            user_message=request.message,
            session_id=session_id,
            db=db
        )
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
