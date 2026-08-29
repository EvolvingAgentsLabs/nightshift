#!/usr/bin/env bash
# El `embedding_command` de referencia: envuelve al ollama LOCAL (ADR-003, enmienda
# 2026-08-29; el patrón es el de ADR-006 — un comando, no un servicio).
#
# Contrato: lee {"texts": [...]} por stdin, escribe {"vectors": [...]} por stdout.
# nightshift no sabe ni le importa qué hay del otro lado: la red la habla ESTE script,
# que es del usuario, contra su propio ollama en localhost.
#
# Config: {"embedding_command": ["sh", "tools/embed-ollama.sh"]}
# Modelo: EMBED_MODEL en el entorno, o embeddinggemma (el medido en la calibración).
set -euo pipefail
MODEL="${EMBED_MODEL:-embeddinggemma}"

# El stdin se captura ANTES de invocar python: un heredoc de script se comería el pipe.
ENTRADA="$(cat)"

ENTRADA="$ENTRADA" MODEL="$MODEL" python3 -c '
import json, os, subprocess, sys

texts = json.loads(os.environ["ENTRADA"]).get("texts") or []
if not texts:
    print(json.dumps({"vectors": []})); raise SystemExit(0)
payload = json.dumps({"model": os.environ["MODEL"], "input": texts})
out = subprocess.run(
    ["curl", "-s", "--max-time", "15", "http://localhost:11434/api/embed",
     "-d", payload], capture_output=True, text=True, timeout=20)
if out.returncode != 0:
    raise SystemExit(1)
print(json.dumps({"vectors": json.loads(out.stdout).get("embeddings") or []}))
'
