# CORRECAO POSICAO RESULTADOS TOPO

Data: 2026-06-06

Branch: `ELITE_X_COBRANCA_PIX_DEV`

## Objetivo

Exibir pagamento PIX, QR Code, previsoes e jogos gerados imediatamente abaixo do upload/base e antes dos cards principais do dashboard.

## Problema

Os resultados de `Geracao de Jogos` e `Previsao do Proximo Concurso` apareciam abaixo dos cards e de outros blocos, obrigando o usuario a rolar a pagina para encontrar o resultado.

## Correcoes Aplicadas

Arquivo alterado:

- `app.py`

Alteracoes:

- Criado container dedicado:

```python
resultado_topo_container = st.container()
```

- Criado estado do ultimo resultado:

```python
st.session_state["resultado_topo"] = {
    "tipo": "previsao" | "geracao_jogos" | "pix",
    "conteudo": dados_resultado,
}
```

- Criada funcao `definir_resultado_topo(tipo, conteudo)`.
- Criado card visual de topo com `render_card_resultado_topo(...)`.
- `Geração de Jogos` agora renderiza dentro do `resultado_topo_container`.
- `Previsão do Próximo Concurso` agora renderiza dentro do `resultado_topo_container`.
- Pagamento PIX, QR Code, copia-e-cola, botao `Verificar pagamento` e resultado aprovado ficam no topo.
- Cards de resumo continuam abaixo do container de resultado.
- Conteudo das demais secoes foi movido para `conteudo_slot`, abaixo dos cards.
- Removida a chamada de Geração/Previsão no bloco final da página, evitando duplicidade.

## Ordem Atual da Pagina

```text
Cabeçalho Mega-Sena Pro
Menu de botões
Upload CSV
RESULTADO GERADO / PAGAMENTO PIX / PREVISÃO
Cards de resumo
Status da base
Painel de premiação
Restante da página
```

## Fluxos Ajustados

### Previsao do Proximo Concurso

No topo:

- Pagamento PIX
- QR Code
- Codigo copia e cola
- Botao `Verificar pagamento`
- Apos aprovacao: jogo principal e alternativos

### Geracao de Jogos

No topo:

- Quantidade de jogos
- Pagamento PIX
- Jogos gerados
- Scores

## Validacao

- `python -m py_compile app.py`: aprovado.
- `localhost:8501`: HTTP 200 OK.
- AppTest `Geração de Jogos`:
  - sem excecoes.
  - bloco `Resultado gerado` presente.
  - controles PIX e botao de geracao aparecem no topo.
- AppTest `Previsão do Próximo Concurso`:
  - sem excecoes.
  - bloco `Pagamento PIX` presente.
  - controles PIX e botao de previsao aparecem no topo.
- Busca confirmou que:
  - `render_gerador_inteligente(df)` e chamado dentro de `resultado_topo_container`.
  - `render_previsao_concurso_alvo(df)` e chamado dentro de `resultado_topo_container`.
  - nao ha segunda chamada desses resultados no final da pagina.

## Observacao

Nao foi alterada a logica estatistica do Motor Elite nem a integracao de pagamento. A mudanca foi de posicionamento e organizacao visual dos resultados.
