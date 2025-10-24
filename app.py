from fastapi import FastAPI, UploadFile, File, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
from self_improving_debug_agent import self_improve, self_improve_generator
import asyncio

app = FastAPI()

# Carpeta de frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# POST para ejecutar agente con logs subidos
@app.post("/run-agent/")
async def run_agent(log_file: UploadFile = File(...)):
    logs_json = json.loads(await log_file.read())
    history = self_improve(logs_data=logs_json)
    return history

# WebSocket para progreso en tiempo real
@app.websocket("/ws/progress")
async def websocket_progress(ws: WebSocket):
    await ws.accept()
    logs_text = await ws.receive_text()
    logs = json.loads(logs_text)
    async for update in self_improve_generator(logs):
        await ws.send_json(update)
        await asyncio.sleep(0.5)
    await ws.close()
