import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "").strip()
DB_NAME = os.getenv("MONGO_DB", "Family_Relations").strip()
PERSONS_COLLECTION = os.getenv("MONGO_PERSONS_COLLECTION", "persons").strip()
RELATIONS_COLLECTION = os.getenv("MONGO_RELATIONS_COLLECTION", "relationships").strip()
USERS_COLLECTION = os.getenv("MONGO_USERS_COLLECTION", "users").strip()
JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip()
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "").strip()
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5"))

if not MONGO_URI:
    raise RuntimeError("MONGO_URI is not configured")
if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must contain at least 32 characters")
if not ADMIN_PASSWORD_HASH:
    raise RuntimeError("ADMIN_PASSWORD_HASH is not configured")
if MAX_UPLOAD_MB < 1 or MAX_UPLOAD_MB > 20:
    raise RuntimeError("MAX_UPLOAD_MB must be between 1 and 20")

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
    socketTimeoutMS=20000,
    retryWrites=True,
    appname="MyFamilyRelations",
)
db = client[DB_NAME]
persons = db[PERSONS_COLLECTION]
relationships = db[RELATIONS_COLLECTION]
users = db[USERS_COLLECTION]

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)

RELATION_OPTIONS = [
    "Father", "Mother", "Spouse", "Son", "Daughter", "Brother", "Sister",
    "Grandfather", "Grandmother", "Uncle", "Aunt", "Cousin", "Nephew", "Niece", "Other"
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    client.admin.command("ping")
    persons.create_index([("Person_id", ASCENDING)], unique=True, sparse=True)
    persons.create_index([("Name", ASCENDING)])
    relationships.create_index([("person_id_1", ASCENDING), ("person_id_2", ASCENDING)], unique=True)
    users.create_index("username", unique=True)
    yield
    client.close()


app = FastAPI(
    title="My Family Relations API",
    version="1.0.0",
    docs_url="/api/docs" if os.getenv("ENABLE_API_DOCS", "false").lower() == "true" else None,
    redoc_url=None,
    lifespan=lifespan,
)

# Same-origin production deployment needs no cross-origin access. If a separate
# frontend is deployed later, set CORS_ORIGINS to a comma-separated allowlist.
cors_origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


class LoginIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    identifier: str = Field(min_length=1, max_length=160)


class MemberIn(BaseModel):
    Name: str = Field(min_length=1, max_length=120)
    DOB: str = ""
    DOD: str = ""
    Mobile: str = Field(default="", max_length=40)
    Mail_id: str = Field(default="", max_length=160)
    Gender: str = Field(default="", max_length=30)


class RelationIn(BaseModel):
    relative_person_id: int
    relation: str = Field(min_length=1, max_length=50)
    how_related: str = Field(default="", max_length=500)


def serialize(doc):
    if not doc:
        return None
    out = {k: v for k, v in doc.items() if k not in ("_id", "Embedding", "Profile_Pic")}
    pic = doc.get("Profile_Pic")
    out["has_photo"] = bool(pic)
    return out


def token_for(user):
    payload = {
        "sub": str(user.get("Person_id")),
        "role": user.get("role", "user"),
        "name": user.get("Name", ""),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if not creds:
        raise HTTPException(401, "Login required")
    try:
        return jwt.decode(creds.credentials, JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(401, "Invalid or expired login")


def is_admin(user):
    return user.get("role") == "admin"


def next_person_id():
    counter = db["counters"].find_one_and_update(
        {"_id": "person_id"},
        {"$inc": {"seq_value": 1}},
        upsert=True,
        return_document=True,
    )
    return int(counter["seq_value"])


def find_person(pid):
    return persons.find_one({"Person_id": int(pid)})


@app.get("/api/health")
def health():
    try:
        client.admin.command("ping")
        return {"ok": True, "database": DB_NAME}
    except PyMongoError:
        raise HTTPException(503, "Database unavailable")


@app.post("/api/login")
def login(data: LoginIn):
    if data.name.strip().lower() == ADMIN_USERNAME.lower() and pwd.verify(data.identifier, ADMIN_PASSWORD_HASH):
        return {
            "token": token_for({"Person_id": "admin", "Name": ADMIN_USERNAME, "role": "admin"}),
            "user": {"Name": ADMIN_USERNAME, "role": "admin"},
        }

    safe_name = re.escape(data.name.strip())
    doc = persons.find_one({"Name": {"$regex": f"^{safe_name}$", "$options": "i"}})
    if not doc:
        raise HTTPException(401, "Member not found")

    mobile = str(doc.get("Mobile", "")).strip()
    email = str(doc.get("Mail_id", "")).strip()
    if data.identifier.strip() not in {mobile, email}:
        raise HTTPException(401, "Mobile or Mail ID does not match")

    return {
        "token": token_for({"Person_id": doc.get("Person_id"), "Name": doc.get("Name"), "role": "user"}),
        "user": serialize(doc),
    }


@app.get("/api/me")
def me(user=Depends(current_user)):
    if is_admin(user):
        return {"Name": ADMIN_USERNAME, "role": "admin"}
    doc = find_person(user["sub"])
    if not doc:
        raise HTTPException(404, "Profile not found")
    return serialize(doc)


@app.get("/api/members")
def members(q: str = "", user=Depends(current_user)):
    regex = {"$regex": re.escape(q.strip()), "$options": "i"} if q.strip() else {"$exists": True}
    projection = {"_id": 0, "Person_id": 1, "Name": 1, "Gender": 1, "DOB": 1, "DOD": 1}
    docs = persons.find({"Name": regex}, projection).sort("Name", 1).limit(100)
    return [dict(d) for d in docs]


@app.get("/api/members/{pid}")
def member(pid: int, user=Depends(current_user)):
    doc = find_person(pid)
    if not doc:
        raise HTTPException(404, "Member not found")
    if not is_admin(user) and int(user["sub"]) != pid:
        doc = {k: doc.get(k) for k in ["Person_id", "Name", "Gender", "DOB", "DOD"]}
    return serialize(doc)


@app.post("/api/members")
def add_member(data: MemberIn, user=Depends(current_user)):
    if not is_admin(user):
        raise HTTPException(403, "Only admin can add members")
    safe_name = re.escape(data.Name.strip())
    if persons.find_one({"Name": {"$regex": f"^{safe_name}$", "$options": "i"}}):
        raise HTTPException(409, "A member with this name already exists")
    pid = next_person_id()
    doc = data.model_dump()
    doc.update({"Person_id": pid, "Profile_Pic": None, "Embedding": None})
    try:
        persons.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(409, "Person ID collision; please retry")
    return serialize(doc)


@app.put("/api/members/{pid}")
def update_member(pid: int, data: MemberIn, user=Depends(current_user)):
    if not is_admin(user) and int(user["sub"]) != pid:
        raise HTTPException(403, "You can edit only your own profile")
    if not find_person(pid):
        raise HTTPException(404, "Member not found")
    persons.update_one({"Person_id": pid}, {"$set": data.model_dump()})
    return serialize(find_person(pid))


@app.delete("/api/members/{pid}")
def delete_member(pid: int, user=Depends(current_user)):
    if not is_admin(user):
        raise HTTPException(403, "Only admin can delete members")
    persons.delete_one({"Person_id": pid})
    relationships.delete_many({"$or": [{"person_id_1": pid}, {"person_id_2": pid}]})
    return {"ok": True}


@app.get("/api/relations/{pid}")
def get_relations(pid: int, user=Depends(current_user)):
    if not is_admin(user) and int(user["sub"]) != pid:
        raise HTTPException(403, "Access denied")
    rows = []
    for rel in relationships.find({"person_id_2": pid}):
        person = find_person(rel.get("person_id_1"))
        if person:
            rows.append({
                "person": serialize(person),
                "relation": rel.get("relation", "Unknown"),
                "how_related": rel.get("how_related", ""),
            })
    return rows


@app.post("/api/relations/{pid}")
def add_relation(pid: int, data: RelationIn, user=Depends(current_user)):
    if not is_admin(user) and int(user["sub"]) != pid:
        raise HTTPException(403, "You can edit only your own relationships")
    if pid == data.relative_person_id:
        raise HTTPException(400, "You cannot create a relationship with yourself")
    if not find_person(pid) or not find_person(data.relative_person_id):
        raise HTTPException(404, "Member not found")
    if data.relation not in RELATION_OPTIONS:
        raise HTTPException(400, "Invalid relation")
    try:
        relationships.insert_one({
            "person_id_1": data.relative_person_id,
            "person_id_2": pid,
            "relation": data.relation,
            "how_related": data.how_related,
        })
    except DuplicateKeyError:
        raise HTTPException(409, "This relationship already exists")
    return {"ok": True}


@app.get("/api/relation/{pid}/{target}")
def find_relation(pid: int, target: int, user=Depends(current_user)):
    if not is_admin(user) and int(user["sub"]) != pid:
        raise HTTPException(403, "Access denied")
    rel = relationships.find_one({"person_id_1": target, "person_id_2": pid})
    if not rel:
        return {"found": False}
    person = find_person(target)
    return {"found": True, "person": serialize(person), "relation": rel.get("relation"), "how_related": rel.get("how_related")}


@app.post("/api/members/{pid}/photo")
async def upload_photo(pid: int, file: UploadFile = File(...), user=Depends(current_user)):
    if not is_admin(user) and int(user["sub"]) != pid:
        raise HTTPException(403, "You can change only your own photo")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(400, "Please upload an image")
    data = await file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, "Image is too large")
    persons.update_one({"Person_id": pid}, {"$set": {"Profile_Pic": data, "photo_content_type": file.content_type}})
    return {"ok": True}


@app.get("/api/members/{pid}/photo")
def photo(pid: int, user=Depends(current_user)):
    # Photo access is authenticated to avoid turning family photos into public URLs.
    doc = find_person(pid)
    if not doc or not doc.get("Profile_Pic"):
        raise HTTPException(404, "Photo not found")
    if not is_admin(user) and int(user["sub"]) != pid:
        raise HTTPException(403, "Access denied")
    return Response(content=bytes(doc["Profile_Pic"]), media_type=doc.get("photo_content_type", "image/jpeg"))


# Keep this mount LAST so /api/* routes are matched before the SPA fallback.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
