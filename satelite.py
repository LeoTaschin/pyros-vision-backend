"""
Pyros Vision — Satélite
Busca focos de calor da NASA FIRMS e retorna como lista de dicts.
"""

import csv
import io
import math
import os
import random
import time
import urllib.request

from contorno import dentro_sp

# Bounding box do estado de SP (pré-filtro rápido)
LAT_MIN, LAT_MAX = -25.35, -19.70
LON_MIN, LON_MAX = -53.20, -44.10

# Contorno real do estado de SP (ray-casting)
CONTORNO_SP = [
    (-19.78,-50.16),(-19.85,-49.80),(-19.92,-49.40),(-20.00,-48.95),
    (-20.08,-48.50),(-20.18,-48.05),(-20.30,-47.55),(-20.42,-47.10),
    (-20.58,-46.65),(-20.78,-46.30),(-21.05,-45.95),(-21.30,-45.55),
    (-21.60,-45.15),(-21.95,-44.80),(-22.25,-44.50),
    (-22.45,-44.30),(-22.70,-44.15),(-22.95,-44.10),(-23.20,-44.35),
    (-23.45,-44.80),(-23.65,-45.10),(-23.80,-45.40),(-23.92,-45.75),
    (-23.98,-46.10),(-24.00,-46.45),(-24.05,-46.85),(-24.20,-47.20),
    (-24.45,-47.55),(-24.70,-47.85),(-24.95,-48.15),(-25.15,-48.40),
    (-25.20,-48.75),(-25.05,-49.15),(-24.85,-49.55),(-24.65,-49.95),
    (-24.45,-50.35),(-24.25,-50.85),(-24.10,-51.40),(-23.95,-51.95),
    (-23.80,-52.50),(-23.65,-53.00),(-23.40,-53.15),
    (-23.05,-53.10),(-22.70,-53.05),(-22.35,-52.85),(-22.05,-52.60),
    (-21.75,-52.35),(-21.45,-52.15),(-21.15,-51.90),(-20.85,-51.60),
    (-20.55,-51.30),(-20.25,-51.00),(-20.00,-50.60),(-19.85,-50.35),
    (-19.78,-50.16),
]

CIDADES_SP = [
    # Região Metropolitana de SP
    ("Sao Paulo",              -23.55, -46.63),
    ("Guarulhos",              -23.46, -46.53),
    ("Sao Bernardo do Campo",  -23.69, -46.56),
    ("Santo Andre",            -23.66, -46.53),
    ("Osasco",                 -23.53, -46.79),
    ("Mogi das Cruzes",        -23.52, -46.19),
    ("Jundiai",                -23.19, -46.88),
    # Interior Leste
    ("Sao Jose dos Campos",    -23.18, -45.88),
    ("Taubate",                -23.03, -45.56),
    ("Guaratingueta",          -22.82, -45.19),
    ("Pindamonhangaba",        -22.92, -45.46),
    # Interior Norte
    ("Ribeirao Preto",         -21.17, -47.81),
    ("Franca",                 -20.54, -47.40),
    ("Sao Jose Rio Preto",     -20.81, -49.37),
    ("Catanduva",              -21.14, -48.97),
    ("Votuporanga",            -20.42, -49.97),
    ("Fernandopolis",          -20.28, -50.24),
    ("Olimpia",                -20.73, -48.91),
    ("Barretos",               -20.56, -48.57),
    # Interior Centro
    ("Campinas",               -22.90, -47.06),
    ("Piracicaba",             -22.72, -47.65),
    ("Limeira",                -22.56, -47.40),
    ("Rio Claro",              -22.41, -47.56),
    ("Americana",              -22.74, -47.33),
    ("Araraquara",             -21.79, -48.17),
    ("Sao Carlos",             -22.01, -47.89),
    ("Araras",                 -22.35, -47.38),
    # Interior Oeste / Centro-Oeste
    ("Bauru",                  -22.31, -49.06),
    ("Marilia",                -22.21, -49.95),
    ("Botucatu",               -22.88, -48.44),
    ("Avare",                  -23.10, -48.92),
    ("Ourinhos",               -22.98, -49.87),
    ("Assis",                  -22.66, -50.41),
    ("Presidente Venceslau",   -21.88, -51.84),
    ("Presidente Prudente",    -22.12, -51.39),
    ("Adamantina",             -21.68, -51.07),
    ("Dracena",                -21.48, -51.53),
    ("Panorama",               -21.36, -51.86),
    ("Andradina",              -20.90, -51.38),
    ("Araçatuba",              -21.21, -50.43),
    ("Birigui",                -21.29, -50.34),
    ("Penapolis",              -21.42, -50.08),
    ("Tupã",                   -21.93, -50.51),
    ("Garça",                  -22.21, -49.65),
    ("Lins",                   -21.68, -49.74),
    ("Promissao",              -21.54, -49.86),
    # Sul / Litoral
    ("Sorocaba",               -23.50, -47.46),
    ("Itapetininga",           -23.59, -48.05),
    ("Itapeva",                -23.98, -48.88),
    ("Itarare",                -24.11, -49.33),
    ("Santos",                 -23.96, -46.33),
    ("Sao Vicente",            -23.96, -46.39),
    ("Praia Grande",           -24.00, -46.41),
    ("Registro",               -24.49, -47.84),
    ("Iguape",                 -24.71, -47.56),
    ("Itanhaem",               -24.18, -46.79),
    ("Miracatu",               -24.28, -47.46),
]

# Distância máxima para associar um foco a uma cidade (km)
_DIST_MAX_CIDADE = 80


def _distancia_km(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _cidade_mais_proxima(lat, lon):
    cidade = min(CIDADES_SP, key=lambda c: _distancia_km(lat, lon, c[1], c[2]))
    dist   = _distancia_km(lat, lon, cidade[1], cidade[2])
    if dist > _DIST_MAX_CIDADE:
        # Sem cidade próxima conhecida — retorna coordenadas
        return (f"{abs(lat):.2f}°S {abs(lon):.2f}°O", lat, lon)
    return cidade


def dentro_sp(lat, lon):
    pts = CONTORNO_SP
    n, dentro, j = len(pts), False, len(pts) - 1
    for i in range(n):
        lat_i, lon_i = pts[i]
        lat_j, lon_j = pts[j]
        if ((lat_i > lat) != (lat_j > lat)) and \
           (lon < (lon_j - lon_i) * (lat - lat_i) / (lat_j - lat_i) + lon_i):
            dentro = not dentro
        j = i
    return dentro


def _nivel(brightness: float) -> str:
    if brightness >= 390:
        return "CRITICO"
    if brightness >= 320:
        return "ALERTA"
    return "MONITORANDO"


def buscar_focos() -> list:
    api_key = os.environ.get("FIRMS_API_KEY", "").strip()
    if not api_key:
        return _focos_demo()

    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{api_key}/MODIS_NRT/"
        f"{LON_MIN},{LAT_MIN},{LON_MAX},{LAT_MAX}/1"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            conteudo = resp.read().decode("utf-8")

        reader = csv.DictReader(io.StringIO(conteudo))
        todos = []
        for row in reader:
            try:
                todos.append({
                    "lat":        float(row["latitude"]),
                    "lon":        float(row["longitude"]),
                    "brightness": float(row.get("brightness", 300)),
                    "confidence": row.get("confidence", "n"),
                    "data":       row.get("acq_date", "N/A"),
                    "hora":       row.get("acq_time", "N/A"),
                    "frp":        row.get("frp", "N/A"),
                    "satelite":   row.get("satellite", "MODIS"),
                    "daynight":   row.get("daynight", "N/A"),
                })
            except (ValueError, KeyError):
                continue

        focos = [f for f in todos if dentro_sp(f["lat"], f["lon"])]
        for f in focos:
            nome, lat_c, lon_c = _cidade_mais_proxima(f["lat"], f["lon"])
            f["cidade"]  = nome
            f["dist_km"] = round(_distancia_km(f["lat"], f["lon"], lat_c, lon_c), 1)
            f["nivel"]   = _nivel(f["brightness"])

        return focos

    except Exception:
        return _focos_demo()


def _focos_demo() -> list:
    random.seed(int(time.time()) // 60)
    base = [
        (-22.50,-47.50),(-21.80,-48.20),(-23.10,-46.80),
        (-22.00,-50.50),(-21.20,-47.80),(-23.50,-48.50),
    ]
    focos = []
    for lat_b, lon_b in random.sample(base, k=min(4, len(base))):
        lat = lat_b + random.uniform(-0.2, 0.2)
        lon = lon_b + random.uniform(-0.2, 0.2)
        if dentro_sp(lat, lon):
            bri  = random.uniform(295, 460)
            nome, lat_c, lon_c = _cidade_mais_proxima(lat, lon)
            focos.append({
                "lat":        round(lat, 4),
                "lon":        round(lon, 4),
                "brightness": round(bri, 1),
                "confidence": random.choice(["n", "h", "l"]),
                "data":       "2026-06-02",
                "hora":       f"{random.randint(0,23):02d}{random.randint(0,59):02d}",
                "frp":        str(round(random.uniform(5, 80), 1)),
                "satelite":   "Terra (demo)",
                "daynight":   random.choice(["D", "N"]),
                "cidade":     nome,
                "dist_km":    round(_distancia_km(lat, lon, lat_c, lon_c), 1),
                "nivel":      _nivel(bri),
            })
    return focos
