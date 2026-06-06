# UX NUMEROS DA SORTE FINAL

Data: 2026-06-06

## Objetivo

Melhorar a comunicacao para usuarios leigos sem alterar o fluxo atual de e-mail e PIX.

## Alteracoes aplicadas

### Titulo principal

Antes:

- Gere seus numeros para o proximo sorteio da Mega-Sena

Depois:

- 🍀 Gere seus numeros da sorte para o proximo sorteio da Mega-Sena

### Subtitulo

Antes:

- Um fluxo simples: informe seu e-mail, pague R$ 1,00 via PIX e veja os numeros sugeridos.

Depois:

- Informe seu e-mail, gere o PIX de R$ 1,00 e desbloqueie seus numeros da sorte para o proximo sorteio.

### Campo de e-mail

Mantido:

- Label: `📧 Coloque seu e-mail aqui`
- Placeholder: `seunome@email.com`

Texto auxiliar atualizado:

- Seu e-mail e utilizado apenas para identificar sua solicitacao e liberar seus numeros da sorte.

### Texto abaixo do botao LED

Antes:

- Ganhe acesso a previsao do proximo premio de R$ 32 milhoes

Depois:

- 🍀 Descubra seus numeros da sorte para concorrer ao proximo premio de R$ 32 milhoes

## Arquivos alterados

- `app.py`
- `exports/UX_NUMEROS_DA_SORTE_FINAL.md`

## Nao alterado

- Mercado Pago PIX
- Campo de e-mail
- Motor Elite
- Estatisticas
- Valor da cobranca
- Fluxo de pagamento

## Validacao

- Compilacao Python: aprovada com `.venv\Scripts\python.exe -m py_compile app.py`.
- App em localhost: HTTP 200 OK em `http://localhost:8501`.
- Interface renderizada via AppTest Streamlit sem excecoes.
- Campo de e-mail mantido:
  - 1 campo de e-mail renderizado.
  - Label validado.
  - Placeholder validado.
- Textos finais validados na interface publica.
- PIX preservado: textos alterados sem modificar chamadas Mercado Pago, valor, fluxo ou validacao de pagamento.
