import httpx
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Attempting to create and update shapes...")
    async with httpx.AsyncClient() as client:
        # This payload includes:
        # - An existing shape (rect1) with a modified x coordinate.
        # - An existing shape (circ1) with no changes.
        # - A new shape (new_shape_1).
        data = {
            "user": "demo_user",
            "data": [
                {
                    "id": "rect1",
                    "type": "rectangle",
                    "x": 150,  # Changed from 100
                    "y": 100,
                    "width": 300,
                    "height": 200,
                    "selectedBy": []
                },
                {
                    "id": "circ1",
                    "type": "circle",
                    "x": 600,
                    "y": 400,
                    "radius": 100,
                    "selectedBy": ["User2"]
                },
                {
                    "id": "new_shape_1",
                    "type": "circle",
                    "x": 300,
                    "y": 300,
                    "radius": 50,
                    "selectedBy": ["User1"]
                }
            ]
        }
        try:
            response = await client.post("http://127.0.0.1:8000/shapes", json=data, timeout=10)
            response.raise_for_status()
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response JSON: {response.json()}")
            logger.info("Shapes updated successfully.")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"An error occurred while requesting {e.request.url!r}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
