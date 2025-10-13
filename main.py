import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

shapes = [
    {'id': 'rect1', 'type': 'rectangle', 'x': 100, 'y': 100, 'width': 300, 'height': 200, 'selectedBy': []},
    {'id': 'circ1', 'type': 'circle', 'x': 600, 'y': 400, 'radius': 100, 'selectedBy': ['User2']},
]

@app.get("/shapes")
async def get_shapes():
    """Returns the list of shapes."""
    return shapes

def main():
    """Starts the uvicorn server."""
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    main()
