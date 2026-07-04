from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from .address_schema import AddressPublic


class CreateUserSchema(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    role: str
    is_verified: bool = False
    shop_name: Optional[str] = None
    shop_latitude: Optional[float] = None
    shop_longitude: Optional[float] = None
    shop_district: Optional[str] = None
    shop_zone: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class TokenSchema(BaseModel):
    token: str
    token_type: str


class LoginResponse(BaseModel):
    token: str
    token_type: str
    refresh_token: str
    user: UserPublic


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    token: str
    token_type: str
    refresh_token: str


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    role: str
    is_verified: bool = False
    shop_name: Optional[str] = None
    shop_latitude: Optional[float] = None
    shop_longitude: Optional[float] = None
    shop_district: Optional[str] = None
    shop_zone: Optional[str] = None
    addresses: list[AddressPublic] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpdateUserSchema(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    shop_name: Optional[str] = Field(None, max_length=200)
    shop_latitude: Optional[float] = None
    shop_longitude: Optional[float] = None
    shop_district: Optional[str] = Field(None, max_length=100)
    shop_zone: Optional[str] = Field(None, max_length=100)

    model_config = {"from_attributes": True}


class RegisterResponse(BaseModel):
    message: str = "Registration successful. Please check your email to verify your account."


class VerificationStatus(BaseModel):
    valid: bool
    verified: bool


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class DeleteUserResponseModel(BaseModel):
    detail: str
