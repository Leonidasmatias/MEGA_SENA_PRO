# Relatorio de validacao do projeto ativo

Data: 05/06/2026

## Projetos verificados

- `MEGA_SENA_ANALYTICS_SITE`
- `MEGA_SENA_PREVISAO_LOCAL`

## 1. Qual app.py esta sendo executado pelo Streamlit

Conclusao: o projeto ativo identificado e `MEGA_SENA_ANALYTICS_SITE/app.py`.

Evidencias:

- Existe um processo Python/Streamlit ouvindo na porta `8501`.
- Os logs/restarts de Streamlit mais recentes associados aos projetos encontrados estao em `MEGA_SENA_ANALYTICS_SITE`.
- Antes da migracao, `MEGA_SENA_ANALYTICS_SITE/app.py` nao continha as correcoes dos botoes (`SECOES_APP`, `inicializar_estado`, `Gerar previsao do sorteio`, `Gerar arquivos de exportacao`, `Gerar bolao 15 dezenas`).
- `MEGA_SENA_PREVISAO_LOCAL/app.py` continha as correcoes feitas anteriormente.

Observacao: a leitura direta da linha de comando do PID ativo foi bloqueada pelo Windows com erro de acesso negado, entao a identificacao foi feita por porta, logs e conteudo dos arquivos.

## 2. Porta utilizada

- Porta ativa: `8501`
- Status HTTP em `http://localhost:8501`: `200 OK`
- PID identificado pelo `netstat`: `11988`

## 3. Pasta aberta pelo comando streamlit run

Conclusao: a pasta efetivamente associada ao Streamlit ativo e `C:\Users\Leonidas\Documents\New project\MEGA_SENA_ANALYTICS_SITE`.

Evidencias:

- Logs locais de Streamlit encontrados em `MEGA_SENA_ANALYTICS_SITE`.
- O projeto `MEGA_SENA_ANALYTICS_SITE` estava sem as correcoes e era o candidato ativo pelos registros de execucao.
- A linha de comando/cwd do PID nao pode ser lida por restricao de permissao do Windows.

## 4. As alteracoes dos botoes foram aplicadas ao projeto atualmente em execucao?

Sim. Como o projeto ativo era `MEGA_SENA_ANALYTICS_SITE`, as correcoes foram migradas de:

- `MEGA_SENA_PREVISAO_LOCAL/app.py`

para:

- `MEGA_SENA_ANALYTICS_SITE/app.py`

Validacao apos migracao:

- `MEGA_SENA_ANALYTICS_SITE/app.py` compila com `py_compile`.
- `MEGA_SENA_ANALYTICS_SITE/app.py` agora contem:
  - `SECOES_APP`
  - `inicializar_estado`
  - `Upload CSV`
  - `Gerar previsao do sorteio`
  - `Gerar bolao 15 dezenas`
  - `Gerar arquivos de exportacao`
- Hash SHA256 dos dois `app.py` ficou igual apos a migracao.

## Status final

Concluido. O projeto ativo foi identificado como `MEGA_SENA_ANALYTICS_SITE`, a porta ativa e `8501`, e as correcoes dos botoes foram migradas para o `app.py` atualmente em execucao.
