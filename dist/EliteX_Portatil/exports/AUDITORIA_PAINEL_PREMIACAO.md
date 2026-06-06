# Auditoria do Painel de Premiacao

Base utilizada: C:\Users\Leonidas\Documents\New project\MEGA_SENA_ANALYTICS_SITE\dados\mega_sena_historico.csv
Base ate concurso: 3012
Concursos auditados: 2965 a 3012

## Funcao que alimenta os cards
`render_painel_premiacao()` em `app.py`.

## Motivo do Sem auditoria
O painel dependia de `st.session_state.auditoria_elite_9` ou de `exports/auditoria_elite9_1000_100_resumo.csv`. Os arquivos existentes estavam defasados ate 2964 e havia divergencia de nomes de coluna com/sem acento para score de premiacao.

## Arquivos verificados/criados
- `exports/auditoria.csv`
- `exports/historico_backtest.csv`
- `exports/relatorio_premiacao.csv`

## Resultado usado nos cards
    Motor  Base ate concurso  Concursos analisados  Primeiro concurso auditado  Ultimo concurso auditado  Total de jogos  Total de acertos  Media de acertos por jogo  Melhor acerto                 Melhor jogo  Concurso do melhor jogo  Score total premiacao  Score medio premiacao por jogo  Jogos com 2 acertos  Taxa 2 acertos (%)  Jogos com 3 acertos  Taxa 3 acertos (%)  Jogos com 4 acertos  Taxa 4 acertos (%)  Jogos com 5 acertos  Taxa 5 acertos (%)  Jogos com 6 acertos  Taxa 6 acertos (%)                                                      Conclusao painel
Aleatorio               3012                    48                        2965                      3012             960               567                   0.590625              3 16 - 27 - 32 - 39 - 43 - 46                     2973                    143                        0.148958                   98           10.208333                    9              0.9375                    0                 0.0                    0                 0.0                    0                 0.0 Aleatorio venceu no score total de premiacao. Melhor pico: Aleatorio.