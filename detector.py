"""
Pyros Vision — Detector (Roboflow)
Envia imagem para a API hosted do Roboflow e retorna bounding boxes.
"""

import base64
import os
import requests


ROBOFLOW_API_KEY = os.environ.get("ROBOFLOW_API_KEY", "")
ROBOFLOW_PROJECT = os.environ.get("ROBOFLOW_PROJECT", "")
ROBOFLOW_VERSION = os.environ.get("ROBOFLOW_VERSION", "1")


def _nivel(confidence: float) -> str:
    if confidence >= 0.80:
        return "CRITICO"
    if confidence >= 0.50:
        return "ALERTA"
    return "MONITORANDO"


def detectar(imagem_bytes: bytes) -> dict:
    """
    Recebe bytes de uma imagem (JPEG/PNG) e retorna detecções do Roboflow.

    Retorno:
      {
        "deteccoes": [{"classe": "fire", "confianca": 0.95, "nivel": "CRITICO",
                        "x": 100, "y": 200, "largura": 50, "altura": 60}, ...],
        "total": 2,
        "nivel_geral": "CRITICO",
        "fonte": "roboflow" | "indisponivel"
      }
    """
    if not ROBOFLOW_API_KEY or not ROBOFLOW_PROJECT:
        return _resposta_vazia("roboflow_nao_configurado")

    imagem_b64 = base64.b64encode(imagem_bytes).decode("utf-8")
    url = (
        f"https://detect.roboflow.com/{ROBOFLOW_PROJECT}/{ROBOFLOW_VERSION}"
        f"?api_key={ROBOFLOW_API_KEY}"
    )

    try:
        resp = requests.post(
            url,
            data=imagem_b64,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        resp.raise_for_status()
        predictions = resp.json().get("predictions", [])

        deteccoes = [
            {
                "classe":    p.get("class", "fire"),
                "confianca": round(p.get("confidence", 0), 3),
                "nivel":     _nivel(p.get("confidence", 0)),
                "x":         int(p.get("x", 0) - p.get("width", 0) / 2),
                "y":         int(p.get("y", 0) - p.get("height", 0) / 2),
                "largura":   int(p.get("width", 0)),
                "altura":    int(p.get("height", 0)),
            }
            for p in predictions
        ]

        criticos = sum(1 for d in deteccoes if d["nivel"] == "CRITICO")
        alertas  = sum(1 for d in deteccoes if d["nivel"] == "ALERTA")
        nivel_geral = "CRITICO" if criticos > 0 else ("ALERTA" if alertas > 0 else "SEGURO")

        return {
            "deteccoes":   deteccoes,
            "total":       len(deteccoes),
            "nivel_geral": nivel_geral,
            "fonte":       "roboflow",
        }

    except Exception:
        return _resposta_vazia("indisponivel")


def _resposta_vazia(fonte: str) -> dict:
    return {"deteccoes": [], "total": 0, "nivel_geral": "SEGURO", "fonte": fonte}
