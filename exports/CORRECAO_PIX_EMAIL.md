# CORRECAO PIX EMAIL

Data: 2026-06-06

Branch: `ELITE_X_COBRANCA_PIX_DEV`

## Erro Corrigido

Erro atual do Mercado Pago:

```text
payer.email must be a valid email
```

## Causa

A criacao de pagamento PIX estava usando um e-mail padrao local como pagador. O Mercado Pago exige um e-mail valido no campo:

```json
{
  "payer": {
    "email": "cliente@dominio.com"
  }
}
```

## Correcoes Aplicadas

- Removido e-mail padrao local da funcao `criar_pagamento_pix`.
- `src/mercado_pago_pix.py` agora exige `email_pagador`.
- Adicionada validacao de e-mail em `src/pagamentos.py`.
- Adicionado campo na interface Streamlit:

```python
email_cliente = st.text_input(
    "Digite seu e-mail para receber a cobrança PIX"
)
```

- Botao `Criar cobrança PIX` fica bloqueado enquanto o e-mail estiver vazio ou invalido.
- Payload enviado ao Mercado Pago agora inclui:

```json
{
  "payer": {
    "email": "email_digitado_pelo_cliente"
  }
}
```

## Arquivos Alterados

- `app.py`
- `src/mercado_pago_pix.py`
- `src/pagamentos.py`

## Validacoes

- `python -m py_compile app.py src/pagamentos.py src/mercado_pago_pix.py`: aprovado.
- `localhost:8501`: HTTP 200 OK.
- Teste de interface:
  - Sem e-mail: botao `Criar cobrança PIX` bloqueado.
  - E-mail invalido: botao bloqueado e mensagem de erro exibida.
  - E-mail valido: botao liberado.
- Teste local do payload:
  - Valor: R$ 1,00.
  - `transaction_amount`: `1.0`.
  - `payment_method_id`: `pix`.
  - `payer.email`: `cliente.teste@example.com`.
  - Retorno simulado validou extracao de QR Code e codigo copia-e-cola PIX.

## Observacao Sobre Teste Real

Nao foi possivel gerar uma cobranca PIX real nesta execucao porque o arquivo `.streamlit/secrets.toml` com `MERCADO_PAGO_ACCESS_TOKEN` nao existe no projeto local. O app agora falha de forma controlada quando o token nao esta configurado.

Para teste real, criar:

```toml
MERCADO_PAGO_ACCESS_TOKEN = "TOKEN_REAL_DO_MERCADO_PAGO"
```

em `.streamlit/secrets.toml`.
