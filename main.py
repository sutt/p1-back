import os
import uvicorn
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import engine, Base, get_db
from models import Shape

load_dotenv()

app = FastAPI()

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/shapes")
async def get_shapes(db: AsyncSession = Depends(get_db)):
    """Returns the list of shapes."""
    result = await db.execute(select(Shape))
    shapes = result.scalars().all()
    return shapes

def main():
    """Starts the uvicorn server."""
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    main()
