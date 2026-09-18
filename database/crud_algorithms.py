"""CRUD-функции для работы с алгоритмами"""
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func as sql_func
from database.models import (
    Algorithm, AlgorithmParticipant,
    AlgorithmAttachment, AlgorithmReportAttachment,
    Citizen, Role
)
from typing import Optional, List, Dict, Any
from datetime import datetime


# =============================================
#  ГЕНЕРАЦИЯ НОМЕРА
# =============================================

async def generate_algorithm_number(db: AsyncSession) -> str:
    """Сгенерировать следующий номер алгоритма"""
    result = await db.execute(select(sql_func.count(Algorithm.id)))
    count = result.scalar() or 0
    return f"ALG-{(count + 1):06d}"


# =============================================
#  СОЗДАНИЕ
# =============================================

async def create_algorithm(db: AsyncSession, data: Dict[str, Any]) -> Algorithm:
    """Создать алгоритм"""
    if "number" not in data:
        data["number"] = await generate_algorithm_number(db)
    algorithm = Algorithm(**data)
    db.add(algorithm)
    await db.commit()
    await db.refresh(algorithm)
    return algorithm


async def assign_participant(
    db: AsyncSession, algorithm_id: int, citizen_id: int
) -> AlgorithmParticipant:
    """Назначить участника на алгоритм"""
    # Проверяем, что ещё не назначен
    existing = await db.execute(
        select(AlgorithmParticipant).where(
            AlgorithmParticipant.algorithm_id == algorithm_id,
            AlgorithmParticipant.citizen_id == citizen_id
        )
    )
    if existing.scalar_one_or_none():
        return existing.scalar_one()

    participant = AlgorithmParticipant(
        algorithm_id=algorithm_id,
        citizen_id=citizen_id,
        status="assigned",
    )
    db.add(participant)
    await db.commit()
    await db.refresh(participant)
    return participant


async def add_attachment(
    db: AsyncSession, algorithm_id: int, filename: str, filepath: str,
    file_type: str = "file", file_size: int = 0, uploaded_by: int = None
) -> AlgorithmAttachment:
    """Добавить вложение к алгоритму"""
    att = AlgorithmAttachment(
        algorithm_id=algorithm_id,
        filename=filename,
        filepath=filepath,
        file_type=file_type,
        file_size=file_size,
        uploaded_by=uploaded_by,
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)
    return att


async def add_report_attachment(
    db: AsyncSession, participant_id: int, filename: str, filepath: str,
    file_type: str = "image", file_size: int = 0
) -> AlgorithmReportAttachment:
    """Добавить вложение к отчёту"""
    att = AlgorithmReportAttachment(
        participant_id=participant_id,
        filename=filename,
        filepath=filepath,
        file_type=file_type,
        file_size=file_size,
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)
    return att


# =============================================
#  ПОЛУЧЕНИЕ
# =============================================

async def get_algorithm(db: AsyncSession, algorithm_id: int) -> Optional[Algorithm]:
    result = await db.execute(
        select(Algorithm)
        .options(
            selectinload(Algorithm.participants).selectinload(AlgorithmParticipant.citizen),
            selectinload(Algorithm.participants).selectinload(AlgorithmParticipant.report_attachments),
            selectinload(Algorithm.attachments),
            selectinload(Algorithm.creator),
        )
        .where(Algorithm.id == algorithm_id)
    )
    return result.scalar_one_or_none()


async def get_algorithm_by_number(db: AsyncSession, number: str) -> Optional[Algorithm]:
    result = await db.execute(
        select(Algorithm)
        .options(
            selectinload(Algorithm.participants).selectinload(AlgorithmParticipant.citizen),
            selectinload(Algorithm.participants).selectinload(AlgorithmParticipant.report_attachments),
            selectinload(Algorithm.attachments),
            selectinload(Algorithm.creator),
        )
        .where(Algorithm.number == number)
    )
    return result.scalar_one_or_none()


async def get_all_algorithms(
    db: AsyncSession,
    status: str = None,
    task_type: str = None,
    scope: str = None,
    creator_id: int = None,
    limit: int = 100,
    offset: int = 0
) -> List[Algorithm]:
    """Список алгоритмов с фильтрами"""
    query = select(Algorithm).options(
        selectinload(Algorithm.creator),
        selectinload(Algorithm.participants),
    )
    conditions = []
    if status:
        conditions.append(Algorithm.status == status)
    if task_type:
        conditions.append(Algorithm.task_type == task_type)
    if scope:
        conditions.append(Algorithm.scope == scope)
    if creator_id:
        conditions.append(Algorithm.created_by == creator_id)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(Algorithm.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_visible_algorithms(db: AsyncSession, citizen_id: int) -> List[Algorithm]:
    """
    Алгоритмы, которые видит гражданин:
    - все public со статусом open/in_progress
    - personal, где он участник
    - все, где он участник
    """
    # Получаем ID алгоритмов, где он участник
    part_result = await db.execute(
        select(AlgorithmParticipant.algorithm_id)
        .where(AlgorithmParticipant.citizen_id == citizen_id)
    )
    my_algorithm_ids = [row[0] for row in part_result.all()]

    query = select(Algorithm).options(
        selectinload(Algorithm.creator),
        selectinload(Algorithm.participants),
    ).where(
        or_(
            and_(
                Algorithm.scope == "public",
                Algorithm.status.in_(["open", "in_progress"])
            ),
            Algorithm.id.in_(my_algorithm_ids) if my_algorithm_ids else False
        )
    ).order_by(Algorithm.created_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_my_algorithms(db: AsyncSession, citizen_id: int) -> List[AlgorithmParticipant]:
    """Мои алгоритмы (где я участник)"""
    result = await db.execute(
        select(AlgorithmParticipant)
        .options(
            selectinload(AlgorithmParticipant.algorithm).selectinload(Algorithm.creator),
        )
        .where(AlgorithmParticipant.citizen_id == citizen_id)
        .order_by(AlgorithmParticipant.assigned_at.desc())
    )
    return list(result.scalars().all())


async def get_participant(
    db: AsyncSession, algorithm_id: int, citizen_id: int
) -> Optional[AlgorithmParticipant]:
    result = await db.execute(
        select(AlgorithmParticipant).where(
            AlgorithmParticipant.algorithm_id == algorithm_id,
            AlgorithmParticipant.citizen_id == citizen_id
        )
    )
    return result.scalar_one_or_none()


async def get_participants_count(db: AsyncSession, algorithm_id: int) -> int:
    result = await db.execute(
        select(sql_func.count(AlgorithmParticipant.id))
        .where(AlgorithmParticipant.algorithm_id == algorithm_id)
    )
    return result.scalar() or 0


async def get_algorithms_count(db: AsyncSession) -> int:
    result = await db.execute(select(sql_func.count(Algorithm.id)))
    return result.scalar() or 0


# =============================================
#  ОБНОВЛЕНИЕ
# =============================================

async def update_algorithm(
    db: AsyncSession, algorithm_id: int, data: Dict[str, Any]
) -> Optional[Algorithm]:
    result = await db.execute(select(Algorithm).where(Algorithm.id == algorithm_id))
    algo = result.scalar_one_or_none()
    if not algo:
        return None
    for key, value in data.items():
        if hasattr(algo, key):
            setattr(algo, key, value)
    await db.commit()
    await db.refresh(algo)
    return algo


async def submit_report(
    db: AsyncSession,
    participant_id: int,
    report_text: str
) -> Optional[AlgorithmParticipant]:
    """Сдать отчёт по алгоритму"""
    result = await db.execute(
        select(AlgorithmParticipant).where(AlgorithmParticipant.id == participant_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        return None
    p.report_text = report_text
    p.submitted_at = sql_func.now()
    p.status = "submitted"
    await db.commit()
    await db.refresh(p)

    # Если все участники сдали — переводим алгоритм в review
    algo_result = await db.execute(select(Algorithm).where(Algorithm.id == p.algorithm_id))
    algo = algo_result.scalar_one_or_none()
    if algo:
        all_result = await db.execute(
            select(AlgorithmParticipant)
            .where(AlgorithmParticipant.algorithm_id == algo.id)
        )
        all_parts = list(all_result.scalars().all())
        if all_parts and all(
            ap.status in ["submitted", "approved", "rejected"]
            for ap in all_parts
        ):
            algo.status = "review"
            await db.commit()

    return p


async def review_participant(
    db: AsyncSession,
    participant_id: int,
    stars: int,
    feedback: str,
    approve: bool = True
) -> Optional[AlgorithmParticipant]:
    """Оценить работу участника"""
    result = await db.execute(
        select(AlgorithmParticipant).where(AlgorithmParticipant.id == participant_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        return None
    p.stars = max(1, min(5, stars))
    p.feedback = feedback
    p.status = "approved" if approve else "rejected"
    p.reviewed_at = sql_func.now()
    await db.commit()
    await db.refresh(p)

    # Если все одобрены — закрываем алгоритм
    algo_result = await db.execute(select(Algorithm).where(Algorithm.id == p.algorithm_id))
    algo = algo_result.scalar_one_or_none()
    if algo:
        all_result = await db.execute(
            select(AlgorithmParticipant)
            .where(AlgorithmParticipant.algorithm_id == algo.id)
        )
        all_parts = all_result.scalars().all()
        if all_parts and all(ap.status == "approved" for ap in all_parts):
            algo.status = "completed"
            await db.commit()
        elif any(ap.status == "rejected" for ap in all_parts):
            algo.status = "in_progress"  # возвращаем в работу

    return p


async def close_algorithm(db: AsyncSession, algorithm_id: int) -> bool:
    """Закрыть алгоритм (куратор)"""
    result = await db.execute(select(Algorithm).where(Algorithm.id == algorithm_id))
    algo = result.scalar_one_or_none()
    if not algo:
        return False
    algo.status = "completed"
    await db.commit()
    return True


# =============================================
#  УДАЛЕНИЕ
# =============================================

async def delete_algorithm(db: AsyncSession, algorithm_id: int) -> bool:
    result = await db.execute(select(Algorithm).where(Algorithm.id == algorithm_id))
    algo = result.scalar_one_or_none()
    if not algo:
        return False
    await db.delete(algo)
    await db.commit()
    return True


async def remove_participant(db: AsyncSession, participant_id: int) -> bool:
    result = await db.execute(
        select(AlgorithmParticipant).where(AlgorithmParticipant.id == participant_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        return False
    await db.delete(p)
    await db.commit()
    return True