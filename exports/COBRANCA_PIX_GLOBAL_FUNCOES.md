# COBRANCA PIX GLOBAL POR FUNCOES

Data: 2026-06-06

Branch: `ELITE_X_COBRANCA_PIX_DEV`

## Objetivo

Aplicar cobranca PIX de R$ 1,00 antes de liberar qualquer secao ou funcao do menu que gere valor ao usuario.

## Excecao gratuita

- `Visao Geral`

A Visao Geral permanece gratuita, exibindo apenas cards basicos e informacoes publicas.

## Secoes pagas

- Resultados
- Motor Elite 9
- Banco Mestre
- Elite X
- Boloes
- Auditorias
- Exportacoes
- Geracao de Jogos
- Previsao do Proximo Concurso

## Implementacao

Criada funcao central:

```python
exigir_pagamento_para_funcao(
    chave_funcao,
    nome_funcao,
    valor=1.00,
    quantidade=1
)
```

Essa funcao:

- pede e-mail valido;
- cria cobranca PIX real via Mercado Pago;
- exibe QR Code reduzido;
- exibe codigo PIX copia e cola;
- exibe botao `Verificar pagamento`;
- libera conteudo somente quando Mercado Pago retorna `approved`;
- usa estado separado por funcao.

## Session state por funcao

Estados criados dinamicamente:

- `pagamento_aprovado_resultados`
- `pagamento_aprovado_motor_elite_9`
- `pagamento_aprovado_banco_mestre`
- `pagamento_aprovado_elite_x`
- `pagamento_aprovado_boloes`
- `pagamento_aprovado_auditorias`
- `pagamento_aprovado_exportacoes`
- `pagamento_aprovado_geracao_jogos`
- `pagamento_aprovado_previsao`

## Regra de acesso

Cada pagamento libera apenas a funcao correspondente.

Exemplos:

- Pagar em `Previsao do Proximo Concurso` libera apenas previsao.
- Pagar em `Banco Mestre` libera apenas Banco Mestre.
- Pagar em `Auditorias` libera apenas auditorias.
- Para acessar outra funcao, novo PIX de R$ 1,00 e necessario.

## Logs

Arquivo:

- `exports/pagamentos.csv`

Colunas:

- `data_hora`
- `funcao`
- `concurso_alvo`
- `quantidade_palpites`
- `valor_total`
- `status_pagamento`
- `payment_id`
- `email_pagador`
- `jogos_liberados`
- `conteudo_liberado`

## Removido ou impedido

- Nao ha botao de simulacao.
- Nao ha `payment_id` fake.
- Nao ha status `approved_simulado`.
- Secoes pagas nao renderizam conteudo antes do pagamento aprovado.

## Arquivos alterados

- `app.py`
- `src/pagamentos.py`
- `exports/pagamentos.csv`
- `exports/COBRANCA_PIX_GLOBAL_FUNCOES.md`

## Validacao

- `.venv\Scripts\python.exe -m py_compile app.py src\pagamentos.py src\mercado_pago_pix.py`: aprovado.
- `localhost:8501`: HTTP 200 OK.
- Busca por `Simular pagamento`, `SIMULADO`, `approved_simulado` e `simular_pix`: sem resultados.
- AppTest validou os 10 botoes do menu:
  - Visao Geral abre sem PIX.
  - Resultados exige PIX.
  - Motor Elite 9 exige PIX.
  - Banco Mestre exige PIX.
  - Elite X exige PIX.
  - Boloes exige PIX.
  - Auditorias exige PIX.
  - Exportacoes exige PIX.
  - Geracao de Jogos exige PIX.
  - Previsao do Proximo Concurso exige PIX.

## Observacao

Nao foi alterado o Motor Elite, estatisticas, previsoes, auditorias ou base historica. A alteracao foi limitada a camada de acesso/pagamento por funcao.
