from app.models import User
from app.database import sessionlocal
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError,ExpiredSignatureError
from fastapi import HTTPException,Request,Depends


JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


def check_admin(email):
    db = sessionlocal()
    user = db.query(User).filter(User.email==email).first()
    return user


def create_access_token(data:dict,expires_delta:timedelta | None=None):
    to_encode = data.copy()
    if expires_delta:
        expires = datetime.now(timezone.utc) + expires_delta
    else:
        expires = datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE_MINUTES
    to_encode.update({"exp":expires})
    encoded_jwt = jwt.encode(to_encode,JWT_SECRET_KEY,algorithm=JWT_ALGORITHM)
    return encoded_jwt


def get_token_from_cookie(request: Request) -> str:
    token = request.cookies.get("access_token")    
    if not token:
        print("No token")
        raise HTTPException(status_code=401, detail="Access token missing from cookies")
    return token


async def get_current_user(access_token: str = Depends(get_token_from_cookie)):
    try:
        payload = jwt.decode(access_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email = payload.get('user')
        if email is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = check_admin(email)
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")
    return user