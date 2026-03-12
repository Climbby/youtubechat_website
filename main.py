from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles # New import

import pytchat
import asyncio
from contextlib import asynccontextmanager

VIDEO_ID = "XSXEaikz0Bc"

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

async def fetch_youtube_chat():
    chat = pytchat.create(video_id=VIDEO_ID)
    while True:
        if chat.is_alive():
            for c in chat.get().sync_items():
                full_message = ""
                try:
                    for part in c.messageEx:
                        if isinstance(part, str):
                            full_message += part
                        elif isinstance(part, dict):
                            # Try multiple keys just in case
                            url = part.get("url") or part.get("src")
                            if url:
                                full_message += f'<img class="emoji" src="{url}">'
                            else:
                                full_message += part.get("txt", "")
                        else:
                            # Try attribute access for objects
                            url = getattr(part, "url", None) or getattr(part, "src", None)
                            if url:
                                full_message += f'<img class="emoji" src="{url}">'
                            else:
                                full_message += getattr(part, "txt", str(part))
                except Exception:
                    full_message = c.message
                
                await manager.broadcast({
                    "author": c.author.name,
                    "authorImage": c.author.imageUrl,
                    "message": full_message
                })
        else:
            await asyncio.sleep(5)
            chat = pytchat.create(video_id=VIDEO_ID)
        await asyncio.sleep(0.5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background task
    task = asyncio.create_task(fetch_youtube_chat())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/manifest.json")
async def manifest():
    from fastapi.responses import FileResponse
    return FileResponse("static/manifest.json")

@app.get("/sw.js")
async def service_worker():
    from fastapi.responses import FileResponse
    return FileResponse("static/sw.js")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)