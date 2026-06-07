# CARD CONCURSO E PREMIO PUBLICO

Data: 2026-06-06

## Objetivo

Exibir sempre o concurso alvo junto com o premio estimado e a data do sorteio na tela publica, aumentando a confianca do usuario.

## Dados exibidos

O card publico passou a exibir:

- Concurso alvo.
- Premio estimado.
- Data do sorteio.
- Texto de confianca informando que a previsao sera gerada para o concurso oficial disponivel.

## Fonte dos dados

Os dados continuam vindo da mesma fonte oficial ja usada pelo app:

- `buscar_info_concurso_atual()`
- `obter_info_caixa_cached()`
- `obter_metadados_concurso_alvo_previsao()`

## Fallbacks

Se o concurso estiver indisponivel:

- `Concurso aguardando atualizacao oficial.`

Se o premio estiver indisponivel:

- `Premio estimado aguardando atualizacao oficial.`

## Fluxo PIX

O texto do botao PIX da previsao foi atualizado para usar o concurso dinamico:

- `Gerar numeros da sorte para o concurso [CONCURSO_ALVO]`

Nao ha numero de concurso fixo no codigo.

## Atualizacao oficial

Quando a base oficial e atualizada, o app limpa o cache da Caixa por meio de:

- `obter_info_caixa_cached.clear()`

Na proxima renderizacao, sao atualizados:

- concurso alvo;
- data do sorteio;
- premio estimado;
- acumulou.

## Arquivos alterados

- `app.py`
- `exports/CARD_CONCURSO_PREMIO_PUBLICO.md`

## Nao alterado

- PIX
- Motor Elite
- Logica estatistica
- Valor da cobranca

## Validacao

- Compilacao Python: aprovada com `.venv\Scripts\python.exe -m py_compile app.py`.
- App em localhost: HTTP 200 OK em `http://localhost:8501`.
- Interface publica validada via AppTest Streamlit sem excecoes.
- Card publico validado:
  - campo `Concurso alvo`;
  - campo `Premio estimado`;
  - campo `Data do sorteio`;
  - texto de confianca.
- Botao PIX validado com texto dinamico:
  - `Gerar numeros da sorte para o concurso ...`
- Em fallback local, sem retorno oficial da Caixa durante o teste, o fluxo exibe `concurso oficial` em vez de numero fixo.
- Confirmado que nao foi inserido concurso fixo no codigo.
