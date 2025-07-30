from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException
from .database import User, Task, SessionLocal
from .models import UserCreate, TaskCreate, TaskUpdate
import os

# Settings (replace with environment variables as appropriate)
SECRET_KEY = os.getenv("TASK_MANAGER_SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# PUBLIC_INTERFACE
def get_db():
    """Dependency for getting DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# PUBLIC_INTERFACE
def get_password_hash(password: str):
    """Hashes password."""
    return pwd_context.hash(password)

# PUBLIC_INTERFACE
def verify_password(plain_password, hashed_password):
    """Verifies password."""
    return pwd_context.verify(plain_password, hashed_password)

# PUBLIC_INTERFACE
def create_access_token(data: dict, expires_delta: timedelta = None):
    """Generates JWT for a user."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- User CRUD/AUTH ---

# PUBLIC_INTERFACE
def create_user(db: Session, user_in: UserCreate):
    """Creates a new user. Fails if email exists."""
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = get_password_hash(user_in.password)
    user = User(email=user_in.email, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# PUBLIC_INTERFACE
def authenticate_user(db: Session, email: str, password: str):
    """Authenticate user by email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

# PUBLIC_INTERFACE
def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

# --- Task CRUD/Logic ---

# PUBLIC_INTERFACE
def create_task_for_user(db: Session, user_id: int, task_in: TaskCreate):
    task = Task(**task_in.model_dump(), user_id=user_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

# PUBLIC_INTERFACE
def get_task(db: Session, user_id: int, task_id: int):
    return db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()

# PUBLIC_INTERFACE
def update_task(db: Session, user_id: int, task_id: int, task_in: TaskUpdate):
    task = get_task(db, user_id, task_id)
    if not task:
        return None
    for attr, val in task_in.model_dump(exclude_unset=True).items():
        setattr(task, attr, val)
    db.commit()
    db.refresh(task)
    return task

# PUBLIC_INTERFACE
def delete_task(db: Session, user_id: int, task_id: int):
    task = get_task(db, user_id, task_id)
    if not task:
        return False
    db.delete(task)
    db.commit()
    return True

# PUBLIC_INTERFACE
def list_tasks(
    db: Session,
    user_id: int,
    task_status: str = None,
    sort_by: str = None,
    sort_order: str = "asc",
    skip: int = 0,
    limit: int = 20
):
    query = db.query(Task).filter(Task.user_id == user_id)
    if task_status:
        query = query.filter(Task.status == task_status)
    if sort_by in ["created_at", "updated_at"]:
        field = getattr(Task, sort_by)
        field = field.desc() if sort_order == "desc" else field.asc()
        query = query.order_by(field)
    else:
        query = query.order_by(Task.created_at.desc())
    total = query.count()
    results = query.offset(skip).limit(limit).all()
    return results, total
