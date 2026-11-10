"""Gera o projeto inteiro a partir da base TMDB 5000.

Uso (na raiz do repositório):
    python scripts/pipeline.py --tmdb dados/brutos

Etapas: simulação da locadora -> modelo estrela -> análises em Python -> projeto Power BI (.pbip) -> scripts SQL Server -> CSVs.
"""
import argparse, os, pickle, shutil, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)


def rodar(*args):
    print(">>", " ".join(os.path.relpath(a, RAIZ) if os.path.isabs(a) else a for a in args))
    subprocess.run([sys.executable, *args], check=True, cwd=AQUI)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tmdb", default=os.path.join(RAIZ, "dados", "brutos"),
                    help="pasta com tmdb_5000_movies.csv e tmdb_5000_credits.csv")
    a = ap.parse_args()
    build = os.path.join(RAIZ, "build")
    os.makedirs(build, exist_ok=True)

    # 1. simulação
    rodar(os.path.join(AQUI, "gerar_v2.py"), os.path.abspath(a.tmdb), build)
    # 2. modelo estrela
    import tabelas_estrela
    tabelas, D = tabelas_estrela.montar(os.path.join(build, "dados.pkl"))
    # 2b. análises em Python (previsão, otimização de cópias, risco de abandono)
    import analises_python
    novas, risco, _ = analises_python.rodar(D, tabelas)
    tabelas["dim_cliente"] = tabelas["dim_cliente"].merge(risco, on="id_cliente", how="left")
    tabelas.update(novas)
    pickle.dump(tabelas, open(os.path.join(build, "estrela.pkl"), "wb"))
    # 3. fundos das páginas
    img = os.path.join(build, "img")
    os.makedirs(img, exist_ok=True)
    rodar(os.path.join(AQUI, "fundos3.py"), img)
    # 4. projeto Power BI
    pbip = os.path.join(RAIZ, "powerbi")
    sm = os.path.join(pbip, "Locadora_Rebobina.SemanticModel")
    shutil.rmtree(sm, ignore_errors=True)
    rodar(os.path.join(AQUI, "build_modelo.py"), os.path.join(build, "estrela.pkl"), sm)
    rodar(os.path.join(AQUI, "build_relatorio.py"), pbip, img, os.path.join(AQUI, "recursos", "CY24SU10.json"))
    # 5. scripts SQL Server
    sql = os.path.join(RAIZ, "sql")
    os.makedirs(sql, exist_ok=True)
    rodar(os.path.join(AQUI, "gerar_sql.py"), os.path.join(build, "dados.pkl"), sql)
    for f in ("01_criar_banco_rebobina.sql", "05_views_bi.sql"):
        shutil.copy(os.path.join(AQUI, "sql", f), os.path.join(sql, f))
    # 6. CSVs do modelo estrela
    csv = os.path.join(RAIZ, "dados", "csv")
    os.makedirs(csv, exist_ok=True)
    for nome, df in tabelas.items():
        df.to_csv(os.path.join(csv, f"{nome}.csv"), index=False, encoding="utf-8-sig")
    print("Concluído.")


if __name__ == "__main__":
    main()
