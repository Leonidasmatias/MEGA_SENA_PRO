# UX MENU PUBLICO SIMPLIFICADO

Data: 2026-06-06

## Objetivo

Simplificar a interface publica do Mega-Sena Pro para usuario final, ocultando botoes tecnicos e mantendo visivel apenas o CTA principal de previsao.

## Controle implementado

Criada variavel de controle:

```python
MODO_ADMIN = False
```

Tambem foi criada leitura por secrets:

```python
st.secrets.get("MODO_ADMIN", False)
```

## Modo publico

Quando `MODO_ADMIN = False`, a interface mostra:

- Header Mega-Sena Pro.
- Card explicativo simples:
  - `Gere seus numeros para o proximo sorteio da Mega-Sena`
- Selo:
  - `🔥 MAIS ACESSADO`
- Botao principal:
  - `🎯 PREVER PROXIMO SORTEIO`
- Texto abaixo:
  - `Ganhe acesso a previsao do proximo premio de R$ 32 milhoes`
- Fluxo de pagamento PIX.
- Resultado liberado apos pagamento aprovado.

## Botoes ocultos no publico

- Visao Geral
- Resultados
- Motor Elite 9
- Banco Mestre
- Elite X
- Boloes
- Auditorias
- Exportacoes
- Geracao de Jogos
- Atualizar base oficial

## Modo admin

Quando `MODO_ADMIN = True`, o menu tecnico completo volta a ser exibido, incluindo:

- Visao Geral
- Resultados
- Motor Elite 9
- Banco Mestre
- Elite X
- Boloes
- Auditorias
- Exportacoes
- Geracao de Jogos
- Previsao do Proximo Concurso
- Atualizar base oficial

## Arquivos alterados

- `app.py`
- `exports/UX_MENU_PUBLICO_SIMPLIFICADO.md`

## Nao alterado

- PIX
- Motor Elite
- Estatisticas
- Base historica
- Valor da cobranca
- Funcoes tecnicas do codigo

## Validacao

- Compilacao Python: aprovada com `.venv\Scripts\python.exe -m py_compile app.py`.
- App em localhost: HTTP 200 OK em `http://localhost:8501`.
- AppTest modo publico: sem excecoes.
- Botoes visiveis no modo publico:
  - `🎯 PREVER PROXIMO SORTEIO`
  - `💳 Gerar QR Code PIX de R$ 1,00` dentro do fluxo de pagamento.
- Botoes tecnicos confirmados como ocultos:
  - Visao Geral
  - Resultados
  - Motor Elite 9
  - Banco Mestre
  - Elite X
  - Boloes
  - Auditorias
  - Exportacoes
  - Geracao de Jogos
  - Atualizar base oficial
- Card publico validado:
  - `Gere seus numeros para o proximo sorteio da Mega-Sena`
