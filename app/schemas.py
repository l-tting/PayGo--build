from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    full_name:str
    email:str
    phone_number:str
    password:str

class UserLogin(BaseModel):
    email:str
    password:str

class MpesaCallback(BaseModel):
    merchant_request_id: str
    checkout_request_id: str
    result_code: str
    result_desc: str
    mpesa_receipt_number: Optional[str] = None
    transaction_date: Optional[datetime] = None

class STK_PushCreate(BaseModel):
    phone_number:str
    amount: float


class STK_PushResponse(BaseModel):
    merchant_request_id:str
    checkout_request_id:str
    status:str
    response_code:str='0'
    response_desc:str='Success. Request accepted for processing'
    customer_message: str = "Please check your phone to complete the payment" 


class STKPushCheckResponse(BaseModel):
    success: bool
    message: str
    status: Optional[str] = None

class UserReset(BaseModel):
    old_password:str
    new_password:str

class ResetResponse(BaseModel):
    message:str