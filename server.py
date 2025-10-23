import os
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Any, Dict
from fastapi import FastAPI
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="MCP Server")
client = OpenAI(api_key=openai_api_key)

# Definir herramientas
TOOLS = [
    {
        "name": "get_user",
        "description": "Obtiene la información de un usuario por su ID.",
        "parameters": {"id": "string"}
    },
    {
        "name": "sum_numbers",
        "description": "Suma dos números.",
        "parameters": {"a": "number", "b": "number"}
    }
]

#Modelo de Pydantic que define la estructura de la consulta al MCP
class MCPRequest(BaseModel):
    method: str
    params: Dict[str, Any] | None = None

# Endpoint que muestra todas las herramientas que posee el sistema
@app.get("/mcp/tools")
async def get_tools():
    return {"tools": TOOLS}

# Analizador
@app.post("/analyze_logs")
async def analyze_logs(data: dict):
    logs = data["logs"]
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": f"Analiza estos logs:\n{logs}"}
        ]
    )
    return {"summary": resp.choices[0].message.content}

# Comprobar ejecucion del servidor
@app.get("/")
async def root():
    return {"message": "Servidor MCP activo"}