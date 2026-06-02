"""
Pyros Vision — Frota de Drones
Dados simulados de drones de combate a incêndio no estado de SP.
"""

import random
import time

FROTA = [
    {"id": "DR-01", "nome": "Falcão 1",  "base": "Campinas",           "lat": -22.90, "lon": -47.06},
    {"id": "DR-02", "nome": "Falcão 2",  "base": "Ribeirão Preto",     "lat": -21.17, "lon": -47.81},
    {"id": "DR-03", "nome": "Falcão 3",  "base": "São José do Rio Preto", "lat": -20.81, "lon": -49.37},
    {"id": "DR-04", "nome": "Águia 1",   "base": "Presidente Prudente","lat": -22.12, "lon": -51.39},
    {"id": "DR-05", "nome": "Águia 2",   "base": "Sorocaba",           "lat": -23.50, "lon": -47.46},
    {"id": "DR-06", "nome": "Guardião 1","base": "Bauru",              "lat": -22.31, "lon": -49.06},
    {"id": "DR-07", "nome": "Guardião 2","base": "Franca",             "lat": -20.54, "lon": -47.40},
    {"id": "DR-08", "nome": "Sentinela 1","base": "Marília",           "lat": -22.21, "lon": -49.95},
]

# Seed por minuto para simular mudanças graduais
def _seed():
    return int(time.time()) // 120


def listar_drones() -> list:
    rng = random.Random(_seed())
    drones = []
    for d in FROTA:
        status = rng.choices(
            ["DISPONIVEL", "EM_MISSAO", "MANUTENCAO"],
            weights=[55, 35, 10],
        )[0]

        bateria = rng.randint(20, 100) if status != "MANUTENCAO" else rng.randint(0, 30)

        missao_lat = missao_lon = missao_alvo = None
        if status == "EM_MISSAO":
            offset_lat = rng.uniform(-1.5, 1.5)
            offset_lon = rng.uniform(-1.5, 1.5)
            missao_lat = round(d["lat"] + offset_lat, 4)
            missao_lon = round(d["lon"] + offset_lon, 4)
            missao_alvo = rng.choice(["Araraquara", "Presidente Prudente", "Ribeirão Preto"])

        drones.append({
            "id":          d["id"],
            "nome":        d["nome"],
            "base":        d["base"],
            "lat_base":    d["lat"],
            "lon_base":    d["lon"],
            "status":      status,
            "bateria":     bateria,
            "missao_lat":  missao_lat,
            "missao_lon":  missao_lon,
            "missao_alvo": missao_alvo,
        })

    return drones
