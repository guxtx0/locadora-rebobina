"""Gera o relatório (PBIR) do projeto Power BI da Locadora Rebobina."""
import json, os, shutil, sys

RAIZ = sys.argv[1]            # pasta do projeto
IMG = sys.argv[2]             # pasta com os fundos
BASE_THEME = sys.argv[3]      # CY24SU10.json
REP = os.path.join(RAIZ, "Locadora_Rebobina.Report")
SCH = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
V_SCHEMA = f"{SCH}/visualContainer/2.7.0/schema.json"
M = "_Medidas"


def lit(v): return {"expr": {"Literal": {"Value": v}}}
def s(v): return lit("'" + str(v).replace("'", "''") + "'")
def b(v): return lit("true" if v else "false")
def d(v): return lit(f"{v}D")
def cor(hexa): return {"solid": {"color": s(hexa)}}


def medida(nome, rotulo=None):
    p = {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": M}}, "Property": nome}},
         "queryRef": f"{M}.{nome}", "nativeQueryRef": nome}
    if rotulo: p["displayName"] = rotulo
    return p


def coluna(tab, col, rotulo=None, ativa=True):
    p = {"field": {"Column": {"Expression": {"SourceRef": {"Entity": tab}}, "Property": col}},
         "queryRef": f"{tab}.{col}", "nativeQueryRef": col}
    if ativa: p["active"] = True
    if rotulo: p["displayName"] = rotulo
    return p


def campo(p): return p["field"]


def titulo(texto):
    return {"title": [{"properties": {"show": b(True), "text": s(texto), "fontSize": d(11)}}]}


def sem_titulo():
    return {"title": [{"properties": {"show": b(False)}}]}


def visual(nome, x, y, w, h, z, tipo, query=None, objects=None, vco=None, sort=None, extra=None):
    v = {"visualType": tipo}
    if query is not None:
        v["query"] = {"queryState": query}
        if sort:
            v["query"]["sortDefinition"] = {"sort": [{"field": campo(sort[0]), "direction": sort[1]}], "isDefaultSort": True}
    if objects: v["objects"] = objects
    if vco: v["visualContainerObjects"] = vco
    if extra: v.update(extra)
    v["drillFilterOtherVisuals"] = True
    return {"$schema": V_SCHEMA, "name": nome,
            "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z}, "visual": v}


KPI_X = [24, 273, 522, 771, 1020]


def kpis(prefixo, medidas):
    out = []
    for i, (m, rot) in enumerate(medidas):
        out.append(visual(f"{prefixo}_kpi{i + 1}", KPI_X[i] + 12, 140, 220, 92, 3000 + i, "card",
                          {"Values": {"projections": [medida(m, rot)]}},
                          objects={"labels": [{"properties": {"fontSize": d(22), "color": cor("#F3F4F6")}}],
                                   "categoryLabels": [{"properties": {"show": b(True), "fontSize": d(10),
                                                                      "color": cor("#AEB4C0")}}]},
                          vco=sem_titulo()))
    return out


def caixa(rotulo):
    """Moldura do próprio visual: fundo, borda arredondada e rótulo dourado.
    O filtro deixa de depender de uma caixa desenhada na imagem de fundo,
    então rótulo, campo e moldura ficam sempre alinhados entre si."""
    return {"title": [{"properties": {"show": b(True), "text": s(rotulo), "fontColor": cor("#F5B841"),
                                      "fontSize": d(8), "bold": b(True), "alignment": s("left")}}],
            "background": [{"properties": {"show": b(True), "color": cor("#171B24"), "transparency": d(0)}}],
            "border": [{"properties": {"show": b(True), "color": cor("#262C38"), "radius": d(8), "width": d(1)}}],
            "padding": [{"properties": {"top": d(4), "bottom": d(6), "left": d(10), "right": d(10)}}],
            "dropShadow": [{"properties": {"show": b(False)}}]}


def filtro(nome, x, y, w, h, z, t, c, rotulo, extra=None, unico=False):
    obj = {"data": [{"properties": {"mode": s("Dropdown")}}],
           "header": [{"properties": {"show": b(False)}}],
           "general": [{"properties": {"outlineColor": cor("#2E3442"), "outlineWeight": d(1)}}],
           "items": [{"properties": {"fontColor": cor("#F3F4F6"), "background": cor("#1C212C"), "textSize": d(10)}}]}
    if unico: obj["selection"] = [{"properties": {"singleSelect": b(True)}}]
    return visual(nome, x, y, w, h, z, "slicer", {"Values": {"projections": [coluna(t, c, rotulo.title())]}},
                  objects=obj, vco=caixa(rotulo), extra=extra)


# linha de filtros: quatro caixas de mesma altura, mesmo y e mesmo espaçamento (13 px) das linhas de KPI
FILTRO_Y, FILTRO_H = 74, 52


def comuns(prefixo):
    vs = []
    slicers = [("dim_loja", "loja", "LOJA", 24), ("dim_filme", "categoria", "CATEGORIA", 273),
               ("dim_calendario", "Mês/Ano", "MÊS", 522)]
    for i, (t, c, rot, x) in enumerate(slicers):
        vs.append(filtro(f"{prefixo}_filtro{i + 1}", x, FILTRO_Y, 236, FILTRO_H, 2000 + i, t, c, rot,
                         extra={"syncGroup": {"groupName": f"sync_{c}", "fieldChanges": True, "filterChanges": True}}))
    vs.append(visual(f"{prefixo}_periodo", 771, FILTRO_Y, 485, FILTRO_H, 2010, "card",
                     {"Values": {"projections": [medida("Período Analisado")]}},
                     objects={"labels": [{"properties": {"fontSize": d(12), "color": cor("#F3F4F6")}}],
                              "categoryLabels": [{"properties": {"show": b(False)}}]},
                     vco=caixa("PERÍODO ANALISADO")))
    return vs


def rotulos(show=True):
    return {"labels": [{"properties": {"show": b(show), "fontSize": d(9), "color": cor("#AEB4C0")}}]}


def barras(nome, pos, t, c, m, tit, ordem_desc=True, tipo="clusteredBarChart", z=4000, ordem_campo=None, labels=True):
    cat = coluna(t, c)
    med = medida(m)
    sort = (med, "Descending") if ordem_desc else (ordem_campo or cat, "Ascending")
    return visual(nome, *pos, z, tipo, {"Category": {"projections": [cat]}, "Y": {"projections": [med]}},
                  objects=rotulos(labels), vco=titulo(tit), sort=sort)


def rosca(nome, pos, t, c, m, tit, cores=None, z=4000):
    obj = {"labels": [{"properties": {"show": b(True), "fontSize": d(9), "color": cor("#AEB4C0"),
                                      "labelStyle": s("Category, percent of total")}}],
           "legend": [{"properties": {"show": b(True), "position": s("Right"), "labelColor": cor("#AEB4C0")}}]}
    if cores:
        obj["dataPoint"] = [{"properties": {"fill": cor(h)},
                             "selector": {"data": [{"scopeId": {"Comparison": {
                                 "ComparisonKind": 0,
                                 "Left": {"Column": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}},
                                 "Right": {"Literal": {"Value": "'" + v + "'"}}}}}]}} for v, h in cores]
    return visual(nome, *pos, z, "donutChart",
                  {"Category": {"projections": [coluna(t, c)]}, "Y": {"projections": [medida(m)]}},
                  objects=obj, vco=titulo(tit), sort=(medida(m), "Descending"))


def tabela(nome, pos, cols, meds, tit, ordem, z=4000):
    proj = [coluna(t, c, rot, ativa=False) for t, c, rot in cols] + [medida(m, rot) for m, rot in meds]
    return visual(nome, *pos, z, "tableEx", {"Values": {"projections": proj}}, vco=titulo(tit),
                  sort=(medida(ordem), "Descending"))


def linha(nome, pos, t, c, meds, tit, ordem_campo=None, z=4000):
    cat = coluna(t, c)
    return visual(nome, *pos, z, "lineChart",
                  {"Category": {"projections": [cat]}, "Y": {"projections": [medida(m) for m in meds]}},
                  objects={"legend": [{"properties": {"show": b(len(meds) > 1), "position": s("Top"),
                                                      "labelColor": cor("#AEB4C0")}}]},
                  vco=titulo(tit), sort=(ordem_campo or cat, "Ascending"))


def matriz_coorte(nome, pos, z=4000):
    med = medida("Retenção %")
    grad = {"solid": {"color": {"expr": {"FillRule": {
        "Input": med["field"],
        "FillRule": {"linearGradient2": {
            "min": {"color": {"Literal": {"Value": "'#1C212C'"}}, "value": {"Literal": {"Value": "0D"}}},
            "max": {"color": {"Literal": {"Value": "'#E5484D'"}}, "value": {"Literal": {"Value": "1D"}}},
            "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'noColor'"}}}}}}}}}}
    return visual(nome, *pos, z, "pivotTable",
                  {"Rows": {"projections": [coluna("dim_cliente", "coorte", "Coorte (1ª locação)")]},
                   "Columns": {"projections": [coluna("meses_relativos", "Mês", "Meses depois")]},
                   "Values": {"projections": [med]}},
                  objects={"values": [{"properties": {"backColor": grad},
                                       "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                                                    "metadata": f"{M}.Retenção %"}}],
                           "subTotals": [{"properties": {"rowSubtotals": b(False), "columnSubtotals": b(False)}}]},
                  vco=titulo("Coorte de retenção: % dos clientes que voltaram a alugar k meses após a 1ª locação"))


def dispersao(nome, pos, z=4000):
    return visual(nome, *pos, z, "scatterChart",
                  {"Category": {"projections": [coluna("dim_filme", "filme")]},
                   "X": {"projections": [medida("Demanda Prevista (teste)", "Demanda prevista")]},
                   "Y": {"projections": [medida("Demanda Real (teste)", "Demanda real")]}},
                  objects={"dataPoint": [{"properties": {"fill": cor("#F5B841")}}]},
                  vco=titulo("Previsto × real: lançamentos de teste (mai a dez/2010), 8 primeiras semanas"))


# ------------------------------------------------------------------ páginas
PAGINAS = []

p = "visao_geral"
PAGINAS.append((p, "Visão Geral", "fundo_1_visao_geral.png",
    comuns(p) + kpis(p, [("Faturamento", None), ("Locações", None), ("Clientes Ativos", None),
                         ("Ticket Médio por Locação", "Ticket médio por locação"), ("% Receita de Multas", "% da receita vinda de multas")]) + [
    visual(f"{p}_mensal", 30, 256, 748, 212, 4000, "lineClusteredColumnComboChart",
           {"Category": {"projections": [coluna("dim_calendario", "Mês/Ano")]},
            "Y": {"projections": [medida("Faturamento")]},
            "Y2": {"projections": [medida("Locações")]}},
           objects={"legend": [{"properties": {"show": b(True), "position": s("Top"), "labelColor": cor("#AEB4C0")}}]},
           vco=titulo("Faturamento (colunas) e locações (linha) por mês"),
           sort=(coluna("dim_calendario", "Mês/Ano"), "Ascending")),
    rosca(f"{p}_lojas", (806, 256, 444, 212), "dim_loja", "loja", "Faturamento", "Faturamento por loja"),
    filtro(f"{p}_comparacao", 896, 8, 360, 50, 2100, "Comparação de Tempo", "Comparação", "COMPARAÇÃO",
           unico=True),
    barras(f"{p}_categorias", (30, 492, 598, 200), "dim_filme", "categoria", "Faturamento", "Faturamento por categoria"),
    barras(f"{p}_bairros", (656, 492, 594, 200), "dim_cliente", "bairro_cidade", "Faturamento (Top 10 bairros)",
           "Top 10 bairros por faturamento"),
]))

p = "filmes_atores"
PAGINAS.append((p, "Filmes e Atores", "fundo_2_filmes_atores.png",
    comuns(p) + kpis(p, [("Filmes no Catálogo", "Filmes no catálogo"), ("Filmes Locados", "Filmes alugados ao menos 1 vez"),
                         ("% Locações de Lançamentos", "% das locações em lançamentos"),
                         ("Preço Médio de Locação", "Preço médio da locação"), ("Locações por Título", "Locações por título")]) + [
    tabela(f"{p}_top_filmes", (30, 256, 588, 436),
           [("dim_filme", "filme", "Filme"), ("dim_filme", "categoria", "Categoria"), ("dim_filme", "ano_lancamento", "Ano")],
           [("Locações (Top 15 filmes)", "Locações"), ("Faturamento (Top 15 filmes)", "Faturamento")],
           "Top 15 filmes por faturamento", "Faturamento (Top 15 filmes)"),
    barras(f"{p}_atores", (646, 256, 604, 204), "dim_ator", "ator", "Locações (Top 10 atores)", "Top 10 atores por locações"),
    barras(f"{p}_perfil", (646, 486, 288, 206), "dim_filme", "perfil_titulo", "Locações", "Locações por perfil do título",
           tipo="clusteredColumnChart"),
    barras(f"{p}_bilheteria", (962, 486, 288, 206), "dim_filme", "faixa_bilheteria", "Locações por Título",
           "Locações por título × bilheteria (R$)", ordem_desc=False, tipo="clusteredColumnChart"),
]))

p = "clientes_operacao"
PAGINAS.append((p, "Clientes e Operação", "fundo_3_clientes_operacao.png",
    comuns(p) + kpis(p, [("Clientes Ativos", None), ("Locações por Cliente", "Locações por cliente"),
                         ("% Devoluções com Atraso", "% devoluções com atraso"), ("Receita de Multas", "Receita de multas"),
                         ("Multas Pendentes", "Multas não pagas")]) + [
    barras(f"{p}_semana", (30, 256, 598, 212), "dim_calendario", "Dia da Semana", "Locações", "Locações por dia da semana",
           ordem_desc=False, tipo="clusteredColumnChart"),
    rosca(f"{p}_status", (656, 256, 594, 212), "fato_locacao", "status_devolucao", "Locações", "Status das devoluções",
          cores=[("No prazo", "#5FBF77"), ("Com atraso", "#E5484D"), ("Em aberto", "#F5B841")]),
    tabela(f"{p}_top_clientes", (30, 492, 598, 200),
           [("dim_cliente", "cliente", "Cliente"), ("dim_cliente", "bairro_cidade", "Bairro")],
           [("Locações (Top 10 clientes)", "Locações"), ("Faturamento (Top 10 clientes)", "Faturamento")],
           "Top 10 clientes", "Faturamento (Top 10 clientes)"),
    barras(f"{p}_faixa_etaria", (656, 492, 594, 200), "dim_cliente", "faixa_etaria", "Locações", "Locações por faixa etária",
           ordem_desc=False, tipo="clusteredColumnChart"),
]))

p = "sazonalidade"
PAGINAS.append((p, "Sazonalidade e Datas", "fundo_4_sazonalidade.png",
    comuns(p) + kpis(p, [("Média Diária de Locações", "Média diária de locações"),
                         ("Média Diária em Vésperas", "Média em vésperas de feriado"),
                         ("Média Diária em Dias Úteis", "Média em dias úteis comuns"),
                         ("Efeito Véspera de Feriado %", "A mais na véspera de feriado"),
                         ("Locações de Filmes Temáticos", "Locações de filmes temáticos")]) + [
    linha(f"{p}_diario", (30, 256, 748, 212), "dim_calendario", "Data", ["Locações"], "Locações por dia"),
    barras(f"{p}_tipo_dia", (806, 256, 444, 212), "dim_calendario", "Tipo de Dia", "Média Diária de Locações",
           "Média diária de locações por tipo de dia", ordem_desc=False, tipo="clusteredColumnChart"),
    barras(f"{p}_datas", (30, 492, 598, 200), "dim_calendario", "Data Comemorativa", "Média Diária em Datas Comemorativas",
           "Média diária de locações em datas comemorativas"),
    linha(f"{p}_generos", (656, 492, 594, 200), "dim_calendario", "Mês/Ano", ["% Animação e Família", "% Terror"],
          "% das locações: Animação/Família × Terror"),
]))


p = "estoque_retencao"
PAGINAS.append((p, "Estoque e Retenção", "fundo_5_estoque_retencao.png",
    comuns(p) + kpis(p, [("Taxa de Ocupação", "Ocupação das cópias"),
                         ("Ocupação – Lançamentos do Período", "Ocupação dos lançamentos"),
                         ("Demanda Não Atendida", "Tentativas sem cópia livre"),
                         ("Retenção Média no 3º Mês", "Retenção média no 3º mês"),
                         ("Retenção Média no 12º Mês", "Retenção média no 12º mês")]) + [
    matriz_coorte(f"{p}_coorte", (30, 256, 748, 436)),
    linha(f"{p}_ocupacao_mes", (806, 256, 444, 212), "dim_calendario", "Mês/Ano",
          ["Ocupação – Lançamentos do Período", "Ocupação – Acervo", "Ocupação – Clássicos"], "Taxa de ocupação das cópias por mês"),
    barras(f"{p}_ocupacao_cat", (806, 492, 444, 200), "dim_filme", "categoria", "Taxa de Ocupação", "Taxa de ocupação por categoria"),
]))

p = "modelos"
PAGINAS.append((p, "Previsões e Recomendações", "fundo_6_modelos.png",
    comuns(p) + kpis(p, [("R² da Previsão", "R² da previsão de demanda"), ("Erro Médio da Previsão", "Erro médio (locações em 8 semanas)"),
                         ("Ganho com Cópias Ideais", "Ganho com o nº ideal de cópias"),
                         ("AUC do Modelo de Abandono", "AUC do modelo de abandono"), ("Clientes em Risco Alto", "Clientes em risco alto")]) + [
    dispersao(f"{p}_previsao", (30, 256, 598, 212)),
    barras(f"{p}_fatores", (656, 256, 594, 212), "importancia_churn", "fator", "Importância do Fator",
           "O que mais pesa no risco de abandono (importância por permutação)"),
    tabela(f"{p}_copias", (30, 492, 598, 200), [("dim_filme", "filme", "Filme")],
           [("Cópias Atuais", "Cópias hoje"), ("Cópias Ideais", "Cópias ideais"), ("Ganho com Cópias Ideais", "Ganho estimado")],
           "Cópias atuais × ideais na fase de lançamento (3 lojas)", "Ganho com Cópias Ideais"),
    barras(f"{p}_risco", (656, 492, 594, 200), "dim_cliente", "faixa_risco", "Clientes", "Clientes por faixa de risco de abandono",
           ordem_desc=False, tipo="clusteredColumnChart"),
]))


# ------------------------------------------------------------------ escrita
def wjson(caminho, obj):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)


def tema():
    t = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tema_rebobina.json"), encoding="utf-8"))
    return t


shutil.rmtree(REP, ignore_errors=True)
DEF = os.path.join(REP, "definition")
wjson(os.path.join(REP, "definition.pbir"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
    "version": "4.0", "datasetReference": {"byPath": {"path": "../Locadora_Rebobina.SemanticModel"}}})
wjson(os.path.join(REP, ".platform"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
    "metadata": {"type": "Report", "displayName": "Locadora Rebobina"},
    "config": {"version": "2.0", "logicalId": "3c9b1f6e-7d2a-4f58-9a41-2b8e5c0d7f13"}})
wjson(os.path.join(DEF, "version.json"), {"$schema": f"{SCH}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})

reg = os.path.join(REP, "StaticResources", "RegisteredResources")
os.makedirs(reg, exist_ok=True)
shared = os.path.join(REP, "StaticResources", "SharedResources", "BaseThemes")
os.makedirs(shared, exist_ok=True)
shutil.copy(BASE_THEME, os.path.join(shared, "CY24SU10.json"))
wjson(os.path.join(reg, "RebobinaDark.json"), tema())
imgs = []
for _, _, fundo, _ in PAGINAS:
    nome = fundo.replace(".png", "") + "2026111001.png"
    shutil.copy(os.path.join(IMG, fundo), os.path.join(reg, nome))
    imgs.append(nome)

wjson(os.path.join(DEF, "report.json"), {
    "$schema": f"{SCH}/report/3.0.0/schema.json",
    "themeCollection": {
        "baseTheme": {"name": "CY24SU10", "reportVersionAtImport": {"visual": "1.8.95", "report": "2.0.95", "page": "1.3.95"},
                      "type": "SharedResources"},
        "customTheme": {"name": "RebobinaDark.json", "reportVersionAtImport": {"visual": "2.1.0", "report": "2.1.0", "page": "2.0.0"},
                        "type": "RegisteredResources"}},
    "objects": {"outspacePane": [{"properties": {"expanded": b(False), "visible": b(True)}}]},
    "resourcePackages": [
        {"name": "SharedResources", "type": "SharedResources",
         "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}]},
        {"name": "RegisteredResources", "type": "RegisteredResources",
         "items": [{"name": "RebobinaDark.json", "path": "RebobinaDark.json", "type": "CustomTheme"}] +
                  [{"name": n, "path": n, "type": "Image"} for n in imgs]}],
    "settings": {"useStylableVisualContainerHeader": True, "defaultFilterActionIsDataFilter": True,
                 "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True, "useEnhancedTooltips": True},
})
wjson(os.path.join(DEF, "pages", "pages.json"), {"$schema": f"{SCH}/pagesMetadata/1.0.0/schema.json",
                                               "pageOrder": [p[0] for p in PAGINAS], "activePageName": PAGINAS[0][0]})
for (nome, titulo_pag, fundo, visuais), img in zip(PAGINAS, imgs):
    pd_ = os.path.join(DEF, "pages", nome)
    wjson(os.path.join(pd_, "page.json"), {
        "$schema": f"{SCH}/page/2.0.0/schema.json", "name": nome, "displayName": titulo_pag,
        "displayOption": "FitToPage", "height": 720, "width": 1280,
        "objects": {
            "background": [{"properties": {
                "image": {"image": {"name": s(fundo), "url": {"expr": {"ResourcePackageItem": {
                    "PackageName": "RegisteredResources", "PackageType": 1, "ItemName": img}}},
                    "scaling": s("Fit")}},
                "transparency": d(0)}}],
            "outspace": [{"properties": {"color": cor("#0E1117"), "transparency": d(0)}}]}})
    for v in visuais:
        wjson(os.path.join(pd_, "visuals", v["name"], "visual.json"), v)

wjson(os.path.join(RAIZ, "Locadora_Rebobina.pbip"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
    "version": "1.0", "artifacts": [{"report": {"path": "Locadora_Rebobina.Report"}}],
    "settings": {"enableAutoRecovery": True}})
print("páginas:", len(PAGINAS), "visuais:", sum(len(p[3]) for p in PAGINAS))
