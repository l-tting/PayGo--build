from fastapi import APIRouter,HTTPException
from base64 import b64encode
from sqlalchemy.orm import Session
import requests
from datetime import datetime
import httpx
from app import schemas,models
from app.models import Payment
import os
from dotenv import load_dotenv
import pytz


router = APIRouter()

load_dotenv()


consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
pass_key = os.getenv("PASS_KEY")
short_code = os.getenv("SHORT_CODE")
callback_url = os.getenv("CALLBACK_URL")
saf_url = os.getenv("SAF_URL")



def format_phone_number(phone: str) -> str:
    if phone.startswith("0"):
        return "254" + phone[1:]
    elif phone.startswith("+"):
        return phone[1:]
    return phone



def get_access_token():
   
    try:
        if not consumer_key or not consumer_secret:
            raise ValueError("CONSUMER_KEY or CONSUMER_SECRET not set")

        credentials = f"{consumer_key}:{consumer_secret}"
        encoded_credentials = b64encode(credentials.encode()).decode()
        print(f"Encoded Credentials: {encoded_credentials}") 

        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }

        url = f"{saf_url}oauth/v1/generate?grant_type=client_credentials"
        
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            print(f"Response body: {response.text}")  
            raise Exception(f"Auth failed: {response.status_code} - {response.text}")

        json_response = response.json()
        
        access_token = json_response.get("access_token")
        if not access_token:
            raise Exception(f"No access token found in the response: {json_response}")
        return access_token
    
    except Exception as e:
        print(f"Error getting access token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get access token: {str(e)}")
    

async def stk_push_sender(mobile:str, amount:float, access_token:str):
    try:

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        stk_password = b64encode((short_code + pass_key + timestamp).encode('utf-8')).decode()

        url = f"{saf_url}mpesa/stkpush/v1/processrequest"
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}

        request = {
            "BusinessShortCode": str(short_code),
            "Password": stk_password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": str(mobile),
            "PartyB": str(short_code),
            "PhoneNumber": str(mobile),
            "CallBackURL": callback_url,
            "AccountReference": "myduka1",
            "TransactionDesc": "Testing STK Push"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=request, headers=headers)
        
        response.raise_for_status()  
       
        print("Raw response from MPESA:", response.text)
        return response.json()

    except httpx.RequestError as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Error occurred: {str(e)}"}
    


def check_transaction_status(merchant_request_id: str, checkout_request_id: str, db:Session):
    transaction = db.query(Payment).filter(
        models.Payment.merchant_request_id == merchant_request_id,
        models.Payment.checkout_request_id == checkout_request_id ).first()
    
    if not transaction:
         raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction



async def process_stk_push_callback(callback_data: schemas.MpesaCallback, db: Session):
    try:
        # Find the matching transaction using MerchantRequestID and CheckoutRequestID
        transaction = db.query(models.Payment).filter(
            models.Payment.merchant_request_id == callback_data.merchant_request_id,
            models.Payment.checkout_request_id == callback_data.checkout_request_id
        ).first()

        # If transaction is not found, raise 404
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # Handle failed payment
        if callback_data.result_code != "0":
            transaction.status = models.MPESAStatus.FAILED
            transaction.response_code = callback_data.result_code
            transaction.response_description = callback_data.result_desc
            db.commit()

            return {
                "status": "failure",
                "message": "Transaction failed",
                "result_code": callback_data.result_code,
                "result_desc": callback_data.result_desc
            }
        nairobi = pytz.timezone("Africa/Nairobi")

        if isinstance(callback_data.transaction_date, str):
            parsed_date = datetime.strptime(callback_data.transaction_date, "%Y%m%d%H%M%S")
        else:
            parsed_date = callback_data.transaction_date


        nairobi_time = nairobi.localize(parsed_date)

        # Handle successful payment
        transaction.status = models.MPESAStatus.COMPLETED
        transaction.response_code = callback_data.result_code
        transaction.response_description = callback_data.result_desc
        transaction.mpesa_receipt_number = callback_data.mpesa_receipt_number
        transaction.transaction_date = nairobi_time

        db.commit()

        return {
            "status": "success",
            "message": "Transaction completed",
            "result_code": callback_data.result_code,
            "result_desc": callback_data.result_desc,
            "mpesa_receipt_number": callback_data.mpesa_receipt_number,
            "transaction_date": callback_data.transaction_date
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing callback: {str(e)}")
