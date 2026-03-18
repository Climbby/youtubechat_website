from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from collections import deque
from dotenv import load_dotenv

import pytchat
import asyncio
import requests
import re
import os

load_dotenv()
CHANNEL_HANDLE = "@climbby"
NODE_LXC_IP = os.getenv("NODE_LXC_IP", "127.0.0.1")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.message_history = deque(maxlen=50)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        if message.get("type") != "status":
            self.message_history.append(message)

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
    global active_chat_task
    print(f"Connecting to chat for stream: {video_id}")
    
    try:
        while True:
            chat = await asyncio.to_thread(pytchat.create, video_id=video_id, interruptable=False)
            
            while chat.is_alive():
                chat_data = await asyncio.to_thread(chat.get)
                
                for c in chat_data.sync_items():
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
            
            # If the code reaches here, YouTube dropped the connection.
            print("Connection lost or session expired. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
            
    except asyncio.CancelledError:
        print("Chat listener stopped.")
    except Exception as e:
        print(f"CRASH ERROR: {e}") 
    finally:
        await manager.broadcast({"type": "status", "status": "disconnected"})

origins = [
    "https://youtube-chat-website.tail2fdcaf.ts.net",
    "http://localhost:8001",
]
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- WEBHOOK ENDPOINTS ---

@app.get("/start")
async def start_stream(video_id: str = None):
    global active_chat_task
    
    if active_chat_task and not active_chat_task.done():
        return {"status": "Chat is already being monitored."}

    # Use the provided ID, or scrape it if none is provided
    target_id = video_id if video_id else await asyncio.to_thread(get_live_video_id)
    
    if not target_id:
        return {"status": "Error: Could not find a live stream."}

    active_chat_task = asyncio.create_task(chat_listener(target_id))
    
    # Broadcast status change
    await manager.broadcast({"type": "status", "status": "connected"})
    
    return {"status": "Success", "video_id": target_id}

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

@app.get("/trigger-discord/{server_name}")
async def trigger_discord(server_name: str):
    video_id = await asyncio.to_thread(get_live_video_id)

    if video_id:
        current_url = f"https://www.youtube.com/watch?v={video_id}"
    else:
        current_url = f"https://www.youtube.com/@climbby/live"
    
    if server_name.lower() == "none":
        url = f"http://{NODE_LXC_IP}:3000/send?content={current_url}"
    else:
        url = f"http://{NODE_LXC_IP}:3000/send?content={current_url}&server={server_name}"
    
    try:
        response = await asyncio.to_thread(lambda: requests.get(url, timeout=40))
        return {"status": "success" if response.status_code == 200 else "error"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Send the current status immediately upon connection
    global active_chat_task
    if active_chat_task and not active_chat_task.done():
        await websocket.send_json({"type": "status", "status": "connected"})
    else:
        await websocket.send_json({"type": "status", "status": "disconnected"})

    for msg in manager.message_history:
        await websocket.send_json(msg)
        
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)