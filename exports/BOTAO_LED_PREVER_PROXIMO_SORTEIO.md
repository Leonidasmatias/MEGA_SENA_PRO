# BOTAO LED - PREVER PROXIMO SORTEIO

Data: 2026-06-06

## Objetivo

Criar efeito LED piscante no botao `🎯 PREVER PROXIMO SORTEIO`, deixando o acesso a previsao mais chamativo para usuario leigo.

## Alteracoes aplicadas

- Texto do botao alterado para `🎯 PREVER PROXIMO SORTEIO`.
- Aplicado fundo verde brilhante.
- Aplicado texto branco em negrito.
- Aplicada borda verde neon.
- Aplicada sombra neon.
- Criada animacao `ledPulse` com efeito de acender e apagar.
- Botao aumentado em relacao aos demais.
- Adicionado texto abaixo do botao:
  - `Clique aqui para gerar seus numeros do proximo sorteio`

## Escopo

Alteracao aplicada somente ao botao de previsao, por meio do container visual `.mega-previsao-menu`.

## Arquivos alterados

- `app.py`
- `exports/BOTAO_LED_PREVER_PROXIMO_SORTEIO.md`

## Nao alterado

- PIX
- Motor Elite
- Estatisticas
- Base historica
- Valor da cobranca

## Validacao

- Compilacao Python: aprovada com `.venv\Scripts\python.exe -m py_compile app.py`.
- App em localhost: HTTP 200 OK em `http://localhost:8501`.
- AppTest Streamlit: sem excecoes.
- Botao validado no render:
  - `🎯 PREVER PROXIMO SORTEIO`
- Texto auxiliar validado:
  - `Clique aqui para gerar seus numeros do proximo sorteio`
- Mobile: regra CSS revisada com altura maior, texto ajustavel e fonte reduzida em telas pequenas.
