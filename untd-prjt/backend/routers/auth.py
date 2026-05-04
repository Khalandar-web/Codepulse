from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserCreds(BaseModel):
    username: str
    password: str

class TokenCheck(BaseModel):
    token: str

@router.post("/register")
def register(creds: UserCreds):
    if not creds.username or not creds.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    if len(creds.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(creds.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
    result = db.create_user(creds.username, creds.password)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
        
    # Auto login after register
    token = db.create_session(result["user_id"])
    return {"message": "Registration successful", "token": token, "username": creds.username}

@router.post("/login")
def login(creds: UserCreds):
    result = db.verify_user(creds.username, creds.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
        
    token = db.create_session(result["user"]["id"])
    return {"message": "Login successful", "token": token, "username": creds.username}

@router.post("/verify")
def verify(data: TokenCheck):
    result = db.verify_session(data.token)
    if not result["valid"]:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
        
    return {"valid": True, "username": result["username"]}
