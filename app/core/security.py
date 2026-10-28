
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from app.core.config import settings
password_hash=PasswordHash.recommended()
SECRET_KEY = settings.JWT_SECRET_KEY

if not SECRET_KEY:
 raise RuntimeError("JWT_SECRET_KEY is missing. Add it to your environment variable")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def hash_password(password:str)->str:
 return password_hash.hash(password)

def verify_password(plain_password:str,hashed_password:str)->bool:
 return password_hash.verify(plain_password,hashed_password)

def create_access_token(user_id:str)->str:
 expires_at = datetime.now(timezone.utc)+timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
 payload={
  "sub":user_id,
  "exp":expires_at,
  "jti":secrets.token_urlsafe(16)
 }
 return jwt.encode(payload,SECRET_KEY,algorithm=ALGORITHM)

def decode_access_token(token:str)->dict:
 payload=jwt.decode(
  token,
  SECRET_KEY,
  algorithms=[ALGORITHM]
 )
 return payload