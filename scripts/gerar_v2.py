"""
Gera a base fictícia "Locadora Rebobina" (jan/2009 a jan/2011) a partir do TMDB 5000.
Uso: python3 -I gerar_locadora.py <pasta_tmdb> <pasta_saida>
Saída: dados em parquet/pickle intermediário + scripts .sql para SQL Server.
"""
import sys, os, json, math, random, pickle
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd

SEED = 2009
rng = np.random.default_rng(SEED)
random.seed(SEED)

SRC, OUT = sys.argv[1], sys.argv[2]
INICIO = date(2009, 1, 1)
FIM = date(2011, 1, 31)
SNAPSHOT = datetime(2011, 1, 31, 23, 59, 59)
DIAS = (FIM - INICIO).days + 1

# ------------------------------------------------------------------ FILMES
m = pd.read_csv(f"{SRC}/tmdb_5000_movies.csv")
cr = pd.read_csv(f"{SRC}/tmdb_5000_credits.csv")
m["rd"] = pd.to_datetime(m.release_date, errors="coerce")
f = m[(m.rd <= "2011-01-31") & (m.status == "Released")].copy()
lanc = f[f.rd >= "2009-01-01"]
antigos = f[f.rd < "2009-01-01"].sort_values("vote_count", ascending=False).head(3000 - len(lanc))
f = pd.concat([lanc, antigos]).copy()
assert len(f) == 3000
f = f.merge(cr[["movie_id", "cast", "crew"]], left_on="id", right_on="movie_id", how="left")
f["kw"] = f.keywords.apply(lambda s: {k["name"] for k in json.loads(s)} if isinstance(s, str) else set())
f["titulo"] = f.title.str.strip()
f = f.sort_values(["titulo", "rd"]).reset_index(drop=True)
f["id_filme"] = np.arange(1, len(f) + 1)
PT = {}
for _l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "titulos_ptbr.txt"), encoding="utf-8"):
    _i, _t = _l.rstrip("\n").split("|", 1); PT[int(_i)] = _t
f["titulo_pt"] = f.id_filme.map(PT)

GEN = {"Action": "Ação", "Adventure": "Aventura", "Animation": "Animação", "Comedy": "Comédia",
       "Crime": "Crime", "Documentary": "Documentário", "Drama": "Drama", "Family": "Família",
       "Fantasy": "Fantasia", "Foreign": "Estrangeiro", "History": "História", "Horror": "Terror",
       "Music": "Musical", "Mystery": "Mistério", "Romance": "Romance", "Science Fiction": "Ficção científica",
       "TV Movie": "Filme para TV", "Thriller": "Suspense", "War": "Guerra", "Western": "Faroeste"}
generos = sorted(GEN.values())
id_gen = {g: i + 1 for i, g in enumerate(generos)}
f["gen_lista"] = f.genres.apply(lambda s: [GEN[x["name"]] for x in json.loads(s)] or ["Drama"])
f["gen_principal"] = f.gen_lista.str[0]

IDI = {"en": "Inglês", "fr": "Francês", "es": "Espanhol", "de": "Alemão", "zh": "Mandarim", "ja": "Japonês",
       "hi": "Hindi", "it": "Italiano", "ko": "Coreano", "cn": "Cantonês", "ru": "Russo", "sv": "Sueco",
       "da": "Dinamarquês", "pt": "Português", "nl": "Holandês", "th": "Tailandês", "he": "Hebraico",
       "fa": "Persa", "xx": "Sem idioma", "hu": "Húngaro", "tr": "Turco", "cs": "Tcheco", "nb": "Norueguês",
       "no": "Norueguês", "af": "Africâner", "ar": "Árabe", "vi": "Vietnamita", "ro": "Romeno",
       "ps": "Pashto", "el": "Grego", "pl": "Polonês", "id": "Indonésio"}
f["idioma"] = f.original_language.map(lambda c: IDI.get(c, c.upper()))
idiomas = sorted(set(f.idioma))
id_idi = {n: i + 1 for i, n in enumerate(idiomas)}

f["duracao_min"] = f.runtime.where(f.runtime > 0, np.nan).fillna(100).round().astype(int)

def diretor(s):
    try:
        for p in json.loads(s):
            if p.get("job") == "Director":
                return p["name"]
    except Exception:
        pass
    return None
f["diretor"] = f.crew.apply(diretor)

def classificacao(gs):
    s = set(gs)
    r = random.random
    if "Terror" in s: return "16" if r() < .6 else "18"
    if s & {"Crime", "Suspense", "Guerra"}: return "14" if r() < .5 else "16"
    if s & {"Animação", "Família"}: return "L" if r() < .75 else "10"
    if s & {"Ação", "Ficção científica", "Fantasia", "Aventura"}: return "12" if r() < .6 else "14"
    if s & {"Romance", "Comédia", "Musical"}: return random.choices(["L", "10", "12"], [.2, .3, .5])[0]
    if "Documentário" in s: return "L" if r() < .6 else "10"
    return "12" if r() < .5 else "14"
f["classificacao"] = f.gen_lista.apply(classificacao)

# fama: bilheteria (50%), votos (35%), popularidade (15%) em percentis
pr = lambda s: s.rank(pct=True, method="average")
rev_rank = pr(f.revenue.where(f.revenue > 0, 0))
f["fama"] = 0.5 * rev_rank + 0.35 * pr(f.vote_count) + 0.15 * pr(f.popularity)
f["classico"] = ((f.rd.dt.year < 1990) & (f.vote_average >= 7.0) & (f.vote_count >= 300))

# chegada na locadora: janela de ~2 a 3,5 meses depois do cinema para títulos recentes
LOJAS = [  # id, cidade, bairro, inauguração, porte
    (1, "Contagem", "Eldorado", date(2003, 5, 10), 1.00),
    (2, "Belo Horizonte", "Savassi", date(2005, 9, 1), 1.25),
    (3, "Betim", "Centro", date(2007, 3, 15), 0.80),
]
def chegada(rd):
    rd = rd.date()
    if rd >= date(2008, 7, 1):
        return rd + timedelta(days=int(rng.integers(60, 111)))
    return min(max(rd + timedelta(days=100), date(2003, 5, 10)), date(2008, 12, 31))
f["chegada"] = f.rd.apply(chegada)
f["ano"] = f.rd.dt.year

# ------------------------------------------------------------------ ATORES
atores, fa = {}, []
for _, r in f.iterrows():
    try:
        cast = json.loads(r["cast"])[:5]
    except Exception:
        cast = []
    for o, p in enumerate(cast, 1):
        nome = p["name"].strip()
        if nome not in atores:
            atores[nome] = len(atores) + 1
        fa.append((r.id_filme, atores[nome], o, (p.get("character") or "")[:100]))
# remove pares duplicados (mesmo ator em dois papéis)
seen, fa2 = set(), []
for x in fa:
    if (x[0], x[1]) not in seen:
        seen.add((x[0], x[1])); fa2.append(x)
fa = fa2

# ------------------------------------------------------------------ PESSOAS
NF = ["Ana", "Maria", "Juliana", "Fernanda", "Patrícia", "Camila", "Amanda", "Bruna", "Letícia", "Mariana",
      "Aline", "Larissa", "Vanessa", "Débora", "Cristiane", "Renata", "Tatiane", "Priscila", "Gabriela", "Natália",
      "Luana", "Carla", "Sandra", "Simone", "Adriana", "Márcia", "Rosana", "Elaine", "Daniela", "Raquel",
      "Bianca", "Isabela", "Carolina", "Jéssica", "Thaís", "Paula", "Lúcia", "Helena", "Beatriz", "Viviane"]
NM = ["José", "João", "Carlos", "Paulo", "Lucas", "Pedro", "Marcos", "Rafael", "Gustavo", "Felipe",
      "Bruno", "Rodrigo", "Thiago", "Leonardo", "Eduardo", "Ricardo", "Fernando", "Diego", "André", "Marcelo",
      "Daniel", "Gabriel", "Matheus", "Vinícius", "Alexandre", "Fábio", "Renato", "Leandro", "Júlio", "Sérgio",
      "Wellington", "Anderson", "Henrique", "Igor", "Caio", "Otávio", "Márcio", "Flávio", "Wagner", "Roberto"]
SN = ["Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves", "Pereira", "Lima", "Gomes",
      "Costa", "Ribeiro", "Martins", "Carvalho", "Almeida", "Lopes", "Soares", "Fernandes", "Vieira", "Barbosa",
      "Rocha", "Dias", "Nascimento", "Andrade", "Moreira", "Nunes", "Marques", "Machado", "Mendes", "Freitas",
      "Cardoso", "Ramos", "Gonçalves", "Santana", "Teixeira", "Moura", "Campos", "Pinto", "Araújo", "Castro",
      "Reis", "Faria", "Rezende", "Batista", "Pimenta", "Drummond", "Guimarães", "Lacerda", "Fonseca", "Assis"]
BAIRROS = {
    "Contagem": ["Eldorado", "Novo Eldorado", "Riacho das Pedras", "Industrial", "Inconfidentes", "Água Branca",
                 "Jardim Riacho", "Ressaca", "Petrolândia", "Centro", "Jardim Industrial", "Cidade Jardim Eldorado"],
    "Belo Horizonte": ["Savassi", "Funcionários", "Lourdes", "Santo Antônio", "Sion", "Serra", "Cruzeiro",
                       "Anchieta", "Carmo", "Santo Agostinho", "Gutierrez", "Prado", "Barroca", "Coração de Jesus"],
    "Betim": ["Centro", "Angola", "Ingá", "Brasiléia", "Jardim da Cidade", "Filadélfia", "Citrolândia",
              "Imbiruçu", "Vianópolis", "Arquipélago Verde"],
    "Ibirité": ["Centro", "Durval de Barros", "Jardim das Rosas"],
}
CEP = {"Contagem": (32000, 32340), "Belo Horizonte": (30110, 30480), "Betim": (32600, 32690), "Ibirité": (32400, 32420)}
RUAS = ["Rua das Acácias", "Rua dos Ipês", "Rua Pernambuco", "Rua Bahia", "Rua Goiás", "Rua Rio Grande do Norte",
        "Avenida Brasil", "Rua Tiradentes", "Rua São Paulo", "Rua Itabira", "Rua Ouro Preto", "Rua Diamantina",
        "Rua Mariana", "Rua Sabará", "Rua Paracatu", "Rua Montes Claros", "Rua das Palmeiras", "Rua dos Jasmins",
        "Avenida Amazonas", "Rua Santa Rita", "Rua São João", "Rua Dom Pedro II", "Rua Bueno Brandão", "Rua Juiz de Fora"]
UF = {"Contagem": "MG", "Belo Horizonte": "MG", "Betim": "MG", "Ibirité": "MG"}
cidades = list(BAIRROS)
id_cid = {c: i + 1 for i, c in enumerate(cidades)}

def tira_acento(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

enderecos = []
def novo_endereco(cidade, bairro=None):
    bairro = bairro or random.choice(BAIRROS[cidade])
    a, b = CEP[cidade]
    enderecos.append(dict(id_endereco=len(enderecos) + 1, logradouro=random.choice(RUAS),
                          numero=str(int(rng.integers(10, 2500))), bairro=bairro, id_cidade=id_cid[cidade],
                          cep=f"{int(rng.integers(a, b)):05d}-{int(rng.integers(0, 999)):03d}"))
    return len(enderecos)

lojas = []
for idl, cid, bai, inaug, porte in LOJAS:
    lojas.append(dict(id_loja=idl, nome=f"Rebobina {cid if cid != 'Belo Horizonte' else 'BH'} – {bai}",
                      id_endereco=novo_endereco(cid, bai), data_inauguracao=inaug, porte=porte, cidade=cid))

usados = set()
def nome_unico(sexo):
    while True:
        n = random.choice(NF if sexo == "F" else NM)
        s = f"{random.choice(SN)} {random.choice(SN)}" if random.random() < .35 else random.choice(SN)
        if (n, s) not in usados or random.random() < .02:
            usados.add((n, s)); return n, s

funcs = []
for lj in lojas:
    for k, cargo in enumerate(["Gerente", "Atendente", "Atendente", "Atendente"]):
        sx = random.choice("FM"); n, s = nome_unico(sx)
        adm = lj["data_inauguracao"] + timedelta(days=int(rng.integers(0, 400))) if k == 0 else \
            date(2006, 1, 1) + timedelta(days=int(rng.integers(0, 1000)))
        adm = max(adm, lj["data_inauguracao"])
        funcs.append(dict(id_funcionario=len(funcs) + 1, nome=n, sobrenome=s,
                          email=f"{tira_acento(n).lower()}.{tira_acento(s.split()[-1]).lower()}@rebobina.exemplo",
                          id_loja=lj["id_loja"], cargo=cargo, data_admissao=adm, ativo=1))
for lj in lojas:
    lj["id_gerente"] = next(x["id_funcionario"] for x in funcs if x["id_loja"] == lj["id_loja"] and x["cargo"] == "Gerente")

# clientes
N_CLI = 3200
cli = []
cid_por_loja = {1: ["Contagem"] * 9 + ["Ibirité"], 2: ["Belo Horizonte"], 3: ["Betim"]}
pesos_loja = np.array([l["porte"] for l in lojas]); pesos_loja /= pesos_loja.sum()
PROV = ["exemplo.com.br"]
for i in range(N_CLI):
    loja = int(rng.choice([1, 2, 3], p=pesos_loja))
    cidade = random.choice(cid_por_loja[loja])
    sx = "F" if random.random() < .52 else "M"
    n, s = nome_unico(sx)
    idade = int(np.clip(rng.gamma(4.0, 7.5) + 14, 16, 78))
    nasc = date(2009 - idade, int(rng.integers(1, 13)), int(rng.integers(1, 29)))
    inaug = lojas[loja - 1]["data_inauguracao"]
    if random.random() < .62:  # já era cliente antes de 2009
        span = (date(2008, 12, 31) - inaug).days
        cad = inaug + timedelta(days=int(span * rng.beta(1.3, 1.0)))
    else:  # novos cadastros ficam mais raros com o tempo
        cad = INICIO + timedelta(days=int(DIAS * rng.beta(1.0, 1.8)))
    atividade = float(rng.lognormal(0, 1.0))
    churn = None
    if random.random() < .28:
        ini = max(cad, INICIO)
        churn = ini + timedelta(days=int(rng.integers(30, max(31, (FIM - ini).days))))
    em = f"{tira_acento(n).lower()}.{tira_acento(s.split()[-1]).lower()}{int(rng.integers(1, 999))}@{random.choice(PROV)}"
    cli.append(dict(id_cliente=i + 1, nome=n, sobrenome=s, sexo=sx, data_nascimento=nasc, email=em,
                    id_endereco=novo_endereco(cidade), id_loja_cadastro=loja, data_cadastro=cad,
                    ativo=0 if churn else 1, _atv=atividade, _churn=churn))
rng2 = np.random.default_rng(77)          # gerador separado: preços e promoções
for c_ in cli:
    c_["cartao_fidelidade"] = int(rng2.random() < 0.30)
cli_df = pd.DataFrame(cli)
FIDEL = np.array([c_["cartao_fidelidade"] for c_ in cli])

# ------------------------------------------------------------------ PREÇOS
TABELA = [  # tipo, valor, prazo, multa/dia, inicio, fim
    ("Lançamento", 5.89, 1, 2.79, date(2008, 1, 1), date(2009, 12, 31)),
    ("Catálogo", 3.79, 3, 1.89, date(2008, 1, 1), date(2009, 12, 31)),
    ("Clássico", 2.99, 3, 1.89, date(2008, 1, 1), date(2009, 12, 31)),
    ("Lançamento", 6.49, 1, 3.19, date(2010, 1, 1), None),
    ("Catálogo", 4.39, 3, 2.09, date(2010, 1, 1), None),
    ("Clássico", 3.29, 3, 2.09, date(2010, 1, 1), None),
]
def preco(tipo, d):
    for i, t in enumerate(TABELA):
        if t[0] == tipo and t[4] <= d and (t[5] is None or d <= t[5]):
            return i + 1, t[1], t[2], t[3]

# ------------------------------------------------------------------ ESTOQUE (cópias)
copias = []
fama = f.fama.values; chg = f.chegada.values; recente = (f.rd >= "2008-07-01").values
sucesso = (f.fama.rank(pct=True) >= 0.85).values
f["sucesso"] = sucesso
for idx, r in f.iterrows():
    for lj in lojas:
        if sucesso[idx]:           # maiores bilheterias e sucessos: 3 cópias por loja
            n = 3
        elif recente[idx]:
            n = 2
        elif r.classico or fama[idx] > .45:
            n = 1
        else:
            n = 1 if random.random() < .6 else 0
        acq = max(r.chegada, lj["data_inauguracao"])
        for k in range(n):
            bd = recente[idx] and fama[idx] > .6 and k == 0 and r.rd.year >= 2008
            custo = rng.uniform(80, 110) if bd else (rng.uniform(45, 70) if recente[idx] else rng.uniform(15, 35))
            copias.append(dict(id_copia=len(copias) + 1, id_filme=int(r.id_filme), id_loja=lj["id_loja"],
                               midia="Blu-ray" if bd else "DVD", data_aquisicao=acq, custo_aquisicao=round(custo, 2)))
    # garante ao menos uma cópia por filme
    if not any(c["id_filme"] == r.id_filme for c in copias[-6:]):
        lj = lojas[int(rng.integers(0, 3))]
        copias.append(dict(id_copia=len(copias) + 1, id_filme=int(r.id_filme), id_loja=lj["id_loja"], midia="DVD",
                           data_aquisicao=max(r.chegada, lj["data_inauguracao"]), custo_aquisicao=round(rng.uniform(15, 35), 2)))
cop_df = pd.DataFrame(copias)
copias_por = {}
for c in copias:
    copias_por.setdefault((c["id_loja"], c["id_filme"]), []).append(c["id_copia"])
livre = {c["id_copia"]: datetime(2000, 1, 1) for c in copias}
aquis = {c["id_copia"]: c["data_aquisicao"] for c in copias}

# ------------------------------------------------------------------ DEMANDA
datas = [INICIO + timedelta(days=i) for i in range(DIAS)]
nF = len(f)
base = np.exp(3.2 * fama)
idade_anos = (pd.Timestamp("2010-01-01") - f.rd).dt.days.values / 365.25
fator_idade = np.where(f.classico.values, 0.75 * (f.vote_average.values / 7.0),
                       0.30 + 0.70 * np.exp(-np.clip(idade_anos, 0, None) / 6))
gl = f.gen_lista.values
is_fam = np.array([bool(set(g) & {"Animação", "Família"}) for g in gl])
is_hor = np.array(["Terror" in g for g in gl])
is_rom = np.array(["Romance" in g for g in gl])
chg_ord = np.array([d.toordinal() for d in f.chegada])

COPA = {date(2010, 6, 15), date(2010, 6, 20), date(2010, 6, 25), date(2010, 6, 28), date(2010, 7, 2)}
CARNAVAL = [(date(2009, 2, 21), date(2009, 2, 25)), (date(2010, 2, 13), date(2010, 2, 17))]
SAZ_MES = {1: 1.12, 2: 1.0, 3: .95, 4: .96, 5: .95, 6: .97, 7: 1.12, 8: .93, 9: .93, 10: .98, 11: .95, 12: 1.06}
SEM = [.78, .80, .86, .95, 1.32, 1.48, 1.05]  # seg..dom

import calendario_br as CAL
def tem_kw(*ks):
    ks = set(ks)
    return np.array([bool(k & ks) for k in f.kw.values])
tit = f.titulo.str.lower().values
T_NATAL = tem_kw("christmas", "santa claus", "christmas party", "christmas tree", "christmas eve") | \
          np.array([("christmas" in t) or ("santa" in t) or ("grinch" in t) for t in tit])
T_ANONOVO = tem_kw("new year's eve")
T_MAES = tem_kw("mother", "mother daughter relationship", "mother son relationship", "single mother", "motherhood")
T_PAIS = tem_kw("father", "father son relationship", "father daughter relationship", "single father", "fatherhood")
T_PASCOA = tem_kw("jesus christ", "bible", "christianity", "religion", "crucifixion")
T_HALLOWEEN = tem_kw("halloween", "zombie", "vampire", "witch", "haunted house", "ghost")
T_NAMORADOS = is_rom | tem_kw("valentine's day", "love", "romantic comedy", "wedding")
T_FUTEBOL = tem_kw("soccer", "world cup", "football (soccer)")
T_ESPORTE = tem_kw("sport", "sports")
T_CARNAVAL = tem_kw("carnival", "rio de janeiro", "brazil", "samba", "dancing") | (f.original_language.values == "pt")
T_CRIANCA = is_fam | tem_kw("children")

def peso_filmes(d):
    t = d.toordinal() - chg_ord
    w = base * fator_idade
    boost = np.where((t >= 0) & (t < 365), 1 + 16 * np.exp(-np.clip(t, 0, None) / 60.0), 1.0)
    w = w * boost * (t >= 0)
    ev = CAL.eventos(d)
    if "ferias" in ev:        w = w * np.where(T_CRIANCA, 1.6, 1.0)
    if "semana_criancas" in ev: w = w * np.where(T_CRIANCA, 2.0, 1.0)
    if d.month == 10:          w = w * np.where(is_hor, 1.9 if d.day >= 24 else 1.6, 1.0) * np.where(T_HALLOWEEN, 2.0, 1.0)
    if "natal" in ev:          w = w * np.where(T_NATAL, 4.0, 1.0)
    if "ano_novo" in ev:       w = w * np.where(T_ANONOVO, 3.0, 1.0)
    if "namorados" in ev:      w = w * np.where(T_NAMORADOS, 1.9, 1.0)
    if "maes" in ev:           w = w * np.where(T_MAES, 3.0, 1.0)
    if "pais" in ev:           w = w * np.where(T_PAIS, 3.0, 1.0)
    if "pascoa" in ev:         w = w * np.where(T_PASCOA, 3.0, 1.0)
    if "copa" in ev:           w = w * np.where(T_FUTEBOL, 4.0, 1.0) * np.where(T_ESPORTE, 1.5, 1.0)
    if "carnaval" in ev:       w = w * np.where(T_CARNAVAL, 2.5, 1.0)
    return w

def volume_dia(d, porte):
    v = 44.0 * porte * SAZ_MES[d.month] * SEM[d.weekday()]
    v *= CAL.fator_volume(d)
    return v

func_por_loja = {lj["id_loja"]: [x["id_funcionario"] for x in funcs if x["id_loja"] == lj["id_loja"]] for lj in lojas}
peso_func = [0.16, 0.28, 0.28, 0.28]
cli_cad = np.array([c["data_cadastro"].toordinal() for c in cli])
cli_churn = np.array([c["_churn"].toordinal() if c["_churn"] else 10**9 for c in cli])
cli_loja = np.array([c["id_loja_cadastro"] for c in cli])
cli_atv = np.array([c["_atv"] for c in cli])
film_ids = f.id_filme.values
classico = f.classico.values

locs, pags = [], []
sem_copia = []
perdidas = 0
HORAS = np.array([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21])
PH = np.array([2, 3, 4, 4, 4, 5, 6, 8, 11, 13, 12, 8], float); PH /= PH.sum()

TEM = {lj["id_loja"]: np.array([(lj["id_loja"], fid) in copias_por for fid in film_ids]) for lj in lojas}
for d in datas:
    w_all = peso_filmes(d)
    do = d.toordinal()
    for lj in lojas:
        L = lj["id_loja"]
        if d < lj["data_inauguracao"]: continue
        w = w_all * TEM[L]
        if w.sum() == 0: continue
        p = w / w.sum()
        n_trans = rng.poisson(volume_dia(d, lj["porte"]) / 1.6)
        elig = (cli_cad <= do) & (cli_churn > do)
        pc = cli_atv * elig * np.where(cli_loja == L, 1.0, 0.06)
        if pc.sum() == 0: continue
        pc = pc / pc.sum()
        clientes = rng.choice(len(cli), size=n_trans, p=pc)
        for ci in clientes:
            hora = int(rng.choice(HORAS, p=PH))
            dt = datetime(d.year, d.month, d.day, hora, int(rng.integers(0, 60)), int(rng.integers(0, 60)))
            k = int(rng.choice([1, 2, 3], p=[.55, .30, .15]))
            func = int(rng.choice(func_por_loja[L], p=peso_func))
            forma = rng.choice(["Dinheiro", "Cartão de débito", "Cartão de crédito"],
                               p=[.56, .29, .15] if d.year == 2009 else [.47, .35, .18])
            # comportamento de devolução da "sacola" inteira
            u = random.random()
            perfil = "prazo" if u < .785 else ("atraso" if u < .996 else "nunca")
            extra = int(rng.geometric(.5)) if perfil == "atraso" else 0
            escolhidos = set()
            for _ in range(k):
                for tentativa in range(3):
                    idx = int(rng.choice(nF, p=p))
                    fid = int(film_ids[idx])
                    if fid in escolhidos: continue
                    livres = [c for c in copias_por[(L, fid)] if livre[c] <= dt and aquis[c] <= d]
                    if livres: break
                    sem_copia.append((d, L, fid, int(ci + 1)))   # demanda não atendida: não havia cópia livre
                    if random.random() > .65: idx = None; break
                    idx = None
                if idx is None or fid in escolhidos:
                    perdidas += 1; continue
                escolhidos.add(fid)
                cop = random.choice(livres)
                if classico[idx]: tipo = "Clássico"
                elif (d - f.chegada.iat[idx]).days <= 180: tipo = "Lançamento"
                else: tipo = "Catálogo"
                id_tp, valor, prazo, multa_dia = preco(tipo, d)
                prevista = datetime.combine(d + timedelta(days=prazo), datetime.min.time()).replace(hour=20)
                if perfil == "nunca":
                    dev = None
                else:
                    if perfil == "prazo":
                        dd = d + timedelta(days=int(rng.integers(1, prazo + 1)) if prazo > 1 else 1)
                        if prazo > 1 and random.random() < .15: dd = d  # devolve no mesmo dia
                        dev = datetime(dd.year, dd.month, dd.day, int(rng.integers(9, 20)), int(rng.integers(0, 60)))
                        if dev < dt: dev = dt + timedelta(hours=2)
                    else:
                        dd = d + timedelta(days=prazo + extra)
                        dev = datetime(dd.year, dd.month, dd.day, int(rng.integers(9, 22)), int(rng.integers(0, 60)))
                    if dev > SNAPSHOT: dev = None
                atraso = max(0, (dev.date() - prevista.date()).days) if dev else 0
                if dev and dev > prevista and atraso == 0: atraso = 1
                livre[cop] = dev if dev else datetime(2099, 1, 1)
                idl = len(locs) + 1
                multa = round(atraso * multa_dia, 2)
                if multa > 0 and rng2.random() < 0.15:        # acordo no balcão: 30% de desconto na multa
                    multa = round(multa * 0.70, 2)
                valor_tab = valor
                if tipo != "Lançamento" and d.weekday() == 2:
                    promo, pct = "Quarta promocional", 0.25
                elif k == 3:
                    promo, pct = "Combo 3 filmes", 0.10
                elif FIDEL[ci]:
                    promo, pct = "Cartão fidelidade", 0.07
                else:
                    promo, pct = "Sem promoção", 0.0
                valor = round(valor_tab * (1 - pct), 2)
                desconto = round(valor_tab - valor, 2)
                locs.append((idl, cop, int(ci + 1), func, dt, prevista, dev, id_tp, valor, multa, valor_tab, desconto, promo))
                pags.append((len(pags) + 1, idl, int(ci + 1), func, "Locação", str(forma), valor, dt))
                if multa > 0 and random.random() < .9:
                    fpag = int(rng.choice(func_por_loja[L], p=peso_func))
                    pags.append((len(pags) + 1, idl, int(ci + 1), fpag, "Multa por atraso", str(forma), multa,
                                 dev + timedelta(minutes=int(rng.integers(1, 5)))))

print("locações", len(locs), "pagamentos", len(pags), "perdidas", perdidas)

f["titulo_en"] = f.titulo
f["titulo"] = f.titulo_pt.fillna(f.titulo)
# títulos brasileiros repetidos (ex.: "O Sobrevivente" para The Running Man e Rescue Dawn) ganham o ano
_dup = f.titulo.duplicated(keep=False)
f.loc[_dup, "titulo"] = f.loc[_dup, "titulo"] + " (" + f.loc[_dup, "ano"].astype(int).astype(str) + ")"
with open(f"{OUT}/dados.pkl", "wb") as fh:
    pickle.dump(dict(f=f, generos=generos, id_gen=id_gen, idiomas=idiomas, id_idi=id_idi, atores=atores, fa=fa,
                     cidades=cidades, id_cid=id_cid, UF=UF, enderecos=enderecos, lojas=lojas, funcs=funcs,
                     cli=cli_df, TABELA=TABELA, copias=cop_df, locs=locs, pags=pags, sem_copia=sem_copia), fh)
