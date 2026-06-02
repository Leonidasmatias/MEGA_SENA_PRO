# Mega Sena Analytics

Sistema web em Streamlit para análise estatística da Mega-Sena, visualização da base histórica e geração de jogos com 6 dezenas.

> Aviso: as análises e jogos gerados são estatísticos. Não existe garantia de acerto ou premiação.

## Estrutura do projeto

```text
mega_sena_analytics_site/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── dados/
│   └── mega_sena_historico.csv
├── src/
│   ├── __init__.py
│   ├── carregar_dados.py
│   ├── estatisticas.py
│   ├── gerador_jogos.py
│   └── visualizacoes.py
└── assets/
    └── .gitkeep
```

## Como rodar localmente

1. Instale Python 3.10 ou superior.
2. Entre na pasta do projeto:

```bash
cd mega_sena_analytics_site
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Rode o app:

```bash
streamlit run app.py
```

5. Acesse o endereço exibido no terminal, normalmente:

```text
http://localhost:8501
```

## Como subir no GitHub

1. Crie um repositório no GitHub.
2. Envie todo o conteúdo da pasta `mega_sena_analytics_site`.
3. Garanta que estes arquivos estejam no repositório:

```text
app.py
requirements.txt
README.md
dados/mega_sena_historico.csv
src/
assets/.gitkeep
```

## Como fazer deploy no Streamlit Community Cloud

1. Acesse `https://share.streamlit.io`.
2. Clique em `New app`.
3. Selecione o repositório do GitHub.
4. Em `Main file path`, informe:

```text
app.py
```

5. Confirme o deploy.

O arquivo `dados/mega_sena_historico.csv` já está dentro do projeto e é carregado por caminho relativo, então o deploy não depende de arquivos externos nem de caminhos locais do Windows.

## Formato esperado do CSV

O CSV deve conter as colunas:

```text
Concurso,Data,D1,D2,D3,D4,D5,D6
```

Exemplo:

```csv
Concurso,Data,D1,D2,D3,D4,D5,D6
1,11/03/1996,04,05,30,33,41,52
```
