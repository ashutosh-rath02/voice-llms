from datetime import timedelta
from typing import Annotated

import jwt
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core import security
from app.models import Role, RoleName, User
from app.schemas.auth import RefreshRequest, SignupRequest, TokenPair, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
log = structlog.get_logger()

# Redis keyspace for still-valid refresh tokens (value: user id, TTL: token exp).
REFRESH_KEY = "auth:refresh:{jti}"


async def _issue_token_pair(request: Request, user: User) -> TokenPair:
    """Mint access+refresh tokens and register the refresh jti in Redis.

    Only refresh tokens are tracked server-side. Access tokens stay stateless
    and short-lived (30 min): revoking a user takes effect on their next
    refresh, without a Redis round-trip on every API call.
    """
    settings = request.app.state.settings
    access_token, _ = security.create_token(
        user_id=user.id,
        role=user.role.name,
        token_type="access",
        lifetime=timedelta(minutes=settings.access_token_expire_minutes),
        secret=settings.jwt_secret,
    )
    refresh_lifetime = timedelta(days=settings.refresh_token_expire_days)
    refresh_token, refresh_jti = security.create_token(
        user_id=user.id,
        role=user.role.name,
        token_type="refresh",
        lifetime=refresh_lifetime,
        secret=settings.jwt_secret,
    )
    await request.app.state.redis.set(
        REFRESH_KEY.format(jti=refresh_jti), str(user.id), ex=refresh_lifetime
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, session: DbSession) -> UserOut:
    """Open registration always creates a CUSTOMER; staff roles are granted
    by an admin, never self-assigned."""
    role_id = (
        await session.execute(select(Role.id).where(Role.name == RoleName.CUSTOMER))
    ).scalar_one()
    user = User(
        email=body.email.lower(),
        hashed_password=security.hash_password(body.password),
        full_name=body.full_name,
        role_id=role_id,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An account with this email already exists"
        ) from exc
    log.info("user_signed_up", user_id=str(user.id))
    return UserOut(id=user.id, email=user.email, full_name=user.full_name, role=RoleName.CUSTOMER)


@router.post("/login", response_model=TokenPair)
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: DbSession,
) -> TokenPair:
    result = await session.execute(
        select(User)
        .options(selectinload(User.role))
        .where(User.email == form.username.lower(), User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None:
        # Burn the same hashing time as a real check — see security.DUMMY_HASH.
        security.verify_password(form.password, security.DUMMY_HASH)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not security.verify_password(form.password, user.hashed_password) or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    log.info("user_logged_in", user_id=str(user.id))
    return await _issue_token_pair(request, user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(request: Request, body: RefreshRequest, session: DbSession) -> TokenPair:
    """Rotate the refresh token: each one is single-use.

    GETDEL is atomic, so a stolen-and-replayed refresh token loses the race —
    whichever request arrives second gets a 401.
    """
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    settings = request.app.state.settings
    try:
        payload = security.decode_token(body.refresh_token, settings.jwt_secret)
    except jwt.PyJWTError:
        # from None: the JWT library's reason (bad signature vs expired) is
        # deliberately not chained — clients get one uniform 401.
        raise invalid from None
    if payload.get("type") != "refresh":
        raise invalid

    user_id = await request.app.state.redis.getdel(REFRESH_KEY.format(jti=payload["jti"]))
    if user_id is None:
        raise invalid

    result = await session.execute(
        select(User)
        .options(selectinload(User.role))
        .where(User.id == payload["sub"], User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise invalid
    return await _issue_token_pair(request, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, body: RefreshRequest) -> None:
    """Revoke the refresh token. Idempotent: an already-invalid token still
    yields 204 — logout never fails, and responses don't leak token validity."""
    settings = request.app.state.settings
    try:
        payload = security.decode_token(body.refresh_token, settings.jwt_secret)
    except jwt.PyJWTError:
        return
    if payload.get("type") == "refresh":
        await request.app.state.redis.delete(REFRESH_KEY.format(jti=payload["jti"]))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.from_user(user)
