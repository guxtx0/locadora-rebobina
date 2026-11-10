/* =====================================================================
   LOCADORA REBOBINA · camada de BI (modelo estrela) para o Power BI
   Rode depois dos scripts 1 a 4.

   Cria o esquema [bi] com:
     dimensões: bi.dim_filme, bi.dim_ator, bi.dim_cliente, bi.dim_loja
     ponte:     bi.ponte_filme_ator
     fatos:     bi.fato_locacao, bi.fato_pagamento
   ===================================================================== */
USE locadora_rebobina;
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'bi')
    EXEC('CREATE SCHEMA bi');
GO

/* ---------------------------------------------------------------------
   DIM_FILME
   --------------------------------------------------------------------- */
CREATE OR ALTER VIEW bi.dim_filme AS
SELECT
    f.id_filme,
    f.titulo                               AS filme,
    f.titulo_original,
    f.titulo_ingles,
    g.nome                                 AS categoria,
    i.nome                                 AS idioma,
    f.classificacao_indicativa             AS classificacao,
    CASE f.classificacao_indicativa
        WHEN 'L' THEN 'Livre'
        ELSE 'Não recomendado para menores de ' + f.classificacao_indicativa + ' anos'
    END                                    AS classificacao_descricao,
    f.duracao_min,
    CASE
        WHEN f.duracao_min < 90  THEN '1. Até 89 min'
        WHEN f.duracao_min < 120 THEN '2. De 90 a 119 min'
        WHEN f.duracao_min < 150 THEN '3. De 120 a 149 min'
        ELSE                          '4. 150 min ou mais'
    END                                    AS faixa_duracao,
    f.data_lancamento,
    f.ano_lancamento,
    CAST(f.ano_lancamento / 10 * 10 AS VARCHAR(4)) + 's' AS decada,
    f.data_chegada_locadora,
    CASE
        WHEN f.data_lancamento >= '2009-01-01' THEN 'Lançamento do período (2009–2011)'
        WHEN f.classico = 1                    THEN 'Clássico'
        ELSE                                        'Acervo'
    END                                    AS perfil_titulo,
    CASE WHEN f.classico = 1 THEN 'Sim' ELSE 'Não' END AS classico,
    f.diretor,
    -- valores convertidos para reais pelo câmbio médio de 2010 (R$ 1,76 por US$)
    CAST(f.orcamento_usd  * 1.76 AS DECIMAL(18,2)) AS orcamento_rs,
    CAST(f.bilheteria_usd * 1.76 AS DECIMAL(18,2)) AS bilheteria_rs,
    CASE
        WHEN f.bilheteria_usd IS NULL                 THEN '0. Sem informação'
        WHEN f.bilheteria_usd * 1.76 <  100000000     THEN '1. Até R$ 100 mi'
        WHEN f.bilheteria_usd * 1.76 <  400000000     THEN '2. R$ 100 a 400 mi'
        WHEN f.bilheteria_usd * 1.76 < 1000000000     THEN '3. R$ 400 mi a 1 bi'
        ELSE                                               '4. Acima de R$ 1 bi'
    END                                    AS faixa_bilheteria,
    f.nota_media,
    f.total_votos,
    tp.valor_diaria                        AS preco_locacao,     -- preço da tabela vigente em jan/2011
    tp.tipo                                AS tipo_preco_atual
FROM dbo.filme f
JOIN dbo.genero g ON g.id_genero = f.id_genero_principal
JOIN dbo.idioma i ON i.id_idioma = f.id_idioma
JOIN dbo.tabela_preco tp
  ON tp.vigencia_fim IS NULL
 AND tp.tipo = CASE
                   WHEN f.classico = 1 THEN N'Clássico'
                   WHEN DATEDIFF(DAY, f.data_chegada_locadora, '2011-01-31') <= 180 THEN N'Lançamento'
                   ELSE N'Catálogo'
               END;
GO

/* ---------------------------------------------------------------------
   DIM_ATOR e PONTE_FILME_ATOR
   --------------------------------------------------------------------- */
CREATE OR ALTER VIEW bi.dim_ator AS
SELECT a.id_ator, a.nome AS ator
FROM dbo.ator a;
GO

CREATE OR ALTER VIEW bi.ponte_filme_ator AS
SELECT fa.id_filme, fa.id_ator, fa.ordem_credito
FROM dbo.filme_ator fa;
GO

/* ---------------------------------------------------------------------
   DIM_CLIENTE (idade calculada na data de corte, 31/01/2011)
   --------------------------------------------------------------------- */
CREATE OR ALTER VIEW bi.dim_cliente AS
SELECT
    c.id_cliente,
    c.nome + ' ' + c.sobrenome            AS cliente,
    CASE c.sexo WHEN 'F' THEN 'Feminino' ELSE 'Masculino' END AS sexo,
    x.idade,
    CASE
        WHEN x.idade < 18 THEN '1. Até 17 anos'
        WHEN x.idade < 25 THEN '2. 18 a 24 anos'
        WHEN x.idade < 35 THEN '3. 25 a 34 anos'
        WHEN x.idade < 45 THEN '4. 35 a 44 anos'
        WHEN x.idade < 60 THEN '5. 45 a 59 anos'
        ELSE                   '6. 60 anos ou mais'
    END                                    AS faixa_etaria,
    e.bairro,
    ci.nome                                AS cidade,
    ci.uf,
    'Brasil'                               AS pais,
    l.nome                                 AS loja_cadastro,
    c.data_cadastro,
    CASE WHEN c.ativo = 1 THEN 'Ativo' ELSE 'Inativo' END AS situacao_cadastro,
    CASE WHEN c.cartao_fidelidade = 1 THEN 'Sim' ELSE 'Não' END AS cartao_fidelidade
FROM dbo.cliente c
JOIN dbo.endereco e  ON e.id_endereco = c.id_endereco
JOIN dbo.cidade   ci ON ci.id_cidade  = e.id_cidade
JOIN dbo.loja     l  ON l.id_loja     = c.id_loja_cadastro
CROSS APPLY (
    SELECT DATEDIFF(YEAR, c.data_nascimento, '2011-01-31')
         - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, c.data_nascimento, '2011-01-31'), c.data_nascimento) > '2011-01-31'
                THEN 1 ELSE 0 END AS idade
) x;
GO

/* ---------------------------------------------------------------------
   DIM_LOJA
   --------------------------------------------------------------------- */
CREATE OR ALTER VIEW bi.dim_loja AS
SELECT
    l.id_loja,
    l.nome                                 AS loja,
    e.bairro,
    ci.nome                                AS cidade,
    'Brasil'                               AS pais,
    f.nome + ' ' + f.sobrenome             AS gerente,
    l.data_inauguracao
FROM dbo.loja l
JOIN dbo.endereco e  ON e.id_endereco = l.id_endereco
JOIN dbo.cidade   ci ON ci.id_cidade  = e.id_cidade
LEFT JOIN dbo.funcionario f ON f.id_funcionario = l.id_gerente;
GO

/* ---------------------------------------------------------------------
   FATO_LOCACAO: uma linha por locação
   --------------------------------------------------------------------- */
CREATE OR ALTER VIEW bi.fato_locacao AS
SELECT
    lo.id_locacao,
    CAST(lo.data_hora_locacao AS DATE)       AS data_locacao,
    DATEPART(HOUR, lo.data_hora_locacao)     AS hora_locacao,
    CAST(lo.data_hora_devolucao AS DATE)     AS data_devolucao,
    cp.id_filme,
    cp.id_loja,
    lo.id_cliente,
    lo.id_funcionario,
    cp.midia,
    tp.tipo                                  AS tipo_preco,
    tp.prazo_dias,
    DATEDIFF(DAY, lo.data_hora_locacao, lo.data_hora_devolucao) AS dias_com_cliente,
    CASE
        WHEN lo.data_hora_devolucao IS NULL THEN NULL
        WHEN lo.data_hora_devolucao > lo.data_prevista_devolucao
             THEN CASE WHEN DATEDIFF(DAY, lo.data_prevista_devolucao, lo.data_hora_devolucao) = 0 THEN 1
                       ELSE DATEDIFF(DAY, lo.data_prevista_devolucao, lo.data_hora_devolucao) END
        ELSE 0
    END                                      AS dias_atraso,
    CASE
        WHEN lo.data_hora_devolucao IS NULL                         THEN 'Em aberto'
        WHEN lo.data_hora_devolucao > lo.data_prevista_devolucao    THEN 'Com atraso'
        ELSE                                                             'No prazo'
    END                                      AS status_devolucao,
    lo.promocao,
    lo.valor_tabela,
    lo.valor_desconto,
    lo.valor_locacao,
    lo.valor_multa,
    ISNULL(p.valor_pago, 0)                  AS valor_pago,
    lo.valor_locacao + lo.valor_multa - ISNULL(p.valor_pago, 0) AS valor_pendente
FROM dbo.locacao lo
JOIN dbo.copia        cp ON cp.id_copia        = lo.id_copia
JOIN dbo.tabela_preco tp ON tp.id_tabela_preco = lo.id_tabela_preco
LEFT JOIN (
    SELECT id_locacao, SUM(valor) AS valor_pago
    FROM dbo.pagamento
    GROUP BY id_locacao
) p ON p.id_locacao = lo.id_locacao;
GO

/* ---------------------------------------------------------------------
   FATO_PAGAMENTO: uma linha por pagamento (fonte do faturamento)
   --------------------------------------------------------------------- */
CREATE OR ALTER VIEW bi.fato_pagamento AS
SELECT
    pg.id_pagamento,
    CAST(pg.data_hora_pagamento AS DATE) AS data_pagamento,
    pg.id_cliente,
    fu.id_loja,
    cp.id_filme,
    pg.tipo                              AS tipo_pagamento,
    pg.forma_pagamento,
    pg.valor
FROM dbo.pagamento pg
JOIN dbo.funcionario fu ON fu.id_funcionario = pg.id_funcionario
JOIN dbo.locacao     lo ON lo.id_locacao     = pg.id_locacao
JOIN dbo.copia       cp ON cp.id_copia       = lo.id_copia;
GO

/* ---------------------------------------------------------------------
   CONFERÊNCIA (compare com os valores do guia)
   --------------------------------------------------------------------- */
SELECT 'Filmes' AS item, COUNT(*) AS total FROM bi.dim_filme      UNION ALL
SELECT 'Atores',         COUNT(*)          FROM bi.dim_ator       UNION ALL
SELECT 'Clientes',       COUNT(*)          FROM bi.dim_cliente    UNION ALL
SELECT 'Lojas',          COUNT(*)          FROM bi.dim_loja       UNION ALL
SELECT 'Locações',       COUNT(*)          FROM bi.fato_locacao   UNION ALL
SELECT 'Pagamentos',     COUNT(*)          FROM bi.fato_pagamento;

SELECT tipo_pagamento, SUM(valor) AS total
FROM bi.fato_pagamento
GROUP BY ROLLUP (tipo_pagamento);
GO
