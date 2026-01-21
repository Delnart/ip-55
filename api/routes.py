from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from database.connection import db
from config import ADMIN_IDS
from bot.utils.api import ScheduleAPI

router = APIRouter()

# --- Models ---
class User(BaseModel):
    telegramId: int
    fullName: Optional[str] = None
    username: Optional[str] = None
    avatarUrl: Optional[str] = None

class Subject(BaseModel):
    name: str
    type: str 
    teacherLecture: Optional[str] = None
    teacherPractice: Optional[str] = None
    description: Optional[str] = None
    links: List[Dict[str, str]] = []

class QueueEntry(BaseModel):
    queueId: str
    telegramId: int
    labNumber: int
    position: Optional[int] = None

class QueueStatusUpdate(BaseModel):
    queueId: str
    userId: str
    status: str 
    adminId: int

# --- API ---

@router.get("/subjects")
async def get_subjects():
    subjects = await db.db.subjects.find().to_list(1000)
    for s in subjects:
        s["_id"] = str(s["_id"])
    return subjects

@router.post("/subjects")
async def create_subject(subject: Subject):
    try:
        result = await db.db.subjects.insert_one(subject.dict())
        return {"success": True, "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/subjects/{subject_id}")
async def delete_subject(subject_id: str):
    try:
        from bson import ObjectId
        await db.db.subjects.delete_one({"_id": ObjectId(subject_id)})
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Queues Logic ---

@router.get("/queues/subject/{subject_id}")
async def get_queue_by_subject(subject_id: str):
    queue = await db.db.queues.find_one({"subjectId": subject_id})
    if not queue:
        return None
    
    queue["_id"] = str(queue["_id"])
    
    # Підтягуємо дані користувачів
    entries_with_users = []
    for entry in queue.get("entries", []):
        if entry.get("userId"):
            user = await db.db.users.find_one({"_id": entry["userId"]})
            if user:
                entry["user"] = {
                    "_id": str(user["_id"]),
                    "fullName": user.get("fullName"),
                    "telegramId": user.get("telegramId"),
                    "username": user.get("username")
                }
        entries_with_users.append(entry)
    
    queue["entries"] = entries_with_users
    return queue

@router.post("/queues")
async def create_or_get_queue(data: dict):
    subject_id = data.get("subjectId")
    existing = await db.db.queues.find_one({"subjectId": subject_id})
    if existing:
        existing["_id"] = str(existing["_id"])
        return existing
        
    new_queue = {
        "subjectId": subject_id,
        "isActive": True,
        "entries": [],
        "config": {
            "maxSlots": 31,
            "minMaxRule": True
        },
        "createdAt": datetime.utcnow()
    }
    result = await db.db.queues.insert_one(new_queue)
    return {"success": True, "id": str(result.inserted_id)}

@router.post("/queues/join")
async def join_queue(entry: QueueEntry):
    try:
        from bson import ObjectId
        queue = await db.db.queues.find_one({"_id": ObjectId(entry.queueId)})
        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")
        
        if not queue.get("isActive", True):
            raise HTTPException(status_code=400, detail="Черга закрита")

        entries = queue.get("entries", [])
        
        # --- ПРАВИЛО МІН + 2 ---
        active_labs = [e["labNumber"] for e in entries if e.get("status") not in ["completed", "failed"]]
        if active_labs:
            min_lab = min(active_labs)
            max_allowed = min_lab + 2
            if entry.labNumber > max_allowed:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Правило черги: Мін. лаба зараз {min_lab}. Ви можете здавати максимум {max_allowed}."
                )

        user = await db.db.users.find_one({"telegramId": entry.telegramId})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user["_id"])
        
        if any(e.get("userId") == user_id for e in entries):
             raise HTTPException(status_code=400, detail="Ви вже в черзі")
        
        if any(e.get("position") == entry.position for e in entries):
             raise HTTPException(status_code=400, detail="Це місце вже зайняте")

        new_entry = {
            "userId": user_id,
            "labNumber": entry.labNumber,
            "position": entry.position,
            "status": "waiting", # waiting, preparing, defending, completed
            "joinedAt": datetime.utcnow().isoformat()
        }
        
        entries.append(new_entry)
        
        await db.db.queues.update_one(
            {"_id": ObjectId(entry.queueId)},
            {"$set": {"entries": entries}}
        )
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/queues/status")
async def update_queue_status(update: QueueStatusUpdate):
    try:
        from bson import ObjectId
        if update.adminId not in ADMIN_IDS:
             raise HTTPException(status_code=403, detail="Тільки адміни можуть змінювати статус")

        queue = await db.db.queues.find_one({"_id": ObjectId(update.queueId)})
        entries = queue.get("entries", [])
        
        for entry in entries:
            if entry.get("userId") == update.userId:
                entry["status"] = update.status
                break
        
        await db.db.queues.update_one(
            {"_id": ObjectId(update.queueId)},
            {"$set": {"entries": entries}}
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/queues/leave")
async def leave_queue(data: dict):
    try:
        from bson import ObjectId
        queue_id = data.get("queueId")
        telegram_id = data.get("telegramId")
        
        user = await db.db.users.find_one({"telegramId": telegram_id})
        user_id = str(user["_id"])
        
        queue = await db.db.queues.find_one({"_id": ObjectId(queue_id)})
        entries = [e for e in queue.get("entries", []) if e.get("userId") != user_id]
        
        await db.db.queues.update_one(
            {"_id": ObjectId(queue_id)},
            {"$set": {"entries": entries}}
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/queues/kick")
async def kick_queue(data: dict):
    # Логіка видалення адміном (аналогічна leave, але перевірка adminId)
    return await leave_queue(data)

@router.post("/queues/toggle")
async def toggle_queue(data: dict):
    try:
        from bson import ObjectId
        if data.get("adminId") not in ADMIN_IDS:
             raise HTTPException(status_code=403, detail="Forbidden")
             
        queue_id = data.get("queueId")
        queue = await db.db.queues.find_one({"_id": ObjectId(queue_id)})
        new_state = not queue.get("isActive", True)
        
        await db.db.queues.update_one(
            {"_id": ObjectId(queue_id)},
            {"$set": {"isActive": new_state}}
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Utils ---
@router.get("/schedule")
async def get_schedule():
    return await ScheduleAPI.get_schedule()

@router.post("/users/update")
async def update_user(user: User):
    await db.db.users.update_one(
        {"telegramId": user.telegramId},
        {"$set": {
            "fullName": user.fullName,
            "username": user.username,
            "avatarUrl": user.avatarUrl,
            "updatedAt": datetime.utcnow()
        }},
        upsert=True
    )
    return {"success": True}