"""
Pyros Vision — Contorno oficial do estado de SP.
Fonte: IBGE Malhas Geográficas (API pública, sem autenticação).
Cacheado localmente após o primeiro download.
"""

import gzip
import json
import os
import urllib.request
from shapely.geometry import shape, Point
from shapely.prepared import prep

_IBGE_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/estados/35"
    "?formato=application/vnd.geo+json&resolucao=2"
)
_CACHE = os.path.join(os.path.dirname(__file__), "sp_contorno_cache.json")

_poligono = None


def _carregar():
    global _poligono

    geojson = None

    if os.path.exists(_CACHE):
        try:
            with open(_CACHE, encoding="utf-8") as f:
                geojson = json.load(f)
            print("[Pyros] Contorno SP carregado do cache local.")
        except Exception as e:
            print(f"[Pyros] Cache corrompido, rebuscando: {e}")

    if geojson is None:
        try:
            print("[Pyros] Baixando contorno SP do IBGE…")
            req = urllib.request.Request(_IBGE_URL, headers={"Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read()
                if resp.info().get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                geojson = json.loads(raw.decode("utf-8"))
            with open(_CACHE, "w", encoding="utf-8") as f:
                json.dump(geojson, f)
            print("[Pyros] Contorno SP salvo em cache.")
        except Exception as e:
            print(f"[Pyros] Falha ao buscar IBGE: {e}. Usando bounding box.")
            return

    try:
        geometry = geojson["features"][0]["geometry"]
        _poligono = prep(shape(geometry))
        print("[Pyros] Polígono SP pronto (IBGE).")
    except Exception as e:
        print(f"[Pyros] Erro ao construir polígono: {e}")


def dentro_sp(lat: float, lon: float) -> bool:
    if _poligono is None:
        return -25.35 <= lat <= -19.70 and -53.20 <= lon <= -44.10
    return bool(_poligono.contains(Point(lon, lat)))


_carregar()
