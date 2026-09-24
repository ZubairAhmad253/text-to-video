#!/bin/sh
# Container start: run Ollama in the background, then the web server on the port Spaces expects.
ollama serve > /tmp/ollama.log 2>&1 &
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port 7860
