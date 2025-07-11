from app.database import Base
from sqlalchemy import Column,String,ForeignKey,Integer,func, DateTime,Enum, JSON
from sqlalchemy.orm import relationship
import enum


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255),nullable=False)
    email = Column(String(255),unique=True,nullable=False)
    phone_number = Column(String(15),nullable=False)
    password = Column(String(255),nullable=False)


class MPESAStatus(str, enum.Enum):
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    TIMEOUT = 'timeout'


class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer,primary_key=True,nullable=False)
    phone_number = Column(String(15), nullable=False)
    amount = Column(Integer, nullable=False)
    account_reference = Column(String(50), nullable=False, unique=True)
    description = Column(String(255),default="Product Purchase")
    checkout_request_id = Column(String(100), unique=True)
    merchant_request_id = Column(String(100))
    response_code = Column(String(10))
    response_description = Column(String)
    status = Column(String(20), default='PENDING')
    mpesa_receipt_number = Column(String(50))
    transaction_date = Column(DateTime)
    callbacks = relationship("MpesaCallback", back_populates="payment", cascade="all, delete-orphan")


class MpesaCallback(Base):
    __tablename__ = "mpesa_callbacks"

    id = Column(Integer, primary_key=True)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"))
    callback_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship back to Payment
    payment = relationship("Payment", back_populates="callbacks")

