"""Tema comemorativo de cada filme (pelas palavras-chave do TMDB), na mesma lógica da simulação."""

TEMAS = [
    ("Natal", {"christmas", "santa claus", "christmas party", "christmas tree", "christmas eve"}),
    ("Réveillon", {"new year's eve"}),
    ("Dia das Mães", {"mother", "mother daughter relationship", "mother son relationship", "single mother", "motherhood"}),
    ("Dia dos Pais", {"father", "father son relationship", "father daughter relationship", "single father", "fatherhood"}),
    ("Semana Santa e Páscoa", {"jesus christ", "bible", "christianity", "religion", "crucifixion"}),
    ("Halloween", {"halloween", "zombie", "vampire", "witch", "haunted house", "ghost"}),
    ("Futebol / Copa do Mundo", {"soccer", "world cup", "football (soccer)"}),
    ("Dia dos Namorados", {"valentine's day", "romantic comedy", "wedding"}),
    ("Carnaval / Brasil", {"carnival", "rio de janeiro", "brazil", "samba"}),
]


def temas(f):
    out = []
    for kw, tit, lang in zip(f.kw, f.titulo_en.str.lower(), f.original_language):
        t = None
        if any(x in tit for x in ("christmas", "santa", "grinch")):
            t = "Natal"
        else:
            for nome, ks in TEMAS:
                if kw & ks:
                    t = nome
                    break
        if t is None and lang == "pt":
            t = "Carnaval / Brasil"
        out.append(t)
    return out
