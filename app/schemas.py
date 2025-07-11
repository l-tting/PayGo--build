from pydantic import BaseModel

class UserCreate(BaseModel):
    full_name:str
    email:str
    phone_number:str
    password:str

class UserLogin(BaseModel):
    email:str
    password:str