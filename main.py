from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import pytchat
import asyncio
import requests
import re

# Replace with your actual handle
CHANNEL_HANDLE = "@climbby"

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
active_chat_task = None

def get_live_video_id():
    """Scrapes the channel's live URL to find the active stream ID."""
    try:
        url = f"https://www.youtube.com/{CHANNEL_HANDLE}/live"
        response = requests.get(url, timeout=5)
        match = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', response.text)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Error fetching live ID: {e}")
    return None

async def chat_listener(video_id: str):
    """Connects to the chat and broadcasts messages."""
    print(f"Connecting to chat for stream: {video_id}")
    chat = pytchat.create(video_id=video_id)
    
    try:
        while chat.is_alive():
            for c in chat.get().sync_items():
                full_message = ""
                try:
                    for part in c.messageEx:
                        if isinstance(part, str):
                            full_message += part
                        elif isinstance(part, dict):
                            url = part.get("url") or part.get("src")
                            if url:
                                full_message += f'<img class="emoji" src="{url}">'
                            else:
                                full_message += part.get("txt", "")
                        else:
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
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        print("Chat listener stopped.")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- WEBHOOK ENDPOINTS ---

@app.get("/start")
async def start_stream():
    global active_chat_task
    
    # Don't start a new listener if one is already running
    if active_chat_task and not active_chat_task.done():
        return {"status": "Chat is already being monitored."}

    video_id = get_live_video_id()
    if not video_id:
        return {"status": "Error: Could not find a live stream. Make sure you are live first."}

    # Start the chat listener in the background
    active_chat_task = asyncio.create_task(chat_listener(video_id))
    await manager.broadcast({"type": "status", "status": "connected"}) # ADD THIS
    return {"status": "Success", "video_id": video_id}

@app.get("/stop")
async def stop_stream():
    global active_chat_task
    if active_chat_task and not active_chat_task.done():
        active_chat_task.cancel()
        await manager.broadcast({"type": "status", "status": "disconnected"})
        return {"status": "Stopped monitoring chat."}
    return {"status": "No active chat monitor to stop."}

# --- STANDARD ENDPOINTS ---

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
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)