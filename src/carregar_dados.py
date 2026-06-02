from __future__ import annotations

import json
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import BinaryIO
from unicodedata import normalize
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


CAMINHO_BASE_PADRAO = Path("dados") / "mega_sena_historico.csv"
FONTE_CAIXA_URL = "https://loterias.caixa.gov.br/Paginas/Mega-Sena.aspx"
API_CAIXA_MEGA_SENA_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"
DOWNLOAD_CAIXA_MEGA_SENA_URL = (
    "https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download"
    "?modalidade=MEGA_SENA"
)
COLUNAS_OBRIGATORIAS = ["Concurso", "Data", "D1", "D2", "D3", "D4", "D5", "D6"]
COLUNAS_DEZENAS = ["D1", "D2", "D3", "D4", "D5", "D6"]
ERROS_REDE_CAIXA = (HTTPError, URLError, TimeoutError, OSError, ValueError, ImportError)


def _abrir_url(url: str, timeout: int = 20) -> bytes:
    requisicao = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/html,application/octet-stream,*/*",
            "Referer": FONTE_CAIXA_URL,
        },
    )
    with urlopen(requisicao, timeout=timeout) as resposta:
        return resposta.read()


def _normalizar_texto_coluna(valor: object) -> str:
    texto = normalize("NFKD", str(valor).strip().lower())
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.replace("-", " ").replace("_", " ").replace(".", " ")
    return re.sub(r"\s+", " ", texto).strip()


def _mapear_coluna_oficial(coluna: object) -> str:
    texto = _normalizar_texto_coluna(coluna)
    compacto = texto.replace(" ", "")
    if re.fullmatch(r"d[1-6]", compacto):
        return compacto.upper()

    mapa = {
        "concurso": "Concurso",
        "n concurso": "Concurso",
        "numero concurso": "Concurso",
        "numero do concurso": "Concurso",
        "data": "Data",
        "data sorteio": "Data",
        "data do sorteio": "Data",
    }
    for indice in range(1, 7):
        mapa[f"bola{indice}"] = f"D{indice}"
        mapa[f"bola {indice}"] = f"D{indice}"
        mapa[f"dezena{indice}"] = f"D{indice}"
        mapa[f"dezena {indice}"] = f"D{indice}"
        mapa[f"{indice} dezena"] = f"D{indice}"
        mapa[f"{indice}a dezena"] = f"D{indice}"

    return mapa.get(texto, mapa.get(compacto, str(coluna).strip()))


def _ler_tabela_download_caixa(conteudo: bytes) -> pd.DataFrame:
    if zipfile.is_zipfile(BytesIO(conteudo)):
        with zipfile.ZipFile(BytesIO(conteudo)) as arquivo_zip:
            nomes = arquivo_zip.namelist()
            if "xl/workbook.xml" in nomes:
                return pd.read_excel(BytesIO(conteudo))
            candidatos = [
                nome
                for nome in nomes
                if Path(nome).suffix.lower() in {".csv", ".xlsx", ".xls", ".htm", ".html"}
            ]
            if not candidatos:
                raise ValueError("Download oficial da CAIXA sem CSV, Excel ou HTML.")
            conteudo = arquivo_zip.read(candidatos[0])

    try:
        return pd.read_excel(BytesIO(conteudo))
    except Exception:
        pass

    try:
        return pd.read_csv(BytesIO(conteudo), sep=None, engine="python", encoding="utf-8-sig")
    except Exception:
        pass

    try:
        return pd.read_csv(BytesIO(conteudo), sep=None, engine="python", encoding="latin1")
    except Exception:
        pass

    tabelas = pd.read_html(BytesIO(conteudo))
    if not tabelas:
        raise ValueError("Nenhuma tabela encontrada no download oficial da CAIXA.")
    return max(tabelas, key=len)


def _normalizar_base_oficial(df: pd.DataFrame) -> pd.DataFrame:
    dados = df.copy()
    dados.columns = [_mapear_coluna_oficial(coluna) for coluna in dados.columns]
    return validar_base(dados)


def _baixar_base_por_download() -> pd.DataFrame:
    _abrir_url(FONTE_CAIXA_URL)
    conteudo = _abrir_url(DOWNLOAD_CAIXA_MEGA_SENA_URL)
    return _normalizar_base_oficial(_ler_tabela_download_caixa(conteudo))


def _baixar_json_caixa(url: str) -> dict:
    return json.loads(_abrir_url(url).decode("utf-8-sig"))


def _baixar_base_por_api() -> pd.DataFrame:
    _abrir_url(FONTE_CAIXA_URL)
    ultimo = _baixar_json_caixa(API_CAIXA_MEGA_SENA_URL)
    ultimo_concurso = int(ultimo["numero"])
    registros = []

    for concurso in range(1, ultimo_concurso + 1):
        resultado = _baixar_json_caixa(f"{API_CAIXA_MEGA_SENA_URL}/{concurso}")
        dezenas = resultado.get("listaDezenas") or resultado.get("dezenasSorteadasOrdemSorteio")
        if not dezenas or len(dezenas) < 6:
            continue
        registros.append(
            {
                "Concurso": resultado["numero"],
                "Data": resultado["dataApuracao"],
                "D1": dezenas[0],
                "D2": dezenas[1],
                "D3": dezenas[2],
                "D4": dezenas[3],
                "D5": dezenas[4],
                "D6": dezenas[5],
            }
        )

    if not registros:
        raise ValueError("Nenhum resultado oficial foi retornado pela CAIXA.")
    return validar_base(pd.DataFrame(registros))


def _baixar_base_oficial_sem_fallback() -> pd.DataFrame:
    try:
        return _baixar_base_por_download()
    except ERROS_REDE_CAIXA:
        return _baixar_base_por_api()


def baixar_base_oficial_caixa() -> pd.DataFrame:
    try:
        return _baixar_base_oficial_sem_fallback()
    except ERROS_REDE_CAIXA:
        return carregar_base(CAMINHO_BASE_PADRAO)


def atualizar_base_local() -> bool:
    try:
        dados = _baixar_base_oficial_sem_fallback()
    except ERROS_REDE_CAIXA:
        return False

    CAMINHO_BASE_PADRAO.parent.mkdir(parents=True, exist_ok=True)
    dados.to_csv(CAMINHO_BASE_PADRAO, index=False, encoding="utf-8-sig")
    return True


def validar_base(df: pd.DataFrame) -> pd.DataFrame:
    dados = df.copy()
    dados.columns = [str(coluna).strip() for coluna in dados.columns]

    faltantes = [coluna for coluna in COLUNAS_OBRIGATORIAS if coluna not in dados.columns]
    if faltantes:
        raise ValueError(f"Colunas obrigatorias ausentes: {', '.join(faltantes)}")

    dados = dados[COLUNAS_OBRIGATORIAS].copy()
    dados["Concurso"] = pd.to_numeric(dados["Concurso"], errors="coerce")
    dados["Data"] = pd.to_datetime(dados["Data"], errors="coerce", dayfirst=True)

    for coluna in COLUNAS_DEZENAS:
        dados[coluna] = pd.to_numeric(dados[coluna], errors="coerce")

    dados = dados.dropna(subset=COLUNAS_OBRIGATORIAS).copy()
    dados["Concurso"] = dados["Concurso"].astype(int)
    for coluna in COLUNAS_DEZENAS:
        dados[coluna] = dados[coluna].astype(int)

    fora_intervalo = ~dados[COLUNAS_DEZENAS].apply(
        lambda linha: linha.between(1, 60).all(),
        axis=1,
    )
    if fora_intervalo.any():
        raise ValueError("A base contem dezenas fora do intervalo de 1 a 60.")

    repetidas = dados[COLUNAS_DEZENAS].apply(lambda linha: len(set(linha)) != 6, axis=1)
    if repetidas.any():
        raise ValueError("A base contem concursos com dezenas repetidas.")

    dados = dados.drop_duplicates("Concurso", keep="last")
    dados = dados.sort_values("Concurso", ascending=False).reset_index(drop=True)
    dados["Data"] = dados["Data"].dt.strftime("%d/%m/%Y")
    return dados


def carregar_base(caminho: str | Path = CAMINHO_BASE_PADRAO) -> pd.DataFrame:
    arquivo = Path(caminho)
    if not arquivo.exists():
        raise FileNotFoundError(str(arquivo))

    return validar_base(pd.read_csv(arquivo, dtype=str))


def carregar_upload(arquivo: BinaryIO) -> pd.DataFrame:
    return validar_base(pd.read_csv(arquivo, dtype=str))
