# CORRECAO QRCODE 300PX

Data: 2026-06-06

Branch: `ELITE_X_COBRANCA_PIX_DEV`

## Objetivo

Garantir que o QR Code PIX do Mega-Sena Pro / Elite X seja exibido de forma profissional, centralizada e sem ocupar toda a largura da tela.

## Renderizacoes Localizadas

Busca realizada por:

- `st.image`
- `qr_code`
- `QR Code`
- `data:image/png`

Resultado:

- Nao ha `st.image(...)` relacionado ao PIX.
- A renderizacao PIX ativa usa HTML com `data:image/png;base64`.

## Correcoes Aplicadas

Arquivo alterado:

- `app.py`

Alteracoes:

- Card visual adicionado com fundo branco.
- QR Code centralizado.
- Largura maxima em desktop: `300px`.
- Largura maxima em tablet: `250px`.
- Largura maxima em mobile: `220px`.
- Proporcao quadrada preservada com `width="300"`, `height="300"` e `aspect-ratio: 1 / 1`.
- `overflow: hidden` aplicado no card para evitar barra horizontal.
- `box-sizing: border-box` aplicado no card.
- Valor da cobranca exibido acima do QR Code.
- Botao `COPIAR PIX` mantido.
- Mensagem `Após o pagamento, clique em Verificar pagamento.` mantida.

## Layout Final

```text
Pagamento PIX
Valor: R$ 1,00

[ QR CODE 300x300 ]

[COPIAR PIX]

[VERIFICAR PAGAMENTO]
```

## Validacao

- `python -m py_compile app.py`: aprovado.
- `localhost:8501`: HTTP 200 OK.
- Busca confirmou:
  - classe `.pix-payment-card`
  - classe `.pix-qr-img`
  - `max-width: 300px`
  - `max-width: 250px`
  - `max-width: 220px`
  - `width="300"`
  - `height="300"`
  - `overflow: hidden`

## Observacao

Nao houve alteracao na logica de pagamento, Mercado Pago, Motor Elite ou geracao estatistica. A mudanca foi apenas de layout do QR Code PIX.
