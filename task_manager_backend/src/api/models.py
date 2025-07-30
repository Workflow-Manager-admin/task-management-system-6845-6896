from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from enum import Enum
import datetime

class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    completed = "completed"

# PUBLIC_INTERFACE
class UserCreate(BaseModel):
    """Model for new user signup."""
    email: EmailStr = Field(..., description="User's email")
    password: str = Field(..., min_length=6, description="Password")

# PUBLIC_INTERFACE
class UserLogin(BaseModel):
    """Model for user login."""
    email: EmailStr
    password: str

# PUBLIC_INTERFACE
class UserOut(BaseModel):
    """Model for user output."""
    id: int
    email: EmailStr

# PUBLIC_INTERFACE
class Token(BaseModel):
    """JWT access token with type."""
    access_token: str
    token_type: str = "bearer"

# PUBLIC_INTERFACE
class TaskBase(BaseModel):
    """Base properties for tasks."""
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Description of the task")
    status: TaskStatus = Field(TaskStatus.todo, description="Status of the task")

# PUBLIC_INTERFACE
class TaskCreate(TaskBase):
    """Properties for creating a task."""
    pass

# PUBLIC_INTERFACE
class TaskUpdate(BaseModel):
    """Properties for updating a task."""
    title: Optional[str]
    description: Optional[str]
    status: Optional[TaskStatus]

# PUBLIC_INTERFACE
class TaskOut(TaskBase):
    """Task as returned to the client."""
    id: int
    user_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

# PUBLIC_INTERFACE
class TaskList(BaseModel):
    """Response model for a task list."""
    tasks: List[TaskOut]
    total: int

