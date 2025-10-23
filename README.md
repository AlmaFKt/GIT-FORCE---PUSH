# GIT-FORCE---PUSH

Cómo correr el prototipo

Instala dependencias:

pip install openai websocket-client faiss-cpu
npm install ws


Inicia el MCP Server:

python mcp_server.py


Ejecuta el Debug Agent para analizar logs y enviar diagnósticos:

python debug_agent.py


Abre VS Code y activa la extensión Cursor Listener (extension.js) para recibir los mensajes y resaltar el código.