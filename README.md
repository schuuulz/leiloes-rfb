# Leilões da Receita — protótipo

Interface independente (sem vínculo com a Receita Federal) para buscar lotes abertos
do Sistema de Leilão Eletrônico, usando a API pública do portal.

## Rodar

```
python coletar.py              # gera site/dados.json (cache em cache/lotes/)
cd site && python -m http.server 8765
# abrir http://localhost:8765
```

Página única `index.html`: busca de lotes com fotos + mapa do ICMS por UF (clique no estado filtra; aceita `?uf=SP`).
Não usa cookies, analytics nem fontes/scripts externos; filtros ficam só no localStorage do visitante.
O mapa lê `site/brasil-ufs.json`, gerado uma vez com `python gerar_mapa.py` (malha do IBGE).
Editar `site/icms.json` atualiza mapa e custos ao recarregar a página.

A primeira coleta leva ~10 min (1 requisição por lote, com intervalo de 0,4 s). As seguintes
só baixam lotes novos. `--situacoes 2,3` inclui outras situações de edital (2 = recebendo propostas).

## API usada (pública, sem login)

- `api/editais-disponiveis` — editais agrupados por situação
- `api/edital/{unidade}/{numero}/{ano}` — dados do edital + lista de lotes (valor mínimo/avaliação, PF)
- `api/lote/{unidade}/{numero}/{ano}/{lote}` — itens e recinto armazenador
- `api/edital/{unidade}/{numero}/{ano}/edital-completo` — PDF

## Limitações conhecidas

- **ICMS**: `site/icms.json` tem a alíquota interna por UF. Só SP está conferida (pelo edital);
  as demais são estimativas a conferir. Alíquotas por produto (perfume, videogame…) não são tratadas.
- **Armazenagem** (ex.: lotes 1–120 do edital SP/GRU) não vem da API; está só no PDF.
- **UF do lote** é inferida do nome do recinto ou da região fiscal. A 9ª RF cobre PR e SC; alguns
  terminais com nome genérico (Barra do Rio, Multilog, Poly, Conexão Marítima) ficam como PR mas
  podem ser SC — revisar.
- Fotos não são exibidas ainda.

## Hospedagem (GitHub Pages, grátis)

`.github/workflows/atualizar.yml` roda a cada 6 h (e a cada push / manualmente em Actions → Run workflow):
coleta os lotes, gera `site/dados.json` e publica a pasta `site/` no GitHub Pages. O cache dos lotes
fica no `actions/cache`, então nada de dados é commitado. Pages deve estar com Source = "GitHub Actions".
Workflows agendados são pausados pelo GitHub após 60 dias sem atividade no repositório.
