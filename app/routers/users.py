from fastapi import APIRouter,status,Depends,HTTPException
from werkzeug.security import generate_password_hash,check_password_hash
from app.schemas import UserCreate,UserLogin
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

router = APIRouter()


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_admin(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Admin already exists")

    hashed_password = generate_password_hash(user.password)
    new_admin = User(
        full_name=user.full_name,
        email=user.email,
        admin_phone=admin.admin_phone,
        password=hashed_password,
      
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return {"message": "Admin created successfully"}