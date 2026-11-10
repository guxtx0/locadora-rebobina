"""Calendário brasileiro (jan/2009 a jan/2011): feriados nacionais, vésperas, férias escolares
(rede estadual de MG, aproximado) e datas comemorativas usadas no varejo."""
from datetime import date, timedelta

FERIADOS = {
    date(2009, 1, 1): "Confraternização Universal",
    date(2009, 2, 23): "Carnaval", date(2009, 2, 24): "Carnaval",
    date(2009, 4, 10): "Sexta-feira Santa", date(2009, 4, 21): "Tiradentes",
    date(2009, 5, 1): "Dia do Trabalho", date(2009, 6, 11): "Corpus Christi",
    date(2009, 9, 7): "Independência do Brasil", date(2009, 10, 12): "Nossa Senhora Aparecida",
    date(2009, 11, 2): "Finados", date(2009, 11, 15): "Proclamação da República",
    date(2009, 12, 25): "Natal",
    date(2010, 1, 1): "Confraternização Universal",
    date(2010, 2, 15): "Carnaval", date(2010, 2, 16): "Carnaval",
    date(2010, 4, 2): "Sexta-feira Santa", date(2010, 4, 21): "Tiradentes",
    date(2010, 5, 1): "Dia do Trabalho", date(2010, 6, 3): "Corpus Christi",
    date(2010, 9, 7): "Independência do Brasil", date(2010, 10, 12): "Nossa Senhora Aparecida",
    date(2010, 11, 2): "Finados", date(2010, 11, 15): "Proclamação da República",
    date(2010, 12, 25): "Natal",
    date(2011, 1, 1): "Confraternização Universal",
}
PASCOA = {2009: date(2009, 4, 12), 2010: date(2010, 4, 4)}
CARNAVAL_TERCA = {2009: date(2009, 2, 24), 2010: date(2010, 2, 16)}
DIA_MAES = {2009: date(2009, 5, 10), 2010: date(2010, 5, 9)}
DIA_PAIS = {2009: date(2009, 8, 9), 2010: date(2010, 8, 8)}
JOGOS_BRASIL_COPA = {date(2010, 6, 15), date(2010, 6, 20), date(2010, 6, 25), date(2010, 6, 28), date(2010, 7, 2)}

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
MESES_LONGO = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
               "setembro", "outubro", "novembro", "dezembro"]
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def vespera(d):
    return (d + timedelta(days=1)) in FERIADOS and d not in FERIADOS


def ferias(d):
    return (d.month == 1) or (d.month == 2 and d.day <= 6) or d.month == 7 or (d.month == 12 and d.day >= 15)


def eventos(d):
    e = set()
    y = d.year
    if ferias(d): e.add("ferias")
    if d.month == 10 and 5 <= d.day <= 12: e.add("semana_criancas")
    if d.month == 12 and d.day <= 25: e.add("natal")
    if (d.month == 12 and d.day >= 26) or (d.month == 1 and d.day == 1): e.add("ano_novo")
    if d.month == 6 and d.day <= 12: e.add("namorados")
    if y in DIA_MAES and DIA_MAES[y] - timedelta(days=7) <= d <= DIA_MAES[y]: e.add("maes")
    if y in DIA_PAIS and DIA_PAIS[y] - timedelta(days=7) <= d <= DIA_PAIS[y]: e.add("pais")
    if y in PASCOA and PASCOA[y] - timedelta(days=7) <= d <= PASCOA[y]: e.add("pascoa")
    if date(2010, 6, 11) <= d <= date(2010, 7, 11): e.add("copa")
    if y in CARNAVAL_TERCA and CARNAVAL_TERCA[y] - timedelta(days=4) <= d <= CARNAVAL_TERCA[y] + timedelta(days=1):
        e.add("carnaval")
    if d.month == 10 and d.day >= 24: e.add("halloween")
    return e


def fator_volume(d):
    """Multiplicador do movimento do dia em relação a um dia comum."""
    v = 1.0
    nome = FERIADOS.get(d)
    if nome == "Natal": v *= 0.50
    elif nome == "Confraternização Universal": v *= 0.45
    elif nome == "Carnaval": v *= 1.30
    elif nome: v *= 1.15
    if vespera(d): v *= 1.45                       # véspera de feriado: o cliente se abastece
    if (d.month, d.day) == (12, 24): v *= 0.80
    if (d.month, d.day) == (12, 31): v *= 0.70
    for y, t in CARNAVAL_TERCA.items():
        if d == t - timedelta(days=4): v *= 1.30    # sexta pré-carnaval
    if d in JOGOS_BRASIL_COPA: v *= 0.55
    return v


DATA_COMEMORATIVA = [  # prioridade quando há sobreposição
    ("copa", "Copa do Mundo 2010"), ("carnaval", "Carnaval"), ("pascoa", "Semana Santa e Páscoa"),
    ("maes", "Dia das Mães"), ("pais", "Dia dos Pais"), ("namorados", "Dia dos Namorados"),
    ("semana_criancas", "Semana das Crianças"), ("halloween", "Halloween"), ("natal", "Natal"),
    ("ano_novo", "Réveillon"),
]


def linha_calendario(d):
    ev = eventos(d)
    com = next((n for k, n in DATA_COMEMORATIVA if k in ev), None)
    if d in FERIADOS: tipo = "Feriado"
    elif vespera(d): tipo = "Véspera de feriado"
    elif d.weekday() >= 5: tipo = "Fim de semana"
    else: tipo = "Dia útil"
    tipo_ord = {"Dia útil": 1, "Fim de semana": 2, "Véspera de feriado": 3, "Feriado": 4}[tipo]
    return dict(
        Data=d, Ano=d.year, MesNum=d.month, Mes=MESES[d.month - 1],
        AnoMesNum=d.year * 100 + d.month, MesAno=f"{MESES[d.month - 1]}/{str(d.year)[2:]}",
        Trimestre=f"{(d.month - 1) // 3 + 1}º tri/{d.year}", TrimestreNum=d.year * 10 + (d.month - 1) // 3 + 1,
        DiaSemana=DIAS[d.weekday()], DiaSemanaNum=d.weekday() + 1,
        Feriado=FERIADOS.get(d), TipoDia=tipo, TipoDiaOrdem=tipo_ord,
        PeriodoEscolar="Férias escolares" if ferias(d) else "Período letivo",
        DataComemorativa=com, JogoBrasil="Sim" if d in JOGOS_BRASIL_COPA else "Não",
    )
