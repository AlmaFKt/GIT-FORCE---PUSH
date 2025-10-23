from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Any, Dict

app = FastAPI(title="MCP Server")

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

# ⚙️ 4. Endpoint de ejecución — el modelo invoca una herramienta
@app.post("/mcp/execute")
async def execute_tool(request: MCPRequest):
    if request.method == "get_user":
        user_id = request.params.get("id")
        return {"result": {"id": user_id, "name": "Abraham", "role": "student"}}

    elif request.method == "sum_numbers":
        a = request.params.get("a", 0)
        b = request.params.get("b", 0)
        return {"result": a + b}

    else:
        return {"error": f"Herramienta desconocida: {request.method}"}

# Comprobar ejecucion del servidor
@app.get("/")
async def root():
    return {"message": "Servidor MCP activo"}
