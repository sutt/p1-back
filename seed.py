import asyncio
import logging
from database import AsyncSessionLocal, engine
from models import Base, Shape

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        shapes_data = [
            Shape(id='rect1', type='rectangle', x=100, y=100, width=300, height=200, selectedBy=[]),
            Shape(id='circ1', type='circle', x=600, y=400, radius=100, selectedBy=['User2']),
        ]
        session.add_all(shapes_data)
        await session.commit()

async def main():
    logger.info("Seeding database...")
    await seed_data()
    logger.info("Database seeded.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
