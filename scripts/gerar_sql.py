import sys, pickle, math
from datetime import date, datetime
import pandas as pd

D = pickle.load(open(sys.argv[1], "rb"))
OUT = sys.argv[2]
f = D["f"]
# ids em ordem cronológica, como num sistema real
locs = sorted(D["locs"], key=lambda r: (r[4], r[0]))
novo = {r[0]: i + 1 for i, r in enumerate(locs)}
D["locs"] = [(novo[r[0]],) + tuple(r[1:]) for r in locs]
pags = sorted(D["pags"], key=lambda r: (r[7], r[0]))
D["pags"] = [(i + 1, novo[r[1]]) + tuple(r[2:]) for i, r in enumerate(pags)]

def q(v):
    if v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NaT:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, datetime) or isinstance(v, pd.Timestamp):
        return "'" + v.strftime("%Y-%m-%dT%H:%M:%S") + "'"
    if isinstance(v, date):
        return "'" + v.strftime("%Y-%m-%d") + "'"
    if isinstance(v, (int,)) or hasattr(v, "dtype") and "int" in str(v.dtype):
        return str(int(v))
    if isinstance(v, float):
        return f"{v:.2f}" if abs(v - round(v, 2)) < 1e-9 else repr(v)
    return "N'" + str(v).replace("'", "''") + "'"

def bloco(fh, tabela, cols, rows, identity=True, chunk=1000):
    fh.write(f"\n-- {tabela}: {len(rows)} registros\n")
    if identity:
        fh.write(f"SET IDENTITY_INSERT dbo.{tabela} ON;\nGO\n")
    for i in range(0, len(rows), chunk):
        fh.write(f"INSERT INTO dbo.{tabela} ({', '.join(cols)}) VALUES\n")
        fh.write(",\n".join("(" + ", ".join(q(v) for v in r) + ")" for r in rows[i:i + chunk]))
        fh.write(";\nGO\n")
    if identity:
        fh.write(f"SET IDENTITY_INSERT dbo.{tabela} OFF;\nGO\n")

CAB = """/* =====================================================================
   LOCADORA REBOBINA · base fictícia para estudo de SQL e Power BI
   {titulo}
   Filmes reais (TMDB 5000); lojas, clientes, estoque e movimento simulados.
   ===================================================================== */
USE locadora_rebobina;
GO
SET NOCOUNT ON;
GO
"""

# ---------------------------------------------------------------- cadastros
with open(f"{OUT}/02_carga_cadastros.sql", "w", encoding="utf-8-sig") as fh:
    fh.write(CAB.format(titulo="Script 2 de 4 · cadastros (cidades, lojas, clientes, filmes, elenco, preços, estoque)"))
    bloco(fh, "cidade", ["id_cidade", "nome", "uf"], [(D["id_cid"][c], c, D["UF"][c]) for c in D["cidades"]])
    bloco(fh, "endereco", ["id_endereco", "logradouro", "numero", "bairro", "id_cidade", "cep"],
          [(e["id_endereco"], e["logradouro"], e["numero"], e["bairro"], e["id_cidade"], e["cep"]) for e in D["enderecos"]])
    bloco(fh, "loja", ["id_loja", "nome", "id_endereco", "data_inauguracao"],
          [(l["id_loja"], l["nome"], l["id_endereco"], l["data_inauguracao"]) for l in D["lojas"]])
    bloco(fh, "funcionario", ["id_funcionario", "nome", "sobrenome", "email", "id_loja", "cargo", "data_admissao", "ativo"],
          [(x["id_funcionario"], x["nome"], x["sobrenome"], x["email"], x["id_loja"], x["cargo"], x["data_admissao"], x["ativo"]) for x in D["funcs"]])
    for l in D["lojas"]:
        fh.write(f"UPDATE dbo.loja SET id_gerente = {l['id_gerente']} WHERE id_loja = {l['id_loja']};\n")
    fh.write("GO\n")
    c = D["cli"]
    bloco(fh, "cliente", ["id_cliente", "nome", "sobrenome", "sexo", "data_nascimento", "email", "id_endereco",
                          "id_loja_cadastro", "data_cadastro", "ativo", "cartao_fidelidade"],
          [(r.id_cliente, r.nome, r.sobrenome, r.sexo, r.data_nascimento, r.email, r.id_endereco,
            r.id_loja_cadastro, r.data_cadastro, int(r.ativo), int(r.cartao_fidelidade)) for r in c.itertuples()])
    bloco(fh, "idioma", ["id_idioma", "nome"], [(D["id_idi"][n], n) for n in D["idiomas"]])
    bloco(fh, "genero", ["id_genero", "nome"], [(D["id_gen"][g], g) for g in D["generos"]])
    rows = []
    for r in f.itertuples():
        rows.append((r.id_filme, r.titulo, r.original_title.strip(), r.titulo_en, r.rd.date(), int(r.rd.year), int(r.duracao_min),
                     D["id_idi"][r.idioma], D["id_gen"][r.gen_principal], r.classificacao,
                     r.diretor if isinstance(r.diretor, str) else None,
                     int(r.budget) if r.budget > 0 else None, int(r.revenue) if r.revenue > 0 else None,
                     round(float(r.popularity), 3), round(float(r.vote_average), 1), int(r.vote_count),
                     r.chegada, int(bool(r.classico)), int(r.id)))
    bloco(fh, "filme", ["id_filme", "titulo", "titulo_original", "titulo_ingles", "data_lancamento", "ano_lancamento", "duracao_min",
                        "id_idioma", "id_genero_principal", "classificacao_indicativa", "diretor", "orcamento_usd",
                        "bilheteria_usd", "popularidade", "nota_media", "total_votos", "data_chegada_locadora",
                        "classico", "id_tmdb"], rows)
    fg = sorted({(r.id_filme, D["id_gen"][g]) for r in f.itertuples() for g in r.gen_lista})
    bloco(fh, "filme_genero", ["id_filme", "id_genero"], fg, identity=False)
    bloco(fh, "ator", ["id_ator", "nome"], sorted((i, n) for n, i in D["atores"].items()))
    bloco(fh, "filme_ator", ["id_filme", "id_ator", "ordem_credito", "personagem"],
          [(a, b, o, p if p else None) for a, b, o, p in D["fa"]], identity=False)
    bloco(fh, "tabela_preco", ["id_tabela_preco", "tipo", "valor_diaria", "prazo_dias", "multa_dia",
                               "vigencia_inicio", "vigencia_fim"],
          [(i + 1, *t) for i, t in enumerate(D["TABELA"])])
    cp = D["copias"]
    bloco(fh, "copia", ["id_copia", "id_filme", "id_loja", "midia", "data_aquisicao", "custo_aquisicao"],
          [(r.id_copia, r.id_filme, r.id_loja, r.midia, r.data_aquisicao, float(r.custo_aquisicao)) for r in cp.itertuples()])

with open(f"{OUT}/03_carga_locacoes.sql", "w", encoding="utf-8-sig") as fh:
    fh.write(CAB.format(titulo="Script 3 de 4 · locações (jan/2009 a jan/2011)"))
    bloco(fh, "locacao", ["id_locacao", "id_copia", "id_cliente", "id_funcionario", "data_hora_locacao",
                          "data_prevista_devolucao", "data_hora_devolucao", "id_tabela_preco", "valor_locacao", "valor_multa",
                          "valor_tabela", "valor_desconto", "promocao"],
          [tuple(r) for r in D["locs"]])

with open(f"{OUT}/04_carga_pagamentos.sql", "w", encoding="utf-8-sig") as fh:
    fh.write(CAB.format(titulo="Script 4 de 4 · pagamentos (locações e multas)"))
    bloco(fh, "pagamento", ["id_pagamento", "id_locacao", "id_cliente", "id_funcionario", "tipo", "forma_pagamento",
                            "valor", "data_hora_pagamento"], [tuple(r) for r in D["pags"]])
print("ok")
