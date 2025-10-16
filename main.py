import os
import uvicorn
import logging
import datetime
import asyncio
from typing import List, Optional, Dict
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import auth
from database import engine, Base, get_db
from models import Shape, User
from seed import reset_shapes

# MANUAL INTERVENTION: AI routes are registered below
# Ensure OPENAI_API_KEY is set in .env file before using AI features
try:
    from routes.ai import router as ai_router
    AI_ROUTES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: AI routes not available - {e}")
    AI_ROUTES_AVAILABLE = False

load_dotenv()


# In-memory store for online users
HEARTBEAT_POLL_INTERVAL = 5  # seconds
GRACE_PERIOD = 5  # seconds


class UserStatus(BaseModel):
    userName: str
    created_at: datetime.datetime
    modified_at: datetime.datetime


online_users: Dict[str, UserStatus] = {}
online_users_lock = asyncio.Lock()


app = FastAPI()


class ShapeModel(BaseModel):
    id: str
    type: str
    x: int
    y: int
    width: Optional[int] = None
    height: Optional[int] = None
    radius: Optional[int] = None
    text: Optional[str] = None
    selectedBy: List[str] = []


class ShapesUpdateRequest(BaseModel):
    user: str
    data: List[ShapeModel]


class UserOnlineRequest(BaseModel):
    userName: str


class UserOnlineResponse(BaseModel):
    userName: str
    created_at: datetime.datetime


class UserResponse(BaseModel):
    username: str


logger = logging.getLogger(__name__)

@app.on_event("startup")
async def on_startup():
    try:
        async with engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database connection successful and tables created.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

if bool(int(os.getenv("SHAPES_DEBUG", 0))):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register AI routes if available
# MANUAL INTERVENTION: Ensure OPENAI_API_KEY is set in .env
if AI_ROUTES_AVAILABLE:
    app.include_router(ai_router)
    logger.info("AI routes registered successfully")
else:
    logger.warning("AI routes not registered - check OpenAI service installation")


# Frontend should store the token (e.g., in localStorage) and send it in the
# Authorization header for subsequent requests to protected routes.
# Example: Authorization: Bearer <token>
@app.post("/api/login", response_model=auth.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """
    Logs in a user and returns an access token.
    After successful login, the frontend should redirect to the /canvas route.
    """
    user = await auth.get_user(db, username=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = datetime.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/signup")
async def signup(user: auth.UserCreate, db: AsyncSession = Depends(get_db)):
    """Creates a new user."""
    db_user = await auth.get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    await db.commit()
    return {"message": "User created successfully"}


@app.get("/api/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(auth.get_current_user)):
    """Returns the current user's username."""
    return {"username": current_user.username}


@app.get("/api/shapes")
# TODO: Protect this route. Requires authentication.
async def get_shapes(db: AsyncSession = Depends(get_db)):
    """Returns the list of shapes."""
    result = await db.execute(select(Shape))
    shapes = result.scalars().all()
    return shapes


@app.post("/api/shapes")
# TODO: Protect this route. Requires authentication.
async def create_or_update_shapes(request: ShapesUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Creates new shapes or updates existing ones from the provided list."""
    # Validate that each shape has at most one user in selectedBy
    for s in request.data:
        if len(s.selectedBy) > 1:
            raise HTTPException(
                status_code=400,
                detail=f"Shape {s.id} has multiple users in selectedBy. Only one user allowed per shape."
            )
        await db.merge(Shape(**s.model_dump()))

    await db.commit()

    return {"message": "Shapes updated successfully"}


def _get_and_prune_online_users() -> List[UserOnlineResponse]:
    """
    Prunes stale users and returns a sorted list of online users.
    This function is not thread-safe and should be called within a lock.
    """
    now = datetime.datetime.utcnow()
    stale_users = [
        userName
        for userName, user_status in online_users.items()
        if (
            now - user_status.modified_at
            > datetime.timedelta(seconds=HEARTBEAT_POLL_INTERVAL + GRACE_PERIOD)
        )
    ]

    for userName in stale_users:
        del online_users[userName]

    sorted_users = sorted(online_users.values(), key=lambda u: u.created_at)
    return [
        UserOnlineResponse(userName=u.userName, created_at=u.created_at)
        for u in sorted_users
    ]


@app.get("/api/user_online", response_model=List[UserOnlineResponse])
# TODO: Protect this route. Requires authentication.
async def get_online_users():
    """Returns the list of currently online users."""
    async with online_users_lock:
        return _get_and_prune_online_users()


@app.post("/api/user_online", response_model=List[UserOnlineResponse])
# TODO: Protect this route. Requires authentication.
async def user_heartbeat(request: UserOnlineRequest):
    """Registers a user heartbeat and returns the list of currently online users."""
    async with online_users_lock:
        now = datetime.datetime.utcnow()
        userName = request.userName
        if userName not in online_users:
            online_users[userName] = UserStatus(
                userName=userName,
                created_at=now,
                modified_at=now,
            )
        else:
            online_users[userName].modified_at = now

        return _get_and_prune_online_users()


@app.post("/api/reset_data")
# TODO: Protect this route. Requires authentication.
async def reset_data():
    """Resets the shapes data to the initial seed data."""
    await reset_shapes()
    return {"message": "Data reset successfully"}


def main():
    """Starts the uvicorn server."""
    port = int(os.getenv("SHAPES_PORT", 8000))
    reload = bool(int(os.getenv("SHAPES_DEBUG", 0)))
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=reload,
    )

if __name__ == "__main__":
    main()
