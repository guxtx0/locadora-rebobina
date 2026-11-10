"""Monta as tabelas do modelo estrela (mesma lógica das views bi.*) a partir dos dados simulados."""
import pickle, math
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd
import calendario_br as CAL

CAMBIO = 1.76  # R$ por US$ — média de 2010, usada para converter bilheteria e orçamento
CORTE = date(2011, 1, 31)


def montar(pkl):
    D = pickle.load(open(pkl, "rb"))
    f = D["f"].copy()
    TAB = D["TABELA"]
    tipo_tp = {i + 1: t[0] for i, t in enumerate(TAB)}
    prazo_tp = {i + 1: t[2] for i, t in enumerate(TAB)}

    # ---------------- dim_filme
    dup = f.titulo.duplicated(keep=False)
    f["filme"] = np.where(dup, f.titulo + " (" + f.ano.astype(str) + ")", f.titulo)
    import tema_filmes
    f["tema"] = tema_filmes.temas(f)

    def faixa_dur(m):
        return "1. Até 89 min" if m < 90 else "2. De 90 a 119 min" if m < 120 else "3. De 120 a 149 min" if m < 150 else "4. 150 min ou mais"

    def faixa_bil(v):
        if not v or v <= 0: return "0. Sem informação"
        r = v * CAMBIO
        return "1. Até R$ 100 mi" if r < 100e6 else "2. R$ 100 a 400 mi" if r < 400e6 else "3. R$ 400 mi a 1 bi" if r < 1e9 else "4. Acima de R$ 1 bi"

    def tipo_atual(r):
        if r.classico: return "Clássico"
        return "Lançamento" if (CORTE - r.chegada).days <= 180 else "Catálogo"
    preco_atual = {t[0]: t[1] for t in TAB if t[5] is None}

    dim_filme = pd.DataFrame({
        "id_filme": f.id_filme,
        "filme": f.filme,
        "titulo_original": f.original_title.str.strip(),
        "titulo_ingles": f.titulo_en,
        "categoria": f.gen_principal,
        "idioma": f.idioma,
        "classificacao": f.classificacao,
        "duracao_min": f.duracao_min,
        "faixa_duracao": f.duracao_min.apply(faixa_dur),
        "data_lancamento": f.rd.dt.date,
        "ano_lancamento": f.ano.astype(int),
        "decada": (f.ano // 10 * 10).astype(str) + "s",
        "data_chegada_locadora": f.chegada,
        "perfil_titulo": np.where(f.rd >= "2009-01-01", "Lançamento do período",
                                  np.where(f.classico, "Clássico", "Acervo")),
        "sucesso_bilheteria": np.where(f.sucesso, "Sim", "Não"),
        "diretor": f.diretor,
        "bilheteria_rs": np.where(f.revenue > 0, (f.revenue * CAMBIO).round(0), np.nan),
        "orcamento_rs": np.where(f.budget > 0, (f.budget * CAMBIO).round(0), np.nan),
        "faixa_bilheteria": f.revenue.apply(faixa_bil),
        "nota_media": f.vote_average.round(1),
        "tema": f.tema,
        "tipo_preco_atual": f.apply(tipo_atual, axis=1),
    })
    dim_filme["preco_locacao"] = dim_filme.tipo_preco_atual.map(preco_atual)

    # ---------------- ator
    dim_ator = pd.DataFrame(sorted(((i, n) for n, i in D["atores"].items())), columns=["id_ator", "ator"])
    ponte = pd.DataFrame([(a, b, o) for a, b, o, _ in D["fa"]], columns=["id_filme", "id_ator", "ordem_credito"])

    # ---------------- cliente / loja
    end = pd.DataFrame(D["enderecos"]).set_index("id_endereco")
    cid_nome = {v: k for k, v in D["id_cid"].items()}
    lojas = pd.DataFrame(D["lojas"])
    funcs = pd.DataFrame(D["funcs"])
    c = D["cli"].copy()
    c["bairro"] = c.id_endereco.map(end.bairro)
    c["cidade"] = c.id_endereco.map(end.id_cidade).map(cid_nome)

    def idade(n):
        return CORTE.year - n.year - ((CORTE.month, CORTE.day) < (n.month, n.day))
    c["idade"] = c.data_nascimento.apply(idade)

    def faixa_et(i):
        return ("1. Até 17 anos" if i < 18 else "2. 18 a 24 anos" if i < 25 else "3. 25 a 34 anos" if i < 35
                else "4. 35 a 44 anos" if i < 45 else "5. 45 a 59 anos" if i < 60 else "6. 60 anos ou mais")
    dim_cliente = pd.DataFrame({
        "id_cliente": c.id_cliente,
        "cliente": c.nome + " " + c.sobrenome + " (cód. " + c.id_cliente.astype(str) + ")",
        "sexo": np.where(c.sexo == "F", "Feminino", "Masculino"),
        "idade": c.idade,
        "faixa_etaria": c.idade.apply(faixa_et),
        "bairro": c.bairro,
        "bairro_cidade": c.bairro + " – " + c.cidade,
        "cidade": c.cidade,
        "loja_cadastro": c.id_loja_cadastro.map(lojas.set_index("id_loja").nome),
        "data_cadastro": c.data_cadastro,
        "situacao_cadastro": np.where(c.ativo == 1, "Ativo", "Inativo"),
        "cartao_fidelidade": np.where(c.cartao_fidelidade == 1, "Sim", "Não"),
    })
    ger = funcs.set_index("id_funcionario")
    dim_loja = pd.DataFrame({
        "id_loja": lojas.id_loja,
        "loja": lojas.nome,
        "bairro": lojas.id_endereco.map(end.bairro),
        "cidade": lojas.cidade,
        "gerente": lojas.id_gerente.map(lambda i: ger.loc[i, "nome"] + " " + ger.loc[i, "sobrenome"]),
        "data_inauguracao": lojas.data_inauguracao,
    })

    # ---------------- fatos
    cop = D["copias"].set_index("id_copia")
    L = pd.DataFrame(D["locs"], columns="id cop cli func dt prev dev tp valor multa valor_tab desconto promo".split())
    P = pd.DataFrame(D["pags"], columns="id loc cli func tipo forma valor dt".split())
    # ids cronológicos (mesma regra dos scripts SQL)
    L = L.sort_values(["dt", "id"]).reset_index(drop=True)
    novo = dict(zip(L.id, range(1, len(L) + 1)))
    L["id"] = L.id.map(novo)
    P = P.sort_values(["dt", "id"]).reset_index(drop=True)
    P["id"] = range(1, len(P) + 1)
    P["loc"] = P["loc"].map(novo)
    pago = P.groupby("loc").valor.sum()

    dev_ok = L.dev.notna()
    dias_com = np.where(dev_ok, (L.dev.dt.normalize() - L.dt.dt.normalize()).dt.days, np.nan)
    atras = dev_ok & (L.dev > L.prev)
    dias_atr = np.where(~dev_ok, np.nan,
                        np.where(atras, np.maximum(1, (L.dev.dt.normalize() - L.prev.dt.normalize()).dt.days), 0))
    fato_locacao = pd.DataFrame({
        "id_locacao": L.id,
        "data_locacao": L.dt.dt.date,
        "hora_locacao": L.dt.dt.hour,
        "data_devolucao": L.dev.dt.date.where(dev_ok, None),
        "id_filme": L.cop.map(cop.id_filme),
        "id_loja": L.cop.map(cop.id_loja),
        "id_cliente": L.cli,
        "id_copia": L.cop,
        # fim (exclusivo) do período em que a cópia ficou fora da loja: devolução ou data de corte
        "data_fim_ocupacao": [max((dv.date() if pd.notna(dv) else CORTE + timedelta(days=1)), dt.date() + timedelta(days=1))
                              for dv, dt in zip(L.dev, L.dt)],
        "midia": L.cop.map(cop.midia),
        "tipo_preco": L.tp.map(tipo_tp),
        "prazo_dias": L.tp.map(prazo_tp),
        "dias_com_cliente": dias_com,
        "dias_atraso": dias_atr,
        "status_devolucao": np.where(~dev_ok, "Em aberto", np.where(atras, "Com atraso", "No prazo")),
        "promocao": L.promo,
        "valor_tabela": L.valor_tab.round(2),
        "valor_desconto": L.desconto.round(2),
        "valor_locacao": L.valor.round(2),
        "valor_multa": L.multa.round(2),
    })
    fato_locacao["valor_pago"] = fato_locacao.id_locacao.map(pago).fillna(0).round(2)
    fato_locacao["valor_pendente"] = (fato_locacao.valor_locacao + fato_locacao.valor_multa - fato_locacao.valor_pago).round(2)

    loc_filme = fato_locacao.set_index("id_locacao").id_filme
    fato_pagamento = pd.DataFrame({
        "id_pagamento": P.id,
        "data_pagamento": P.dt.dt.date,
        "id_cliente": P.cli,
        "id_loja": P.func.map(ger.id_loja),
        "id_filme": P["loc"].map(loc_filme),
        "tipo_pagamento": P.tipo,
        "forma_pagamento": P.forma,
        "valor": P.valor.round(2),
    })

    # ---------------- cópias e demanda não atendida
    cp = D["copias"]
    dim_copia = pd.DataFrame({"id_copia": cp.id_copia, "id_filme": cp.id_filme, "id_loja": cp.id_loja, "midia": cp.midia,
                              "data_aquisicao": cp.data_aquisicao, "custo_aquisicao": cp.custo_aquisicao.round(2)})
    sc = pd.DataFrame(D["sem_copia"], columns=["data", "id_loja", "id_filme", "id_cliente"])
    fx = f.set_index("id_filme")

    def preco_em(fid, d):
        r = fx.loc[fid]
        tipo = "Clássico" if r.classico else ("Lançamento" if (d - r.chegada).days <= 180 else "Catálogo")
        return next(t[1] for t in TAB if t[0] == tipo and t[4] <= d and (t[5] is None or d <= t[5]))
    fato_demanda = pd.DataFrame({"data": sc.data, "id_loja": sc.id_loja, "id_filme": sc.id_filme, "id_cliente": sc.id_cliente,
                                 "valor_estimado": [preco_em(i, d) for i, d in zip(sc.id_filme, sc.data)]})

    # ---------------- coorte (mês da primeira locação no período)
    primeira = fato_locacao.groupby("id_cliente").data_locacao.min()
    idx = primeira.apply(lambda d: (d.year - 2009) * 12 + d.month)
    dim_cliente["coorte_indice"] = dim_cliente.id_cliente.map(idx)
    dim_cliente["coorte"] = dim_cliente.coorte_indice.map(
        lambda i: None if pd.isna(i) else f"{CAL.MESES[(int(i) - 1) % 12]}/{str(2009 + (int(i) - 1) // 12)[2:]}")

    # ---------------- calendário
    dias = [date(2009, 1, 1) + timedelta(days=i) for i in range((date(2011, 1, 31) - date(2009, 1, 1)).days + 1)]
    cal = pd.DataFrame([CAL.linha_calendario(d) for d in dias])
    dim_calendario = cal.rename(columns={
        "MesNum": "Mês Nº", "Mes": "Mês", "AnoMesNum": "Ano-Mês Nº", "MesAno": "Mês/Ano",
        "TrimestreNum": "Trimestre Nº", "DiaSemana": "Dia da Semana", "DiaSemanaNum": "Dia da Semana Nº",
        "TipoDia": "Tipo de Dia", "TipoDiaOrdem": "Tipo de Dia Nº", "PeriodoEscolar": "Período Escolar",
        "DataComemorativa": "Data Comemorativa", "JogoBrasil": "Jogo do Brasil na Copa"})
    dim_calendario["Mês Índice"] = (dim_calendario.Ano - 2009) * 12 + dim_calendario["Mês Nº"]

    return dict(dim_filme=dim_filme, dim_ator=dim_ator, ponte_filme_ator=ponte, dim_cliente=dim_cliente,
                dim_loja=dim_loja, dim_calendario=dim_calendario, fato_locacao=fato_locacao,
                fato_pagamento=fato_pagamento, dim_copia=dim_copia, fato_demanda_nao_atendida=fato_demanda), D
