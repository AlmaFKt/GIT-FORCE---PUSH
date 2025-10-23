import json
import websocket
from self_improving_debug_agent import self_improve

MCP_SERVER_URL = "ws://localhost:8765"

def send_diagnosis_to_cursor(diagnosis):
    """Envía el diagnóstico a Cursor mediante WebSocket."""
    ws = websocket.create_connection(MCP_SERVER_URL)
    message = {
        "sender": "DebugAgent",
        "recipient": "Cursor",
        "type": "diagnosis",
        "payload": diagnosis,
    }
    ws.send(json.dumps(message))
    ws.close()


if __name__ == "__main__":
    print("🚀 Ejecutando ciclo de diagnóstico y conexión con Cursor...\n")

    results = self_improve()

    for r in results:
        diagnosis = r["diagnosis"]
        logs = r.get("logs", [])

        diagnosis_payload = {
            "root_cause": diagnosis.get("root_cause"),
            "explanation": diagnosis.get("explanation"),
            "suggested_fix": diagnosis.get("suggested_fix"),
            "involved_logs": logs,  # logs relevantes al error
        }

        print("📤 Diagnosis Payload:")
        print(json.dumps(diagnosis_payload, indent=2, ensure_ascii=False))

        # Descomenta esta línea para habilitar el envío real a Cursor:
        # send_diagnosis_to_cursor(diagnosis_payload)
