# MEGA SENA PRO - MOTOR ELITE X: Execucao Local

## Stack detectada

- Linguagem: Python
- Framework principal: Streamlit
- Arquivo principal: `app.py`
- Dados locais: `dados/mega_sena_historico.csv`
- Backend/API separado: nao ha
- Frontend React/Node: nao ha `package.json` neste projeto
- Banco de dados: nao ha banco externo; o sistema usa CSV local
- Variaveis obrigatorias: nenhuma

## Preparar ambiente no Windows

```powershell
cd "C:\Users\Leonidas\Documents\New project\MEGA_SENA_ANALYTICS_SITE"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Caso o comando `python` nao esteja no PATH, use o Python instalado na maquina ou o runtime informado pelo Codex.

## Executar

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```

URL local:

```text
http://localhost:8501
```

Usuario e senha padrao:

```text
Nao ha autenticacao local configurada.
```

## Validacoes recomendadas

```powershell
.\.venv\Scripts\python.exe -m py_compile app.py src\*.py
.\.venv\Scripts\python.exe -c "from src.carregar_dados import carregar_base; print(len(carregar_base()))"
.\.venv\Scripts\python.exe -c "from src.elite_x_fechamento import gerar_fechamento_elite_x; r=gerar_fechamento_elite_x(orcamento=5, valor_aposta_simples=5, quantidade_candidatos=1000); print(r['indicadores'])"
```

## Observacoes

- O diretorio `pages/` nao e obrigatorio porque a navegacao e feita dentro de `app.py` por `st.radio`.
- A atualizacao online da base depende de acesso aos endpoints oficiais da CAIXA; se a rede falhar, o app usa `dados/mega_sena_historico.csv`.
- Os motores estatisticos nao garantem premio; eles apenas organizam e pontuam jogos com base historica.
