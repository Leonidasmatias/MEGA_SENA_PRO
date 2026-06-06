# CORRECAO PREVISAO TOPO MENU

Data: 2026-06-06

Branch: `ELITE_X_COBRANCA_PIX_DEV`

## Objetivo

Renderizar `PREVISAO DO SORTEIO / PIX / RESULTADO` imediatamente abaixo dos botoes do menu principal, antes do Upload CSV e antes dos cards de resumo.

## Problema

A secao `Previsao do Proximo Concurso` estava sendo renderizada abaixo do Upload CSV, cards e estrutura principal, exigindo rolagem da pagina.

## Correcoes Aplicadas

Arquivo alterado:

- `app.py`

Alteracoes:

- Criada carga de base sem renderizar Upload CSV:

```python
carregar_dados_ativos_sem_upload()
```

- Criado render separado do Upload CSV:

```python
render_upload_csv_base_topo()
```

- Criado container logo apos o menu:

```python
area_resultado_topo = st.container()
```

- A chamada da previsao foi movida para dentro desse container:

```python
with area_resultado_topo:
    if secao == "Previsao do Proximo Concurso":
        render_previsao_concurso_alvo(df)
```

- A chamada de `Geração de Jogos` tambem foi movida para o mesmo topo.
- Removido bloco duplicado antigo que renderizava previsao/geracao abaixo do Upload CSV.

## Ordem Atual

```text
Header Mega-Sena Pro
Menu de botoes
PREVISAO DO SORTEIO / PIX / RESULTADO
Upload CSV
Cards resumo
Demais secoes
```

## Validacao

- `python -m py_compile app.py`: aprovado.
- `localhost:8501`: HTTP 200 OK.
- AppTest `Previsão do Próximo Concurso`:
  - sem excecoes.
  - bloco `Pagamento PIX` renderizado.
  - botao de previsao disponivel no topo.
- AppTest `Geração de Jogos`:
  - sem excecoes.
  - bloco `Resultado gerado` renderizado.
  - controles PIX/geracao disponiveis no topo.
- Busca no codigo confirmou:
  - `area_resultado_topo` criado antes de `render_upload_csv_base_topo()`.
  - `render_previsao_concurso_alvo(df)` chamado dentro de `area_resultado_topo`.
  - `render_gerador_inteligente(df)` chamado dentro de `area_resultado_topo`.

## Observacao

Nao houve alteracao no Motor Elite, na logica estatistica ou na regra de pagamento PIX. A mudanca foi de layout e ordem de renderizacao.
