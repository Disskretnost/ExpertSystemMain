import hashlib
import secrets
import base64
from datetime import datetime
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import fetch_one, execute_query

SECRET_KEY = "your-secret-key-change-in-production"
security = HTTPBearer()

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return salt + ":" + hashlib.sha256((password + salt).encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    salt, hash_value = password_hash.split(":")
    return hash_value == hashlib.sha256((password + salt).encode()).hexdigest()

def create_token(user_id: int, username: str) -> str:
    data = f"{user_id}:{username}:{datetime.now().timestamp()}"
    signature = hashlib.sha256((data + SECRET_KEY).encode()).hexdigest()
    return base64.urlsafe_b64encode(f"{data}|{signature}".encode()).decode()

def verify_token(token: str):
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        data, signature = decoded.rsplit("|", 1)
        expected = hashlib.sha256((data + SECRET_KEY).encode()).hexdigest()
        if signature == expected:
            parts = data.split(":")
            return {"user_id": int(parts[0]), "username": parts[1]}
    except:
        pass
    return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_data = verify_token(credentials.credentials)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_data