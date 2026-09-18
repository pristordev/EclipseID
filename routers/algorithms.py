import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from datetime import datetime
from typing import Optional

from database.db import get_db
from database import crud_algorithms as algo_crud
from database import crud
from auth import get_current_user, require_permission, has_permission


router = APIRouter(prefix="/api/algorithms", tags=["Algorithms"])

# Папка для загрузки вложений
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads" / "algorithms"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Разрешённые типы
ALLOWED_IMAGE_TYPES = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
ALLOWED_FILE_TYPES = [".pdf", ".txt", ".doc", ".docx", ".zip", ".rar"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 МБ


def save_upload(file: UploadFile, algorithm_id: int) -> dict:
    """Сохранить файл в static/uploads/algorithms/{algorithm_id}/"""
    # Папка под конкретный алгоритм
    algo_dir = UPLOAD_DIR / str(algorithm_id)
    algo_dir.mkdir(exist_ok=True)

    # Проверка расширения
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_TYPES + ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail=f"Недопустимый тип файла: {ext}")

    # Уникальное имя
    unique_name = f"{uuid.uuid4().hex}{ext}"
    filepath = algo_dir / unique_name

    # Сохраняем
    contents = file.file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Файл больше 10 МБ")

    with open(filepath, "wb") as f:
        f.write(contents)

    file_type = "image" if ext in ALLOWED_IMAGE_TYPES else "file"

    return {
        "filename": file.filename,
        "filepath": f"/static/uploads/algorithms/{algorithm_id}/{unique_name}",
        "file_type": file_type,
        "file_size": len(contents),
    }


# ============================================
#  СПИСОК АЛГОРИТМОВ
# ============================================

@router.get("")
async def list_algorithms(
    status: str = Query(None),
    task_type: str = Query(None),
    current_user = Depends(require_permission("view_algorithms")),
    db: AsyncSession = Depends(get_db)
):
    """Список доступных алгоритмов"""
    # Проверяем, есть ли право видеть все
    can_view_all = await has_permission(db, current_user, "view_all_algorithms")

    if can_view_all:
        algorithms = await algo_crud.get_all_algorithms(
            db, status=status, task_type=task_type, limit=200
        )
    else:
        algorithms = await algo_crud.get_visible_algorithms(db, current_user.id)

    # Формируем данные
    result = []
    for a in algorithms:
        creator = await crud.get_citizen(db, a.created_by)
        participants_count = await algo_crud.get_participants_count(db, a.id)

        result.append({
            "id": a.id,
            "number": a.number,
            "title": a.title,
            "task_type": a.task_type,
            "scope": a.scope,
            "status": a.status,
            "deadline": a.deadline.isoformat() if a.deadline else None,
            "creator": {
                "id": creator.id if creator else None,
                "username": creator.username if creator else "—",
            },
            "participants_count": participants_count,
            "max_participants": a.max_participants,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })

    return {"status": "success", "count": len(result), "data": result}


# ============================================
#  ДЕТАЛИ АЛГОРИТМА
# ============================================

@router.get("/{number}")
async def get_algorithm_details(
    number: str,
    current_user = Depends(require_permission("view_algorithm_details")),
    db: AsyncSession = Depends(get_db)
):
    """Детали алгоритма по номеру"""
    algo = await algo_crud.get_algorithm_by_number(db, number)
    if not algo:
        raise HTTPException(status_code=404, detail="Алгоритм не найден")

    creator = await crud.get_citizen(db, algo.created_by)

    from utils.avatars import get_avatar_url
    participants_data = []
    for p in algo.participants:
        c = p.citizen
        avatar_url = get_avatar_url(c.minecraft_uuid) if c.minecraft_uuid else None
        participants_data.append({
            "id": p.id,
            "citizen_id": c.id,
            "username": c.username,
            "avatar_url": avatar_url,
            "status": p.status,
            "assigned_at": p.assigned_at.isoformat() if p.assigned_at else None,
            "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
            "report_text": p.report_text,
            "stars": p.stars,
            "feedback": p.feedback,
            "report_attachments": [
                {"id": a.id, "filename": a.filename, "filepath": a.filepath, "file_type": a.file_type}
                for a in p.report_attachments
            ],
        })

    # Вложения
    attachments_data = [
        {"id": a.id, "filename": a.filename, "filepath": a.filepath, "file_type": a.file_type}
        for a in algo.attachments
    ]

    # Может ли текущий пользователь оценивать
    can_review = await has_permission(db, current_user, "review_algorithm")
    # Может ли взять задачу
    my_participation = await algo_crud.get_participant(db, algo.id, current_user.id)

    return {
        "status": "success",
        "data": {
            "id": algo.id,
            "number": algo.number,
            "title": algo.title,
            "description": algo.description,
            "task_type": algo.task_type,
            "scope": algo.scope,
            "status": algo.status,
            "deadline": algo.deadline.isoformat() if algo.deadline else None,
            "reward_reputation": algo.reward_reputation,
            "max_participants": algo.max_participants,
            "creator": {
                "id": creator.id if creator else None,
                "username": creator.username if creator else "—",
            },
            "participants": participants_data,
            "attachments": attachments_data,
            "can_review": can_review,
            "my_participation": {
                "id": my_participation.id,
                "status": my_participation.status,
            } if my_participation else None,
            "created_at": algo.created_at.isoformat() if algo.created_at else None,
        }
    }


# ============================================
#  СОЗДАНИЕ АЛГОРИТМА (Куратор)
# ============================================

@router.post("")
async def create_algorithm(
    title: str = Form(...),
    description: str = Form(""),
    task_type: str = Form(...),
    scope: str = Form("public"),
    deadline: str = Form(...),  # ISO: 2026-09-20T18:00
    reward_reputation: int = Form(0),
    max_participants: int = Form(5),
    participant_ids: str = Form(""),  # "1,2,3" через запятую
    current_user = Depends(require_permission("create_algorithm")),
    db: AsyncSession = Depends(get_db)
):
    """Создать алгоритм"""
    # Проверка типа задачи
    if task_type not in ["mining", "building", "sorting"]:
        raise HTTPException(status_code=400, detail="Неверный тип задачи")

    if scope not in ["public", "personal"]:
        raise HTTPException(status_code=400, detail="Неверный scope")

    # Парсим дедлайн
    try:
        deadline_dt = datetime.fromisoformat(deadline)
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат дедлайна")

    # Создаём алгоритм
    algo = await algo_crud.create_algorithm(db, {
        "title": title,
        "description": description,
        "task_type": task_type,
        "scope": scope,
        "deadline": deadline_dt,
        "reward_reputation": reward_reputation,
        "max_participants": max_participants,
        "created_by": current_user.id,
        "status": "open",
    })

    # Если персональный — назначаем участников
    if scope == "personal" and participant_ids:
        ids = [int(x.strip()) for x in participant_ids.split(",") if x.strip()]
        for cid in ids[:max_participants]:
            await algo_crud.assign_participant(db, algo.id, cid)

    return {
        "status": "success",
        "message": f"Алгоритм {algo.number} создан",
        "data": {"id": algo.id, "number": algo.number}
    }


# ============================================
#  ОБНОВЛЕНИЕ АЛГОРИТМА
# ============================================

@router.put("/{algorithm_id}")
async def update_algorithm(
    algorithm_id: int,
    title: str = Form(None),
    description: str = Form(None),
    deadline: str = Form(None),
    reward_reputation: int = Form(None),
    status: str = Form(None),
    current_user = Depends(require_permission("review_algorithm")),
    db: AsyncSession = Depends(get_db)
):
    """Обновить алгоритм"""
    algo = await algo_crud.get_algorithm(db, algorithm_id)
    if not algo:
        raise HTTPException(status_code=404, detail="Алгоритм не найден")

    data = {}
    if title is not None:
        data["title"] = title
    if description is not None:
        data["description"] = description
    if deadline is not None:
        try:
            data["deadline"] = datetime.fromisoformat(deadline)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат дедлайна")
    if reward_reputation is not None:
        data["reward_reputation"] = reward_reputation
    if status is not None:
        data["status"] = status

    await algo_crud.update_algorithm(db, algorithm_id, data)
    return {"status": "success", "message": "Алгоритм обновлён"}


# ============================================
#  УДАЛЕНИЕ
# ============================================

@router.delete("/{algorithm_id}")
async def delete_algorithm(
    algorithm_id: int,
    current_user = Depends(require_permission("delete_algorithm")),
    db: AsyncSession = Depends(get_db)
):
    success = await algo_crud.delete_algorithm(db, algorithm_id)
    if not success:
        raise HTTPException(status_code=404, detail="Алгоритм не найден")
    return {"status": "success", "message": "Алгоритм удалён"}


# ============================================
#  НАЗНАЧЕНИЕ УЧАСТНИКА
# ============================================

@router.post("/{algorithm_id}/assign")
async def assign_participant(
    algorithm_id: int,
    citizen_id: int = Query(...),
    current_user = Depends(require_permission("assign_algorithm")),
    db: AsyncSession = Depends(get_db)
):
    """Назначить участника"""
    algo = await algo_crud.get_algorithm(db, algorithm_id)
    if not algo:
        raise HTTPException(status_code=404, detail="Алгоритм не найден")

    count = await algo_crud.get_participants_count(db, algorithm_id)
    if count >= algo.max_participants:
        raise HTTPException(status_code=400, detail="Максимум участников достигнут")

    participant = await algo_crud.assign_participant(db, algorithm_id, citizen_id)
    return {"status": "success", "message": "Участник назначен", "data": {"id": participant.id}}


@router.delete("/participants/{participant_id}")
async def remove_participant(
    participant_id: int,
    current_user = Depends(require_permission("assign_algorithm")),
    db: AsyncSession = Depends(get_db)
):
    """Убрать участника"""
    success = await algo_crud.remove_participant(db, participant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Участник не найден")
    return {"status": "success", "message": "Участник убран"}


# ============================================
#  ВЗЯТЬ ОБЩУЮ ЗАДАЧУ
# ============================================

@router.post("/{algorithm_id}/join")
async def join_algorithm(
    algorithm_id: int,
    current_user = Depends(require_permission("join_algorithm")),
    db: AsyncSession = Depends(get_db)
):
    """Взять общий алгоритм"""
    algo = await algo_crud.get_algorithm(db, algorithm_id)
    if not algo:
        raise HTTPException(status_code=404, detail="Алгоритм не найден")

    if algo.scope != "public":
        raise HTTPException(status_code=400, detail="Это не общий алгоритм")

    if algo.status not in ["open", "in_progress"]:
        raise HTTPException(status_code=400, detail="Алгоритм уже неактуален")

    # Проверяем, что не участник
    existing = await algo_crud.get_participant(db, algorithm_id, current_user.id)
    if existing:
        raise HTTPException(status_code=400, detail="Вы уже участник")

    count = await algo_crud.get_participants_count(db, algorithm_id)
    if count >= algo.max_participants:
        raise HTTPException(status_code=400, detail="Максимум участников достигнут")

    await algo_crud.assign_participant(db, algorithm_id, current_user.id)

    # Меняем статус на in_progress
    if algo.status == "open":
        await algo_crud.update_algorithm(db, algorithm_id, {"status": "in_progress"})

    return {"status": "success", "message": "Вы записаны на алгоритм"}


# ============================================
#  СДАТЬ ОТЧЁТ
# ============================================

@router.post("/{algorithm_id}/submit")
async def submit_report(
    algorithm_id: int,
    report_text: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    current_user = Depends(require_permission("submit_algorithm_report")),
    db: AsyncSession = Depends(get_db)
):
    """Сдать отчёт"""
    algo = await algo_crud.get_algorithm(db, algorithm_id)
    if not algo:
        raise HTTPException(status_code=404, detail="Алгоритм не найден")

    participant = await algo_crud.get_participant(db, algorithm_id, current_user.id)
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник алгоритма")

    if participant.status == "submitted":
        raise HTTPException(status_code=400, detail="Вы уже сдали отчёт")

    # Сохраняем отчёт
    await algo_crud.submit_report(db, participant.id, report_text)

    # Загружаем файлы
    for f in files:
        if f and f.filename:
            info = save_upload(f, algorithm_id)
            await algo_crud.add_report_attachment(
                db, participant.id,
                info["filename"], info["filepath"],
                info["file_type"], info["file_size"]
            )

    return {"status": "success", "message": "Отчёт сдан"}


# ============================================
#  ОЦЕНКА (Куратор)
# ============================================

@router.post("/participants/{participant_id}/review")
async def review_participant(
    participant_id: int,
    stars: int = Form(...),
    feedback: str = Form(""),
    approve: bool = Form(True),
    current_user = Depends(require_permission("review_algorithm")),
    db: AsyncSession = Depends(get_db)
):
    """Оценить работу участника"""
    if stars < 1 or stars > 5:
        raise HTTPException(status_code=400, detail="Оценка от 1 до 5")

    p = await algo_crud.review_participant(db, participant_id, stars, feedback, approve)
    if not p:
        raise HTTPException(status_code=404, detail="Участник не найден")

    # Начисляем репутацию, если одобрено
    if approve and p.stars:
        algo = await algo_crud.get_algorithm(db, p.algorithm_id)
        if algo and algo.reward_reputation > 0:
            # Репутация = базовая * (звёзды / 5)
            bonus = int(algo.reward_reputation * (p.stars / 5))
            await crud.update_reputation(db, p.citizen_id, bonus)

    return {"status": "success", "message": "Оценка сохранена"}


# ============================================
#  ЗАГРУЗКА ВЛОЖЕНИЙ К АЛГОРИТМУ
# ============================================

@router.post("/{algorithm_id}/attachments")
async def upload_attachment(
    algorithm_id: int,
    file: UploadFile = File(...),
    current_user = Depends(require_permission("create_algorithm")),
    db: AsyncSession = Depends(get_db)
):
    """Загрузить вложение к алгоритму"""
    algo = await algo_crud.get_algorithm(db, algorithm_id)
    if not algo:
        raise HTTPException(status_code=404, detail="Алгоритм не найден")

    info = save_upload(file, algorithm_id)
    att = await algo_crud.add_attachment(
        db, algorithm_id,
        info["filename"], info["filepath"],
        info["file_type"], info["file_size"],
        uploaded_by=current_user.id
    )

    return {
        "status": "success",
        "data": {"id": att.id, "filename": att.filename, "filepath": att.filepath, "file_type": att.file_type}
    }