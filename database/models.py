from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    BigInteger, ARRAY, ForeignKey, Table, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.db import Base


# =============================================
#  РОЛИ И ПРАВА
# =============================================

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id')),
    Column('permission_id', Integer, ForeignKey('permissions.id'))
)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    level = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


# =============================================
#  ГРАЖДАНЕ
# =============================================

class Citizen(Base):
    __tablename__ = "citizens"

    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=False)
    minecraft_uuid = Column(String(36), unique=True, nullable=True, index=True)

    role_ids = Column(ARRAY(Integer), default=[1])
    main_role_id = Column(Integer, ForeignKey('roles.id'), nullable=True)

    reputation = Column(Integer, default=0)
    citizenship_date = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    main_role = relationship("Role", foreign_keys=[main_role_id])
    isb_employee = relationship("ISBEmployee", back_populates="citizen", uselist=False)


# =============================================
#  ИСБ — СОТРУДНИКИ
# =============================================

class ISBEmployee(Base):
    __tablename__ = "isb_employees"

    id = Column(Integer, primary_key=True, index=True)
    citizen_id = Column(Integer, ForeignKey('citizens.id'), unique=True, nullable=False, index=True)

    service_number = Column(String(20), unique=True, nullable=False, index=True)
    rank_name = Column(String(100), nullable=False)
    rank_short = Column(String(20), nullable=True)
    branch = Column(String(20), nullable=False)
    level = Column(Integer, default=0)

    position = Column(String(100), nullable=True)
    enlisted_at = Column(DateTime, server_default=func.now())
    promoted_at = Column(DateTime, nullable=True)
    discharged_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    can_arrest = Column(Boolean, default=False)
    can_conduct_searches = Column(Boolean, default=False)
    can_issue_warrants = Column(Boolean, default=False)
    can_command = Column(Boolean, default=False)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    citizen = relationship("Citizen", back_populates="isb_employee")


# =============================================
#  ИСБ — НАГРАДЫ
# =============================================

class ISBAward(Base):
    __tablename__ = "isb_awards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(20), nullable=True)
    rarity = Column(String(20), default="common")
    category = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class ISBAwardGrant(Base):
    __tablename__ = "isb_award_grants"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('isb_employees.id'), nullable=False, index=True)
    award_id = Column(Integer, ForeignKey('isb_awards.id'), nullable=False, index=True)
    granted_at = Column(DateTime, server_default=func.now())
    granted_by = Column(Integer, ForeignKey('citizens.id'), nullable=True)
    reason = Column(Text, nullable=True)

    award = relationship("ISBAward")
