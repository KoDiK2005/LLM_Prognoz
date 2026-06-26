import uuid
from enum import Enum

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class UserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class User(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "users"

    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(String(20), nullable=False, default=UserRole.MEMBER)

    organization: Mapped["Organization"] = relationship(back_populates="users")
