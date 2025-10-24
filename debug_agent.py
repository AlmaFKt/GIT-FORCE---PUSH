import json
import asyncio
import websocket
from self_improving_debug_agent import self_improve_generator

# URL del servidor Cursor
MCP_SERVER_URL = "ws://localhost:8765"

def send_diagnosis_to_cursor(diagnosis):
    """Envía el diagnóstico a Cursor mediante WebSocket."""
    try:
        ws = websocket.create_connection(MCP_SERVER_URL)
        message = {
            "sender": "DebugAgent",
            "recipient": "Cursor",
            "type": "diagnosis",
            "payload": diagnosis,
        }
        ws.send(json.dumps(message))
        ws.close()
        print("Enviado a Cursor")
    except Exception as e:
        print("Error enviando a Cursor:", e)


async def run_agent_with_logs(log_file_path):
    """Ejecuta el agente usando logs desde un archivo y envía cada diagnóstico a Cursor."""
    # Cargar logs desde archivo JSON
    with open(log_file_path, "r", encoding="utf-8") as f:
        logs_data = json.load(f)

    # Ejecutar el generador para progresos en tiempo real
    async for update in self_improve_generator(logs_data):
        diagnosis = update["diagnosis"]
        logs = update.get("logs", [])

        diagnosis_payload = {
            "root_cause": diagnosis.get("root_cause"),
            "explanation": diagnosis.get("explanation"),
            "suggested_fix": diagnosis.get("suggested_fix"),
            "involved_logs": logs,
        }

        print("Diagnosis Payload:")
        print(json.dumps(diagnosis_payload, indent=2, ensure_ascii=False))

        # Enviar a Cursor
        # send_diagnosis_to_cursor(diagnosis_payload)


if __name__ == "__main__":
    print("Ejecutando ciclo de diagnóstico y envío a Cursor...\n")

    # Cambia aquí por la ruta del archivo de logs que quieres analizar
    log_file_path = "mi_logs.json"

    asyncio.run(run_agent_with_logs(log_file_path))

    print("\nCiclo completado")
