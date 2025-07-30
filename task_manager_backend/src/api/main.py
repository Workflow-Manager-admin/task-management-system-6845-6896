from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import timedelta
from . import crud
from .models import (
    UserCreate, UserOut, Token,
    TaskCreate, TaskUpdate, TaskOut, TaskList, TaskStatus
)
import os

openapi_tags = [
    {"name": "auth", "description": "User authentication"},
    {"name": "tasks", "description": "CRUD operations on tasks"},
]

app = FastAPI(
    title="Task Manager API",
    description="API for user authentication and task management.",
    version="1.0.0",
    openapi_tags=openapi_tags
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

SECRET_KEY = os.getenv("TASK_MANAGER_SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(crud.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    return user

@app.get("/", tags=["health"])
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}

# --- Authentication API ---
@app.post("/auth/signup", response_model=UserOut, tags=["auth"], summary="User signup")
def signup(user_in: UserCreate, db: Session = Depends(crud.get_db)):
    """Register a new user."""
    user = crud.create_user(db, user_in)
    return UserOut(id=user.id, email=user.email)

@app.post("/auth/login", response_model=Token, tags=["auth"], summary="User login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(crud.get_db)):
    """Authenticate a user and obtain JWT access token."""
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = crud.create_access_token(
        data={"user_id": user.id}, expires_delta=timedelta(minutes=crud.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me", response_model=UserOut, tags=["auth"], summary="Get current user")
def get_me(current_user = Depends(get_current_user)):
    """Fetch the currently authenticated user's profile."""
    return UserOut(id=current_user.id, email=current_user.email)

# --- Task CRUD ---
@app.post("/tasks", response_model=TaskOut, tags=["tasks"], summary="Create a new task")
def create_task(task_in: TaskCreate, db: Session = Depends(crud.get_db), current_user=Depends(get_current_user)):
    """Create a new task for the authenticated user."""
    task = crud.create_task_for_user(db, current_user.id, task_in)
    return TaskOut(**task.__dict__)

@app.get("/tasks", response_model=TaskList, tags=["tasks"], summary="List tasks with filter/sort")
def list_tasks(
    status: Optional[TaskStatus] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(crud.get_db),
    current_user=Depends(get_current_user)
):
    """
    List tasks for the authenticated user, optionally filter by status and apply sorting and pagination.

    - **status**: Filter by task status (`todo`, `in_progress`, `completed`)
    - **sort_by**: Field to sort by (`created_at`, `updated_at`)
    - **sort_order**: `"asc"` or `"desc"`
    - **skip**: Number of records to skip
    - **limit**: Max records to return
    """
    tasks, total = crud.list_tasks(
        db, current_user.id,
        task_status=status.value if status else None,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit
    )
    tasks_out = [TaskOut(**task.__dict__) for task in tasks]
    return TaskList(tasks=tasks_out, total=total)

@app.get("/tasks/{task_id}", response_model=TaskOut, tags=["tasks"], summary="Get task by ID")
def get_task(task_id: int, db: Session = Depends(crud.get_db), current_user=Depends(get_current_user)):
    """Get a single task by ID."""
    task = crud.get_task(db, current_user.id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskOut(**task.__dict__)

@app.put("/tasks/{task_id}", response_model=TaskOut, tags=["tasks"], summary="Update a task")
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(crud.get_db),
    current_user=Depends(get_current_user)
):
    """Update an existing task."""
    task = crud.update_task(db, current_user.id, task_id, task_in)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskOut(**task.__dict__)

@app.delete("/tasks/{task_id}", tags=["tasks"], summary="Delete task", status_code=204)
def delete_task(task_id: int, db: Session = Depends(crud.get_db), current_user=Depends(get_current_user)):
    """Delete a task."""
    success = crud.delete_task(db, current_user.id, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return

