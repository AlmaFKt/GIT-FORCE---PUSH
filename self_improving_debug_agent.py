import os
import json
from openai import OpenAI

# Variables de entorno necesarias
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("Debes establecer la variable de entorno OPENAI_API_KEY antes de ejecutar el script.")

client = OpenAI(api_key=API_KEY)

LOGS_FILE = "logs/kavak_logs_1761252062628.json"
FEW_SHOTS_FILE = "few_shots.json"


# -------------------------------
# Utilidades
# -------------------------------
def safe_json_load(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            cleaned = text[text.index("{"): text.rindex("}") + 1]
            return json.loads(cleaned)
        except Exception:
            return {"error": "Invalid JSON", "raw": text}


# -------------------------------
# Diagnóstico agrupado de logs
# -------------------------------
def diagnose_logs_grouped(all_logs, few_shots=None):
    logs_text = json.dumps(all_logs, indent=2)
    few_shot_text = ""

    if few_shots:
        example_lines = []
        for ex in few_shots:
            logs_data = ex.get("logs") if isinstance(ex, dict) else None
            if logs_data is None:
                logs_data = ex.get("log") if isinstance(ex, dict) else None
            try:
                logs_json = json.dumps(logs_data, indent=2, ensure_ascii=False) if logs_data is not None else "<sin logs>"
            except Exception:
                logs_json = str(logs_data)
            diag_json = json.dumps(ex.get("diagnosis", {}), indent=2, ensure_ascii=False) if isinstance(ex, dict) else str(ex)
            example_lines.append(f"Ejemplo:\nLogs: {logs_json}\nDiagnóstico: {diag_json}\nFeedback Explanation: {ex.get('feedback_explanation', '<sin explanation>')}")
        few_shot_text = "\n".join(example_lines)

    prompt = f"""
Eres un experto en diagnóstico de sistemas distribuidos. Se te proporciona un conjunto de logs JSON.

Tu tarea es:
- Identificar **hasta 3 errores principales** distintos dentro de todos los logs.
- Agrupar los logs relacionados a cada error (basado en servicio, mensaje o contexto).
- Producir una salida **estrictamente JSON válida** con la estructura:
{{
  "errors": [
    {{
      "root_cause": "Descripción breve del problema principal",
      "explanation": "Explicación técnica detallada del error (por qué ocurrió)",
      "suggested_fix": "Recomendación de solución o mejora",
      "involved_logs": [ <lista de logs JSON que corresponden a este error> ]
    }}
  ]
}}

Reglas:
- Devuelve máximo 3 elementos dentro de "errors".
- Si no hay errores (nivel ERROR), devuelve: {{ "errors": [] }}
- Devuelve **solo JSON válido**, sin texto adicional ni explicaciones fuera del JSON.
- Usa los WARNING e INFO solo como contexto si ayudan a entender un error.
- NO repitas el mismo log en más de un grupo.

Ejemplos de formato (few-shots):
{few_shot_text if few_shot_text else "Ninguno"}

Logs del sistema a analizar:
{logs_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    response_text = response.choices[0].message.content
    print("Diagnosis Response Text:", response_text)
    return safe_json_load(response_text)


# -------------------------------
# Evaluación (LLM-as-a-Judge)
# -------------------------------
def judge_response(logs, diagnosis):
    logs_text = json.dumps(logs, indent=2)
    diagnosis_text = json.dumps(diagnosis, indent=2)

    prompt = f"""
Eres un juez experto en debugging. Evalúa el siguiente diagnóstico generado por un agente AI.

### Logs
{logs_text}

### Diagnóstico del agente
{diagnosis_text}

Evalúa del 1 al 10: relevancia, precisión técnica, utilidad, claridad.
Incluye explicación general en campo "explanation".

Devuelve únicamente JSON con:
{{
  "scores": {{
    "relevance": <1-10>,
    "precision": <1-10>,
    "utility": <1-10>,
    "clarity": <1-10>
  }},
  "overall_score": <promedio>,
  "explanation": "Texto explicativo general"
}}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    text = response.choices[0].message.content
    print("Judge Response Text:", text)
    return safe_json_load(text)


# -------------------------------
# Self-improvement loop
# -------------------------------
def self_improve(logs_file=LOGS_FILE, few_shots_file=FEW_SHOTS_FILE, logs_data=None):
    """
    logs_data: si se proporciona, se usa directamente en lugar de leer un archivo
    """
    if logs_data is not None:
        logs = logs_data
    else:
        with open(logs_file, "r", encoding="utf-8") as f:
            logs = json.load(f)

    few_shots = []
    if os.path.exists(few_shots_file):
        with open(few_shots_file, "r", encoding="utf-8") as f:
            few_shots = json.load(f)

    diagnosis = diagnose_logs_grouped(logs, few_shots=few_shots)
    print("Grouped Diagnosis:", diagnosis)

    history = []

    if "errors" in diagnosis:
        for err in diagnosis["errors"]:
            involved_logs = err.get("involved_logs", [])
            feedback = judge_response(involved_logs, err)
            err["feedback_explanation"] = feedback.get("explanation", "")
            history.append({"logs": involved_logs, "diagnosis": err, "feedback": feedback})

    # Guardar few-shots de alta calidad
    best = [h for h in history if "overall_score" in h["feedback"] and h["feedback"]["overall_score"] >= 8.5]
    new_few_shots = []
    for b in best:
        logs_for_shot = b.get("logs") or b.get("log") or []
        new_few_shots.append({
            "logs": logs_for_shot,
            "diagnosis": b.get("diagnosis", {}),
            "feedback_explanation": b["diagnosis"].get("feedback_explanation", "")
        })
    few_shots.extend(new_few_shots)

    with open(few_shots_file, "w", encoding="utf-8") as f:
        json.dump(few_shots, f, indent=2, ensure_ascii=False)

    print(f"Guardados {len(new_few_shots)} nuevos ejemplos de alta calidad.")
    return history


# -------------------------------
# Generador para WebSocket
# -------------------------------
async def self_improve_generator(logs):
    diagnosis = diagnose_logs_grouped(logs)
    if "errors" in diagnosis:
        for err in diagnosis["errors"]:
            involved_logs = err.get("involved_logs", [])
            feedback = judge_response(involved_logs, err)
            err["feedback_explanation"] = feedback.get("explanation", "")
            yield {"diagnosis": err, "feedback": feedback, "logs": involved_logs}


# -------------------------------
# Ejecución local
# -------------------------------
if __name__ == "__main__":
    print("Ejecutando agente de debugging auto-mejorable...\n")
    history = self_improve()
    print("\nResultados del ciclo de mejora:")
    print(json.dumps(history, indent=2, ensure_ascii=False))
