from fastapi import APIRouter,status,Depends,HTTPException,Request
from app import schemas,models
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.database import get_db
from app.daraja import stk_push_sender,get_access_token,process_stk_push_callback,check_transaction_status,format_phone_number
from uuid import uuid4
from datetime import datetime


router = APIRouter()



@router.post('/test_token')
def test_token():
    token = get_access_token()
    return {"token":token}


@router.post('/', response_model=schemas.STK_PushResponse)
async def stk_push(transaction: schemas.STK_PushCreate, db: Session = Depends(get_db)):
    try:
        token = get_access_token()

        formatted_number = format_phone_number(transaction.phone_number)

        # Use a dynamic or provided account reference
        account_reference = f"ACC_{formatted_number[-4:]}_{transaction.amount}_{uuid4().hex[:6]}"

        response = await stk_push_sender(formatted_number, transaction.amount, token)

        print("Received STK Push data:", response)

        if 'CheckoutRequestID' in response:
            try:
                # Save the STK push response to the DB
                mpesa_tx = models.Payment(
                    checkout_request_id=response["CheckoutRequestID"],
                    merchant_request_id=response["MerchantRequestID"],
                    phone_number=transaction.phone_number,
                    amount=transaction.amount,
                    account_reference=account_reference,  
                    status=models.MPESAStatus.PENDING  
                )
                db.add(mpesa_tx)
                db.commit()
                db.refresh(mpesa_tx)

                return {
                    "checkout_request_id": response["CheckoutRequestID"],
                    "merchant_request_id": response["MerchantRequestID"],
                    "account_reference": account_reference,  
                    "status": "pending",
                    "response_code": "0",
                    "response_description": "Success. Request accepted for processing",
                    "customer_message": "Please check your phone to complete the payment"
                }

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error adding STK push to db: {e}")
        else:
            raise HTTPException(status_code=400, detail="Invalid response from MPESA")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"STK Push error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/checker", response_model=schemas.STKPushCheckResponse)
async def check_stk_push_status(merchant_request_id: str,checkout_request_id: str,db: Session = Depends(get_db)):
    transaction = check_transaction_status(merchant_request_id, checkout_request_id, db)
    
    if not transaction:
        return {
            "success": False,
            "message": "Transaction not found",
            "status": None
        }
    return {
            "success": transaction.status == models.MPESAStatus.COMPLETED,
           "message": f"Transaction {transaction.status}",
        "status": transaction.status
    }

   


@router.post("/callback")
async def stk_push_callback(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    print("🔔 Raw callback body received:", body)

    try:
        stk_callback = body["Body"]["stkCallback"]

        merchant_request_id = stk_callback.get("MerchantRequestID")
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")

        # Optional fields from CallbackMetadata
        metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])

        mpesa_receipt_number = None
        transaction_date = None
        phone_number = None
        amount = None

        for item in metadata:
            if item["Name"] == "MpesaReceiptNumber":
                mpesa_receipt_number = item["Value"]
            elif item["Name"] == "TransactionDate":
                transaction_date = item["Value"]
            elif item["Name"] == "PhoneNumber":
                phone_number = item["Value"]
            elif item["Name"] == "Amount":
                amount = item["Value"]

        # Save or update in DB
        transaction = db.query(models.Payment).filter(
            models.Payment.merchant_request_id == merchant_request_id,
            models.Payment.checkout_request_id == checkout_request_id
        ).first()

        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        if result_code != 0:
            transaction.status = models.MPESAStatus.FAILED
        else:
            transaction.status = models.MPESAStatus.COMPLETED

        transaction.response_code = str(result_code)
        transaction.response_description = result_desc
        transaction.mpesa_receipt_number = mpesa_receipt_number
        transaction.transaction_date = datetime.strptime(str(transaction_date), "%Y%m%d%H%M%S")
        db.commit()

        return {"ResultCode": 0, "ResultDesc": "Callback received successfully"}

    except Exception as e:
        print("⚠️ Error in callback processing:", e)
        db.rollback()
        return {"ResultCode": 1, "ResultDesc": "Callback processing failed"}


@router.get("/test")
async def test_payment_route():
    return {"message": "Payment route is working"}