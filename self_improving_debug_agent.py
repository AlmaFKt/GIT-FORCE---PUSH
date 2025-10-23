import os, json, pickle
from openai import OpenAI
import numpy as np
import faiss
import re

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

FEW_SHOTS_FILE = "few_shots.json"
LOGS_FILE = "logs/kavak_logs_1761252062628.json"  # ahora JSON
RAG_INDEX_FILE = "code_index.faiss"
RAG_MAP_FILE = "code_map.pkl"
EMBED_MODEL = "text-embedding-3-small"

def safe_json_load(text):
    try:
        # Busca la primera ocurrencia de {...} grande
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except json.JSONDecodeError:
        pass
    return {"error": "No se pudo parsear la respuesta del modelo"}

# ------------------------
# Diagnosis Agent
# ------------------------
def diagnose_bug(log_entry, related_logs=None, few_shots=None):
    """
    Diagnostica un log individual considerando logs relacionados para detectar patrones de error.
    - log_entry: dict del log actual
    - related_logs: lista de logs relacionados al mismo error (opcional)
    - few_shots: ejemplos previos de diagnosis
    """
    # Convertimos los logs a string
    log_text = json.dumps(log_entry, indent=2)
    related_text = ""
    if related_logs:
        related_text = "\n".join([json.dumps(l, indent=2) for l in related_logs])

    few_shot_text = ""
    if few_shots:
        few_shot_text = "\n".join([
            f"Ejemplo:\nLog: {json.dumps(ex['log'], indent=2)}\nDiagnóstico: {json.dumps(ex['diagnosis'], indent=2)}"
            for ex in few_shots
        ])

    prompt = f"""
Analiza los logs JSON proporcionados y genera un diagnóstico en **estrictamente JSON válido**.
- Identifica si el log actual pertenece al mismo error que otros logs relacionados.
- Agrupa los logs que correspondan al mismo problema.
- Devuelve un solo objeto JSON con la siguiente estructura:

{{
  "root_cause": "Descripción de la causa raíz del error",
  "explanation": "Explicación técnica detallada del error",
  "suggested_fix": "Recomendación de solución o fix",
  "involved_logs": [<lista de logs JSON involucrados en este error>]
}}

- Devuelve **solo JSON**, sin explicaciones adicionales.
- Usa los siguientes ejemplos como guía (few-shots):

{few_shot_text}

Log a analizar:
{log_text}

Logs relacionados:
{related_text if related_text else "Ninguno"}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = response.choices[0].message.content
    print("Diagnosis Response Text:", response_text)
    return safe_json_load(response_text)


# ------------------------
# LLM-as-a-Judge Agent
# ------------------------
def judge_response(log_entry, diagnosis):
    log_text = json.dumps(log_entry, indent=2)
    prompt = f"""
Eres un evaluador técnico experto.
Dada la siguiente respuesta técnica:

Log:
{log_text}

Diagnóstico:
{diagnosis}

Evalúa en JSON con estos campos:
- accuracy_score (1-10)
- clarity_score (1-10)
- usefulness_score (1-10)
- overall_score (1-10)
- comments (breve comentario sobre la evaluación)
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        return {"error": "No se pudo parsear la evaluación del juez"}

# ------------------------
# RAG Context Retrieval (Opcional)
# ------------------------
def retrieve_context(query, top_k=3):
    if not os.path.exists(RAG_INDEX_FILE) or not os.path.exists(RAG_MAP_FILE):
        return []

    with open(RAG_MAP_FILE, "rb") as f:
        file_map = pickle.load(f)
    index = faiss.read_index(RAG_INDEX_FILE)

    emb = client.embeddings.create(input=query, model=EMBED_MODEL).data[0].embedding
    D, I = index.search(np.array([emb]).astype("float32"), top_k)
    return [file_map[i] for i in I[0]]

# ------------------------
# Self-Improvement Loop
# ------------------------
def self_improve(logs_file=LOGS_FILE, few_shots_file=FEW_SHOTS_FILE):
    with open(logs_file, "r", encoding="utf-8") as f:
        logs_json = json.load(f)

    logs = logs_json  # cada entry es un dict completo

    few_shots = []
    if os.path.exists(few_shots_file):
        with open(few_shots_file, "r", encoding="utf-8") as f:
            few_shots = json.load(f)

    history = []

    for log_entry in logs:
        context_files = retrieve_context(json.dumps(log_entry))
        context_text = ""
        for fpath in context_files:
            with open(fpath, "r", encoding="utf-8") as f:
                context_text += f"\n### {fpath}\n" + f.read()

        diagnosis = diagnose_bug(log_entry, few_shots=few_shots)
        print("Diagnosis:", diagnosis)
        if context_text:
            diagnosis["context_files"] = context_files

        feedback = judge_response(log_entry, diagnosis)
        history.append({"log": log_entry, "diagnosis": diagnosis, "feedback": feedback})

    # Guardar los mejores ejemplos como few-shots
    best = [h for h in history if "overall_score" in h["feedback"] and h["feedback"]["overall_score"] >= 8.5]
    new_few_shots = [{"log": b["log"], "diagnosis": b["diagnosis"]} for b in best]
    few_shots.extend(new_few_shots)

    with open(few_shots_file, "w", encoding="utf-8") as f:
        json.dump(few_shots, f, indent=2, ensure_ascii=False)

    print(f"Guardados {len(new_few_shots)} nuevos ejemplos de alta calidad.")
    return history
