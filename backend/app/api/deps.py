"""Temporary stand-in for auth, used until the auth/multi-tenancy iteration.

get_current_user lazily creates a single dev organization + user so
foreign keys on datasets/forecast_runs resolve. Replace with real
session-based auth later; call sites only depend on getting a User back.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User

_DEV_EMAIL = "dev@local"


async def get_current_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == _DEV_EMAIL))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    org = Organization(name="Dev Org")
    db.add(org)
    await db.flush()

    user = User(org_id=org.id, email=_DEV_EMAIL, hashed_password="", role="owner")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
