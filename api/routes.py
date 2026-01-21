from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, ADMIN_IDS
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncIOMotorClient(MONGODB_URL)
db = client.university_bot

class User(BaseModel):
    telegramId: int
    fullName: Optional[str] = None
    username: Optional[str] = None

class QueueEntry(BaseModel):
    queueId: str
    telegramId: int
    labNumber: int
    position: Optional[int] = None

class QueueUpdate(BaseModel):
    queueId: str
    userId: str
    status: str

class QueueConfig(BaseModel):
    maxSlots: int = 31
    minMaxRule: bool = True
    priorityMove: bool = True
    maxAttempts: int = 3

class Subject(BaseModel):
    name: str
    type: str

class TopicEntry(BaseModel):
    subjectId: str
    telegramId: int
    topicNumber: int

class Homework(BaseModel):
    subject: str
    description: str
    deadline: Optional[str] = None

async def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS

@app.post("/users/update")
async def update_user(user: User):
    try:
        await db.users.update_one(
            {"telegramId": user.telegramId},
            {"$set": {
                "fullName": user.fullName,
                "username": user.username,
                "updatedAt": datetime.utcnow()
            }},
            upsert=True
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{telegram_id}")
async def get_user(telegram_id: int):
    user = await db.users.find_one({"telegramId": telegram_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["_id"] = str(user["_id"])
    return user

@app.post("/subjects")
async def create_subject(subject: Subject):
    try:
        result = await db.subjects.insert_one({
            "name": subject.name,
            "type": subject.type,
            "createdAt": datetime.utcnow()
        })
        return {"success": True, "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/subjects")
async def get_subjects():
    subjects = await db.subjects.find().to_list(1000)
    for s in subjects:
        s["_id"] = str(s["_id"])
    return subjects

@app.post("/queues")
async def create_queue(data: dict):
    try:
        subject_id = data.get("subjectId")
        existing = await db.queues.find_one({"subjectId": subject_id})
        if existing:
            return {"success": True, "queue": {
                "_id": str(existing["_id"]),
                "subjectId": existing["subjectId"],
                "isActive": existing.get("isActive", True),
                "entries": existing.get("entries", []),
                "config": existing.get("config", {})
            }}
        
        result = await db.queues.insert_one({
            "subjectId": subject_id,
            "isActive": True,
            "entries": [],
            "config": {
                "maxSlots": 31,
                "minMaxRule": True,
                "priorityMove": True,
                "maxAttempts": 3
            },
            "createdAt": datetime.utcnow()
        })
        return {"success": True, "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queues/subject/{subject_id}")
async def get_queue_by_subject(subject_id: str):
    queue = await db.queues.find_one({"subjectId": subject_id})
    if not queue:
        return None
    
    queue["_id"] = str(queue["_id"])
    
    for entry in queue.get("entries", []):
        if entry.get("userId"):
            user = await db.users.find_one({"_id": entry["userId"]})
            if user:
                entry["user"] = {
                    "_id": str(user["_id"]),
                    "fullName": user.get("fullName"),
                    "telegramId": user.get("telegramId"),
                    "username": user.get("username")
                }
    
    return queue

@app.post("/queues/join")
async def join_queue(entry: QueueEntry):
    try:
        queue = await db.queues.find_one({"_id": entry.queueId})
        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")
        
        if not queue.get("isActive", True):
            raise HTTPException(status_code=400, detail="Queue is closed")
        
        user = await db.users.find_one({"telegramId": entry.telegramId})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        entries = queue.get("entries", [])
        user_id = str(user["_id"])
        
        existing_entry = next((e for e in entries if e.get("userId") == user_id), None)
        if existing_entry:
            raise HTTPException(status_code=400, detail="Already in queue")
        
        if entry.position:
            position_taken = next((e for e in entries if e.get("position") == entry.position), None)
            if position_taken:
                raise HTTPException(status_code=400, detail="Position already taken")
        else:
            entry.position = len(entries) + 1
        
        new_entry = {
            "userId": user_id,
            "labNumber": entry.labNumber,
            "position": entry.position,
            "status": "waiting",
            "joinedAt": datetime.utcnow().isoformat()
        }
        
        entries.append(new_entry)
        
        await db.queues.update_one(
            {"_id": entry.queueId},
            {"$set": {"entries": entries}}
        )
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/queues/leave")
async def leave_queue(data: dict):
    try:
        queue_id = data.get("queueId")
        telegram_id = data.get("telegramId")
        
        user = await db.users.find_one({"telegramId": telegram_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user["_id"])
        
        queue = await db.queues.find_one({"_id": queue_id})
        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")
        
        entries = queue.get("entries", [])
        entries = [e for e in entries if e.get("userId") != user_id]
        
        await db.queues.update_one(
            {"_id": queue_id},
            {"$set": {"entries": entries}}
        )
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/queues/kick")
async def kick_from_queue(data: dict):
    try:
        queue_id = data.get("queueId")
        admin_tg_id = data.get("adminTgId")
        target_user_id = data.get("targetUserId")
        
        if not await is_admin(admin_tg_id):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        queue = await db.queues.find_one({"_id": queue_id})
        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")
        
        entries = queue.get("entries", [])
        entries = [e for e in entries if e.get("userId") != target_user_id]
        
        await db.queues.update_one(
            {"_id": queue_id},
            {"$set": {"entries": entries}}
        )
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/queues/toggle")
async def toggle_queue(data: dict):
    try:
        queue_id = data.get("queueId")
        
        queue = await db.queues.find_one({"_id": queue_id})
        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")
        
        new_state = not queue.get("isActive", True)
        
        await db.queues.update_one(
            {"_id": queue_id},
            {"$set": {"isActive": new_state}}
        )
        
        return {"success": True, "isActive": new_state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/queues/status")
async def update_queue_status(update: QueueUpdate):
    try:
        queue = await db.queues.find_one({"_id": update.queueId})
        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")
        
        entries = queue.get("entries", [])
        
        for entry in entries:
            if entry.get("userId") == update.userId:
                entry["status"] = update.status
                break
        
        await db.queues.update_one(
            {"_id": update.queueId},
            {"$set": {"entries": entries}}
        )
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/topics")
async def create_topics_list(data: dict):
    try:
        subject_id = data.get("subjectId")
        max_topics = data.get("maxTopics", 30)
        
        result = await db.topics.insert_one({
            "subjectId": subject_id,
            "maxTopics": max_topics,
            "entries": [],
            "createdAt": datetime.utcnow()
        })
        
        return {"success": True, "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/topics/subject/{subject_id}")
async def get_topics_by_subject(subject_id: str):
    topics = await db.topics.find_one({"subjectId": subject_id})
    if not topics:
        return None
    
    topics["_id"] = str(topics["_id"])
    
    for entry in topics.get("entries", []):
        if entry.get("userId"):
            user = await db.users.find_one({"_id": entry["userId"]})
            if user:
                entry["user"] = {
                    "_id": str(user["_id"]),
                    "fullName": user.get("fullName"),
                    "telegramId": user.get("telegramId")
                }
    
    return topics

@app.post("/topics/claim")
async def claim_topic(entry: TopicEntry):
    try:
        topics = await db.topics.find_one({"_id": entry.subjectId})
        if not topics:
            raise HTTPException(status_code=404, detail="Topics list not found")
        
        user = await db.users.find_one({"telegramId": entry.telegramId})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        entries = topics.get("entries", [])
        user_id = str(user["_id"])
        
        topic_taken = next((e for e in entries if e.get("topicNumber") == entry.topicNumber), None)
        if topic_taken:
            raise HTTPException(status_code=400, detail="Topic already taken")
        
        new_entry = {
            "userId": user_id,
            "topicNumber": entry.topicNumber,
            "claimedAt": datetime.utcnow().isoformat()
        }
        
        entries.append(new_entry)
        
        await db.topics.update_one(
            {"_id": entry.subjectId},
            {"$set": {"entries": entries}}
        )
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/homework")
async def add_homework(hw: Homework):
    try:
        result = await db.homework.insert_one({
            "subject": hw.subject,
            "description": hw.description,
            "deadline": hw.deadline,
            "createdAt": datetime.utcnow()
        })
        return {"success": True, "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/homework")
async def get_homework():
    homework = await db.homework.find().sort("createdAt", -1).to_list(100)
    for hw in homework:
        hw["_id"] = str(hw["_id"])
    return homework

@app.delete("/homework/{hw_id}")
async def delete_homework(hw_id: str, telegram_id: int):
    try:
        if not await is_admin(telegram_id):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        await db.homework.delete_one({"_id": hw_id})
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/homework/{hw_id}")
async def update_homework(hw_id: str, hw: Homework, telegram_id: int):
    try:
        if not await is_admin(telegram_id):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        await db.homework.update_one(
            {"_id": hw_id},
            {"$set": {
                "subject": hw.subject,
                "description": hw.description,
                "deadline": hw.deadline,
                "updatedAt": datetime.utcnow()
            }}
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queues/{queue_id}/config")
async def get_queue_config(queue_id: str):
    try:
        queue = await db.queues.find_one({"_id": queue_id})
        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")
        
        return queue.get("config", {
            "maxSlots": 31,
            "minMaxRule": True,
            "priorityMove": True,
            "maxAttempts": 3
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/queues/{queue_id}/config")
async def update_queue_config(queue_id: str, config: QueueConfig):
    try:
        await db.queues.update_one(
            {"_id": queue_id},
            {"$set": {"config": config.dict()}}
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/topics/release")
async def release_topic(data: dict):
    try:
        subject_id = data.get("subjectId")
        telegram_id = data.get("telegramId")
        topic_number = data.get("topicNumber")
        
        topics = await db.topics.find_one({"_id": subject_id})
        if not topics:
            raise HTTPException(status_code=404, detail="Topics list not found")
        
        user = await db.users.find_one({"telegramId": telegram_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user["_id"])
        entries = topics.get("entries", [])
        
        entries = [e for e in entries if not (e.get("userId") == user_id and e.get("topicNumber") == topic_number)]
        
        await db.topics.update_one(
            {"_id": subject_id},
            {"$set": {"entries": entries}}
        )
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/queues/move")
async def move_in_queue(data: dict):
    try:
        queue_id = data.get("queueId")
        user_id = data.get("userId")
        new_position = data.get("newPosition")
        
        queue = await db.queues.find_one({"_id": queue_id})
        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")
        
        if not queue.get("config", {}).get("priorityMove", True):
            raise HTTPException(status_code=400, detail="Moving is disabled")
        
        entries = queue.get("entries", [])
        
        user_entry = next((e for e in entries if e.get("userId") == user_id), None)
        if not user_entry:
            raise HTTPException(status_code=404, detail="User not in queue")
        
        position_taken = next((e for e in entries if e.get("position") == new_position and e.get("userId") != user_id), None)
        if position_taken:
            raise HTTPException(status_code=400, detail="Position already taken")
        
        user_entry["position"] = new_position
        
        await db.queues.update_one(
            {"_id": queue_id},
            {"$set": {"entries": entries}}
        )
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)