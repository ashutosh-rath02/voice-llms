import enum
import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum


class ContactType(enum.StrEnum):
    EMAIL = "email"
    PHONE = "phone"


class CustomerProductStatus(enum.StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Customer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A real support customer — distinct from `users` (platform logins).

    A customer need not have a login (a phone caller in Phase 4 may never
    create an account); `user_id` links the two only when a logged-in web
    user has a matching support profile.
    """

    __tablename__ = "customers"

    full_name: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), unique=True, index=True
    )

    contacts: Mapped[list["CustomerContact"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    products: Mapped[list["CustomerProduct"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )


class CustomerContact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One contact method. Plural per customer — PRD 6.9 requires confirmation
    before sending to a *new* destination, which implies contacts are a
    managed list, not a single fixed field."""

    __tablename__ = "customer_contacts"
    __table_args__ = (UniqueConstraint("contact_type", "value"),)

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    contact_type: Mapped[ContactType] = mapped_column(str_enum(ContactType))
    value: Mapped[str] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(default=False)

    customer: Mapped[Customer] = relationship(back_populates="contacts")


class ProductOrService(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Catalog entry for a supportable device/integration (our domain's
    equivalent of a product SKU)."""

    __tablename__ = "products_or_services"

    name: Mapped[str] = mapped_column(String(255), unique=True)
    category: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text)

    customer_links: Mapped[list["CustomerProduct"]] = relationship(back_populates="product")


class CustomerProduct(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A specific device a customer has registered — what the agent looks up
    to answer 'what do I own' and scope troubleshooting."""

    __tablename__ = "customer_products"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products_or_services.id"))
    identifier: Mapped[str | None] = mapped_column(String(255))  # serial/device name, if any
    status: Mapped[CustomerProductStatus] = mapped_column(
        str_enum(CustomerProductStatus), default=CustomerProductStatus.ACTIVE
    )

    customer: Mapped[Customer] = relationship(back_populates="products")
    product: Mapped[ProductOrService] = relationship(back_populates="customer_links")
