"""Request/response bodies for the auth endpoints.

Pydantic schemas are the API contract; ORM models are storage. Keeping them
separate means the database can change without breaking clients — and fields
like hashed_password can never leak into a response by accident.
"""

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models import User


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str

    @classmethod
    def from_user(cls, user: User) -> "UserOut":
        # role is flattened to its name; clients never see the roles table shape.
        return cls(id=user.id, email=user.email, full_name=user.full_name, role=user.role.name)
