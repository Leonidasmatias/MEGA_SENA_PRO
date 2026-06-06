# UX LEIGO - PREVISAO DO PROXIMO SORTEIO

Data: 2026-06-06

## Objetivo

Simplificar a experiencia da secao `Previsao do Proximo Concurso` para usuarios leigos, deixando claro onde clicar, por que informar e-mail, como gerar o PIX e como liberar os numeros.

## Alteracoes aplicadas

- Botao do menu alterado para `🎯 Prever Proximo Sorteio`.
- Botao de previsao destacado em verde forte, texto branco, borda arredondada, sombra e pulso suave.
- Criado card de topo com linguagem simples:
  - `🎯 Gerar meus numeros para o proximo sorteio`
  - Concurso alvo e premio estimado.
  - Instrucao direta sobre e-mail, PIX de R$ 1,00 e liberacao dos numeros.
- Campo de e-mail ajustado:
  - Label: `📧 Coloque seu e-mail aqui`
  - Placeholder: `seunome@email.com`
  - Mensagem explicando uso do e-mail.
- Botao de criacao PIX alterado para:
  - `💳 Gerar QR Code PIX de R$ 1,00`
- Botao de verificacao alterado para:
  - `✅ Ja paguei, liberar meus numeros`
- Mensagem de pagamento aprovado ajustada para:
  - `✅ Pagamento aprovado! Seus numeros foram liberados abaixo.`
- Metricas do pagamento ajustadas para linguagem simples:
  - Produto
  - Valor
  - Total
- Aviso obrigatorio reescrito em linguagem simples:
  - `A Mega-Sena e aleatoria. Estes numeros sao uma analise estatistica e nao garantem premio.`
- Mantido QR Code reduzido e centralizado para desktop, tablet e mobile.

## Arquivos alterados

- `app.py`
- `exports/UX_LEIGO_PREVISAO_PROXIMO_SORTEIO.md`

## Escopo preservado

Nao foram alterados:

- Motor Elite
- Mercado Pago PIX
- Valor da cobranca
- Logica estatistica
- Base historica

## Validacao

- Compilacao Python: aprovada com `.venv\Scripts\python.exe -m py_compile app.py`.
- App em localhost: HTTP 200 OK em `http://localhost:8501`.
- Renderizacao Streamlit: AppTest sem excecoes.
- Botao do menu validado: `🎯 Prever Proximo Sorteio`.
- Card leigo validado no topo da secao.
- Campo de e-mail validado com label e placeholder.
- Botao PIX validado com texto `💳 Gerar QR Code PIX de R$ 1,00`.
- Metricas validadas:
  - Produto: Previsao do Proximo Sorteio
  - Valor: R$ 1,00
  - Total: R$ 1,00
- Aviso obrigatorio em linguagem simples validado.
- Responsividade revisada via CSS:
  - Botao grande no mobile.
  - Card com padding reduzido em telas pequenas.
  - QR Code mantido em 300px desktop, 250px tablet e 220px mobile.
