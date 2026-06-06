# CORRECAO CONCURSO ALVO PREVISAO 3015

Data: 2026-06-06

## Objetivo

Corrigir a origem do concurso alvo da previsao para usar o proximo concurso oficial informado pela CAIXA, evitando gerar previsoes apenas com base em `ultimo_concurso_base + 1`.

## Fonte Oficial Validada

- API CAIXA: `https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena`
- Proximo concurso oficial: 3015
- Data provavel: 06/06/2026
- Premio estimado: R$ 32.000.000,00
- Ultimo concurso retornado pela CAIXA: 3014

## Base Historica Local

- Arquivo: `dados/mega_sena_historico.csv`
- Ultimo concurso carregado na base local: 3012
- Regra mantida: a base historica pode permanecer em 3012 enquanto o concurso alvo da previsao usa o proximo oficial da CAIXA.

## Correcoes Aplicadas

- Criada funcao central `obter_metadados_concurso_alvo_previsao(df)`.
- Criada funcao auxiliar `obter_concurso_alvo_previsao(df)`.
- Prioridade implementada:
  1. Proximo concurso oficial carregado da CAIXA.
  2. Valor exibido no card `Proximo concurso`.
  3. Fallback `ultimo_concurso_base + 1`.
- Card `Proximo concurso` passou a usar os mesmos metadados centralizados.
- Secao de previsao passou a usar o concurso alvo oficial.
- Relatorio Markdown passou a registrar:
  - Concurso alvo: 3015
  - Ultimo concurso da base: 3012
  - Data provavel: 06/06/2026
  - Premio estimado: R$ 32.000.000,00
- Exportacoes passaram a usar nomes com o concurso alvo.
- Justificativa estatistica foi ajustada para nao afirmar que o alvo e necessariamente o concurso imediatamente posterior ao ultimo da base.

## Arquivos Gerados

- `exports/RELATORIO_PREVISAO_CONCURSO_3015.md`
- `exports/RELATORIO_PREVISAO_CONCURSO_3015.csv`
- `exports/RELATORIO_PREVISAO_CONCURSO_3015.xlsx`
- `exports/RELATORIO_PREVISAO_CONCURSO_3015.pdf`

## Arquivos Alterados

- `app.py`
- `src/gerador_jogos.py`

## Validacao

- `python -m py_compile app.py src/gerador_jogos.py`: aprovado.
- `localhost:8501`: HTTP 200 OK.
- Teste com metadados oficiais simulados:
  - Concurso alvo resolvido: 3015
  - Ultimo concurso da base: 3012
  - Data provavel: 06/06/2026
  - Premio estimado: R$ 32.000.000,00
  - Exportacao gerada com coluna `Concurso alvo` igual a 3015.

## Observacao

Nao foi alterada a logica estatistica do Motor Elite. A mudanca foi restrita a origem e propagacao do concurso alvo da previsao.
