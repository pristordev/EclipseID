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
    access_level = Column(Integer, default=1)

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
  
class StatsHistory(Base):
    """История статистики для графиков"""
    __tablename__ = "stats_history"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_at = Column(DateTime, server_default=func.now(), index=True)

    citizens_count = Column(Integer, default=0)
    isb_employees_count = Column(Integer, default=0)
    awards_granted_count = Column(Integer, default=0)
    total_reputation = Column(Integer, default=0)
    api_requests = Column(Integer, default=0)

  # =============================================
#  АЛГОРИТМЫ (РАБОЧИЕ ЗАДАЧИ)
# =============================================

class Algorithm(Base):
    """Алгоритм — рабочая задача от Куратора"""
    __tablename__ = "algorithms"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(20), unique=True, nullable=False, index=True)  # ALG-000001
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Тип задачи: mining / building / sorting
    task_type = Column(String(20), nullable=False)

    # Область: public / personal
    scope = Column(String(20), default="public")

    # Статус: open / in_progress / review / completed / rejected / expired
    status = Column(String(20), default="open", index=True)

    # Дедлайн обязателен
    deadline = Column(DateTime, nullable=False, index=True)

    # Награда
    reward_reputation = Column(Integer, default=0)   # сколько репутации дать
    # reward_money — позже, когда сделаем экономику

    # Кто создал (Куратор)
    created_by = Column(Integer, ForeignKey('citizens.id'), nullable=False, index=True)

    # Максимум участников (для public)
    max_participants = Column(Integer, default=5)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Связи
    creator = relationship("Citizen", foreign_keys=[created_by])
    participants = relationship("AlgorithmParticipant", back_populates="algorithm", cascade="all, delete-orphan")
    attachments = relationship("AlgorithmAttachment", back_populates="algorithm", cascade="all, delete-orphan")


class AlgorithmParticipant(Base):
    """Участник алгоритма"""
    __tablename__ = "algorithm_participants"

    id = Column(Integer, primary_key=True, index=True)
    algorithm_id = Column(Integer, ForeignKey('algorithms.id'), nullable=False, index=True)
    citizen_id = Column(Integer, ForeignKey('citizens.id'), nullable=False, index=True)

    # Статус: assigned / submitted / approved / rejected
    status = Column(String(20), default="assigned", index=True)

    # Когда назначен / сдал
    assigned_at = Column(DateTime, server_default=func.now())
    submitted_at = Column(DateTime, nullable=True)

    # Отчёт
    report_text = Column(Text, nullable=True)

    # Оценка куратора
    stars = Column(Integer, nullable=True)        # 1..5
    feedback = Column(Text, nullable=True)         # комментарий куратора
    reviewed_at = Column(DateTime, nullable=True)

    # Связи
    algorithm = relationship("Algorithm", back_populates="participants")
    citizen = relationship("Citizen", foreign_keys=[citizen_id])
    report_attachments = relationship("AlgorithmReportAttachment", back_populates="participant", cascade="all, delete-orphan")


class AlgorithmAttachment(Base):
    """Вложение к алгоритму (от куратора)"""
    __tablename__ = "algorithm_attachments"

    id = Column(Integer, primary_key=True, index=True)
    algorithm_id = Column(Integer, ForeignKey('algorithms.id'), nullable=False, index=True)

    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    file_type = Column(String(20), default="file")  # image / file
    file_size = Column(Integer, default=0)

    uploaded_by = Column(Integer, ForeignKey('citizens.id'), nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now())

    algorithm = relationship("Algorithm", back_populates="attachments")


class AlgorithmReportAttachment(Base):
    """Вложение к отчёту участника"""
    __tablename__ = "algorithm_report_attachments"

    id = Column(Integer, primary_key=True, index=True)
    participant_id = Column(Integer, ForeignKey('algorithm_participants.id'), nullable=False, index=True)

    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    file_type = Column(String(20), default="image")  # image / file
    file_size = Column(Integer, default=0)

    uploaded_at = Column(DateTime, server_default=func.now())

    participant = relationship("AlgorithmParticipant", back_populates="report_attachments")

  # =============================================
#  ИСБ · СЕКТОРА
# =============================================

class ISBSector(Base):
    """Сектор — зона ответственности ИСБ"""
    __tablename__ = "isb_sectors"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    center_x = Column(Integer, default=0)
    center_z = Column(Integer, default=0)

    threat_level = Column(Integer, default=1)  # 1-5
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, server_default=func.now())

    assignments = relationship("ISBSectorAssignment", back_populates="sector", cascade="all, delete-orphan")


class ISBSectorAssignment(Base):
    """Назначение сотрудника на сектор"""
    __tablename__ = "isb_sector_assignments"

    id = Column(Integer, primary_key=True, index=True)
    sector_id = Column(Integer, ForeignKey('isb_sectors.id'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('isb_employees.id'), nullable=False, index=True)

    assigned_at = Column(DateTime, server_default=func.now())
    is_leader = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    sector = relationship("ISBSector", back_populates="assignments")
    employee = relationship("ISBEmployee")


# =============================================
#  ИСБ · ЛОГИ СОБЫТИЙ
# =============================================

class ISBLog(Base):
    """Лог событий ИСБ"""
    __tablename__ = "isb_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    severity = Column(String(20), default="info", index=True)  # info / warning / critical
    category = Column(String(50), nullable=True, index=True)   # patrol / arrest / search / system / order

    message = Column(Text, nullable=False)
    actor_id = Column(Integer, ForeignKey('citizens.id'), nullable=True)
    sector_id = Column(Integer, ForeignKey('isb_sectors.id'), nullable=True)

    meta = Column(Text, nullable=True)  # JSON или свободный текст

    actor = relationship("Citizen", foreign_keys=[actor_id])
    sector = relationship("ISBSector")