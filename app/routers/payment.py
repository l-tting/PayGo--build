from fastapi import APIRouter,HTTPException
from base64 import b64encode
from sqlalchemy.orm import Session
import requests
from datetime import datetime
import httpx
from app import schemas,models


router = APIRouter()

consumer_key = 'cjFxSqo6QiLhEYPHAU8zAntSCtPeIUzvQ53JQKzYiocpOhnr'
consumer_secret = 'yMNsUbahjfAZjVF1lcsgwWGHbVLjiE5xV96BJhMA8MOmvVvVeAqFzGYmzX0JtCua'
pass_key = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
saf_url = "https://sandbox.safaricom.co.ke/"
short_code = '174379'
callback_url = 'https://oneshop.co.ke/stk_callback'

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
