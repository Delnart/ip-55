from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from database.connection import db
from database.models import HomeworkManager, TopicsManager
from config import ADMIN_IDS
from bot.utils.api import ScheduleAPI
from bson import ObjectId

router = APIRouter()

class Subject(BaseModel):
    name: str
    teacherLecture: Optional[str] = None
    teacherPractice: Optional[str] = None
    note: Optional[str] = None

class QueueConfig(BaseModel):
    queueId: str
    adminId: int
    minMaxRule: bool

@router.get("/subjects")
async def get_subjects():
    subjects = await db.db.subjects.find().to_list(1000)
    for s in subjects: s["_id"] = str(s["_id"])
    return subjects

@router.post("/subjects")
async def upsert_subject(subject: Subject):
    existing = await db.db.subjects.find_one({"name": subject.name})
    if existing:
        await db.db.subjects.update_one({"_id": existing["_id"]}, {"$set": subject.dict()})
        return {"success": True, "id": str(existing["_id"])}
    result = await db.db.subjects.insert_one(subject.dict())
    return {"success": True, "id": str(result.inserted_id)}

@router.delete("/subjects/{subject_id}")
async def delete_subject(subject_id: str):
    await db.db.subjects.delete_one({"_id": ObjectId(subject_id)})
    return {"success": True}

# --- Queue ---

@router.get("/queues/subject/{subject_id}")
async def get_queue(subject_id: str):
    queue = await db.db.queues.find_one({"subjectId": subject_id})
    if not queue: return None
    queue["_id"] = str(queue["_id"])
    
    entries_data = []
    for entry in queue.get("entries", []):
        user = await db.db.users.find_one({"_id": ObjectId(entry["userId"])})
        if user:
            entry["user"] = {
                "_id": str(user["_id"]),
                "fullName": user.get("fullName"),
                "avatarUrl": user.get("avatarUrl"),
                "telegramId": user.get("telegramId")
            }
        entries_data.append(entry)
    queue["entries"] = entries_data
    return queue

@router.post("/queues")
async def create_queue(data: dict):
    subject_id = data.get("subjectId")
    if await db.db.queues.find_one({"subjectId": subject_id}):
        return {"success": False, "message": "Queue exists"}
    
    new_queue = {
        "subjectId": subject_id,
        "isActive": True,
        "config": {"minMaxRule": True},
        "entries": [],
        "createdAt": datetime.utcnow()
    }
    res = await db.db.queues.insert_one(new_queue)
    return {"success": True, "id": str(res.inserted_id)}

@router.patch("/queues/config")
async def update_queue_config(config: QueueConfig):
    if config.adminId not in ADMIN_IDS:
        raise HTTPException(403, "Admin only")
    await db.db.queues.update_one(
        {"_id": ObjectId(config.queueId)},
        {"$set": {"config.minMaxRule": config.minMaxRule}}
    )
    return {"success": True}

@router.post("/queues/join")
async def join_queue(data: dict):
    queue = await db.db.queues.find_one({"_id": ObjectId(data["queueId"])})
    if not queue: raise HTTPException(404, "Queue not found")
    if not queue.get("isActive", True): raise HTTPException(400, "Черга закрита")

    user = await db.db.users.find_one({"telegramId": data["telegramId"]})
    if not user: raise HTTPException(404, "User not found")
    user_id = str(user["_id"])

    entries = queue.get("entries", [])
    if any(e["userId"] == user_id for e in entries):
        raise HTTPException(400, "Ви вже в черзі")
    if any(e["position"] == data["position"] for e in entries):
        raise HTTPException(400, "Місце зайняте")

    # Min/Max Rule Logic
    if queue.get("config", {}).get("minMaxRule", True):
        active_labs = [e["labNumber"] for e in entries if e.get("status") in ["preparing", "defending", "completed"]]
        if active_labs:
            min_lab = min(active_labs)
            if data["labNumber"] > min_lab + 2:
                raise HTTPException(400, f"Правило черги: Макс. лаба = {min_lab + 2} (Мін: {min_lab})")

    new_entry = {
        "userId": user_id,
        "labNumber": data["labNumber"],
        "position": data["position"],
        "status": "waiting",
        "joinedAt": datetime.utcnow().isoformat()
    }
    entries.append(new_entry)
    await db.db.queues.update_one({"_id": ObjectId(data["queueId"])}, {"$set": {"entries": entries}})
    return {"success": True}

@router.post("/queues/leave")
async def leave_queue(data: dict):
    user = await db.db.users.find_one({"telegramId": data["telegramId"]})
    user_id = str(user["_id"])
    await db.db.queues.update_one(
        {"_id": ObjectId(data["queueId"])},
        {"$pull": {"entries": {"userId": user_id}}}
    )
    return {"success": True}

@router.patch("/queues/status")
async def set_status(data: dict):
    if data["adminId"] not in ADMIN_IDS: raise HTTPException(403)
    queue = await db.db.queues.find_one({"_id": ObjectId(data["queueId"])})
    entries = queue["entries"]
    for e in entries:
        if e["userId"] == data["userId"]:
            e["status"] = data["status"]
            break
    await db.db.queues.update_one({"_id": ObjectId(data["queueId"])}, {"$set": {"entries": entries}})
    return {"success": True}

@router.post("/queues/toggle")
async def toggle_queue(data: dict):
    if data["adminId"] not in ADMIN_IDS: raise HTTPException(403)
    queue = await db.db.queues.find_one({"_id": ObjectId(data["queueId"])})
    await db.db.queues.update_one({"_id": ObjectId(data["queueId"])}, {"$set": {"isActive": not queue.get("isActive", True)}})
    return {"success": True}

# --- Topics ---

@router.get("/topics/{subject_id}")
async def get_topics(subject_id: str):
    return await TopicsManager.get_topics(subject_id)

@router.post("/topics")
async def create_topic(data: dict):
    if data["adminId"] not in ADMIN_IDS: raise HTTPException(403)
    await TopicsManager.create_topic(data["subjectId"], data["title"])
    return {"success": True}

@router.post("/topics/toggle")
async def toggle_topic(data: dict):
    user = await db.db.users.find_one({"telegramId": data["telegramId"]})
    res = await TopicsManager.toggle_topic(data["topicId"], str(user["_id"]), user["fullName"])
    if not res: raise HTTPException(400, "Taken by another")
    return {"success": True}

# --- Homework ---

@router.get("/homework/{subject_id}")
async def get_hw(subject_id: str):
    return await HomeworkManager.get_hw(subject_id)

@router.post("/homework")
async def add_hw(data: dict):
    await HomeworkManager.add_hw(data["subjectId"], data["text"], data["deadline"], data["authorId"])
    return {"success": True}

@router.delete("/homework/{hw_id}")
async def delete_hw(hw_id: str, adminId: int):
    if adminId not in ADMIN_IDS: raise HTTPException(403)
    await HomeworkManager.delete_hw(hw_id)
    return {"success": True}

# --- Utils ---
@router.get("/schedule")
async def get_schedule():
    return await ScheduleAPI.get_schedule()

@router.post("/users/update")
async def update_user(data: dict):
    await db.db.users.update_one(
        {"telegramId": data["telegramId"]},
        {"$set": {"fullName": data["fullName"], "username": data["username"], "avatarUrl": data.get("avatarUrl")}},
        upsert=True
    )
    return {"success": True}