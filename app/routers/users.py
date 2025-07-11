from fastapi import APIRouter,status,Depends,HTTPException,Response
from werkzeug.security import generate_password_hash,check_password_hash
from app.schemas import UserCreate,UserLogin
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from app.database import get_db
from app.models import User
from app.auth import create_access_token
from datetime import timedelta

router = APIRouter()


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_admin(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Admin already exists")

    hashed_password = generate_password_hash(user.password)
    new_user = User(
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        password=hashed_password,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Admin created successfully"}

@router.post("/login", status_code=status.HTTP_200_OK)
def login_user(user_login: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email== user_login.email).first()
    
    if user is None or not check_password_hash(user.password, user_login.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(
        data={"user": user_login.email}, 
        expires_delta=timedelta(days=30)
    )
    print("Access token:", access_token)
    
    response = JSONResponse(
        content={"message": "Login successful", "current_user": user.full_name}
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=30 * 24 * 60 * 60, 
        expires=30 * 24 * 60 * 60,
        samesite="Lax",             
        secure=False                
    )
    return response



@router.post("/logout", status_code=status.HTTP_200_OK)
def logout_user(response: Response):
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="Lax",  
        secure=False     # Set to True for HTTPS
    )
    return {"message": "Successfully logged out"}




