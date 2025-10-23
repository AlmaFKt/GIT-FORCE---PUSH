import os, json
from dotenv import load_dotenv
# Cargar variables desde .env (si existe). Esto permite mantener la clave fuera del código.
load_dotenv()
from openai import OpenAI
import pickle
import numpy as np
import faiss

# ------------------------
# 🔑 Configuración
# ------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Archivos
FEW_SHOTS_FILE = "few_shots.json"
LOGS_FILE = "logs/app_error.log"
RAG_INDEX_FILE = "code_index.faiss"
RAG_MAP_FILE = "code_map.pkl"
EMBED_MODEL = "text-embedding-3-small"

# ------------------------
# 1️⃣ Diagnosis Agent
# ------------------------
def diagnose_bug(log_text, few_shots=None):
    few_shot_text = ""
    if few_shots:
        few_shot_text = "\n".join([f"Ejemplo:\nLog: {ex['log']}\nDiagnóstico: {ex['diagnosis']}" for ex in few_shots])

    prompt = f"""
Analiza el siguiente log y genera:
1. Causa raíz
2. Explicación técnica
3. Fix sugerido
Responde en JSON.

{few_shot_text}

Log:
{log_text}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        return {"error": "No se pudo parsear la respuesta del modelo"}

# ------------------------
# 2️⃣ LLM-as-a-Judge Agent
# ------------------------
def judge_response(log_text, diagnosis):
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
# 3️⃣ RAG Context Retrieval (Opcional)
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
# 4️⃣ Self-Improvement Loop
# ------------------------
def self_improve(logs_file=LOGS_FILE, few_shots_file=FEW_SHOTS_FILE):
    # Cargar logs
    with open(logs_file, "r", encoding="utf-8") as f:
        logs = [line.strip() for line in f if line.strip()]

    # Cargar few-shots previos
    few_shots = []
    if os.path.exists(few_shots_file):
        with open(few_shots_file, "r", encoding="utf-8") as f:
            few_shots = json.load(f)

    history = []

    for log in logs:
        # Recuperar contexto opcional
        context_files = retrieve_context(log)
        context_text = ""
        for fpath in context_files:
            with open(fpath, "r", encoding="utf-8") as f:
                context_text += f"\n### {fpath}\n" + f.read()

        # Diagnosis
        diagnosis = diagnose_bug(log, few_shots=few_shots)
        # Agregar contexto a la evaluación si hay
        if context_text:
            diagnosis["context_files"] = context_files

        # Evaluación del juez
        feedback = judge_response(log, diagnosis)

        history.append({"log": log, "diagnosis": diagnosis, "feedback": feedback})

    # Filtrar los mejores y guardarlos como nuevos few-shots
    best = [h for h in history if "overall_score" in h["feedback"] and h["feedback"]["overall_score"] >= 8.5]
    new_few_shots = [{"log": b["log"], "diagnosis": b["diagnosis"]} for b in best]
    few_shots.extend(new_few_shots)

    with open(few_shots_file, "w", encoding="utf-8") as f:
        json.dump(few_shots, f, indent=2, ensure_ascii=False)

    print(f"Guardados {len(new_few_shots)} nuevos ejemplos de alta calidad.")
    return history

# ------------------------
# 5️⃣ Ejecución
# ------------------------
if __name__ == "__main__":
    result = self_improve()
    print("\nResumen de evaluación:")
    for r in result:
        print(f"- Log: {r['log'][:50]}... | Overall Score: {r.get('feedback', {}).get('overall_score', 'N/A')}")
