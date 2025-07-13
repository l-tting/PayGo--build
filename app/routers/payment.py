from fastapi import APIRouter,status,Depends,HTTPException
from app import schemas,models
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.database import get_db
from app.daraja import stk_push_sender,get_access_token,process_stk_push_callback,check_transaction_status,format_phone_number

router = APIRouter()


@router.post('/', response_model=schemas.STK_PushResponse)
async def stk_push(transaction: schemas.STK_PushCreate, db: Session = Depends(get_db)):
    try:
        token = get_access_token()

        formatted_number = format_phone_number(transaction.phone_number)

        # Use a dynamic or provided account reference
        account_reference = f"ACC_{formatted_number[-4:]}_{transaction.amount}"

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
                    account_reference=account_reference,  # ✅ Added here
                    status=models.MPESAStatus.PENDING  
                )
                db.add(mpesa_tx)
                db.commit()
                db.refresh(mpesa_tx)

                return {
                    "checkout_request_id": response["CheckoutRequestID"],
                    "merchant_request_id": response["MerchantRequestID"],
                    "account_reference": account_reference,  # ✅ Include in response
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
async def stk_push_callback(callback_data: schemas.MpesaCallback,db: Session = Depends(get_db)):
    return await process_stk_push_callback(callback_data, db)


