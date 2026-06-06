# CORRECAO LAYOUT QRCODE PIX

Data: 2026-06-06

Branch: `ELITE_X_COBRANCA_PIX_DEV`

## Objetivo

Reduzir o tamanho do QR Code PIX exibido no Mega-Sena Pro / Elite X e melhorar a experiencia visual em desktop e mobile.

## Problema

O QR Code era renderizado com:

```python
st.image(base64.b64decode(estado["qr_code_base64"]), caption="QR Code PIX")
```

Sem largura definida, o Streamlit podia expandir a imagem para ocupar grande parte da pagina.

## Correcoes Aplicadas

- QR Code centralizado.
- QR Code limitado a 300px de largura.
- Proporcao quadrada preservada com `width="300"`, `height="300"` e `aspect-ratio: 1 / 1`.
- QR Code exibido dentro de card visual.
- Valor da cobranca exibido acima do QR Code.
- Botao `COPIAR PIX` adicionado com copia real via `navigator.clipboard.writeText`.
- Campo `Codigo PIX copia e cola` mantido como fallback.
- Mensagem adicionada:

```text
Após o pagamento, clique em Verificar pagamento.
```

- Botao `Verificar pagamento` destacado como botao primario.

## Layout Final

```text
Pagamento PIX
Valor: R$ 1,00

[ QR CODE 300x300 ]

[COPIAR PIX]

Código PIX copia e cola

[VERIFICAR PAGAMENTO]
```

## Arquivo Alterado

- `app.py`

## Validacao

- `python -m py_compile app.py`: aprovado.
- `localhost:8501`: HTTP 200 OK.
- Conferencia no codigo:
  - `Pagamento PIX` presente.
  - `width="300"` presente no QR Code.
  - `height="300"` presente no QR Code.
  - `COPIAR PIX` presente.
  - `Após o pagamento, clique em Verificar pagamento.` presente.
  - `Verificar pagamento` como botao primario.

## Observacao

Nao foi alterada a regra de cobranca nem a logica estatistica. A mudanca foi exclusivamente visual e de usabilidade no bloco de pagamento PIX.
