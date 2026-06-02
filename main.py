"""
Pyros Vision — Backend
FastAPI: REST + WebSocket

Rotas:
  GET  /                → health check
  GET  /api/focos       → focos NASA FIRMS (SP)
  GET  /api/status      → nível geral do sistema
  GET  /api/drones      → frota de drones de combate
  POST /api/analisar    → upload de imagem → Roboflow
  WS   /ws/camera       → stream câmera ao vivo → Roboflow

Integrantes:
  Gabriel Galerani  — RM 557421
  Leonardo Taschin  — RM 554583
"""

import base64
import os
import time
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from satelite import buscar_focos
from detector import detectar
from drones import listar_drones

load_dotenv()

app = FastAPI(
    title="Pyros Vision API",
    description="Detecção de queimadas — NASA FIRMS + Roboflow",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # em produção: restringir para seu domínio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache de focos (evita chamar NASA a cada request)
_cache: dict = {"dados": [], "ts": None}
_CACHE_TTL = 60  # segundos


# ── REST ─────────────────────────────────────────────────────────


@app.get("/")
async def health():
    return {
        "status": "ok",
        "sistema": "Pyros Vision API v3.0",
        "roboflow_project": os.environ.get("ROBOFLOW_PROJECT", "nao_configurado"),
    }


@app.get("/api/focos")
async def get_focos(force: bool = False):
    """Focos de calor da NASA FIRMS dentro do estado de SP."""
    agora = time.time()
    cache_valido = (
        _cache["ts"] is not None
        and agora - _cache["ts"] < _CACHE_TTL
        and not force
    )
    if not cache_valido:
        _cache["dados"] = buscar_focos()
        _cache["ts"] = agora

    focos    = _cache["dados"]
    criticos = sum(1 for f in focos if f.get("nivel") == "CRITICO")
    alertas  = sum(1 for f in focos if f.get("nivel") == "ALERTA")

    return {
        "focos":              focos,
        "total":              len(focos),
        "criticos":           criticos,
        "alertas":            alertas,
        "nivel_geral":        "CRITICO" if criticos > 0 else ("ALERTA" if alertas > 0 else "SEGURO"),
        "ultima_atualizacao": (
            datetime.fromtimestamp(_cache["ts"]).strftime("%H:%M:%S")
            if _cache["ts"] else None
        ),
    }


@app.get("/api/status")
async def get_status():
    """Status rápido — app mobile pode chamar periodicamente."""
    d = await get_focos()
    return {
        "nivel_geral": d["nivel_geral"],
        "total_focos": d["total"],
        "criticos":    d["criticos"],
        "timestamp":   datetime.utcnow().isoformat(),
    }


@app.get("/api/drones")
async def get_drones():
    """Frota de drones de combate a incêndio."""
    drones = listar_drones()
    disponiveis = sum(1 for d in drones if d["status"] == "DISPONIVEL")
    em_missao   = sum(1 for d in drones if d["status"] == "EM_MISSAO")
    manutencao  = sum(1 for d in drones if d["status"] == "MANUTENCAO")
    return {
        "drones":      drones,
        "total":       len(drones),
        "disponiveis": disponiveis,
        "em_missao":   em_missao,
        "manutencao":  manutencao,
    }


@app.post("/api/analisar")
async def analisar_imagem(file: UploadFile = File(...)):
    """
    Recebe uma imagem e retorna as detecções do Roboflow.
    Aceita JPEG ou PNG.
    """
    imagem_bytes = await file.read()
    resultado = detectar(imagem_bytes)
    return resultado


# ── WebSocket ────────────────────────────────────────────────────


@app.websocket("/ws/camera")
async def ws_camera(websocket: WebSocket):
    """
    Stream bidirecional de câmera.

    Cliente  → Servidor:  { "frame": "<JPEG em base64>" }
    Servidor → Cliente:   { "deteccoes": [...], "total": N,
                             "nivel_geral": "ALERTA", "fonte": "roboflow" }
    """
    await websocket.accept()
    try:
        while True:
            data  = await websocket.receive_json()
            frame_b64 = data.get("frame", "")
            if not frame_b64:
                continue

            imagem_bytes = base64.b64decode(frame_b64)
            resultado    = detectar(imagem_bytes)
            await websocket.send_json(resultado)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS] Erro: {e}")
