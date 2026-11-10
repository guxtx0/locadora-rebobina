"""Análises avançadas em Python, gravadas como tabelas do modelo do Power BI.

1. Previsão de demanda dos lançamentos (8 primeiras semanas na locadora)
2. Otimização do número de cópias por filme e loja
3. Risco de abandono (churn) dos clientes
"""
from datetime import date, timedelta
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import mean_absolute_error, r2_score, roc_auc_score
from sklearn.inspection import permutation_importance

CORTE = date(2011, 1, 31)
SEED = 42
JANELA = 56          # 8 semanas
HORIZONTE = 90       # dias para o rótulo de churn
HORIZONTE_COPIAS = 180  # fase de lançamento (preço de lançamento) usada na otimização de cópias
REVENDA = 15.0       # valor de revenda de um DVD seminovo ao fim da fase de lançamento


def _metricas(lista, modelo, nome, valor, texto, ordem):
    lista.append(dict(modelo=modelo, metrica=nome, valor=float(valor), texto=texto, ordem=ordem))


# ---------------------------------------------------------------------------------------------- 1
def previsao_demanda(D, T, metricas):
    f = D["f"]
    fl = T["fato_locacao"]
    sc = pd.DataFrame(D["sem_copia"], columns=["data", "id_loja", "id_filme", "id_cliente"])
    lanc = f[(f.chegada >= date(2009, 1, 1))].copy()
    lanc["fim_janela"] = lanc.chegada.apply(lambda d: d + timedelta(days=JANELA - 1))
    ch = lanc.set_index("id_filme").chegada
    loc = fl[fl.id_filme.isin(lanc.id_filme)][["id_filme", "data_locacao"]].rename(columns={"data_locacao": "data"})
    ev = pd.concat([loc, sc[["id_filme", "data"]]])
    ev = ev[ev.id_filme.isin(ch.index)]
    ev["dias"] = [(d - ch[i]).days for i, d in zip(ev.id_filme, ev.data)]
    dem = ev[(ev.dias >= 0) & (ev.dias < JANELA)].groupby("id_filme").size()
    lanc["demanda_8sem"] = lanc.id_filme.map(dem).fillna(0)
    lanc["completo"] = lanc.fim_janela <= CORTE

    # variáveis explicativas
    X = pd.DataFrame(index=lanc.index)
    X["log_bilheteria"] = np.log1p(lanc.revenue)
    X["sem_bilheteria"] = (lanc.revenue <= 0).astype(int)
    X["log_orcamento"] = np.log1p(lanc.budget)
    X["nota"] = lanc.vote_average
    X["log_votos"] = np.log1p(lanc.vote_count)
    X["log_popularidade"] = np.log1p(lanc.popularity)
    X["duracao"] = lanc.duracao_min
    m = lanc.chegada.apply(lambda d: d.month)
    X["mes_sen"], X["mes_cos"] = np.sin(2 * np.pi * m / 12), np.cos(2 * np.pi * m / 12)
    X["ferias"] = m.isin([1, 7, 12]).astype(int)
    X["dias_cinema_ate_locadora"] = [(c - r.date()).days for c, r in zip(lanc.chegada, lanc.rd)]
    for g in ["Ação", "Animação", "Comédia", "Drama", "Terror", "Aventura", "Família", "Suspense", "Romance"]:
        X["gen_" + g] = lanc.gen_lista.apply(lambda l: int(g in l))
    X["ingles"] = (lanc.original_language == "en").astype(int)
    y = np.log1p(lanc.demanda_8sem)

    comp = lanc.completo.values
    treino = comp & (lanc.chegada < date(2010, 5, 1)).values
    teste = comp & (lanc.chegada >= date(2010, 5, 1)).values

    gb = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.04, max_leaf_nodes=15, min_samples_leaf=8,
                                       l2_regularization=1.0, random_state=SEED)
    base = make_pipeline(StandardScaler(), Ridge(alpha=3.0))
    gb.fit(X[treino], y[treino]); base.fit(X[treino], y[treino])
    real = lanc.demanda_8sem.values[teste]
    p_gb = np.expm1(gb.predict(X[teste])).clip(0)
    p_base = np.expm1(base.predict(X[teste])).clip(0)
    mae_gb, mae_base = mean_absolute_error(real, p_gb), mean_absolute_error(real, p_base)
    wape = np.abs(real - p_gb).sum() / real.sum()
    r2 = r2_score(real, p_gb)
    _metricas(metricas, "Previsão de demanda", "Erro médio absoluto (locações)", mae_gb, f"{mae_gb:.1f}".replace(".", ","), 1)
    _metricas(metricas, "Previsão de demanda", "Erro médio do modelo simples (regressão linear)", mae_base, f"{mae_base:.1f}".replace(".", ","), 2)
    _metricas(metricas, "Previsão de demanda", "Erro percentual ponderado (WAPE)", wape, f"{wape*100:.1f}%".replace(".", ","), 3)
    _metricas(metricas, "Previsão de demanda", "R² no teste", r2, f"{r2:.2f}".replace(".", ","), 4)
    _metricas(metricas, "Previsão de demanda", "Filmes no treino / teste", treino.sum(), f"{treino.sum()} / {teste.sum()}", 5)

    # modelo final com todos os filmes completos, aplicado a todos
    gb.fit(X[comp], y[comp])
    lanc["demanda_prevista_8sem"] = np.expm1(gb.predict(X)).clip(0).round(1)
    # previsões de teste vêm do modelo treinado só com o passado (sem vazamento)
    lanc.loc[teste, "demanda_prevista_8sem"] = p_gb.round(1)
    lanc["conjunto"] = np.where(treino, "Treino", np.where(teste, "Teste", "Previsão (lançamento recente)"))
    imp = permutation_importance(gb, X[comp], y[comp], n_repeats=5, random_state=SEED)
    top = pd.Series(imp.importances_mean, index=X.columns).sort_values(ascending=False).head(3)
    out = pd.DataFrame({
        "id_filme": lanc.id_filme, "data_chegada": lanc.chegada, "conjunto": lanc.conjunto,
        "demanda_real_8sem": np.where(comp, lanc.demanda_8sem, np.nan),
        "demanda_prevista_8sem": lanc.demanda_prevista_8sem,
    })
    out["erro_absoluto"] = (out.demanda_real_8sem - out.demanda_prevista_8sem).abs().round(1)
    return out, lanc, top


# ---------------------------------------------------------------------------------------------- 2
def otimizacao_copias(D, T, lanc, prev, metricas):
    fl = T["fato_locacao"]
    cop = D["copias"]
    sc = pd.DataFrame(D["sem_copia"], columns=["data", "id_loja", "id_filme", "id_cliente"])
    alvo = lanc[lanc.chegada <= CORTE - timedelta(days=HORIZONTE_COPIAS - 1)]
    ch = alvo.set_index("id_filme").chegada
    ev = pd.concat([fl[["id_filme", "id_loja", "data_locacao"]].rename(columns={"data_locacao": "data"}),
                    sc[["id_filme", "id_loja", "data"]]])
    ev = ev[ev.id_filme.isin(ch.index)].copy()
    ev["dia"] = [(d - ch[i]).days for i, d in zip(ev.id_filme, ev.data)]
    ev = ev[(ev.dia >= 0) & (ev.dia < HORIZONTE_COPIAS)]
    diaria = ev.groupby(["id_filme", "id_loja", "dia"]).size()
    preco = fl[fl.id_filme.isin(ch.index)].groupby("id_filme").valor_locacao.mean()
    custo_copia = cop[cop.midia == "DVD"].groupby("id_filme").custo_aquisicao.mean()
    custo_padrao = cop[(cop.midia == "DVD") & cop.id_filme.isin(ch.index)].custo_aquisicao.mean()
    n_atual = cop.groupby(["id_filme", "id_loja"]).size()

    chaves = set(diaria.index.droplevel(2))
    linhas = []
    for (fid, lj), n0 in n_atual.items():
        if fid not in ch.index:
            continue
        d = np.zeros(HORIZONTE_COPIAS)
        if (fid, lj) in chaves:
            s = diaria.loc[(fid, lj)]
            d[s.index.values] = s.values
        p = preco.get(fid, 5.0)
        c = custo_copia.get(fid, custo_padrao) - REVENDA
        # cada cópia de lançamento atende no máximo 1 cliente por dia (prazo de 1 dia)
        lucro = {n: np.minimum(d, n).sum() * p - n * c for n in range(1, 9)}
        n_ot = max(lucro, key=lucro.get)
        atend0 = np.minimum(d, n0).sum()
        linhas.append(dict(id_filme=fid, id_loja=lj, copias_atuais=int(n0), copias_ideais=int(n_ot),
                           demanda_180d=float(d.sum()), locacoes_atendiveis_atual=float(atend0),
                           receita_perdida_atual=round((d.sum() - atend0) * p, 2),
                           ganho_liquido=round(lucro[n_ot] - lucro.get(n0, np.minimum(d, n0).sum() * p - n0 * c), 2),
                           custo_liquido_copia=round(c, 2)))
    otm = pd.DataFrame(linhas)
    otm["ajuste"] = np.where(otm.copias_ideais > otm.copias_atuais, "Comprar mais cópias",
                             np.where(otm.copias_ideais < otm.copias_atuais, "Cópias em excesso", "Quantidade certa"))

    # regra para lançamentos futuros: cópias ideais em função da demanda prevista por loja
    otm = otm.merge(prev[["id_filme", "demanda_prevista_8sem"]], on="id_filme", how="left")
    pares = otm.assign(prev_loja=otm.demanda_prevista_8sem / 3)
    faixas = [0, 5, 10, 20, 35, 55, 80, np.inf]
    pares["faixa"] = pd.cut(pares.prev_loja, faixas, right=False)
    regra = pares.groupby("faixa", observed=True).copias_ideais.median().round().astype(int)
    futuro = prev[prev.conjunto == "Previsão (lançamento recente)"].copy()
    futuro["copias_recomendadas_por_loja"] = pd.cut(futuro.demanda_prevista_8sem / 3, faixas, right=False).map(regra).astype(float)

    tot_ganho = otm.ganho_liquido.sum()
    perdida = otm.receita_perdida_atual.sum()
    _metricas(metricas, "Otimização de cópias", "Ganho líquido potencial (R$)", tot_ganho, f"R$ {tot_ganho:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), 1)
    _metricas(metricas, "Otimização de cópias", "Receita perdida por falta de cópia (R$)", perdida, f"R$ {perdida:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), 2)
    for k, nome in [("Comprar mais cópias", "Pares filme × loja que pedem mais cópias"), ("Cópias em excesso", "Pares filme × loja com cópias em excesso")]:
        v = int((otm.ajuste == k).sum())
        _metricas(metricas, "Otimização de cópias", nome, v, str(v), 3 if "mais" in nome else 4)
    return otm.drop(columns=["demanda_prevista_8sem"]), futuro[["id_filme", "copias_recomendadas_por_loja"]]


# ---------------------------------------------------------------------------------------------- 3
NOMES_FATORES = {
    "recencia": "Dias desde a última locação", "freq_30": "Locações nos últimos 30 dias",
    "freq_90": "Locações nos últimos 90 dias", "freq_180": "Locações nos últimos 180 dias",
    "total": "Locações desde o início", "valor_90": "Gasto nos últimos 90 dias",
    "ticket": "Ticket médio", "pct_atraso": "% de devoluções com atraso", "multas": "Multas pagas",
    "pct_promo": "% de locações com promoção", "fidelidade": "Tem cartão fidelidade", "idade": "Idade",
    "tempo_casa": "Tempo de cadastro", "tendencia": "Tendência (90 dias vs 90 anteriores)",
    "pct_lanc": "% de lançamentos alugados", "loja": "Loja de cadastro",
}


def _features(fl, cli, s):
    h = fl[fl.data_locacao <= s]
    g = h.groupby("id_cliente")
    ult = g.data_locacao.max()
    base = pd.DataFrame(index=ult.index)
    base["recencia"] = [(s - d).days for d in ult]
    for k in (30, 90, 180):
        base[f"freq_{k}"] = h[h.data_locacao > s - timedelta(days=k)].groupby("id_cliente").size().reindex(base.index).fillna(0)
    ant = h[(h.data_locacao > s - timedelta(days=180)) & (h.data_locacao <= s - timedelta(days=90))].groupby("id_cliente").size()
    base["tendencia"] = base.freq_90 - ant.reindex(base.index).fillna(0)
    base["total"] = g.size()
    base["valor_90"] = h[h.data_locacao > s - timedelta(days=90)].groupby("id_cliente").valor_locacao.sum().reindex(base.index).fillna(0)
    base["ticket"] = g.valor_locacao.mean()
    dv = h[h.data_devolucao.notna()]
    dv = dv[[x <= s for x in dv.data_devolucao]]
    base["pct_atraso"] = dv.groupby("id_cliente").apply(lambda z: (z.status_devolucao == "Com atraso").mean()).reindex(base.index).fillna(0)
    base["multas"] = dv.groupby("id_cliente").valor_multa.sum().reindex(base.index).fillna(0)
    base["pct_promo"] = g.apply(lambda z: (z.promocao != "Sem promoção").mean())
    base["pct_lanc"] = g.apply(lambda z: (z.tipo_preco == "Lançamento").mean())
    c = cli.set_index("id_cliente").reindex(base.index)
    base["fidelidade"] = c.cartao_fidelidade
    base["idade"] = c.idade
    base["tempo_casa"] = [(s - d).days for d in c.data_cadastro]
    base["loja"] = c.id_loja_cadastro
    return base


def churn(D, T, metricas):
    fl = T["fato_locacao"]
    cli = D["cli"].copy()
    cli["idade"] = cli.data_nascimento.apply(lambda n: 2011 - n.year)
    fims = pd.date_range("2009-03-31", "2011-01-31", freq="ME").date
    linhas = []
    for s in fims:
        b = _features(fl, cli, s)
        b = b[b.recencia <= 120]                       # só clientes ainda ativos na data
        if s + timedelta(days=HORIZONTE) <= CORTE:
            fut = fl[(fl.data_locacao > s) & (fl.data_locacao <= s + timedelta(days=HORIZONTE))].id_cliente.unique()
            b["churn"] = (~b.index.isin(fut)).astype(int)
        else:
            b["churn"] = np.nan
        b["snapshot"] = s
        linhas.append(b.reset_index())
    df = pd.concat(linhas, ignore_index=True)
    feats = [c for c in df.columns if c not in ("id_cliente", "churn", "snapshot")]
    rot = df[df.churn.notna()]
    tr = rot[rot.snapshot <= date(2010, 4, 30)]
    te = rot[rot.snapshot > date(2010, 4, 30)]
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=40,
                                         categorical_features=[feats.index("loja")], random_state=SEED)
    clf.fit(tr[feats], tr.churn)
    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
    lr.fit(tr[feats], tr.churn)
    p = clf.predict_proba(te[feats])[:, 1]
    auc, auc_lr = roc_auc_score(te.churn, p), roc_auc_score(te.churn, lr.predict_proba(te[feats])[:, 1])
    top = np.argsort(-p)[: int(len(p) * 0.2)]
    prec20 = te.churn.values[top].mean()
    taxa = te.churn.mean()
    rec20 = te.churn.values[top].sum() / te.churn.sum()
    _metricas(metricas, "Risco de abandono", "AUC no teste", auc, f"{auc:.3f}".replace(".", ","), 1)
    _metricas(metricas, "Risco de abandono", "AUC do modelo simples (regressão logística)", auc_lr, f"{auc_lr:.3f}".replace(".", ","), 2)
    _metricas(metricas, "Risco de abandono", "Taxa real de abandono em 90 dias", taxa, f"{taxa*100:.1f}%".replace(".", ","), 3)
    _metricas(metricas, "Risco de abandono", "Acerto nos 20% de maior risco", prec20, f"{prec20*100:.1f}%".replace(".", ","), 4)
    _metricas(metricas, "Risco de abandono", "Abandonos capturados pelos 20% de maior risco", rec20, f"{rec20*100:.1f}%".replace(".", ","), 5)

    imp = permutation_importance(clf, te[feats], te.churn, n_repeats=5, random_state=SEED, scoring="roc_auc")
    importancia = pd.DataFrame({"fator": [NOMES_FATORES[c] for c in feats], "importancia": imp.importances_mean})
    importancia = importancia.sort_values("importancia", ascending=False).reset_index(drop=True)
    importancia["importancia"] = importancia.importancia.clip(lower=0).round(4)

    clf.fit(rot[feats], rot.churn)          # modelo final com todo o histórico rotulado
    atual = df[df.snapshot == fims[-1]].set_index("id_cliente")
    prob = pd.Series(clf.predict_proba(atual[feats])[:, 1], index=atual.index)
    risco = pd.DataFrame({"id_cliente": cli.id_cliente})
    risco["prob_abandono"] = risco.id_cliente.map(prob).round(4)
    risco["faixa_risco"] = np.select(
        [risco.prob_abandono.isna(), risco.prob_abandono >= 0.5, risco.prob_abandono >= 0.25],
        ["Já inativo (+120 dias)", "1. Alto", "2. Médio"], default="3. Baixo")
    gasto180 = fl[fl.data_locacao > CORTE - timedelta(days=180)].groupby("id_cliente").valor_locacao.sum()
    risco["receita_em_risco_180d"] = (risco.id_cliente.map(gasto180).fillna(0) * risco.prob_abandono.fillna(0)).round(2)
    return risco, importancia


def rodar(D, T):
    metricas = []
    prev, lanc, top_prev = previsao_demanda(D, T, metricas)
    otm, recom = otimizacao_copias(D, T, lanc, prev, metricas)
    prev = prev.merge(recom, on="id_filme", how="left")
    risco, imp = churn(D, T, metricas)
    met = pd.DataFrame(metricas)
    return dict(previsao_lancamentos=prev, otimizacao_copias=otm, importancia_churn=imp, metricas_modelos=met), risco, top_prev
