"""Password reset endpoints — 3-step flow."""
import logging
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.password_reset import request_reset, verify_code, reset_password
from ..db.engine import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class VerifyCodeIn(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class VerifyCodeOut(BaseModel):
    reset_token: str


class ResetPasswordIn(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=12, max_length=200)


@router.post("/password-reset/request", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(
    body: ForgotPasswordIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    ip = request.client.host if request.client else "?"
    existed, _ = await request_reset(session, body.email)
    logger.info(f"AUDIT PASSWORD_RESET_REQUESTED email={body.email} existed={existed} ip={ip}")


@router.post("/password-reset/verify", response_model=VerifyCodeOut)
async def verify_reset_code(
    body: VerifyCodeIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    ip = request.client.host if request.client else "?"
    token = await verify_code(session, body.email, body.code)
    if not token:
        logger.warning(f"AUDIT PASSWORD_RESET_CODE_INVALID email={body.email} ip={ip}")
        raise HTTPException(status_code=400, detail="Code invalide ou expiré.")
    logger.info(f"AUDIT PASSWORD_RESET_CODE_VERIFIED email={body.email} ip={ip}")
    return VerifyCodeOut(reset_token=token)


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password_endpoint(
    body: ResetPasswordIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    ip = request.client.host if request.client else "?"
    ok = await reset_password(session, body.reset_token, body.new_password)
    if not ok:
        logger.warning(f"AUDIT PASSWORD_RESET_FAILED ip={ip}")
        raise HTTPException(status_code=400, detail="Token invalide ou expiré.")
    logger.info(f"AUDIT PASSWORD_RESET_COMPLETED ip={ip}")
