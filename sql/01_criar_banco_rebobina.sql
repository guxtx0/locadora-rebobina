/* =====================================================================
   LOCADORA REBOBINA · base fictícia para estudo de SQL e Power BI
   Script 1 de 4 · criação do banco e das tabelas

   Cenário: rede de videolocadoras com 3 lojas na RMBH (Contagem,
   Belo Horizonte e Betim), com movimento de jan/2009 a jan/2011.
   Filmes reais (TMDB 5000); lojas, clientes, estoque e locações simulados.
   Requer SQL Server 2016 ou mais recente.
   ===================================================================== */

IF DB_ID('locadora_rebobina') IS NULL
    CREATE DATABASE locadora_rebobina;
GO
USE locadora_rebobina;
GO

/* ---------------------------------------------------------------------
   LOCALIZAÇÃO
   --------------------------------------------------------------------- */
CREATE TABLE dbo.cidade (
    id_cidade   INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_cidade PRIMARY KEY,
    nome        NVARCHAR(60) NOT NULL,
    uf          CHAR(2)      NOT NULL
);

CREATE TABLE dbo.endereco (
    id_endereco INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_endereco PRIMARY KEY,
    logradouro  NVARCHAR(100) NOT NULL,
    numero      VARCHAR(10)   NOT NULL,
    bairro      NVARCHAR(60)  NOT NULL,
    id_cidade   INT           NOT NULL CONSTRAINT fk_endereco_cidade REFERENCES dbo.cidade (id_cidade),
    cep         CHAR(9)       NOT NULL
);

/* ---------------------------------------------------------------------
   LOJAS E FUNCIONÁRIOS
   --------------------------------------------------------------------- */
CREATE TABLE dbo.loja (
    id_loja          INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_loja PRIMARY KEY,
    nome             NVARCHAR(60) NOT NULL,
    id_endereco      INT          NOT NULL CONSTRAINT fk_loja_endereco REFERENCES dbo.endereco (id_endereco),
    id_gerente       INT          NULL,
    data_inauguracao DATE         NOT NULL
);

CREATE TABLE dbo.funcionario (
    id_funcionario INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_funcionario PRIMARY KEY,
    nome           NVARCHAR(45)  NOT NULL,
    sobrenome      NVARCHAR(60)  NOT NULL,
    email          NVARCHAR(100) NOT NULL,
    id_loja        INT           NOT NULL CONSTRAINT fk_funcionario_loja REFERENCES dbo.loja (id_loja),
    cargo          NVARCHAR(30)  NOT NULL,
    data_admissao  DATE          NOT NULL,
    ativo          BIT           NOT NULL CONSTRAINT df_funcionario_ativo DEFAULT (1)
);

ALTER TABLE dbo.loja
    ADD CONSTRAINT fk_loja_gerente FOREIGN KEY (id_gerente) REFERENCES dbo.funcionario (id_funcionario);

/* ---------------------------------------------------------------------
   CLIENTES
   --------------------------------------------------------------------- */
CREATE TABLE dbo.cliente (
    id_cliente       INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_cliente PRIMARY KEY,
    nome             NVARCHAR(45)  NOT NULL,
    sobrenome        NVARCHAR(60)  NOT NULL,
    sexo             CHAR(1)       NOT NULL CONSTRAINT ck_cliente_sexo CHECK (sexo IN ('F', 'M')),
    data_nascimento  DATE          NOT NULL,
    email            NVARCHAR(100) NULL,
    id_endereco      INT           NOT NULL CONSTRAINT fk_cliente_endereco REFERENCES dbo.endereco (id_endereco),
    id_loja_cadastro INT           NOT NULL CONSTRAINT fk_cliente_loja REFERENCES dbo.loja (id_loja),
    data_cadastro    DATE          NOT NULL,
    ativo            BIT           NOT NULL CONSTRAINT df_cliente_ativo DEFAULT (1),
    cartao_fidelidade BIT          NOT NULL CONSTRAINT df_cliente_fidelidade DEFAULT (0)
);

/* ---------------------------------------------------------------------
   CATÁLOGO
   --------------------------------------------------------------------- */
CREATE TABLE dbo.idioma (
    id_idioma INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_idioma PRIMARY KEY,
    nome      NVARCHAR(30) NOT NULL
);

CREATE TABLE dbo.genero (
    id_genero INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_genero PRIMARY KEY,
    nome      NVARCHAR(30) NOT NULL
);

CREATE TABLE dbo.filme (
    id_filme                 INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_filme PRIMARY KEY,
    titulo                   NVARCHAR(200) NOT NULL,
    titulo_original          NVARCHAR(200) NOT NULL,
    titulo_ingles            NVARCHAR(200) NOT NULL,
    data_lancamento          DATE          NOT NULL,   -- estreia nos cinemas
    ano_lancamento           SMALLINT      NOT NULL,
    duracao_min              SMALLINT      NOT NULL,
    id_idioma                INT           NOT NULL CONSTRAINT fk_filme_idioma REFERENCES dbo.idioma (id_idioma),
    id_genero_principal      INT           NOT NULL CONSTRAINT fk_filme_genero REFERENCES dbo.genero (id_genero),
    classificacao_indicativa VARCHAR(2)    NOT NULL CONSTRAINT ck_filme_classificacao
                                 CHECK (classificacao_indicativa IN ('L', '10', '12', '14', '16', '18')),
    diretor                  NVARCHAR(100) NULL,
    orcamento_usd            BIGINT        NULL,
    bilheteria_usd           BIGINT        NULL,
    popularidade             DECIMAL(10,3) NOT NULL,   -- índice de popularidade do TMDB
    nota_media               DECIMAL(3,1)  NOT NULL,   -- nota média no TMDB (0 a 10)
    total_votos              INT           NOT NULL,
    data_chegada_locadora    DATE          NOT NULL,   -- quando entrou no acervo da rede
    classico                 BIT           NOT NULL,
    id_tmdb                  INT           NOT NULL
);

CREATE TABLE dbo.filme_genero (
    id_filme  INT NOT NULL CONSTRAINT fk_fg_filme  REFERENCES dbo.filme (id_filme),
    id_genero INT NOT NULL CONSTRAINT fk_fg_genero REFERENCES dbo.genero (id_genero),
    CONSTRAINT pk_filme_genero PRIMARY KEY (id_filme, id_genero)
);

CREATE TABLE dbo.ator (
    id_ator INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_ator PRIMARY KEY,
    nome    NVARCHAR(100) NOT NULL
);

CREATE TABLE dbo.filme_ator (
    id_filme      INT           NOT NULL CONSTRAINT fk_fa_filme REFERENCES dbo.filme (id_filme),
    id_ator       INT           NOT NULL CONSTRAINT fk_fa_ator  REFERENCES dbo.ator (id_ator),
    ordem_credito TINYINT       NOT NULL,
    personagem    NVARCHAR(100) NULL,
    CONSTRAINT pk_filme_ator PRIMARY KEY (id_filme, id_ator)
);

/* ---------------------------------------------------------------------
   PREÇOS E ESTOQUE
   --------------------------------------------------------------------- */
CREATE TABLE dbo.tabela_preco (
    id_tabela_preco INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_tabela_preco PRIMARY KEY,
    tipo            NVARCHAR(20) NOT NULL CONSTRAINT ck_preco_tipo CHECK (tipo IN (N'Lançamento', N'Catálogo', N'Clássico')),
    valor_diaria    DECIMAL(6,2) NOT NULL,
    prazo_dias      TINYINT      NOT NULL,
    multa_dia       DECIMAL(6,2) NOT NULL,
    vigencia_inicio DATE         NOT NULL,
    vigencia_fim    DATE         NULL
);

CREATE TABLE dbo.copia (
    id_copia        INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_copia PRIMARY KEY,
    id_filme        INT          NOT NULL CONSTRAINT fk_copia_filme REFERENCES dbo.filme (id_filme),
    id_loja         INT          NOT NULL CONSTRAINT fk_copia_loja  REFERENCES dbo.loja (id_loja),
    midia           VARCHAR(10)  NOT NULL CONSTRAINT ck_copia_midia CHECK (midia IN ('DVD', 'Blu-ray')),
    data_aquisicao  DATE         NOT NULL,
    custo_aquisicao DECIMAL(7,2) NOT NULL
);

/* ---------------------------------------------------------------------
   MOVIMENTO
   --------------------------------------------------------------------- */
CREATE TABLE dbo.locacao (
    id_locacao              INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_locacao PRIMARY KEY,
    id_copia                INT          NOT NULL CONSTRAINT fk_locacao_copia       REFERENCES dbo.copia (id_copia),
    id_cliente              INT          NOT NULL CONSTRAINT fk_locacao_cliente     REFERENCES dbo.cliente (id_cliente),
    id_funcionario          INT          NOT NULL CONSTRAINT fk_locacao_funcionario REFERENCES dbo.funcionario (id_funcionario),
    data_hora_locacao       DATETIME     NOT NULL,
    data_prevista_devolucao DATETIME     NOT NULL,
    data_hora_devolucao     DATETIME     NULL,      -- NULL = ainda não devolvido em 31/01/2011
    id_tabela_preco         INT          NOT NULL CONSTRAINT fk_locacao_preco REFERENCES dbo.tabela_preco (id_tabela_preco),
    valor_locacao           DECIMAL(6,2) NOT NULL,
    valor_multa             DECIMAL(7,2) NOT NULL CONSTRAINT df_locacao_multa DEFAULT (0),
    valor_tabela            DECIMAL(6,2) NOT NULL,   -- preço de tabela antes do desconto
    valor_desconto          DECIMAL(6,2) NOT NULL,
    promocao                NVARCHAR(30) NOT NULL    -- Quarta promocional, Combo 3 filmes, Cartão fidelidade, Sem promoção
);

CREATE TABLE dbo.pagamento (
    id_pagamento        INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_pagamento PRIMARY KEY,
    id_locacao          INT          NOT NULL CONSTRAINT fk_pagamento_locacao     REFERENCES dbo.locacao (id_locacao),
    id_cliente          INT          NOT NULL CONSTRAINT fk_pagamento_cliente     REFERENCES dbo.cliente (id_cliente),
    id_funcionario      INT          NOT NULL CONSTRAINT fk_pagamento_funcionario REFERENCES dbo.funcionario (id_funcionario),
    tipo                NVARCHAR(20) NOT NULL CONSTRAINT ck_pagamento_tipo CHECK (tipo IN (N'Locação', N'Multa por atraso')),
    forma_pagamento     NVARCHAR(30) NOT NULL,
    valor               DECIMAL(7,2) NOT NULL,
    data_hora_pagamento DATETIME     NOT NULL
);
GO

/* ---------------------------------------------------------------------
   ÍNDICES
   --------------------------------------------------------------------- */
CREATE INDEX ix_copia_filme_loja    ON dbo.copia (id_filme, id_loja);
CREATE INDEX ix_locacao_data        ON dbo.locacao (data_hora_locacao);
CREATE INDEX ix_locacao_copia       ON dbo.locacao (id_copia);
CREATE INDEX ix_locacao_cliente     ON dbo.locacao (id_cliente);
CREATE INDEX ix_pagamento_locacao   ON dbo.pagamento (id_locacao);
CREATE INDEX ix_pagamento_data      ON dbo.pagamento (data_hora_pagamento);
CREATE INDEX ix_filme_ator_ator     ON dbo.filme_ator (id_ator);
GO
