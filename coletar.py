"""Coleta editais abertos do Sistema de Leilão Eletrônico da Receita Federal
e gera site/dados.json para a interface.

Uso: python coletar.py [--situacoes 2,3] [--intervalo 0.4]
Cache em cache/lotes/ evita rebaixar detalhes de lotes já coletados.
"""
import argparse
import json
import re
import time
import unicodedata
import urllib.request
from pathlib import Path

API = "https://www25.receita.fazenda.gov.br/sle-sociedade/api"
PORTAL = "https://www25.receita.fazenda.gov.br/sle-sociedade/portal"
RAIZ = Path(__file__).parent
CACHE = RAIZ / "cache" / "lotes"
SAIDA = RAIZ / "site" / "dados.json"
UA = "leilao-receita-prototipo/0.1 (consulta moderada a dados publicos)"

# Cidade sede da unidade -> UF (usado quando o recinto não traz "/UF")
CIDADE_UF = {
    "SAO PAULO": "SP", "SANTOS": "SP", "CAMPINAS": "SP", "GUARULHOS": "SP",
    "RIO DE JANEIRO": "RJ", "BELO HORIZONTE": "MG", "CURITIBA": "PR",
    "FOZ DO IGUACU": "PR", "PORTO ALEGRE": "RS", "FLORIANOPOLIS": "SC",
    "ITAJAI": "SC", "SALVADOR": "BA", "RECIFE": "PE", "FORTALEZA": "CE",
    "BELEM": "PA", "MANAUS": "AM", "BRASILIA": "DF", "GOIANIA": "GO",
    "VITORIA": "ES", "CAMPO GRANDE": "MS", "CUIABA": "MT", "SAO LUIS": "MA",
    "NATAL": "RN", "JOAO PESSOA": "PB", "MACEIO": "AL", "ARACAJU": "SE",
    "TERESINA": "PI", "PALMAS": "TO", "PORTO VELHO": "RO", "RIO BRANCO": "AC",
    "BOA VISTA": "RR", "MACAPA": "AP", "URUGUAIANA": "RS", "PARANAGUA": "PR",
    "CORUMBA": "MS", "PONTA PORA": "MS", "SANTANA DO LIVRAMENTO": "RS",
    "ITAGUAI": "RJ", "SEPETIBA": "RJ", "CEARAPORTOS": "CE", "PECEM": "CE",
    "DIONISIO CERQUEIRA": "SC", "JOACABA": "SC", "CHAPECO": "SC", "NAVEGANTES": "SC",
    "SAO FRANCISCO DO SUL": "SC", "BLUMENAU": "SC", "JOINVILLE": "SC", "LAGES": "SC",
    "CRICIUMA": "SC", "CASCAVEL": "PR", "LONDRINA": "PR", "MARINGA": "PR",
    "ITAPOA": "SC", "PORTONAVE": "SC", "DCA": "SC", "FOZ": "PR", "PONTA GROSSA": "PR",
    "ARARAQUARA": "SP", "BAURU": "SP", "VIRACOPOS": "SP", "GUARUJA": "SP",
}
# Região fiscal -> UF da sede (para editais de superintendência)
REGIAO_UF = {"1": "DF", "2": "PA", "3": "CE", "4": "PE", "5": "BA",
             "6": "MG", "7": "RJ", "8": "SP", "9": "PR", "10": "RS"}
UFS = set(CIDADE_UF.values())


def sem_acento(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper().strip()


def get(path, tentativas=3):
    for i in range(tentativas):
        try:
            req = urllib.request.Request(f"{API}/{path}", headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == tentativas - 1:
                raise
            print(f"  erro em {path}: {e}; tentando de novo")
            time.sleep(3 * (i + 1))


def uf_do_edital(ed):
    cidade = sem_acento(ed.get("cidade"))
    if cidade in CIDADE_UF:
        return CIDADE_UF[cidade]
    m = re.search(r"(\d+)\S* REGIAO FISCAL", sem_acento(ed.get("uaNm")) + " " + cidade)
    if m:
        return REGIAO_UF.get(m.group(1))
    # 1º dígito do código da unidade = região fiscal (ex.: 717800 -> 7ª RF)
    return REGIAO_UF.get(ed["edle"][0])


def uf_do_recinto(recinto):
    r = sem_acento(recinto)
    m = re.search(r"[/-]\s*([A-Z]{2})\b\s*$", r)
    if m and m.group(1) in UFS:
        return m.group(1)
    # cidade conhecida no nome do recinto (mais longa primeiro)
    return next((CIDADE_UF[c] for c in sorted(CIDADE_UF, key=len, reverse=True) if c in r), None)


def detalhe_lote(edle, nr, intervalo):
    arq = CACHE / f"{edle.replace('/', '_')}_{nr}.json"
    if arq.exists():
        return json.loads(arq.read_text(encoding="utf-8"))
    d = get(f"lote/{edle}/{nr}")
    d.pop("lotesQueUsuarioTemPermissao", None)
    arq.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    time.sleep(intervalo)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--situacoes", default="2", help="códigos de situação a coletar (2 = recebendo propostas)")
    ap.add_argument("--intervalo", type=float, default=0.4, help="segundos entre requisições")
    args = ap.parse_args()
    situacoes = {int(s) for s in args.situacoes.split(",")}
    CACHE.mkdir(parents=True, exist_ok=True)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)

    disp = get("editais-disponiveis")
    editais, lotes = [], []
    for grupo in disp["situacoes"]:
        if grupo["situacao"] not in situacoes:
            continue
        for e in grupo["lista"]:
            edle = e["edle"]
            print(f"Edital {e['edital']} ({e['cidade']}, {e['lotes']} lotes)")
            ed = get(f"edital/{edle}")
            time.sleep(args.intervalo)
            uf_ed = uf_do_edital({**e, **ed})
            editais.append({
                "edle": edle, "edital": e["edital"], "cidade": e["cidade"], "unidade": e.get("uaNm"),
                "uf": uf_ed, "permitePF": e["permitePF"],
                "inicioPropostas": e["dataInicioPropostas"], "fimPropostas": e["dataFimPropostas"],
                "aberturaLances": e["dataAberturaLances"], "contato": ed.get("formaContato"),
                "url": f"{PORTAL}/edital/{edle}",
                "pdf": f"{API}/edital/{edle}/edital-completo",
            })
            for l in ed.get("listaLotes", []):
                nr = l["nrAtribuido"]
                try:
                    d = detalhe_lote(edle, nr, args.intervalo)
                except Exception as ex:
                    print(f"  lote {nr}: falhou ({ex})")
                    d = {}
                itens = d.get("itensDetalhesLote") or []
                recintos = sorted({i.get("recintoArmazenador") for i in itens if i.get("recintoArmazenador")})
                uf = next((u for u in map(uf_do_recinto, recintos) if u), uf_ed)
                lotes.append({
                    "edle": edle, "lote": nr, "tipo": l.get("tipo"),
                    "valorMinimo": l.get("valorMinimo"), "valorAvaliacao": l.get("valorAvaliacao"),
                    "permitePF": l.get("permitePF"), "possuiImagens": l.get("possuiImagens"),
                    "recinto": "; ".join(recintos), "uf": uf,
                    "itens": [{"q": i.get("quantidade"), "un": i.get("unMedida"),
                               "d": (i.get("descricao") or "").rstrip("/ ")} for i in itens],
                    "fotos": [{"src": f["src"], "min": f.get("min") or f["src"]}
                              for f in (d.get("imagens") or []) if f.get("src")],
                    "url": f"{PORTAL}/edital/{edle}/lote/{nr}",
                })
    out = {"geradoEm": disp.get("agora"), "editais": editais, "lotes": lotes}
    SAIDA.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"OK: {len(editais)} editais, {len(lotes)} lotes -> {SAIDA}")


if __name__ == "__main__":
    main()
