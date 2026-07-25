"""Shared FastAPI dependencies: database session, current user, role checks."""

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import security
from app.models import RoleName, User

# tokenUrl tells Swagger UI where its "Authorize" button should POST the form.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One database session per request, closed when the request ends."""
    async with request.app.state.db_sessions() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    session: DbSession,
) -> User:
    """Resolve the Bearer token to a live User row, or 401.

    The database lookup (not just trusting the token's claims) means a
    deactivated or deleted user is locked out immediately, not at token expiry.
    """
    credentials_error = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = security.decode_token(token, request.app.state.settings.jwt_secret)
    except jwt.PyJWTError:
        raise credentials_error from None
    if payload.get("type") != "access":  # a refresh token must not grant API access
        raise credentials_error

    result = await session.execute(
        select(User)
        .options(selectinload(User.role))
        .where(User.id == uuid.UUID(payload["sub"]), User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed: RoleName):
    """Endpoint guard: Depends(require_roles(RoleName.ADMIN, ...)) -> 403 otherwise."""

    async def checker(user: CurrentUser) -> User:
        if user.role.name not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted for your role")
        return user

    return checker
