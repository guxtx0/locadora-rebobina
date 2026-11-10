"""Gera o modelo semântico (TMDL) do projeto Power BI com os dados embutidos nas consultas M."""
import base64, json, math, os, pickle, re, uuid, zlib
from datetime import date
import numpy as np
import pandas as pd

NS = uuid.UUID("6f1d8a52-2b0e-4c55-9d8e-0a5e7f3c2b11")
def tag(*p): return str(uuid.uuid5(NS, "|".join(map(str, p))))

def q(name):  # aspas em nomes TMDL quando necessário
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"

MONEY = '"R$"\\ #,0.00;-"R$"\\ #,0.00;"R$"\\ #,0.00'
PCT = "0.0%;-0.0%;0.0%"
INT = "#,0"
DEC1 = "#,0.0"
DATEF = "dd/mm/yyyy"

# tipo: (tipo M, dataType TMDL, formatString)
TIPOS = {
    "int": ("Int64.Type", "int64", "0"),
    "num": ("Int64.Type", "int64", INT),
    "txt": ("type text", "string", None),
    "dat": ("type date", "dateTime", DATEF),
    "dbl": ("type number", "double", DEC1),
    "brl": ("Currency.Type", "decimal", MONEY),
    "brl0": ("Currency.Type", "decimal", '"R$"\\ #,0;-"R$"\\ #,0;"R$"\\ #,0'),
    "pct": ("type number", "double", PCT),
    "dec3": ("type number", "double", "0.000"),
}

# (coluna, tipo, oculta, ordenar_por)
COLS = {
    "dim_filme": [("id_filme", "int", True, None), ("filme", "txt", False, None), ("titulo_original", "txt", True, None), ("titulo_ingles", "txt", True, None),
                  ("categoria", "txt", False, None), ("idioma", "txt", False, None), ("classificacao", "txt", False, None),
                  ("duracao_min", "num", False, None), ("faixa_duracao", "txt", False, None),
                  ("data_lancamento", "dat", False, None), ("ano_lancamento", "int", False, None),
                  ("decada", "txt", False, None), ("data_chegada_locadora", "dat", False, None),
                  ("perfil_titulo", "txt", False, None), ("sucesso_bilheteria", "txt", False, None),
                  ("diretor", "txt", False, None), ("bilheteria_rs", "brl0", False, None), ("orcamento_rs", "brl0", False, None),
                  ("faixa_bilheteria", "txt", False, None), ("nota_media", "dbl", False, None), ("tema", "txt", False, None),
                  ("tipo_preco_atual", "txt", False, None), ("preco_locacao", "brl", False, None)],
    "dim_ator": [("id_ator", "int", True, None), ("ator", "txt", False, None)],
    "ponte_filme_ator": [("id_filme", "int", True, None), ("id_ator", "int", True, None), ("ordem_credito", "int", True, None)],
    "dim_cliente": [("id_cliente", "int", True, None), ("cliente", "txt", False, None), ("sexo", "txt", False, None),
                    ("idade", "int", False, None), ("faixa_etaria", "txt", False, None), ("bairro", "txt", False, None),
                    ("bairro_cidade", "txt", False, None), ("cidade", "txt", False, None), ("loja_cadastro", "txt", False, None),
                    ("data_cadastro", "dat", False, None), ("situacao_cadastro", "txt", False, None),
                    ("cartao_fidelidade", "txt", False, None), ("coorte_indice", "int", True, None),
                    ("coorte", "txt", False, "coorte_indice"), ("prob_abandono", "pct", False, None),
                    ("faixa_risco", "txt", False, None), ("receita_em_risco_180d", "brl", False, None)],
    "dim_loja": [("id_loja", "int", True, None), ("loja", "txt", False, None), ("bairro", "txt", False, None),
                 ("cidade", "txt", False, None), ("gerente", "txt", False, None), ("data_inauguracao", "dat", False, None)],
    "dim_calendario": [("Data", "dat", False, None), ("Ano", "int", False, None), ("Mês Nº", "int", True, None),
                       ("Mês", "txt", False, "Mês Nº"), ("Ano-Mês Nº", "int", True, None), ("Mês/Ano", "txt", False, "Ano-Mês Nº"),
                       ("Trimestre", "txt", False, "Trimestre Nº"), ("Trimestre Nº", "int", True, None),
                       ("Dia da Semana", "txt", False, "Dia da Semana Nº"), ("Dia da Semana Nº", "int", True, None),
                       ("Feriado", "txt", False, None), ("Tipo de Dia", "txt", False, "Tipo de Dia Nº"),
                       ("Tipo de Dia Nº", "int", True, None), ("Período Escolar", "txt", False, None),
                       ("Data Comemorativa", "txt", False, None), ("Jogo do Brasil na Copa", "txt", False, None),
                       ("Mês Índice", "int", True, None)],
    "dim_copia": [("id_copia", "int", True, None), ("id_filme", "int", True, None), ("id_loja", "int", True, None),
                  ("midia", "txt", False, None), ("data_aquisicao", "dat", False, None), ("custo_aquisicao", "brl", False, None)],
    "fato_demanda_nao_atendida": [("data", "dat", False, None), ("id_loja", "int", True, None), ("id_filme", "int", True, None),
                                  ("id_cliente", "int", True, None), ("valor_estimado", "brl", False, None)],
    "previsao_lancamentos": [("id_filme", "int", True, None), ("data_chegada", "dat", False, None), ("conjunto", "txt", False, None),
                             ("demanda_real_8sem", "dbl", False, None), ("demanda_prevista_8sem", "dbl", False, None),
                             ("erro_absoluto", "dbl", False, None), ("copias_recomendadas_por_loja", "dbl", False, None)],
    "otimizacao_copias": [("id_filme", "int", True, None), ("id_loja", "int", True, None), ("copias_atuais", "num", False, None),
                          ("copias_ideais", "num", False, None), ("demanda_180d", "dbl", False, None),
                          ("locacoes_atendiveis_atual", "dbl", False, None), ("receita_perdida_atual", "brl", False, None),
                          ("ganho_liquido", "brl", False, None), ("custo_liquido_copia", "brl", False, None), ("ajuste", "txt", False, None)],
    "importancia_churn": [("fator", "txt", False, None), ("importancia", "dec3", False, None)],
    "metricas_modelos": [("modelo", "txt", False, None), ("metrica", "txt", False, None), ("valor", "dbl", False, None),
                         ("texto", "txt", False, None), ("ordem", "int", False, None)],
    "fato_locacao": [("id_locacao", "int", True, None), ("data_locacao", "dat", False, None), ("hora_locacao", "int", False, None),
                     ("data_devolucao", "dat", False, None), ("id_filme", "int", True, None), ("id_loja", "int", True, None),
                     ("id_cliente", "int", True, None), ("id_copia", "int", True, None),
                     ("data_fim_ocupacao", "dat", True, None), ("midia", "txt", False, None), ("tipo_preco", "txt", False, None),
                     ("prazo_dias", "int", False, None), ("dias_com_cliente", "int", False, None), ("dias_atraso", "int", False, None),
                     ("status_devolucao", "txt", False, None), ("promocao", "txt", False, None),
                     ("valor_tabela", "brl", False, None), ("valor_desconto", "brl", False, None), ("valor_locacao", "brl", False, None),
                     ("valor_multa", "brl", False, None), ("valor_pago", "brl", False, None), ("valor_pendente", "brl", False, None)],
    "fato_pagamento": [("id_pagamento", "int", True, None), ("data_pagamento", "dat", False, None), ("id_cliente", "int", True, None),
                       ("id_loja", "int", True, None), ("id_filme", "int", True, None), ("tipo_pagamento", "txt", False, None),
                       ("forma_pagamento", "txt", False, None), ("valor", "brl", False, None)],
}
DESCR = {
    "dim_filme": "Filmes do acervo (títulos reais do TMDB 5000). Bilheteria e orçamento convertidos para R$ pelo câmbio médio de 2010 (R$ 1,76).",
    "dim_ator": "Atores (5 primeiros créditos de cada filme).",
    "ponte_filme_ator": "Ponte entre filmes e atores (relação muitos-para-muitos).",
    "dim_cliente": "Clientes da rede. Idade calculada em 31/01/2011.",
    "dim_loja": "Lojas da rede Rebobina.",
    "dim_calendario": "Calendário de jan/2009 a jan/2011 com feriados nacionais, vésperas, férias escolares e datas comemorativas.",
    "fato_locacao": "Uma linha por filme alugado.",
    "fato_pagamento": "Uma linha por pagamento (locações e multas). Fonte do faturamento, em R$.",
    "dim_copia": "Cópias físicas (DVD e Blu-ray) de cada filme em cada loja. Base da taxa de ocupação do estoque.",
    "fato_demanda_nao_atendida": "Tentativas de locação sem cópia livre na loja: demanda perdida por falta de estoque.",
    "previsao_lancamentos": "Python: demanda prevista e real dos lançamentos nas 8 primeiras semanas (modelo de gradient boosting).",
    "otimizacao_copias": "Python: número ideal de cópias por filme e loja na fase de lançamento (180 dias).",
    "importancia_churn": "Python: peso de cada fator no modelo de risco de abandono (importância por permutação).",
    "metricas_modelos": "Python: métricas de validação dos modelos.",
}

MAX_B64 = 350_000


def csv_text(df, cols):
    out = df[[c[0] for c in cols]].copy()
    for c, t, *_ in cols:
        if t in ("int", "num"):
            out[c] = out[c].apply(lambda v: "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(int(v)))
        elif t == "dat":
            out[c] = out[c].apply(lambda v: "" if v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NaT else v.isoformat())
        elif t in ("brl", "brl0", "dbl"):
            out[c] = out[c].apply(lambda v: "" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.2f}".rstrip("0").rstrip("."))
        else:
            out[c] = out[c].apply(lambda v: "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v).replace("\n", " ").replace("\r", " "))
    return out


def comprimir(texto):
    co = zlib.compressobj(9, zlib.DEFLATED, -15)
    return base64.b64encode(co.compress(texto.encode("utf-8")) + co.flush()).decode("ascii")


def partes_b64(df, cols):
    tab = csv_text(df, cols)
    n = 1
    while True:
        partes, ok = [], True
        for bloco in np.array_split(np.arange(len(tab)), n):
            b = comprimir(tab.iloc[bloco].to_csv(index=False, lineterminator="\n"))
            if len(b) > MAX_B64:
                ok = False; break
            partes.append(b)
        if ok:
            return partes
        n += 1


def m_query(nome, df, cols):
    partes = partes_b64(df, cols)
    tipos = ", ".join('{"%s", %s}' % (c, TIPOS[t][0]) for c, t, *_ in cols)
    linhas = ["let", "    Partes = {"]
    linhas += ['        "%s"%s' % (p, "," if i < len(partes) - 1 else "") for i, p in enumerate(partes)]
    linhas += [
        "    },",
        "    Ler = (b64 as text) as table =>",
        "        Table.PromoteHeaders(",
        "            Csv.Document(",
        "                Binary.Decompress(Binary.FromText(b64, BinaryEncoding.Base64), Compression.Deflate),",
        "                [Delimiter = \",\", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]",
        "            ),",
        "            [PromoteAllScalars = true]",
        "        ),",
        "    Fonte = Table.Combine(List.Transform(Partes, Ler)),",
        "    Nulos = Table.TransformColumns(Fonte, {}, each if _ = \"\" then null else _),",
        "    Tipos = Table.TransformColumnTypes(Nulos, {%s}, \"en-US\")" % tipos,
        "in",
        "    Tipos",
    ]
    return linhas, partes


def tabela_tmdl(nome, df, cols):
    L = [f"/// {DESCR[nome]}", f"table {q(nome)}", f"\tlineageTag: {tag(nome)}"]
    if nome == "dim_calendario":
        L.append("\tdataCategory: Time")
    L.append("")
    for c, t, oculto, ordem in cols:
        mt, dt, fmt = TIPOS[t]
        L.append(f"\tcolumn {q(c)}")
        L.append(f"\t\tdataType: {dt}")
        if oculto: L.append("\t\tisHidden")
        if nome == "dim_calendario" and c == "Data": L.append("\t\tisKey")
        if fmt: L.append(f"\t\tformatString: {fmt}")
        L.append(f"\t\tlineageTag: {tag(nome, c)}")
        L.append("\t\tsummarizeBy: none")
        L.append(f"\t\tsourceColumn: {c}")
        if ordem: L.append(f"\t\tsortByColumn: {q(ordem)}")
        L.append("")
        if t == "dat":
            L.append("\t\tannotation UnderlyingDateTimeDataType = Date")
            L.append("")
        L.append("\t\tannotation SummarizationSetBy = Automatic")
        L.append("")
    linhas, partes = m_query(nome, df, cols)
    L.append(f"\tpartition {q(nome)} = m")
    L.append("\t\tmode: import")
    L.append("\t\tsource =")
    L += ["\t\t\t\t" + x for x in linhas]
    L.append("")
    L.append("\tannotation PBI_ResultType = Table")
    L.append("")
    return "\n".join(L), partes


# ------------------------------------------------------------------ medidas
MEDIDAS = [
    # (pasta, nome, dax, formato, descrição)
    ("1. Receita", "Faturamento", "SUM ( fato_pagamento[valor] )", MONEY, "Total recebido (locações + multas), em R$."),
    ("1. Receita", "Receita de Locações", 'CALCULATE ( [Faturamento], fato_pagamento[tipo_pagamento] = "Locação" )', MONEY, None),
    ("1. Receita", "Receita de Multas", 'CALCULATE ( [Faturamento], fato_pagamento[tipo_pagamento] = "Multa por atraso" )', MONEY, None),
    ("1. Receita", "% Receita de Multas", "DIVIDE ( [Receita de Multas], [Faturamento] )", PCT, None),
    ("1. Receita", "Ticket Médio por Locação", "DIVIDE ( [Faturamento], [Locações] )", MONEY, "Faturamento dividido pelo número de locações (inclui multas)."),
    ("1. Receita", "Faturamento por Cliente", "DIVIDE ( [Faturamento], [Clientes Ativos] )", MONEY, None),
    ("1. Receita", "Faturamento Mês Anterior", "CALCULATE ( [Faturamento], DATEADD ( dim_calendario[Data], -1, MONTH ) )", MONEY, None),
    ("1. Receita", "Variação vs Mês Anterior %",
     "DIVIDE ( [Faturamento] - [Faturamento Mês Anterior], [Faturamento Mês Anterior] )", PCT, None),
    ("1. Receita", "Descontos Concedidos", "SUM ( fato_locacao[valor_desconto] )", MONEY,
     "Descontos de promoções: quarta promocional, combo de 3 filmes e cartão fidelidade."),
    ("1. Receita", "% Locações com Promoção",
     'DIVIDE ( CALCULATE ( [Locações], fato_locacao[promocao] <> "Sem promoção" ), [Locações] )', PCT, None),
    ("1. Receita", "Multas Pendentes", "SUM ( fato_locacao[valor_pendente] )", MONEY, "Multas de atraso ainda não pagas."),
    ("2. Volume", "Locações", "COUNTROWS ( fato_locacao )", INT, "Quantidade de filmes alugados."),
    ("2. Volume", "Clientes Ativos", "DISTINCTCOUNT ( fato_locacao[id_cliente] )", INT, "Clientes com pelo menos uma locação no período filtrado."),
    ("2. Volume", "Locações por Cliente", "DIVIDE ( [Locações], [Clientes Ativos] )", DEC1, None),
    ("2. Volume", "Locações de Lançamentos", 'CALCULATE ( [Locações], fato_locacao[tipo_preco] = "Lançamento" )', INT, None),
    ("2. Volume", "% Locações de Lançamentos", "DIVIDE ( [Locações de Lançamentos], [Locações] )", PCT, None),
    ("2. Volume", "Média Diária de Locações", "DIVIDE ( [Locações], COUNTROWS ( dim_calendario ) )", DEC1, "Locações divididas pelo número de dias do calendário no filtro."),
    ("3. Catálogo", "Filmes no Catálogo", "COUNTROWS ( dim_filme )", INT, None),
    ("3. Catálogo", "Filmes Locados", "DISTINCTCOUNT ( fato_locacao[id_filme] )", INT, None),
    ("3. Catálogo", "Locações por Título", "DIVIDE ( [Locações], [Filmes Locados] )", DEC1, None),
    ("3. Catálogo", "Preço Médio de Locação", "AVERAGE ( fato_locacao[valor_locacao] )", MONEY, None),
    ("3. Catálogo", "% Animação e Família",
     'DIVIDE ( CALCULATE ( [Locações], KEEPFILTERS ( dim_filme[categoria] IN { "Animação", "Família" } ) ), [Locações] )', PCT, None),
    ("3. Catálogo", "% Terror", 'DIVIDE ( CALCULATE ( [Locações], KEEPFILTERS ( dim_filme[categoria] = "Terror" ) ), [Locações] )', PCT, None),
    ("3. Catálogo", "Locações de Filmes Temáticos", "CALCULATE ( [Locações], KEEPFILTERS ( NOT ISBLANK ( dim_filme[tema] ) ) )", INT,
     "Locações de filmes ligados a alguma data comemorativa (Natal, Dia das Mães, Halloween etc.)."),
    ("4. Operação", "Locações Devolvidas", 'CALCULATE ( [Locações], fato_locacao[status_devolucao] <> "Em aberto" )', INT, None),
    ("4. Operação", "Locações com Atraso", 'CALCULATE ( [Locações], fato_locacao[status_devolucao] = "Com atraso" )', INT, None),
    ("4. Operação", "% Devoluções com Atraso", "DIVIDE ( [Locações com Atraso], [Locações Devolvidas] )", PCT, None),
    ("4. Operação", "Locações em Aberto", 'CALCULATE ( [Locações], fato_locacao[status_devolucao] = "Em aberto" )', INT, None),
    ("4. Operação", "Dias Médios com Cliente", "AVERAGE ( fato_locacao[dias_com_cliente] )", DEC1, None),
    ("5. Calendário", "Média Diária em Vésperas",
     'CALCULATE ( [Média Diária de Locações], dim_calendario[Tipo de Dia] = "Véspera de feriado" )', DEC1, None),
    ("5. Calendário", "Média Diária em Dias Úteis",
     'CALCULATE ( [Média Diária de Locações], dim_calendario[Tipo de Dia] = "Dia útil" )', DEC1, None),
    ("5. Calendário", "Efeito Véspera de Feriado %",
     "DIVIDE ( [Média Diária em Vésperas], [Média Diária em Dias Úteis] ) - 1", PCT,
     "Quanto a média diária de locações na véspera de feriado supera a de um dia útil comum."),
    ("5. Calendário", "Média Diária em Datas Comemorativas",
     "IF ( NOT ISBLANK ( SELECTEDVALUE ( dim_calendario[Data Comemorativa] ) ), [Média Diária de Locações] )", DEC1, None),
    ("5. Calendário", "Período Analisado",
     'VAR _ini = MIN ( fato_locacao[data_locacao] )\nVAR _fim = MAX ( fato_locacao[data_locacao] )\nRETURN\n    FORMAT ( _ini, "dd/mm/yyyy" ) & " a " & FORMAT ( _fim, "dd/mm/yyyy" )', None, None),
    # ---------- DAX avançado: ocupação do estoque (eventos com duração x calendário)
    ("7. Estoque", "Dias Alugados",
     "VAR _ini = MIN ( dim_calendario[Data] )\nVAR _fim = MAX ( dim_calendario[Data] ) + 1\nRETURN\n    SUMX (\n        FILTER (\n            CALCULATETABLE ( fato_locacao, REMOVEFILTERS ( dim_calendario ) ),\n            fato_locacao[data_locacao] < _fim && fato_locacao[data_fim_ocupacao] > _ini\n        ),\n        INT ( MIN ( _fim, fato_locacao[data_fim_ocupacao] ) - MAX ( _ini, fato_locacao[data_locacao] ) )\n    )",
     INT, "Dias-cópia em que as cópias estiveram com clientes dentro do período filtrado (considera locações que começaram antes do período)."),
    ("7. Estoque", "Dias de Cópia Disponíveis",
     "VAR _ini = MIN ( dim_calendario[Data] )\nVAR _fim = MAX ( dim_calendario[Data] ) + 1\nRETURN\n    SUMX (\n        FILTER ( dim_copia, dim_copia[data_aquisicao] < _fim ),\n        INT ( _fim - MAX ( _ini, dim_copia[data_aquisicao] ) )\n    )",
     INT, "Dias-cópia em que cada cópia já estava no acervo dentro do período filtrado."),
    ("7. Estoque", "Taxa de Ocupação", "DIVIDE ( [Dias Alugados], [Dias de Cópia Disponíveis] )", PCT,
     "Percentual do tempo em que as cópias estiveram fora da loja, alugadas."),
    ("7. Estoque", "Ocupação – Lançamentos do Período",
     'CALCULATE ( [Taxa de Ocupação], dim_filme[perfil_titulo] = "Lançamento do período" )', PCT, None),
    ("7. Estoque", "Ocupação – Acervo", 'CALCULATE ( [Taxa de Ocupação], dim_filme[perfil_titulo] = "Acervo" )', PCT, None),
    ("7. Estoque", "Ocupação – Clássicos", 'CALCULATE ( [Taxa de Ocupação], dim_filme[perfil_titulo] = "Clássico" )', PCT, None),
    ("7. Estoque", "Cópias no Acervo",
     "COUNTROWS ( FILTER ( dim_copia, dim_copia[data_aquisicao] <= MAX ( dim_calendario[Data] ) ) )", INT, None),
    ("7. Estoque", "Demanda Não Atendida", "COUNTROWS ( fato_demanda_nao_atendida )", INT,
     "Tentativas de locação em que não havia cópia livre."),
    ("7. Estoque", "Receita em Risco por Falta de Cópia", "SUM ( fato_demanda_nao_atendida[valor_estimado] )", MONEY, None),
    # ---------- DAX avançado: coorte de retenção (tabela desconectada + TREATAS)
    ("8. Retenção", "Clientes na Coorte",
     "CALCULATE ( COUNTROWS ( dim_cliente ), NOT ISBLANK ( dim_cliente[coorte_indice] ) )", INT,
     "Clientes cuja primeira locação do período caiu no mês da coorte."),
    ("8. Retenção", "Retenção %",
     "VAR _k = SELECTEDVALUE ( meses_relativos[Mês] )\nVAR _c = SELECTEDVALUE ( dim_cliente[coorte_indice] )\nVAR _alvo = _c + _k\nVAR _ativos =\n    CALCULATE (\n        DISTINCTCOUNT ( fato_locacao[id_cliente] ),\n        REMOVEFILTERS ( dim_calendario ),\n        TREATAS ( { _alvo }, dim_calendario[Mês Índice] )\n    )\nRETURN\n    IF ( NOT ISBLANK ( _c ) && NOT ISBLANK ( _k ) && _alvo <= 25, DIVIDE ( _ativos, [Clientes na Coorte] ) )",
     PCT, "% dos clientes da coorte que alugaram no k-ésimo mês após a primeira locação."),
    ("8. Retenção", "Retenção Média no 3º Mês",
     "AVERAGEX (\n    VALUES ( dim_cliente[coorte_indice] ),\n    CALCULATE ( [Retenção %], meses_relativos[Mês] = 3 )\n)", PCT, None),
    ("8. Retenção", "Retenção Média no 12º Mês",
     "AVERAGEX (\n    VALUES ( dim_cliente[coorte_indice] ),\n    CALCULATE ( [Retenção %], meses_relativos[Mês] = 12 )\n)", PCT, None),
    # ---------- resultados dos modelos em Python
    ("9. Modelos (Python)", "Demanda Prevista (teste)",
     'CALCULATE ( SUM ( previsao_lancamentos[demanda_prevista_8sem] ), previsao_lancamentos[conjunto] = "Teste" )', DEC1, None),
    ("9. Modelos (Python)", "Demanda Real (teste)",
     'CALCULATE ( SUM ( previsao_lancamentos[demanda_real_8sem] ), previsao_lancamentos[conjunto] = "Teste" )', DEC1, None),
    ("9. Modelos (Python)", "Erro Médio da Previsão",
     'CALCULATE ( AVERAGE ( previsao_lancamentos[erro_absoluto] ), previsao_lancamentos[conjunto] = "Teste" )', DEC1,
     "Erro médio absoluto, em locações, nos lançamentos de teste (mai a dez/2010)."),
    ("9. Modelos (Python)", "R² da Previsão", 'LOOKUPVALUE ( metricas_modelos[texto], metricas_modelos[metrica], "R² no teste" )', None, None),
    ("9. Modelos (Python)", "AUC do Modelo de Abandono", 'LOOKUPVALUE ( metricas_modelos[texto], metricas_modelos[metrica], "AUC no teste" )', None, None),
    ("9. Modelos (Python)", "Cópias Atuais", "SUM ( otimizacao_copias[copias_atuais] )", INT, None),
    ("9. Modelos (Python)", "Cópias Ideais", "SUM ( otimizacao_copias[copias_ideais] )", INT, None),
    ("9. Modelos (Python)", "Ganho com Cópias Ideais", "SUM ( otimizacao_copias[ganho_liquido] )", MONEY,
     "Lucro adicional na fase de lançamento se cada filme tivesse o número ideal de cópias em cada loja."),
    ("9. Modelos (Python)", "Clientes", "COUNTROWS ( dim_cliente )", INT, None),
    ("9. Modelos (Python)", "Clientes em Risco Alto", 'CALCULATE ( COUNTROWS ( dim_cliente ), dim_cliente[faixa_risco] = "1. Alto" )', INT, None),
    ("9. Modelos (Python)", "Receita em Risco (Abandono)", "SUM ( dim_cliente[receita_em_risco_180d] )", MONEY,
     "Gasto dos últimos 180 dias ponderado pela probabilidade de abandono."),
    ("9. Modelos (Python)", "Importância do Fator", "SUM ( importancia_churn[importancia] )", "0.000", None),
    ("6. Rankings", "Faturamento (Top 15 filmes)",
     "IF ( RANKX ( ALLSELECTED ( dim_filme ), [Faturamento],, DESC ) <= 15, [Faturamento] )", MONEY,
     "Faturamento apenas para os 15 filmes que mais faturaram no filtro atual."),
    ("6. Rankings", "Locações (Top 15 filmes)",
     "IF ( RANKX ( ALLSELECTED ( dim_filme ), [Faturamento],, DESC ) <= 15, [Locações] )", INT, None),
    ("6. Rankings", "Locações (Top 10 atores)",
     "IF ( RANKX ( ALLSELECTED ( dim_ator[ator] ), [Locações],, DESC ) <= 10, [Locações] )", INT, None),
    ("6. Rankings", "Faturamento (Top 10 bairros)",
     "IF ( RANKX ( ALLSELECTED ( dim_cliente[bairro_cidade] ), [Faturamento],, DESC ) <= 10, [Faturamento] )", MONEY, None),
    ("6. Rankings", "Faturamento (Top 10 clientes)",
     "IF ( RANKX ( ALLSELECTED ( dim_cliente ), [Faturamento],, DESC ) <= 10, [Faturamento] )", MONEY, None),
    ("6. Rankings", "Locações (Top 10 clientes)",
     "IF ( RANKX ( ALLSELECTED ( dim_cliente ), [Faturamento],, DESC ) <= 10, [Locações] )", INT, None),
]


def medidas_tmdl():
    L = ["/// Tabela só de medidas.", "table _Medidas", f"\tlineageTag: {tag('_Medidas')}", ""]
    for pasta, nome, dax, fmt, desc in MEDIDAS:
        if desc: L.append(f"\t/// {desc}")
        if "\n" in dax:
            L.append(f"\tmeasure {q(nome)} =")
            L += ["\t\t\t" + x for x in dax.split("\n")]
        else:
            L.append(f"\tmeasure {q(nome)} = {dax}")
        if fmt: L.append(f"\t\tformatString: {fmt}")
        L.append(f"\t\tdisplayFolder: {pasta}")
        L.append(f"\t\tlineageTag: {tag('m', nome)}")
        L.append("")
    L += ["\tcolumn Value", "\t\tisHidden", f"\t\tlineageTag: {tag('_Medidas', 'Value')}", "\t\tisNameInferred",
          "\t\tsourceColumn: [Value]", "", "\tpartition _Medidas = calculated", "\t\tmode: import", "\t\tsource = {1}", ""]
    return "\n".join(L)


def meses_relativos_tmdl():
    return "\n".join([
        "/// Tabela desconectada com os meses relativos (0 a 24) usada na matriz de coorte.",
        "table meses_relativos", f"\tlineageTag: {tag('meses_relativos')}", "",
        "\tcolumn 'Mês'", "\t\tdataType: int64", "\t\tformatString: 0", f"\t\tlineageTag: {tag('meses_relativos', 'Mês')}",
        "\t\tsummarizeBy: none", "\t\tsourceColumn: Mês", "", "\t\tannotation SummarizationSetBy = Automatic", "",
        "\tpartition meses_relativos = m", "\t\tmode: import", "\t\tsource =",
        "\t\t\t\tlet", "\t\t\t\t    Fonte = Table.FromColumns({List.Numbers(0, 25)}, type table [Mês = Int64.Type])",
        "\t\t\t\tin", "\t\t\t\t    Fonte", "", "\tannotation PBI_ResultType = Table", ""])


ITENS_TEMPO = [
    ("Período atual", "SELECTEDMEASURE ()", None),
    ("Mês anterior", "CALCULATE ( SELECTEDMEASURE (), DATEADD ( dim_calendario[Data], -1, MONTH ) )", None),
    ("Mesmo período do ano anterior", "CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( dim_calendario[Data] ) )", None),
    ("Acumulado no ano", "CALCULATE ( SELECTEDMEASURE (), DATESYTD ( dim_calendario[Data] ) )", None),
    ("Variação vs ano anterior %",
     "VAR _atual = SELECTEDMEASURE ()\nVAR _anterior = CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( dim_calendario[Data] ) )\nRETURN\n    IF ( ISSELECTEDMEASURE ( [Período Analisado] ), _atual, DIVIDE ( _atual - _anterior, _anterior ) )",
     'IF ( ISSELECTEDMEASURE ( [Período Analisado] ), SELECTEDMEASUREFORMATSTRING (), "+0.0%;-0.0%;0.0%" )'),
]


def grupo_calculo_tmdl():
    L = ["/// Grupo de cálculo: aplica comparações de tempo a qualquer medida do modelo.",
         "table 'Comparação de Tempo'", f"\tlineageTag: {tag('calcgroup')}", "", "\tcalculationGroup", "\t\tprecedence: 1", ""]
    for i, (nome, dax, fmt) in enumerate(ITENS_TEMPO):
        if "\n" in dax:
            L.append(f"\t\tcalculationItem {q(nome)} =")
            L += ["\t\t\t\t" + x for x in dax.split("\n")]
        else:
            L.append(f"\t\tcalculationItem {q(nome)} = {dax}")
        L.append(f"\t\t\tordinal: {i}")
        if fmt:
            L.append("")
            L.append(f"\t\t\tformatStringDefinition = {fmt}")
        L.append("")
    L += ["\tcolumn 'Comparação'", "\t\tdataType: string", f"\t\tlineageTag: {tag('calcgroup', 'nome')}",
          "\t\tsummarizeBy: none", "\t\tsourceColumn: Name", "\t\tsortByColumn: Ordem", "",
          "\t\tannotation SummarizationSetBy = Automatic", "",
          "\tcolumn Ordem", "\t\tdataType: int64", "\t\tisHidden", "\t\tformatString: 0",
          f"\t\tlineageTag: {tag('calcgroup', 'ordem')}", "\t\tsummarizeBy: sum", "\t\tsourceColumn: Ordinal", "",
          "\t\tannotation SummarizationSetBy = Automatic", ""]
    return "\n".join(L)


RELS = [
    ("fato_locacao", "data_locacao", "dim_calendario", "Data", False),
    ("fato_pagamento", "data_pagamento", "dim_calendario", "Data", False),
    ("fato_locacao", "id_filme", "dim_filme", "id_filme", False),
    ("fato_pagamento", "id_filme", "dim_filme", "id_filme", False),
    ("fato_locacao", "id_cliente", "dim_cliente", "id_cliente", False),
    ("fato_pagamento", "id_cliente", "dim_cliente", "id_cliente", False),
    ("fato_locacao", "id_loja", "dim_loja", "id_loja", False),
    ("fato_pagamento", "id_loja", "dim_loja", "id_loja", False),
    ("ponte_filme_ator", "id_ator", "dim_ator", "id_ator", False),
    ("ponte_filme_ator", "id_filme", "dim_filme", "id_filme", True),
    ("dim_copia", "id_filme", "dim_filme", "id_filme", False),
    ("dim_copia", "id_loja", "dim_loja", "id_loja", False),
    ("fato_demanda_nao_atendida", "data", "dim_calendario", "Data", False),
    ("fato_demanda_nao_atendida", "id_filme", "dim_filme", "id_filme", False),
    ("fato_demanda_nao_atendida", "id_loja", "dim_loja", "id_loja", False),
    ("fato_demanda_nao_atendida", "id_cliente", "dim_cliente", "id_cliente", False),
    ("previsao_lancamentos", "id_filme", "dim_filme", "id_filme", False),
    ("otimizacao_copias", "id_filme", "dim_filme", "id_filme", False),
    ("otimizacao_copias", "id_loja", "dim_loja", "id_loja", False),
]


def gerar(tabelas, pasta):
    d = os.path.join(pasta, "definition")
    os.makedirs(os.path.join(d, "tables"), exist_ok=True)
    ordem = ["dim_calendario", "dim_filme", "dim_ator", "ponte_filme_ator", "dim_cliente", "dim_loja", "fato_locacao", "fato_pagamento",
             "dim_copia", "fato_demanda_nao_atendida", "previsao_lancamentos", "otimizacao_copias", "importancia_churn", "metricas_modelos"]
    stats = {}
    for nome in ordem:
        txt, partes = tabela_tmdl(nome, tabelas[nome], COLS[nome])
        open(os.path.join(d, "tables", f"{nome}.tmdl"), "w", encoding="utf-8", newline="\n").write(txt)
        stats[nome] = (len(tabelas[nome]), len(partes), sum(map(len, partes)))
    open(os.path.join(d, "tables", "_Medidas.tmdl"), "w", encoding="utf-8", newline="\n").write(medidas_tmdl())
    open(os.path.join(d, "tables", "meses_relativos.tmdl"), "w", encoding="utf-8", newline="\n").write(meses_relativos_tmdl())
    open(os.path.join(d, "tables", "Comparação de Tempo.tmdl"), "w", encoding="utf-8", newline="\n").write(grupo_calculo_tmdl())

    rel = []
    for a, ca, b, cb, ambos in RELS:
        rel.append(f"relationship {tag('rel', a, ca, b)}")
        if ambos: rel.append("\tcrossFilteringBehavior: bothDirections")
        rel.append(f"\tfromColumn: {q(a)}.{q(ca)}")
        rel.append(f"\ttoColumn: {q(b)}.{q(cb)}")
        rel.append("")
    open(os.path.join(d, "relationships.tmdl"), "w", encoding="utf-8", newline="\n").write("\n".join(rel))

    model = ["model Model", "\tculture: pt-BR", "\tdefaultPowerBIDataSourceVersion: powerBI_V3", "\tdiscourageImplicitMeasures",
             "\tsourceQueryCulture: pt-BR", "\tdataAccessOptions", "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", "",
             "annotation __PBI_TimeIntelligenceEnabled = 0", "",
             "annotation PBI_QueryOrder = " + json.dumps(ordem, ensure_ascii=False), ""]
    model += [f"ref table {q(n)}" for n in ordem + ["_Medidas", "meses_relativos", "Comparação de Tempo"]]
    model.append("")
    open(os.path.join(d, "model.tmdl"), "w", encoding="utf-8", newline="\n").write("\n".join(model))
    open(os.path.join(d, "database.tmdl"), "w", encoding="utf-8", newline="\n").write("database\n\tcompatibilityLevel: 1567\n\n")
    json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
               "version": "4.2", "settings": {}},
              open(os.path.join(pasta, "definition.pbism"), "w"), indent=2)
    json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
               "metadata": {"type": "SemanticModel", "displayName": "Locadora Rebobina"},
               "config": {"version": "2.0", "logicalId": tag("logical", "sm")}},
              open(os.path.join(pasta, ".platform"), "w"), indent=2)
    return stats


if __name__ == "__main__":
    import sys
    t = pickle.load(open(sys.argv[1], "rb"))
    print(gerar(t, sys.argv[2]))
