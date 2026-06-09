"""
Pyros Vision — Detector (TFLite local)
Modelo: OpenMV YOLO fire/smoke (224×224, uint8)
Output shape: [1, 6, 1029] → 2 classes (fire=0, smoke=1)
"""

import io
import os
from typing import Optional
import numpy as np
from PIL import Image
import tensorflow as tf

_interp: Optional[tf.lite.Interpreter] = None
MODEL_PATH = os.environ.get("FIRE_MODEL_PATH", "model.tflite")

CLASSES    = ["fire", "smoke"]
CONF_THRES = {"fire": 0.25, "smoke": 0.15}
IOU_THRES  = 0.45
INPUT_SIZE = 224


def _carregar_modelo() -> tf.lite.Interpreter:
    global _interp
    if _interp is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"[detector] Modelo não encontrado: {MODEL_PATH}")
        print(f"[detector] Carregando modelo TFLite: {MODEL_PATH}")
        _interp = tf.lite.Interpreter(MODEL_PATH)
        _interp.allocate_tensors()
        print(f"[detector] Modelo pronto. Classes: {CLASSES}")
    return _interp


def _iou(box1: np.ndarray, box2: np.ndarray) -> float:
    """IoU entre dois boxes [x1, y1, x2, y2]."""
    xi1 = max(box1[0], box2[0]); yi1 = max(box1[1], box2[1])
    xi2 = min(box1[2], box2[2]); yi2 = min(box1[3], box2[3])
    inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    a1 = (box1[2]-box1[0]) * (box1[3]-box1[1])
    a2 = (box2[2]-box2[0]) * (box2[3]-box2[1])
    return inter / (a1 + a2 - inter + 1e-6)


def _nms(dets: list, iou_thres: float) -> list:
    if not dets:
        return []
    dets = sorted(dets, key=lambda d: d["confianca"], reverse=True)
    kept = []
    for d in dets:
        b = [d["x"], d["y"], d["x"] + d["largura"], d["y"] + d["altura"]]
        if all(_iou(b, [k["x"], k["y"], k["x"]+k["largura"], k["y"]+k["altura"]]) < iou_thres
               for k in kept):
            kept.append(d)
    return kept


def _nivel(confidence: float) -> str:
    if confidence >= 0.80:
        return "CRITICO"
    if confidence >= 0.50:
        return "ALERTA"
    return "MONITORANDO"


def _resposta_vazia(fonte: str) -> dict:
    return {"deteccoes": [], "total": 0, "nivel_geral": "SEGURO", "fonte": fonte}


async def detectar(imagem_bytes: bytes) -> dict:
    try:
        interp = _carregar_modelo()
        inp_det = interp.get_input_details()[0]
        out_det = interp.get_output_details()[0]

        # Pré-processamento: redimensiona para 224×224, uint8
        img = Image.open(io.BytesIO(imagem_bytes)).convert("RGB")
        orig_w, orig_h = img.size
        img_resized = img.resize((INPUT_SIZE, INPUT_SIZE))
        inp_arr = np.expand_dims(np.array(img_resized, dtype=np.uint8), axis=0)

        interp.set_tensor(inp_det["index"], inp_arr)
        interp.invoke()

        # Output: [1, 6, 1029] → transpõe para [1029, 6]
        raw = interp.get_tensor(out_det["index"])[0]  # [6, 1029]
        preds = raw.T                                  # [1029, 6]

        # Colunas: [x_c, y_c, w, h, score_fire, score_smoke] (normalizadas 0-1)
        deteccoes = []
        for row in preds:
            x_c, y_c, w, h = row[0], row[1], row[2], row[3]
            scores = row[4:]
            cls_idx = int(np.argmax(scores))
            conf = float(scores[cls_idx])

            if conf < CONF_THRES[CLASSES[cls_idx]]:
                continue

            # Converte para pixel coords na imagem original
            x1 = int((x_c - w / 2) * orig_w)
            y1 = int((y_c - h / 2) * orig_h)
            bw = int(w * orig_w)
            bh = int(h * orig_h)

            deteccoes.append({
                "classe":    CLASSES[cls_idx],
                "confianca": round(conf, 3),
                "nivel":     _nivel(conf),
                "x":         max(0, x1),
                "y":         max(0, y1),
                "largura":   bw,
                "altura":    bh,
            })

        deteccoes = _nms(deteccoes, IOU_THRES)

        criticos    = sum(1 for d in deteccoes if d["nivel"] == "CRITICO")
        alertas     = sum(1 for d in deteccoes if d["nivel"] == "ALERTA")
        nivel_geral = "CRITICO" if criticos > 0 else ("ALERTA" if alertas > 0 else "SEGURO")

        return {
            "deteccoes":   deteccoes,
            "total":       len(deteccoes),
            "nivel_geral": nivel_geral,
            "fonte":       "local",
        }

    except Exception as e:
        print(f"[detector] Erro na inferência: {e}")
        return _resposta_vazia("indisponivel")
