import json
import websocket
from self_improving_debug_agent import self_improve

MCP_SERVER_URL = "ws://localhost:8765"

def send_diagnosis_to_cursor(diagnosis):
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
    results = self_improve()

    for r in results:
        # Extraemos archivos del contexto si existen, y líneas ejemplo
        context_files = r["diagnosis"].get("context_files", [])
        diagnosis_payload = {
            "log": r["log"],
            "root_cause": r["diagnosis"].get("root_cause"),
            "files": [{"path": f, "lines": list(range(1, 6))} for f in context_files],
            "suggested_fix": r["diagnosis"].get("suggested_fix"),
        }
        print("Diagnosis Payload:", json.dumps(diagnosis_payload, indent=2))
        # send_diagnosis_to_cursor(diagnosis_payload)
