# Container for Hugging Face Spaces (Docker SDK). Also works with plain `docker run -p 7860:7860`.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Ollama writes the stories in AI story mode (copied from the official image)
COPY --from=ollama/ollama:latest /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama/ollama:latest /usr/lib/ollama /usr/lib/ollama

# Hugging Face Spaces run the container as user 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    OLLAMA_HOST=127.0.0.1:11434 \
    PYTHONUNBUFFERED=1
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Download the story model at build time so the first story doesn't wait for it
RUN ollama serve > /tmp/ollama.log 2>&1 & \
    until ollama list > /dev/null 2>&1; do sleep 1; done; \
    ollama pull qwen2.5:3b

# English voice for the narration
RUN mkdir -p voices \
    && curl -fsSL -o voices/en_US-lessac-medium.onnx \
       https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx \
    && curl -fsSL -o voices/en_US-lessac-medium.onnx.json \
       https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

COPY --chown=user . .

EXPOSE 7860
CMD ["sh", "start.sh"]
