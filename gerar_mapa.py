"""Gera site/brasil-ufs.json com o contorno SVG de cada UF a partir da malha do IBGE.

Uso: python gerar_mapa.py   (só precisa rodar de novo se quiser outra qualidade de malha)
"""
import gzip
import json
import math
import urllib.request
from pathlib import Path

IBGE = "https://servicodados.ibge.gov.br/api"
MALHA = f"{IBGE}/v3/malhas/paises/BR?formato=application/vnd.geo%2Bjson&qualidade=minima&intrarregiao=UF"
ESTADOS = f"{IBGE}/v1/localidades/estados"
SAIDA = Path(__file__).parent / "site" / "brasil-ufs.json"
LARGURA = 1000  # largura do viewBox; altura sai da proporção


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "leilao-receita-prototipo/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        dados = r.read()
    if dados[:2] == bytes([0x1F, 0x8B]):  # IBGE responde gzip mesmo sem Accept-Encoding
        dados = gzip.decompress(dados)
    return json.loads(dados.decode("utf-8"))


def aneis(geom):
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    return [anel for poli in geom["coordinates"] for anel in poli]


def main():
    malha = get(MALHA)
    estados = {str(e["id"]): e for e in get(ESTADOS)}

    pts = [p for f in malha["features"] for anel in aneis(f["geometry"]) for p in anel]
    lon0, lon1 = min(p[0] for p in pts), max(p[0] for p in pts)
    lat0, lat1 = min(p[1] for p in pts), max(p[1] for p in pts)
    k = math.cos(math.radians((lat0 + lat1) / 2))  # equiretangular com correção da latitude média
    escala = LARGURA / ((lon1 - lon0) * k)
    altura = round((lat1 - lat0) * escala)

    def xy(p):
        return f"{(p[0] - lon0) * k * escala:.1f},{(lat1 - p[1]) * escala:.1f}"

    ufs = {}
    for f in malha["features"]:
        e = estados[f["properties"]["codarea"]]
        path = "".join("M" + "L".join(xy(p) for p in anel) + "Z" for anel in aneis(f["geometry"]))
        ufs[e["sigla"]] = {"nome": e["nome"], "regiao": e["regiao"]["nome"], "path": path}

    out = {"viewBox": f"0 0 {LARGURA} {altura}", "fonte": "IBGE — malha de UFs", "ufs": ufs}
    SAIDA.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"OK: {len(ufs)} UFs -> {SAIDA} ({SAIDA.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
