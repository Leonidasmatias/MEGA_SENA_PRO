# Mega-Sena Pro / Elite X

Aplicacao web em Streamlit para analise estatistica da Mega-Sena, leitura de base historica, geracao de jogos, ranking de combinacoes, Banco Mestre, boloes e modulos Elite X.

> Aviso: este projeto faz analise estatistica e combinatoria. Ele nao garante acerto, premio ou qualquer resultado em sorteios reais.

## Versao estavel

- Versao: `ELITE_X_ESTAVEL_3012`
- Base ativa: `dados/mega_sena_historico.csv`
- Concursos carregados: `3012`
- Ultimo concurso: `3012`
- Data do ultimo concurso: `28/05/2026`
- Dezenas do ultimo concurso: `05 07 17 41 42 49`

## Como rodar localmente

1. Instale Python 3.10 ou superior.
2. Entre na pasta do projeto:

```bash
cd "C:\Users\Leonidas\Documents\New project\MEGA_SENA_ANALYTICS_SITE"
```

3. Instale as dependencias:

```bash
pip install -r requirements.txt
```

4. Rode o app:

```bash
streamlit run app.py
```

5. Acesse:

```text
http://localhost:8501
```

## Dependencias

As dependencias principais ficam em `requirements.txt`.

```bash
pip install -r requirements.txt
```

## Arquivos principais

- `app.py`: aplicacao Streamlit.
- `requirements.txt`: dependencias do projeto.
- `dados/mega_sena_historico.csv`: base historica ativa.
- `src/`: modulos de dados, estatistica, geracao, auditoria e motores Elite.
- `exports/`: resultados, auditorias e arquivos exportados.
- `VERSAO_OFICIAL_ELITE_X_3012.md`: relatorio da versao oficial estavel.
- `RELATORIO_AUDITORIA_BASES.md`: auditoria das bases historicas.

## Funcionalidades

- Dashboard com cards da base ativa.
- Menu superior por secoes, sem duplicidade.
- Motor Elite 9.
- Elite X e Elite X PRO.
- Banco Mestre.
- Geracao de jogos.
- Boloes profissionais.
- Auditorias e backtests.
- Exportacoes CSV, Excel e PDF.

## Observacao

Mega-Sena e jogo de azar. O sistema organiza informacoes, calcula estatisticas e gera combinacoes com base historica, mas nao altera a aleatoriedade dos sorteios e nao oferece garantia de acerto.
