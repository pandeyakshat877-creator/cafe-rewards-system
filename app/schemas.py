"""
Pydantic models for request/response validation.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator


class UserRole(str, Enum):
    customer = "customer"
    admin = "admin"


class TransactionType(str, Enum):
    earn = "earn"
    redeem = "redeem"


# ---------- Auth / OTP ----------

class UserRegister(BaseModel):
    """First-time signup: phone is the login identifier, email is required
    for notifications."""
    phone_number: str = Field(min_length=10, max_length=15)
    email: EmailStr
    full_name: str = Field(min_length=1)


class OTPRequest(BaseModel):
    """Used for both signup (after UserRegister) and returning-user login —
    always sends a fresh OTP to an existing phone_number."""
    phone_number: str = Field(min_length=10, max_length=15)


class OTPVerify(BaseModel):
    phone_number: str = Field(min_length=10, max_length=15)
    otp_code: str = Field(min_length=4, max_length=8)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None


# ---------- User ----------

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone_number: str
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    qr_code_id: str
    points_balance: int
    created_at: datetime


# ---------- Transaction ----------

class TransactionCreate(BaseModel):
    """Staff submits this from the admin dashboard after scanning the
    customer's QR code."""
    user_qr_code_id: str
    type: TransactionType
    amount_spent: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    points_to_redeem: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def check_fields_for_type(self):
        if self.type == TransactionType.earn and self.amount_spent is None:
            raise ValueError("amount_spent is required for an 'earn' transaction")
        if self.type == TransactionType.redeem and self.points_to_redeem is None:
            raise ValueError("points_to_redeem is required for a 'redeem' transaction")
        return self


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    staff_id: int
    type: TransactionType
    amount_spent: Decimal | None
    points_added: int
    points_deducted: int
    balance_after: int
    notification_sent: bool
    created_at: datetime