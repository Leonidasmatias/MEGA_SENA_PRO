# REMOCAO SIMULACAO PIX

Data: 2026-06-06

Branch: `ELITE_X_COBRANCA_PIX_DEV`

## Objetivo

Remover completamente a funcionalidade de simulacao de pagamento PIX, mantendo apenas o fluxo real com Mercado Pago.

## Removido

- Botao `Simular pagamento aprovado`.
- Chave de interface `simular_pix_*`.
- Geracao de `payment_id` com prefixo `SIMULADO`.
- Status `approved_simulado`.
- Logica de aprovacao artificial de pagamento.
- Registros simulados antigos em `exports/pagamentos.csv`.

## Fluxo Atual

1. Usuario informa e-mail valido.
2. Usuario clica em `Criar cobrança PIX`.
3. Sistema cria cobranca real via Mercado Pago.
4. Sistema exibe QR Code PIX.
5. Sistema exibe codigo PIX copia e cola.
6. Sistema exibe botao `Verificar pagamento`.
7. Se Mercado Pago retornar `approved`:
   - QR Code e codigo PIX sao ocultados.
   - Mensagem exibida: `✅ Pagamento aprovado com sucesso.`
   - Quantidade comprada de palpites e liberada.
   - Pagamento e registrado em `exports/pagamentos.csv`.
8. Geracao de Jogos e Previsao do Proximo Concurso so ficam liberadas apos pagamento aprovado real.

## Mantido

- `Criar cobrança PIX`
- `Verificar pagamento`
- Validacao obrigatoria de e-mail
- Logs em `exports/pagamentos.csv`
- Integracao real com Mercado Pago PIX

## Arquivos Revisados

- `app.py`
- `src/pagamentos.py`
- `src/mercado_pago_pix.py`

## Arquivos Alterados

- `app.py`
- `exports/pagamentos.csv`

## Validacao

- Busca global por `SIMULADO`: sem resultados.
- Busca global por `approved_simulado`: sem resultados.
- Busca global por `Simular pagamento`: sem resultados.
- Busca global por `simular_pix`: sem resultados.
- `python -m py_compile app.py src/pagamentos.py src/mercado_pago_pix.py`: aprovado.
- `localhost:8501`: HTTP 200 OK.
- Interface da secao de geracao mostra apenas o fluxo real PIX, sem botao de simulacao.

## Observacao

Nao foi alterada a logica estatistica do Motor Elite. A alteracao foi limitada ao fluxo de pagamento PIX.
