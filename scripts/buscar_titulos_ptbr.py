"""Completa os títulos brasileiros dos filmes usando a API do TMDB.

O arquivo scripts/titulos_ptbr.txt já traz o título em português dos 3.000 filmes.
Este script é opcional: busca o título pt-BR de filmes que ainda não estejam no arquivo (útil se a base for ampliada).

Uso (na raiz do repositório, depois de rodar o pipeline uma vez):
    set TMDB_API_KEY=sua_chave          (Windows)   |   export TMDB_API_KEY=sua_chave   (Linux/macOS)
    python scripts/buscar_titulos_ptbr.py
    python scripts/pipeline.py --tmdb dados/brutos

A chave é gratuita: crie uma conta em themoviedb.org > Configurações > API.
"""
import json, os, pickle, sys, time, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
ARQ = os.path.join(AQUI, "titulos_ptbr.txt")

chave = os.environ.get("TMDB_API_KEY")
if not chave:
    sys.exit("Defina a variável de ambiente TMDB_API_KEY com a sua chave da API do TMDB.")

f = pickle.load(open(os.path.join(RAIZ, "build", "dados.pkl"), "rb"))["f"]
ja = {int(l.split("|", 1)[0]) for l in open(ARQ, encoding="utf-8") if "|" in l}
faltam = f[~f.id_filme.isin(ja)][["id_filme", "id", "titulo_en"]]
print(f"{len(faltam)} filmes sem título em português. Buscando no TMDB...")

novos = 0
with open(ARQ, "a", encoding="utf-8") as out:
    for r in faltam.itertuples():
        url = f"https://api.themoviedb.org/3/movie/{int(r.id)}?language=pt-BR&api_key={chave}"
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                titulo = json.load(resp).get("title", "").strip()
        except Exception as e:
            print("  erro em", r.titulo_en, "-", e)
            continue
        if titulo:
            out.write(f"{int(r.id_filme)}|{titulo}\n")
            novos += 1
        time.sleep(0.03)  # respeita o limite de requisições da API
print(f"{novos} títulos adicionados a {os.path.relpath(ARQ, RAIZ)}. Rode o pipeline de novo para atualizar o projeto.")
