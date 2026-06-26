from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class Organization(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="free")

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="organization")
