import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class UserRole(str, enum.Enum):
    customer = "customer"
    admin = "admin"

class TierLevel(str, enum.Enum):
    standard = "standard"
    platinum = "platinum"

class TransactionType(str, enum.Enum):
    earn = "earn"
    redeem = "redeem"
    expire = "expire"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=False)
    
    otp_code = Column(String, nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.customer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    qr_code_id = Column(String, unique=True, index=True, default=lambda: uuid.uuid4().hex)

    points_balance = Column(Integer, default=0, nullable=False)
    lifetime_spend = Column(Numeric(10, 2), default=0.00, nullable=False)
    tier = Column(Enum(TierLevel), default=TierLevel.standard, nullable=False)
    last_activity_date = Column(DateTime, default=datetime.utcnow, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan", foreign_keys="Transaction.user_id")
    notifications = relationship("NotificationOutbox", back_populates="user", cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    type = Column(Enum(TransactionType), nullable=False)
    amount_spent = Column(Numeric(10, 2), nullable=True)
    points_added = Column(Integer, default=0, nullable=False)
    points_deducted = Column(Integer, default=0, nullable=False)
    balance_after = Column(Integer, nullable=False)
    notification_sent = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="transactions", foreign_keys=[user_id])
    staff = relationship("User", foreign_keys=[staff_id])

class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    message = Column(String, nullable=False)
    is_sent = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="notifications")