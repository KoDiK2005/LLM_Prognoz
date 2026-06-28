from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.rate_limit import RateLimitExceeded, check_rate_limit

_bearer_scheme = HTTPBearer()


def rate_limiter(action: str, limit: int, window_seconds: int) -> Callable[[Request], Coroutine[Any, Any, None]]:
    """Per-client-IP fixed-window rate limit, for unauthenticated endpoints
    (login/register) where there's no user id yet to key on.
    """

    async def _check(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        try:
            await check_rate_limit(f"ratelimit:{action}:{client_ip}", limit, window_seconds)
        except RateLimitExceeded as exc:
            raise HTTPException(
                status_code=429, detail="Too many requests, please try again later"
            ) from exc

    return _check


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
