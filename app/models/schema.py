from sqlalchemy import Table, Column, String, Integer, Numeric, Boolean, Time, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# =====================================================================
# MANY-TO-MANY LINKING TABLES
# =====================================================================

# Links Menu Periods (Shifts) to specific purchasable SKUs
menu_period_skus = Table(
    "menu_period_skus",
    Base.metadata,
    Column("menu_period_id", ForeignKey("menu_periods.id", ondelete="CASCADE"), primary_key=True),
    Column("sku_id", ForeignKey("skus.id", ondelete="CASCADE"), primary_key=True)
)


# =====================================================================
# SYSTEM CORE CORE ORGANIZATIONAL MODEL
# =====================================================================

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    org_code = Column(String, unique=True, nullable=False)
    name_en = Column(String, nullable=False)
    name_ar = Column(String, nullable=False)
    legal_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    branches = relationship("Branch", back_populates="organization", cascade="all, delete-orphan")


class Branch(Base):
    __tablename__ = "branches"

    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)
    branch_code = Column(String, unique=True, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    name_en = Column(String, nullable=False)
    name_ar = Column(String, nullable=False)
    timezone = Column(String, default="Asia/Riyadh", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="branches")
    menu_periods = relationship("MenuPeriod", back_populates="branch", cascade="all, delete-orphan")


# =====================================================================
# MENU MATRIX CATALOG MODEL (DECOUPLED PRODUCTS & SKUS)
# =====================================================================

class Category(Base):
    __tablename__ = "categories"

    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    category_code = Column(String, unique=True, nullable=False)
    slug = Column(String, nullable=False)
    name_en = Column(String, nullable=False)
    name_ar = Column(String, nullable=False)
    name_ur = Column(String, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    category_id = Column(String, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    product_code = Column(String, unique=True, nullable=False)
    name_en = Column(String, nullable=False)
    name_ar = Column(String, nullable=False)
    name_ur = Column(String, nullable=False)
    description_en = Column(String, nullable=True)
    description_ar = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    category = relationship("Category", back_populates="products")
    skus = relationship("Sku", back_populates="product", cascade="all, delete-orphan")


class Sku(Base):
    __tablename__ = "skus"

    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    product_id = Column(String, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    sku_code = Column(String, unique=True, nullable=False)
    portion_size_en = Column(String, nullable=False)
    portion_size_ar = Column(String, nullable=False)
    portion_size_ur = Column(String, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    product = relationship("Product", back_populates="skus")
    prices = relationship("SkuPrice", back_populates="sku", cascade="all, delete-orphan")
    menu_periods = relationship("MenuPeriod", secondary=menu_period_skus, back_populates="skus")


# =====================================================================
# PRICING MATRIX & SHIFT OPERATIONS CHANNELS
# =====================================================================

class SkuPrice(Base):
    __tablename__ = "sku_prices"

    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    sku_id = Column(String, ForeignKey("skus.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(String, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    channel = Column(String, default="WHATSAPP", nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    effective_from = Column(DateTime(timezone=True), nullable=False)
    effective_to = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    sku = relationship("Sku", back_populates="prices")


class MenuPeriod(Base):
    __tablename__ = "menu_periods"

    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    branch_id = Column(String, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    menu_period_code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)

    # Relationships
    branch = relationship("Branch", back_populates="menu_periods")
    schedules = relationship("MenuSchedule", back_populates="menu_period", cascade="all, delete-orphan")
    skus = relationship("Sku", secondary=menu_period_skus, back_populates="menu_periods")


class MenuSchedule(Base):
    __tablename__ = "menu_schedules"

    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    menu_period_id = Column(String, ForeignKey("menu_periods.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0 (Sunday) to 6 (Saturday)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    # Relationships
    menu_period = relationship("MenuPeriod", back_populates="schedules")