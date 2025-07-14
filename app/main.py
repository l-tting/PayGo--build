from  fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import models
from app.database import engine
from app.routers import payment,users

app = FastAPI()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ad75cbd5dc8c.ngrok-free.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)

app.include_router(users.router,prefix='/users',tags=['users'])
app.include_router(payment.router,prefix='/payment',tags=['payment'])

@app.get('/')
def index():
    return {"message": "PayGo -Payments made easier"}