from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
import random

import pandas as pd
import streamlit as st

from src.carregar_dados import (
    CAMINHO_BASE_PADRAO,
    COLUNAS_DEZENAS,
    FONTE_CAIXA_URL,
    atualizar_base_local,
    buscar_info_concurso_atual,
    carregar_base,
    carregar_upload,
    validar_base,
)
from src.estatisticas import (
    dezenas_atrasadas,
    dezenas_mais_sorteadas_ultimos_concursos,
    dezenas_mais_sorteadas,
    dezenas_menos_sorteadas_ultimos_concursos,
    dezenas_menos_sorteadas,
    estatistica_pares_impares,
    estatistica_soma_dezenas,
    padrao_jogo,
    resumo_base,
)
from src.gerador_jogos import gerar_jogo
from src.gerador_jogos import (
    analisar_atraso,
    analisar_frequencia_geral,
    analisar_regularidade,
    backtest_motor_elite_7_completo,
    calcular_score_dezenas,
    exportar_resultados_backtest,
    gerar_motor_elite_7,
    gerar_previsao_concurso_alvo,
    gerar_ranking_melhores_jogos,
    gerar_varios_jogos_inteligentes,
    score_jogo,
    validar_motor_elite_7,
)
from src.elite8_cobertura import gerar_portfolio_elite8
from src.elite9_motor import gerar_portfolio_elite9
from src.auditoria_elite9 import executar_auditoria_elite9
from src.auditoria_elite9_banco_mestre import executar_banco_mestre_elite9
from src.elite_x_fechamento import exportar_fechamento_csv, gerar_fechamento_elite_x
from src.elite_x_pro import (
    aprendizado_historico,
    backtest_elite_x_pro,
    banco_mestre_inteligente,
    correlacao_dezenas,
    dashboard_melhores_jogos,
    gerar_bolao_profissional,
    gerar_ranking_elite_x_pro,
    simular_jogo_unico_20_dezenas,
)
from src.visualizacoes import grafico_frequencia


st.set_page_config(
    page_title="Mega-Sena Pro",
    page_icon="MS",
    layout="wide",
)

SECOES_APP = [
    "Visão Geral",
    "Resultados",
    "Motor Elite 9",
    "Banco Mestre",
    "Elite X",
    "Bolões",
    "Auditorias",
    "Exportações",
    "Geração de Jogos",
    "Previsão do Próximo Concurso",
]

PASTAS_BASE_HISTORICA = ("dados", "exports")
EXTENSOES_BASE_HISTORICA = {".csv", ".xlsx", ".xls"}


def inicializar_estado() -> None:
    padroes = {
        "aba_ativa": "Visão Geral",
        "jogos_gerados": pd.DataFrame(),
        "score_elite": 0.0,
        "relatorio_atual": "",
        "base_carregada": None,
        "mensagens": [],
        "erro_atual": "",
        "sucesso_atual": "",
    }
    for chave, valor in padroes.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor


def registrar_mensagem(tipo: str, texto: str) -> None:
    mensagem = {
        "tipo": tipo,
        "texto": texto,
        "horario": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }
    mensagens = st.session_state.get("mensagens", [])
    mensagens.append(mensagem)
    st.session_state.mensagens = mensagens[-20:]
    if tipo == "success":
        st.session_state.sucesso_atual = texto
        st.session_state.erro_atual = ""
    elif tipo == "error":
        st.session_state.erro_atual = texto
        st.session_state.sucesso_atual = ""


def render_mensagens_estado() -> None:
    if st.session_state.get("sucesso_atual"):
        st.success(st.session_state.sucesso_atual)
    if st.session_state.get("erro_atual"):
        st.error(st.session_state.erro_atual)


def atualizar_estado_base(df: pd.DataFrame, origem: str) -> None:
    st.session_state.base_carregada = {
        "origem": origem,
        "concursos": int(len(df)),
        "ultimo_concurso": _ultimo_concurso(df),
        "atualizada_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }


def atualizar_estado_jogos(dados: pd.DataFrame, score: float | int | None, relatorio: str) -> None:
    st.session_state.jogos_gerados = dados if isinstance(dados, pd.DataFrame) else pd.DataFrame()
    st.session_state.score_elite = round(float(score or 0.0), 2)
    st.session_state.relatorio_atual = relatorio


def aplicar_css_institucional() -> None:
    st.markdown(
        """
        <style>
        :root {
            --caixa-blue: #005ca9;
            --caixa-blue-dark: #003f7d;
            --mega-green: #209869;
            --mega-green-dark: #147447;
            --surface: #ffffff;
            --soft-bg: #f3f6f8;
            --text-main: #1f2937;
            --muted: #64748b;
        }
        .stApp { background: linear-gradient(180deg, #f7fafc 0%, #eef3f7 100%); color: var(--text-main); }
        .block-container { padding-top: 1.2rem; max-width: 1320px; }
        .mega-hero {
            background: linear-gradient(135deg, var(--caixa-blue) 0%, #0074bf 48%, var(--mega-green) 100%);
            border-radius: 18px; padding: 28px 34px; color: white;
            box-shadow: 0 18px 40px rgba(0, 92, 169, 0.22); margin-bottom: 18px;
        }
            <div class="mega-breadcrumb">Início &rsaquo; Produtos &rsaquo; Loterias &rsaquo; Mega-Sena Pro</div>
        .mega-title { font-size: 44px; line-height: 1.05; font-weight: 850; margin: 0; }
            <div class="mega-subtitle">Sistema inteligente de análise, geração e gestão de jogos</div>
        .mega-menu { display: flex; gap: 10px; flex-wrap: wrap; margin: 10px 0 18px 0; }
        .mega-pill {
            background: #ffffff; color: var(--caixa-blue); border: 1px solid #d8e5ee;
            border-radius: 999px; padding: 9px 15px; font-weight: 800;
            box-shadow: 0 5px 14px rgba(15, 23, 42, .06);
        }
        .mega-card {
            background: var(--surface); border: 1px solid #e3eaf0; border-radius: 14px;
            padding: 18px; box-shadow: 0 8px 24px rgba(15, 23, 42, .07); min-height: 112px;
        }
        .mega-card-label { color: var(--muted); font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: .04em; }
        .mega-card-value { color: var(--caixa-blue-dark); font-size: 25px; font-weight: 850; margin-top: 8px; }
        .mega-card-caption { color: var(--muted); font-size: 12px; margin-top: 4px; }
        .mega-panel {
            background: #ffffff; border-left: 6px solid var(--mega-green); border-radius: 14px;
            padding: 18px; box-shadow: 0 8px 24px rgba(15, 23, 42, .07); margin: 16px 0 20px 0;
        }
        .mega-panel-title { font-size: 18px; font-weight: 850; color: var(--caixa-blue-dark); margin-bottom: 10px; }
        .mega-prize-grid { display: grid; grid-template-columns: repeat(5, minmax(120px, 1fr)); gap: 12px; }
        .mega-prize-item { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; }
        .mega-prize-label { color: var(--muted); font-size: 12px; font-weight: 800; }
        .mega-prize-value { color: var(--mega-green-dark); font-size: 20px; font-weight: 850; margin-top: 5px; }
        .mega-balls-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin: 10px 0 6px; }
        .mega-ball {
            width: 56px; height: 56px; border-radius: 50%;
            background: radial-gradient(circle at 32% 28%, #35c98d 0%, var(--mega-green) 58%, var(--mega-green-dark) 100%);
            color: #fff; display: inline-flex; align-items: center; justify-content: center;
            font-size: 21px; font-weight: 850;
            box-shadow: inset 0 2px 5px rgba(255,255,255,.28), 0 8px 18px rgba(32,152,105,.24);
        }
        div.stButton > button, div.stDownloadButton > button {
            background: linear-gradient(135deg, var(--caixa-blue) 0%, var(--mega-green) 100%);
            color: white; border: 0; border-radius: 10px; font-weight: 800;
            box-shadow: 0 8px 18px rgba(0, 92, 169, .18);
        }
        div.stButton > button:hover, div.stDownloadButton > button:hover { color: white; filter: brightness(1.04); border: 0; }
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px;
            padding: 8px; box-shadow: 0 8px 24px rgba(15, 23, 42, .05);
        }
        .stTabs [data-baseweb="tab"] { border-radius: 10px; padding: 10px 12px; font-weight: 750; }
        .stTabs [aria-selected="true"] { background: #e8f6ef; color: var(--mega-green-dark); }
        div[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; }
        @media (max-width: 860px) {
            .mega-title { font-size: 32px; }
            .mega-prize-grid { grid-template-columns: repeat(2, 1fr); }
            .mega-ball { width: 46px; height: 46px; font-size: 18px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def corrigir_interface_visual() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ui-blue-900: #003f7d;
            --ui-blue-700: #005ca9;
            --ui-blue-100: #d8eafa;
            --ui-green-700: #147447;
            --ui-green-100: #e8f6ef;
            --ui-text: #172033;
        }

        div.stButton > button,
        div.stDownloadButton > button,
        div[data-testid="stLinkButton"] a,
        button[kind="secondary"],
        button[kind="primary"] {
            background: #ffffff !important;
            color: var(--ui-blue-900) !important;
            border: 1.5px solid var(--ui-blue-100) !important;
            border-radius: 10px !important;
            min-height: 42px !important;
            font-weight: 850 !important;
            font-size: 15px !important;
            opacity: 1 !important;
            box-shadow: 0 6px 16px rgba(0, 63, 125, .10) !important;
        }

        div.stButton > button *,
        div.stDownloadButton > button *,
        div[data-testid="stLinkButton"] a *,
        button[kind="secondary"] *,
        button[kind="primary"] * {
            color: var(--ui-blue-900) !important;
            opacity: 1 !important;
        }

        div.stButton > button:hover,
        div.stDownloadButton > button:hover,
        div[data-testid="stLinkButton"] a:hover,
        button[kind="secondary"]:hover,
        button[kind="primary"]:hover {
            background: var(--ui-green-100) !important;
            color: var(--ui-green-700) !important;
            border-color: var(--ui-green-700) !important;
            box-shadow: 0 8px 20px rgba(20, 116, 71, .16) !important;
        }

        .stRadio div[role="radiogroup"] {
            gap: 8px !important;
            align-items: stretch !important;
            background: #ffffff !important;
            border: 1.5px solid var(--ui-blue-100) !important;
            border-radius: 14px !important;
            padding: 10px !important;
            box-shadow: 0 8px 24px rgba(15, 23, 42, .05) !important;
        }

        .stRadio div[role="radiogroup"] > label {
            background: #ffffff !important;
            border: 1.5px solid var(--ui-blue-100) !important;
            border-radius: 10px !important;
            padding: 11px 14px !important;
            min-height: 46px !important;
            opacity: 1 !important;
            box-shadow: 0 5px 14px rgba(15, 23, 42, .06) !important;
        }

        .stRadio div[role="radiogroup"] > label:hover {
            background: #edf7ff !important;
            border-color: var(--ui-blue-700) !important;
        }

        .stRadio div[role="radiogroup"] > label:has(input:checked) {
            background: linear-gradient(135deg, var(--ui-green-100), #edf7ff) !important;
            border-color: var(--ui-green-700) !important;
            box-shadow: inset 0 0 0 1px rgba(20, 116, 71, .20), 0 8px 18px rgba(0, 92, 169, .12) !important;
        }

        .stRadio div[role="radiogroup"] label,
        .stRadio div[role="radiogroup"] label span,
        .stRadio div[role="radiogroup"] label div,
        .stRadio div[role="radiogroup"] label p {
            color: var(--ui-blue-900) !important;
            font-size: 16px !important;
            font-weight: 850 !important;
            opacity: 1 !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            background: #ffffff !important;
            border: 1.5px solid var(--ui-blue-100) !important;
        }

        .stTabs [data-baseweb="tab"] {
            color: var(--ui-blue-900) !important;
            font-size: 15px !important;
            font-weight: 850 !important;
            opacity: 1 !important;
        }

        .stTabs [aria-selected="true"] {
            background: var(--ui-green-100) !important;
            color: var(--ui-green-700) !important;
            border: 1px solid rgba(20, 116, 71, .35) !important;
        }

        .mega-pill {
            color: var(--ui-blue-900) !important;
            border-color: var(--ui-blue-100) !important;
            opacity: 1 !important;
            font-size: 14px !important;
            background: #ffffff !important;
        }

        label,
        label span,
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] span {
            color: var(--ui-text) !important;
            opacity: 1 !important;
            font-weight: 750 !important;
        }

        .mega-alert {
            border-radius: 14px !important;
            padding: 18px 22px !important;
            margin: 12px 0 16px 0 !important;
            font-size: 16px !important;
            line-height: 1.48 !important;
            box-shadow: 0 10px 26px rgba(15, 23, 42, .10) !important;
            color: #1F2937 !important;
        }

        .mega-alert strong,
        .mega-alert span {
            color: inherit !important;
        }

        .mega-alert-warning {
            background: linear-gradient(135deg, #FFF7D6 0%, #FFE9A8 100%) !important;
            border-left: 7px solid #F59E0B !important;
            font-weight: 600 !important;
        }

        .mega-alert-success {
            background: linear-gradient(135deg, #DCFCE7 0%, #BBF7D0 100%) !important;
            border-left: 7px solid #16A34A !important;
            color: #065F46 !important;
            font-weight: 700 !important;
        }

        .mega-alert-icon {
            display: inline-block;
            margin-right: 9px;
            font-size: 18px;
            line-height: 1;
            vertical-align: -1px;
        }

        @media (max-width: 900px) {
            .stRadio div[role="radiogroup"] {
                flex-direction: column !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_alerta_premium(tipo: str, texto: str) -> None:
    if tipo == "success":
        classe = "mega-alert-success"
        icone = "✅"
    else:
        classe = "mega-alert-warning"
        icone = "⚠️"
    st.markdown(
        f"""
        <div class="mega-alert {classe}">
            <span class="mega-alert-icon">{icone}</span>{texto}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_topo_institucional() -> None:
    st.markdown(
        """
        <div class="mega-hero">
            <div class="mega-breadcrumb">Início &rsaquo; Produtos &rsaquo; Loterias &rsaquo; Mega-Sena Pro</div>
            <h1 class="mega-title">Mega-Sena Pro</h1>
            <div class="mega-subtitle">Sistema inteligente de análise, geração e gestão de jogos</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_menu_visual() -> None:
    st.markdown('<div class="mega-menu-toolbar">', unsafe_allow_html=True)
    for inicio in range(0, len(SECOES_APP), 5):
        linha = SECOES_APP[inicio : inicio + 5]
        colunas = st.columns(len(linha))
        for coluna, secao in zip(colunas, linha):
            ativo = secao == st.session_state.get("aba_ativa", SECOES_APP[0])
            label = f"• {secao}" if ativo else secao
            if coluna.button(label, key=f"menu_secao_{secao}", use_container_width=True):
                st.session_state.aba_ativa = secao
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_secao_ativa() -> str:
    secao = st.session_state.get("aba_ativa", SECOES_APP[0])
    if secao not in SECOES_APP:
        secao = SECOES_APP[0]
        st.session_state.aba_ativa = secao
    st.caption(f"Seção ativa: {secao}")
    return secao


def render_card_resumo(label: str, valor: str, legenda: str = "") -> None:
    st.markdown(
        f"""
        <div class="mega-card">
            <div class="mega-card-label">{label}</div>
            <div class="mega-card-value">{valor}</div>
            <div class="mega-card-caption">{legenda}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def dezenas_html(dezenas: list[int] | tuple[int, ...] | set[int]) -> str:
    bolas = "".join(f'<span class="mega-ball">{int(dezena):02d}</span>' for dezena in sorted(dezenas))
    return f'<div class="mega-balls-row">{bolas}</div>'


def render_card_dezenas(label: str, dezenas: list[int] | tuple[int, ...] | set[int], legenda: str = "") -> None:
    st.markdown(
        f"""
        <div class="mega-card">
            <div class="mega-card-label">{label}</div>
            {dezenas_html(dezenas)}
            <div class="mega-card-caption">{legenda}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mostrar_jogo(dezenas: list[int]) -> None:
    st.markdown(dezenas_html(dezenas), unsafe_allow_html=True)


def _formatar_moeda(valor: object) -> str:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return "N/D"
    return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pegar_valor(dados: dict, *chaves: str, padrao: object = 0.0) -> object:
    for chave in chaves:
        if chave in dados:
            return dados[chave]
    return padrao


@st.cache_data(ttl=1800)
def obter_info_caixa_cached() -> dict:
    info = buscar_info_concurso_atual()
    return info if isinstance(info, dict) else {}


def _parse_dezenas_texto(valor: object) -> list[int]:
    partes = str(valor).replace(",", "-").split("-")
    dezenas = []
    for parte in partes:
        texto = parte.strip()
        if texto.isdigit():
            dezenas.append(int(texto))
    return sorted(dezenas)


def _normalizar_jogos_para_sessao(dados: pd.DataFrame, motor: str) -> pd.DataFrame:
    if dados is None or dados.empty:
        return pd.DataFrame()
    linhas = []
    for _, linha in dados.iterrows():
        texto_jogo = linha.get("Jogo", linha.get("Dezenas", ""))
        dezenas = _parse_dezenas_texto(texto_jogo)
        if len(dezenas) != 6:
            continue
        score = linha.get("Score Final", linha.get("Score final", linha.get("Score Elite", linha.get("Score cobertura", linha.get("Score", 0.0)))))
        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 0.0
        linhas.append(
            {
                "Motor": motor,
                "Jogo": " - ".join(f"{dezena:02d}" for dezena in dezenas),
                "Score": round(max(0.0, min(100.0, score)), 2),
                "Soma": sum(dezenas),
                "Pares": sum(dezena % 2 == 0 for dezena in dezenas),
                "Criado em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            }
        )
    return pd.DataFrame(linhas)


def registrar_jogos_sessao(dados: pd.DataFrame, motor: str) -> None:
    novos = _normalizar_jogos_para_sessao(dados, motor)
    if novos.empty:
        return
    atual = st.session_state.get("top_jogos_sessao", pd.DataFrame())
    combinado = pd.concat([atual, novos], ignore_index=True) if isinstance(atual, pd.DataFrame) else novos
    combinado = combinado.drop_duplicates(["Motor", "Jogo"], keep="last")
    st.session_state.top_jogos_sessao = combinado.sort_values("Score", ascending=False).head(1000).reset_index(drop=True)


def registrar_log_execucao(motor: str, concurso: int | None, score: float | int | None) -> None:
    registro = {
        "Horario": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Concurso utilizado": concurso or "",
        "Motor utilizado": motor,
        "Score gerado": round(float(score or 0.0), 4),
    }
    logs = st.session_state.get("log_execucao", [])
    logs.append(registro)
    st.session_state.log_execucao = logs[-500:]

    caminho = Path("exports") / "log_execucao_elite_x.csv"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df_log = pd.DataFrame([registro])
    df_log.to_csv(caminho, mode="a", header=not caminho.exists(), index=False, encoding="utf-8-sig")


def elite_score_sessao() -> float:
    scores = []
    top_sessao = st.session_state.get("top_jogos_sessao")
    if isinstance(top_sessao, pd.DataFrame) and not top_sessao.empty and "Score" in top_sessao.columns:
        scores.extend(top_sessao["Score"].astype(float).tolist())

    for chave in (
        "motor_elite_9",
        "motor_elite_x",
        "elite_x_pro_ranking",
        "elite_x_fechamento",
        "ranking_melhores_jogos",
        "banco_mestre_pro",
    ):
        valor = st.session_state.get(chave)
        if isinstance(valor, pd.DataFrame) and not valor.empty:
            coluna = next(
                (
                    item
                    for item in (
                        "Score Neural Elite X",
                        "Score Mestre",
                        "Score Final",
                        "Score final",
                        "Score Elite",
                        "Score cobertura",
                        "Score",
                    )
                    if item in valor.columns
                ),
                None,
            )
            if coluna:
                scores.append(float(valor[coluna].astype(float).max()))
        elif isinstance(valor, dict):
            indicadores = valor.get("indicadores", {})
            if isinstance(indicadores, dict):
                scores.append(float(indicadores.get("Score final", 0.0)))
    if not scores:
        return 0.0
    return round(max(0.0, min(100.0, max(scores))), 2)


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "dados") -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return buffer.getvalue()


def dataframe_to_pdf_bytes(df: pd.DataFrame, titulo: str) -> bytes:
    linhas = [titulo, "=" * len(titulo)]
    if df.empty:
        linhas.append("Sem dados para exportar.")
    else:
        linhas.extend(df.head(80).astype(str).to_string(index=False).splitlines())
    texto = "\n".join(linhas).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 9 Tf 36 800 Td 11 TL ({texto.replace(chr(10), ') Tj T* (')}) Tj ET"
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
        f"<< /Length {len(stream.encode('latin-1', errors='replace'))} >>\nstream\n{stream}\nendstream".encode("latin-1", errors="replace"),
    ]
    conteudo = bytearray(b"%PDF-1.4\n")
    offsets = []
    for indice, objeto in enumerate(objetos, start=1):
        offsets.append(len(conteudo))
        conteudo.extend(f"{indice} 0 obj\n".encode())
        conteudo.extend(objeto)
        conteudo.extend(b"\nendobj\n")
    xref = len(conteudo)
    conteudo.extend(f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        conteudo.extend(f"{offset:010d} 00000 n \n".encode())
    conteudo.extend(f"trailer << /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(conteudo)


def _candidatos_base_historica() -> list[Path]:
    candidatos = []
    raiz = Path(__file__).resolve().parent
    for pasta_nome in PASTAS_BASE_HISTORICA:
        pasta = raiz / pasta_nome
        if not pasta.exists():
            continue
        for arquivo in pasta.rglob("*"):
            if not arquivo.is_file() or arquivo.suffix.lower() not in EXTENSOES_BASE_HISTORICA:
                continue
            nome = arquivo.name.lower()
            if "historico" not in nome and "histórico" not in nome:
                continue
            candidatos.append(arquivo)
    if CAMINHO_BASE_PADRAO.exists() and CAMINHO_BASE_PADRAO not in candidatos:
        candidatos.append(CAMINHO_BASE_PADRAO)
    return candidatos


def _carregar_base_candidata(caminho: Path) -> pd.DataFrame:
    if caminho.suffix.lower() == ".csv":
        bruto = pd.read_csv(caminho, dtype=str)
    else:
        bruto = pd.read_excel(caminho, dtype=str)
    return validar_base(bruto)


def validar_base_historica_atual() -> dict:
    melhor: dict | None = None
    erros = []
    for caminho in _candidatos_base_historica():
        try:
            dados = _carregar_base_candidata(caminho)
        except Exception as erro:
            erros.append(f"{caminho}: {erro}")
            continue
        if dados.empty:
            continue
        ultimo = dados.sort_values("Concurso", ascending=False).iloc[0]
        info = {
            "caminho": str(caminho.resolve()),
            "total_concursos": int(len(dados)),
            "ultimo_concurso": int(ultimo["Concurso"]),
            "data_ultimo_concurso": str(ultimo["Data"]),
            "status": "Base ativa mais recente encontrada",
            "dataframe": dados,
            "modificado_em": caminho.stat().st_mtime,
        }
        if melhor is None:
            melhor = info
            continue
        if (info["ultimo_concurso"], info["total_concursos"], info["modificado_em"]) > (
            melhor["ultimo_concurso"],
            melhor["total_concursos"],
            melhor["modificado_em"],
        ):
            melhor = info

    if melhor is None:
        return {
            "caminho": str(CAMINHO_BASE_PADRAO.resolve()),
            "total_concursos": 0,
            "ultimo_concurso": None,
            "data_ultimo_concurso": "N/D",
            "status": "Nenhuma base histórica válida encontrada",
            "erros": erros,
            "dataframe": pd.DataFrame(),
        }

    melhor["erros"] = erros
    return melhor


def obter_dados() -> pd.DataFrame | None:
    upload = st.file_uploader(
        "Upload CSV",
        type=["csv"],
        key="upload_csv_base",
        help="Use colunas: Concurso, Data, D1, D2, D3, D4, D5, D6.",
    )

    try:
        if upload is not None:
            df_upload = carregar_upload(upload)
            st.session_state.base_upload_temporaria = df_upload
            atualizar_estado_base(df_upload, f"Upload CSV temporário: {upload.name}")
            registrar_mensagem("success", "Upload CSV carregado como base temporária da sessão.")
            st.session_state.base_historica_atual = {
                "caminho": f"upload://{upload.name}",
                "total_concursos": int(len(df_upload)),
                "ultimo_concurso": _ultimo_concurso(df_upload),
                "data_ultimo_concurso": str(df_upload.sort_values("Concurso", ascending=False).iloc[0]["Data"]),
                "status": "Upload CSV em uso nesta sessão",
            }
            return df_upload
        info_base = validar_base_historica_atual()
        df_local = info_base.get("dataframe")
        if not isinstance(df_local, pd.DataFrame) or df_local.empty:
            df_local = carregar_base(CAMINHO_BASE_PADRAO)
            info_base.update(
                {
                    "total_concursos": int(len(df_local)),
                    "ultimo_concurso": _ultimo_concurso(df_local),
                    "data_ultimo_concurso": str(df_local.sort_values("Concurso", ascending=False).iloc[0]["Data"]),
                    "status": "Fallback para base padrão",
                }
            )
        st.session_state.base_historica_atual = {chave: valor for chave, valor in info_base.items() if chave != "dataframe"}
        atualizar_estado_base(df_local, f"Base ativa: {info_base.get('caminho', CAMINHO_BASE_PADRAO)}")
        return df_local
    except FileNotFoundError:
        mensagem = "Arquivo dados/mega_sena_historico.csv não encontrado. Inclua a base histórica no projeto antes do deploy."
        registrar_mensagem("error", mensagem)
        st.error(mensagem)
    except Exception as erro:
        mensagem = f"Não foi possível carregar a base histórica: {erro}"
        registrar_mensagem("error", mensagem)
        st.error(mensagem)
    return None


def _ler_resumo_auditoria(caminho: str) -> pd.DataFrame:
    arquivo = Path(caminho)
    if not arquivo.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(arquivo)
    except Exception:
        return pd.DataFrame()


def _melhor_motor_disponivel() -> tuple[str, str]:
    top_sessao = st.session_state.get("top_jogos_sessao")
    if isinstance(top_sessao, pd.DataFrame) and not top_sessao.empty and "Score" in top_sessao.columns:
        melhor = top_sessao.sort_values("Score", ascending=False).iloc[0]
        return str(melhor.get("Motor", "Motor Elite")), f"{float(melhor.get('Score', 0.0)):.2f}"

    log_execucao = st.session_state.get("log_execucao", [])
    if log_execucao:
        logs_validos = [item for item in log_execucao if float(item.get("Score gerado") or 0.0) > 0]
        if logs_validos:
            melhor_log = max(logs_validos, key=lambda item: float(item.get("Score gerado") or 0.0))
            return str(melhor_log.get("Motor utilizado", "Motor Elite")), f"{float(melhor_log.get('Score gerado', 0.0)):.2f}"

    auditoria = st.session_state.get("auditoria_elite_9")
    if isinstance(auditoria, dict):
        resumo = auditoria.get("resumo", pd.DataFrame())
        if isinstance(resumo, pd.DataFrame) and not resumo.empty and "Score médio premiação por jogo" in resumo.columns:
            melhor = resumo.loc[resumo["Score médio premiação por jogo"].astype(float).idxmax()]
            return str(melhor.get("Motor", "Auditoria Elite 9")), f"{float(melhor.get('Score médio premiação por jogo', 0.0)):.2f}"

    backtest = st.session_state.get("backtest_elite_x_pro")
    if isinstance(backtest, dict):
        melhor = backtest.get("melhor", {})
        if isinstance(melhor, dict) and melhor:
            return str(melhor.get("Motor", "Elite X PRO")), str(melhor.get("Score", melhor.get("Score_medio", "N/D")))

    candidatos = [
        "exports/auditoria_elite9_1000_100_resumo.csv",
        "exports/auditoria_elite8_comparativa_1000_100_resumo.csv",
        "exports/elite9_banco_mestre_resumo.csv",
    ]
    melhor_motor = "Sem auditoria"
    melhor_score = "N/D"
    for caminho in candidatos:
        resumo_auditoria = _ler_resumo_auditoria(caminho)
        if resumo_auditoria.empty:
            continue
        if "Score total premiação" in resumo_auditoria.columns:
            indice = resumo_auditoria["Score total premiação"].astype(float).idxmax()
            melhor_motor = str(resumo_auditoria.loc[indice, "Motor"])
            melhor_score = f"{float(resumo_auditoria.loc[indice, 'Score total premiação']):,.0f}".replace(",", ".")
            return melhor_motor, melhor_score
        if "Media de acertos por jogo" in resumo_auditoria.columns:
            indice = resumo_auditoria["Media de acertos por jogo"].astype(float).idxmax()
            melhor_motor = str(resumo_auditoria.loc[indice, "Motor"])
            melhor_score = f"{float(resumo_auditoria.loc[indice, 'Media de acertos por jogo']):.5f}"
            return melhor_motor, melhor_score
    return melhor_motor, melhor_score


def _total_jogos_gerados() -> int:
    top_sessao = st.session_state.get("top_jogos_sessao")
    if isinstance(top_sessao, pd.DataFrame) and not top_sessao.empty:
        return int(len(top_sessao))

    total = 0
    for chave in (
        "motor_elite_7",
        "motor_elite_8",
        "motor_elite_9",
        "motor_elite_x",
        "elite_x_pro_ranking",
        "ranking_melhores_jogos",
        "jogos_gerados",
        "previsao_sorteio",
        "banco_mestre_pro",
    ):
        valor = st.session_state.get(chave)
        if isinstance(valor, pd.DataFrame):
            total += int(len(valor))
    fechamento = st.session_state.get("elite_x_fechamento")
    if isinstance(fechamento, dict) and isinstance(fechamento.get("jogos"), pd.DataFrame):
        total += int(len(fechamento["jogos"]))
    for tamanho in (15, 18, 20):
        pacote = st.session_state.get(f"bolao_pro_{tamanho}")
        if isinstance(pacote, dict) and isinstance(pacote.get("jogos"), pd.DataFrame):
            total += int(len(pacote["jogos"]))
    return total


def render_cards_dashboard(df: pd.DataFrame) -> None:
    dados = df.sort_values("Concurso", ascending=False).reset_index(drop=True)
    ultimo = dados.iloc[0]
    dezenas_ultimo = [int(ultimo[coluna]) for coluna in COLUNAS_DEZENAS]
    melhor_motor, melhor_score = _melhor_motor_disponivel()
    col1, col2, col3 = st.columns(3)
    with col1:
        render_card_resumo("Último concurso", str(int(ultimo["Concurso"])), str(ultimo["Data"]))
    with col2:
        render_card_resumo("Próximo prêmio estimado", "Consultar CAIXA", "Valor não disponível na base histórica")
    with col3:
        render_card_resumo("Melhor motor", melhor_motor, "Com base nos relatórios exportados")

    col4, col5, col6 = st.columns(3)
    with col4:
        render_card_dezenas("Dezenas sorteadas", dezenas_ultimo, "Último resultado carregado")
    with col5:
        render_card_resumo("Melhor score", melhor_score, "Score ou média conforme auditoria disponível")
    with col6:
        render_card_resumo("Total de jogos gerados", str(_total_jogos_gerados()), "Nesta sessão do Streamlit")


def render_cards_dashboard_v2(df: pd.DataFrame) -> None:
    dados = df.sort_values("Concurso", ascending=False).reset_index(drop=True)
    ultimo = dados.iloc[0]
    dezenas_ultimo = [int(ultimo[coluna]) for coluna in COLUNAS_DEZENAS]
    melhor_motor, melhor_score = _melhor_motor_disponivel()
    info_caixa = obter_info_caixa_cached() or {}
    proximo = info_caixa.get("proximo_concurso") or (int(ultimo["Concurso"]) + 1)
    premio = _formatar_moeda(info_caixa.get("premio_estimado"))
    acumulou = "Sim" if info_caixa.get("acumulou") else "Não" if info_caixa else "N/D"
    data_proximo = info_caixa.get("data_proximo_concurso") or "Fonte local/indisponivel"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_card_resumo("Último concurso", str(int(ultimo["Concurso"])), str(ultimo["Data"]))
    with col2:
        render_card_resumo("Proximo concurso", str(proximo), str(data_proximo))
    with col3:
        render_card_resumo("Premio estimado", premio, f"Acumulou: {acumulou}")
    with col4:
        render_card_resumo("Melhor motor", melhor_motor, "Relatórios exportados")

    col5, col6, col7 = st.columns(3)
    with col5:
        render_card_dezenas("Dezenas sorteadas", dezenas_ultimo, "Último resultado carregado")
    with col6:
        render_card_resumo("ELITE SCORE", f"{elite_score_sessao():.2f}/100", f"Melhor score: {melhor_score}")
    with col7:
        render_card_resumo("Total de jogos gerados", str(_total_jogos_gerados()), "Sessão atual")


def render_base_historica_status(df: pd.DataFrame) -> None:
    info = st.session_state.get("base_historica_atual", {})
    dados = df.sort_values("Concurso", ascending=False).reset_index(drop=True)
    ultimo = dados.iloc[0] if not dados.empty else {}
    caminho = info.get("caminho", str(CAMINHO_BASE_PADRAO.resolve()))
    total = info.get("total_concursos", len(df))
    ultimo_concurso = info.get("ultimo_concurso", ultimo.get("Concurso", "N/D"))
    data_ultimo = info.get("data_ultimo_concurso", ultimo.get("Data", "N/D"))
    status = info.get("status", "Base carregada")

    st.caption(
        f"Base ativa: {caminho} | "
        f"{total} concursos | "
        f"último concurso {ultimo_concurso} | "
        f"data {data_ultimo} | "
        f"{status}"
    )


def render_painel_premiacao() -> None:
    def coluna_existente(df: pd.DataFrame, *nomes: str) -> str | None:
        mapa = {str(coluna).strip().lower(): coluna for coluna in df.columns}
        for nome in nomes:
            coluna = mapa.get(nome.strip().lower())
            if coluna is not None:
                return str(coluna)
        return None

    def valor_numero(linha: pd.Series, *nomes: str, padrao: float = 0.0) -> float:
        for nome in nomes:
            if nome in linha.index and pd.notna(linha[nome]):
                try:
                    return float(linha[nome])
                except (TypeError, ValueError):
                    return padrao
        return padrao

    def auditoria_valida(df: pd.DataFrame) -> bool:
        if not isinstance(df, pd.DataFrame) or df.empty:
            return False
        return all(
            coluna_existente(df, *nomes) is not None
            for nomes in (
                ("Jogos com 6 acertos", "jogos_com_6_acertos"),
                ("Jogos com 5 acertos", "jogos_com_5_acertos"),
                ("Jogos com 4 acertos", "jogos_com_4_acertos"),
                ("Melhor acerto", "melhor_acerto"),
            )
        ) and coluna_existente(
            df,
            "Score total premiacao",
            "Score total premiação",
            "score_total_premiacao",
            "Score de premiacao",
            "Score de premiação",
        ) is not None

    def carregar_resumo_premiacao() -> pd.DataFrame:
        for caminho in ("exports/relatorio_premiacao.csv", "exports/auditoria.csv"):
            dados = _ler_resumo_auditoria(caminho)
            if auditoria_valida(dados):
                return dados

        historico = _ler_resumo_auditoria("exports/historico_backtest.csv")
        if not isinstance(historico, pd.DataFrame) or historico.empty or "Motor" not in historico.columns:
            return pd.DataFrame()

        linhas = []
        for motor, grupo in historico.groupby("Motor", sort=False):
            total_jogos = int(grupo["Jogos"].astype(float).sum()) if "Jogos" in grupo.columns else int(len(grupo))
            melhor_idx = grupo["Melhor acerto"].astype(float).idxmax() if "Melhor acerto" in grupo.columns else grupo.index[0]
            linha = {
                "Motor": motor,
                "Concursos analisados": int(grupo["Concurso"].nunique()) if "Concurso" in grupo.columns else int(len(grupo)),
                "Total de jogos": total_jogos,
                "Melhor acerto": int(float(grupo.loc[melhor_idx, "Melhor acerto"])) if "Melhor acerto" in grupo.columns else 0,
                "Melhor jogo": grupo.loc[melhor_idx, "Melhor jogo"] if "Melhor jogo" in grupo.columns else "",
                "Concurso do melhor jogo": int(float(grupo.loc[melhor_idx, "Concurso"])) if "Concurso" in grupo.columns else 0,
                "Score total premiacao": float(grupo["Score total premiacao"].astype(float).sum()) if "Score total premiacao" in grupo.columns else 0.0,
            }
            for acertos in (4, 5, 6):
                coluna = f"Jogos com {acertos} acertos"
                linha[coluna] = int(grupo[coluna].astype(float).sum()) if coluna in grupo.columns else 0
            linhas.append(linha)
        return pd.DataFrame(linhas)

    resumo_auditoria = carregar_resumo_premiacao()

    if resumo_auditoria.empty:
        valores = {
            "6 acertos": "Sem auditoria",
            "5 acertos": "Sem auditoria",
            "4 acertos": "Sem auditoria",
            "Score de premiação": "Sem auditoria",
            "Melhor pico": "Sem auditoria",
        }
    else:
        coluna_score = coluna_existente(
            resumo_auditoria,
            "Score total premiacao",
            "Score total premiação",
            "score_total_premiacao",
            "Score de premiacao",
            "Score de premiação",
        )
        if coluna_score is not None:
            melhor = resumo_auditoria.loc[resumo_auditoria[coluna_score].astype(float).idxmax()]
        else:
            melhor = resumo_auditoria.iloc[0]

        score_premiacao = valor_numero(
            melhor,
            "Score total premiacao",
            "Score total premiação",
            "score_total_premiacao",
            "Score de premiacao",
            "Score de premiação",
            padrao=0,
        )
        melhor_acerto = int(valor_numero(melhor, "Melhor acerto", "melhor_acerto", padrao=0))
        concurso_melhor = int(valor_numero(melhor, "Concurso do melhor jogo", "concurso_do_melhor_jogo", padrao=0))
        melhor_pico = f"{melhor_acerto} acertos"
        if concurso_melhor:
            melhor_pico = f"{melhor_pico} - concurso {concurso_melhor}"

        valores = {
            "6 acertos": str(int(valor_numero(melhor, "Jogos com 6 acertos", "jogos_com_6_acertos", padrao=0))),
            "5 acertos": str(int(valor_numero(melhor, "Jogos com 5 acertos", "jogos_com_5_acertos", padrao=0))),
            "4 acertos": str(int(valor_numero(melhor, "Jogos com 4 acertos", "jogos_com_4_acertos", padrao=0))),
            "Score de premiação": f"{float(score_premiacao):,.0f}".replace(",", "."),
            "Melhor pico": melhor_pico,
        }
    itens = "".join(
        f"""
        <div class="mega-prize-item">
            <div class="mega-prize-label">{label}</div>
            <div class="mega-prize-value">{valor}</div>
        </div>
        """
        for label, valor in valores.items()
    )
    st.markdown(
        f"""
        <div class="mega-panel">
            <div class="mega-panel-title">Painel de premiação e desempenho</div>
            <div class="mega-prize-grid">{itens}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_analise_avancada(df: pd.DataFrame) -> None:
    atrasadas = dezenas_atrasadas(df)
    pares_impares = estatistica_pares_impares(df)
    soma_dezenas = estatistica_soma_dezenas(df)
    padrao = padrao_jogo(df)

    st.markdown("### Ranking de dezenas atrasadas")
    st.dataframe(atrasadas.head(20), width="stretch", hide_index=True)

    st.markdown("### Estatística de pares e ímpares")
    col_par, col_impar = st.columns(2)
    media_pares = float(_pegar_valor(padrao, "média de pares", "média de pares"))
    media_impares = float(_pegar_valor(padrao, "média de ímpares", "média de ímpares"))
    col_par.metric("Média de pares por concurso", f"{media_pares:.2f}")
    col_impar.metric("Média de ímpares por concurso", f"{media_impares:.2f}")
    st.dataframe(pares_impares.head(30), width="stretch", hide_index=True)

    st.markdown("### Soma das dezenas")
    col_soma1, col_soma2, col_soma3 = st.columns(3)
    soma_media = float(_pegar_valor(soma_dezenas, "média", "média"))
    soma_minima = _pegar_valor(soma_dezenas, "mínima", "mínima")
    soma_maxima = _pegar_valor(soma_dezenas, "máxima", "máxima")
    col_soma1.metric("Soma média", f"{soma_media:.2f}")
    col_soma2.metric("Soma mínima", soma_minima)
    col_soma3.metric("Soma máxima", soma_maxima)
    st.dataframe(soma_dezenas["por_concurso"].head(30), width="stretch", hide_index=True)

    st.markdown("### Padrão geral de jogo")
    resumo_padrao = pd.DataFrame(
        [
            {
                "Média da soma": round(float(_pegar_valor(padrao, "média da soma", "média da soma")), 2),
                "Média de pares": round(media_pares, 2),
                "Média de ímpares": round(media_impares, 2),
            }
        ]
    )
    st.dataframe(resumo_padrao, width="stretch", hide_index=True)

    col_freq1, col_freq2, col_freq3 = st.columns(3)
    with col_freq1:
        st.caption("Mais frequentes")
        st.dataframe(padrao["dezenas mais frequentes"], width="stretch", hide_index=True)
    with col_freq2:
        st.caption("Menos frequentes")
        st.dataframe(padrao["dezenas menos frequentes"], width="stretch", hide_index=True)
    with col_freq3:
        st.caption("Mais atrasadas")
        st.dataframe(padrao["dezenas mais atrasadas"], width="stretch", hide_index=True)


def render_dezenas_quentes_frias(df: pd.DataFrame) -> None:
    mais_20 = dezenas_mais_sorteadas_ultimos_concursos(
        df,
        quantidade_concursos=20,
        limite=10,
    )
    mais_50 = dezenas_mais_sorteadas_ultimos_concursos(
        df,
        quantidade_concursos=50,
        limite=10,
    )
    menos_50 = dezenas_menos_sorteadas_ultimos_concursos(
        df,
        quantidade_concursos=50,
        limite=10,
    )

    st.markdown("### Top 10 dezenas mais sorteadas nos últimos 20 concursos")
    st.dataframe(mais_20, width="stretch", hide_index=True)

    st.markdown("### Top 10 dezenas mais sorteadas nos últimos 50 concursos")
    st.dataframe(mais_50, width="stretch", hide_index=True)

    st.markdown("### Top 10 dezenas menos sorteadas nos últimos 50 concursos")
    st.dataframe(menos_50, width="stretch", hide_index=True)


def render_gerador_inteligente(df: pd.DataFrame) -> None:
    ranking = calcular_score_dezenas(df)

    st.warning("Este gerador usa estatística histórica e não garante premiação.")
    st.markdown("### Ranking das 20 dezenas com maior score")
    st.dataframe(ranking.head(20), width="stretch", hide_index=True)

    quantidade = st.number_input(
        "Quantidade de jogos",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
    )

    if st.button("Gerar Jogo Inteligente", type="primary"):
        try:
            with st.spinner("Gerando jogos inteligentes."):
                jogos = gerar_varios_jogos_inteligentes(df, quantidade=int(quantidade))
                linhas = []
                for indice, jogo in enumerate(jogos, start=1):
                    pares = sum(dezena % 2 == 0 for dezena in jogo)
                    linhas.append(
                        {
                            "Jogo": indice,
                            "Dezenas": " - ".join(f"{dezena:02d}" for dezena in jogo),
                            "Score": score_jogo(df, jogo),
                            "Soma": sum(jogo),
                            "Pares": pares,
                            "Impares": 6 - pares,
                        }
                    )
                jogos_df = pd.DataFrame(linhas)
                st.session_state.jogos_inteligentes = jogos
                st.session_state.jogos_inteligentes_df = jogos_df
                registrar_jogos_sessao(jogos_df, "Gerador Inteligente")
                score_medio = float(jogos_df["Score"].mean()) if not jogos_df.empty else 0.0
                registrar_log_execucao("Gerador Inteligente", _ultimo_concurso(df), score_medio)
                atualizar_estado_jogos(jogos_df, score_medio, "Jogos inteligentes gerados")
            registrar_mensagem("success", "Geração de Jogos concluída com sucesso.")
            st.success("Jogos gerados com sucesso.")
        except Exception as erro:
            st.session_state.jogos_inteligentes = []
            st.session_state.jogos_inteligentes_df = pd.DataFrame()
            registrar_mensagem("error", f"Falha na geracao de jogos: {erro}")
            st.error(f"Falha na geracao de jogos: {erro}")

    jogos_df = st.session_state.get("jogos_inteligentes_df", pd.DataFrame())
    if isinstance(jogos_df, pd.DataFrame) and not jogos_df.empty:
        st.markdown("### Jogos gerados")
        st.dataframe(jogos_df, width="stretch", hide_index=True)


def render_previsao_sorteio(df: pd.DataFrame) -> None:
    render_alerta_premium(
        "warning",
        "Previsão estatística baseada em frequência, atraso e score histórico. Não garante premiação.",
    )
    quantidade = st.number_input("Quantidade de previsões", min_value=1, max_value=20, value=5, step=1, key="previsao_quantidade")
    janela = st.number_input("Janela histórica da previsão", min_value=20, max_value=max(20, len(df)), value=min(500, len(df)), step=20, key="previsao_janela")

    if st.button("Gerar previsão do sorteio", type="primary"):
        try:
            with st.spinner("Calculando previsão estatística do próximo sorteio."):
                historico = df.sort_values("Concurso", ascending=False).head(int(janela))
                ranking = calcular_score_dezenas(historico)
                jogos = gerar_varios_jogos_inteligentes(historico, quantidade=int(quantidade))
                linhas = []
                for indice, jogo in enumerate(jogos, start=1):
                    linhas.append(
                        {
                            "Previsão": indice,
                            "Jogo": " - ".join(f"{dezena:02d}" for dezena in jogo),
                            "Score estatístico": score_jogo(historico, jogo),
                            "Soma": sum(jogo),
                            "Pares": sum(dezena % 2 == 0 for dezena in jogo),
                            "Janela concursos": int(janela),
                            "Concurso base": _ultimo_concurso(df),
                        }
                    )
                previsao = pd.DataFrame(linhas)
                st.session_state.previsao_sorteio = previsao
                st.session_state.previsao_ranking_dezenas = ranking
                registrar_jogos_sessao(previsao.rename(columns={"Score estatístico": "Score"}), "Previsão do Sorteio")
                score_medio = float(previsao["Score estatístico"].mean()) if not previsao.empty else 0.0
                registrar_log_execucao("Previsão do Sorteio", _ultimo_concurso(df), score_medio)
                atualizar_estado_jogos(previsao, score_medio, "Previsão do Sorteio executada")
            registrar_mensagem("success", "Previsão do Sorteio gerada com sucesso.")
            render_alerta_premium("success", "Previsão do Sorteio gerada com sucesso.")
        except Exception as erro:
            st.session_state.previsao_sorteio = pd.DataFrame()
            registrar_mensagem("error", f"Falha ao gerar previsão do sorteio: {erro}")
            st.error(f"Falha ao gerar previsão do sorteio: {erro}")

    previsao = st.session_state.get("previsao_sorteio", pd.DataFrame())
    ranking = st.session_state.get("previsao_ranking_dezenas", pd.DataFrame())
    if isinstance(previsao, pd.DataFrame) and not previsao.empty:
        st.markdown("### Previsões geradas")
        st.dataframe(previsao, width="stretch", hide_index=True)
        st.download_button("Exportar previsão CSV", previsao.to_csv(index=False).encode("utf-8-sig"), "previsao_sorteio.csv", "text/csv")
        st.download_button("Exportar previsão Excel", dataframe_to_excel_bytes(previsao, "previsao"), "previsao_sorteio.xlsx")
        st.download_button("Exportar previsão PDF", dataframe_to_pdf_bytes(previsao, "PREVISÃO DO SORTEIO"), "previsao_sorteio.pdf", "application/pdf")
    if isinstance(ranking, pd.DataFrame) and not ranking.empty:
        st.markdown("### Ranking de dezenas da previsão")
        st.dataframe(ranking.head(30), width="stretch", hide_index=True)


def render_previsao_concurso_alvo(df: pd.DataFrame) -> None:
    concurso_alvo = _concurso_alvo(df)
    st.session_state.concurso_alvo = concurso_alvo
    info_caixa = obter_info_caixa_cached() or {}
    data_provavel = info_caixa.get("data_proximo_concurso") or "Indisponivel"
    premio_estimado = _formatar_moeda(info_caixa.get("premio_estimado"))

    render_alerta_premium("warning", "Análise estatística. A Mega-Sena é aleatória e nenhum método garante acerto.")
    st.markdown("## PREVISÃO DO PRÓXIMO CONCURSO")
    st.info(f"Gerando previsão para o concurso alvo: {concurso_alvo}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Concurso alvo", concurso_alvo)
    col2.metric("Data provável", data_provavel)
    col3.metric("Prêmio estimado", premio_estimado)

    if st.button("Gerar previsão para concurso alvo", type="primary"):
        try:
            with st.spinner(f"Calculando previsão estatística para o concurso alvo {concurso_alvo}."):
                pacote = gerar_previsao_concurso_alvo(df, concurso_alvo)
                previsao = pacote["exportacao"]
                ranking = pacote["top_20_dezenas"]
                pasta = Path("exports")
                pasta.mkdir(parents=True, exist_ok=True)
                previsao.to_csv(pasta / "previsao_concurso_alvo.csv", index=False, encoding="utf-8-sig")

                relatorio = [
                    "# Relatorio - Previsao Concurso Alvo",
                    "",
                    f"Concurso alvo: {concurso_alvo}",
                    f"Ultimo concurso da base: {pacote['ultimo_concurso']}",
                    f"Data provavel: {data_provavel}",
                    f"Premio estimado: {premio_estimado}",
                    "",
                    "Aviso: Analise estatistica. A Mega-Sena e aleatoria e nenhum metodo garante acerto.",
                    "",
                    "## Jogo principal",
                    pacote["jogo_principal"].to_string(index=False) if not pacote["jogo_principal"].empty else "N/D",
                    "",
                    "## Jogos alternativos",
                    pacote["jogos_alternativos"].to_string(index=False) if not pacote["jogos_alternativos"].empty else "N/D",
                    "",
                    "## Top 20 dezenas",
                    ranking.head(20).to_string(index=False),
                    "",
                    "## Jogo unico de 20 dezenas",
                    pacote["jogo_20_dezenas"].to_string(index=False),
                    "",
                    "## Justificativa estatistica",
                    pacote["justificativa_estatistica"],
                ]
                Path("RELATORIO_PREVISAO_CONCURSO_ALVO.md").write_text("\n".join(relatorio), encoding="utf-8")

                st.session_state.previsao_concurso_alvo = pacote
                st.session_state.previsao_sorteio = previsao
                st.session_state.previsao_ranking_dezenas = ranking
                registrar_jogos_sessao(previsao.rename(columns={"Score Final": "Score"}), "Previsão Concurso Alvo")
                score_medio = float(previsao["Score Final"].astype(float).mean()) if not previsao.empty else 0.0
                registrar_log_execucao("Previsão Concurso Alvo", concurso_alvo, score_medio)
                atualizar_estado_jogos(previsao, score_medio, f"Previsão gerada para concurso alvo {concurso_alvo}")
            registrar_mensagem("success", f"Previsão do concurso alvo {concurso_alvo} gerada com sucesso.")
            render_alerta_premium("success", f"Previsão do concurso alvo {concurso_alvo} gerada com sucesso.")
        except Exception as erro:
            st.session_state.previsao_concurso_alvo = {}
            st.session_state.previsao_sorteio = pd.DataFrame()
            registrar_mensagem("error", f"Falha ao gerar previsão do concurso alvo: {erro}")
            st.error(f"Falha ao gerar previsão do concurso alvo: {erro}")

    pacote = st.session_state.get("previsao_concurso_alvo", {})
    if not isinstance(pacote, dict) or not pacote:
        return

    jogo_principal = pacote.get("jogo_principal", pd.DataFrame())
    jogos_alternativos = pacote.get("jogos_alternativos", pd.DataFrame())
    top_20 = pacote.get("top_20_dezenas", pd.DataFrame())
    jogo_20 = pacote.get("jogo_20_dezenas", pd.DataFrame())
    exportacao = pacote.get("exportacao", pd.DataFrame())

    if isinstance(jogo_principal, pd.DataFrame) and not jogo_principal.empty:
        st.markdown("### Jogo principal recomendado")
        mostrar_jogo(_parse_dezenas_texto(jogo_principal.iloc[0]["Jogo"]))
        st.dataframe(jogo_principal, width="stretch", hide_index=True)

    if isinstance(jogos_alternativos, pd.DataFrame) and not jogos_alternativos.empty:
        st.markdown("### Jogos alternativos")
        st.dataframe(jogos_alternativos, width="stretch", hide_index=True)

    if isinstance(top_20, pd.DataFrame) and not top_20.empty:
        st.markdown("### Top 20 dezenas")
        st.dataframe(top_20.head(20), width="stretch", hide_index=True)

    if isinstance(jogo_20, pd.DataFrame) and not jogo_20.empty:
        st.markdown("### Jogo de cobertura com 20 dezenas")
        mostrar_jogo(pacote.get("jogo_20_dezenas_lista", []))
        st.dataframe(jogo_20, width="stretch", hide_index=True)

    if isinstance(exportacao, pd.DataFrame) and not exportacao.empty:
        st.download_button(
            "Exportar previsão concurso alvo CSV",
            exportacao.to_csv(index=False).encode("utf-8-sig"),
            "previsao_concurso_alvo.csv",
            "text/csv",
        )
        st.download_button(
            "Exportar previsão concurso alvo Excel",
            dataframe_to_excel_bytes(exportacao, "previsao_alvo"),
            "previsao_concurso_alvo.xlsx",
        )
        st.download_button(
            "Exportar previsão concurso alvo PDF",
            dataframe_to_pdf_bytes(exportacao, "PREVISAO CONCURSO ALVO"),
            "previsao_concurso_alvo.pdf",
            "application/pdf",
        )


def render_backtest_historico(df: pd.DataFrame) -> None:
    st.warning("Backtest histórico não garante resultado futuro.")
    total_disponivel = int(len(df))
    quantidade = st.selectbox("Quantidade de concursos", options=[10, 50, 100, 300], index=1)
    candidatos = st.selectbox("Candidatos por concurso", options=[500, 1000, 3000, 5000], index=1)
    top = st.selectbox("Top por concurso", options=[5, 10, 20, 50], index=2)

    if total_disponivel < int(quantidade):
        st.warning("Base possui poucos concursos para esta validação.")

    if st.button("Executar Backtest Motor Elite 7", type="primary"):
        try:
            with st.spinner("Executando backtest completo do Motor Elite 7."):
                st.session_state.backtest_motor_elite_7 = backtest_motor_elite_7_completo(
                    df,
                    quantidade_concursos=int(quantidade),
                    quantidade_candidatos=int(candidatos),
                    top=int(top),
                )
            resultado = st.session_state.backtest_motor_elite_7
            detalhes = resultado.get("detalhes", pd.DataFrame()) if isinstance(resultado, dict) else pd.DataFrame()
            score = float(resultado.get("resumo", {}).get("melhor_resultado", 0)) if isinstance(resultado, dict) else 0.0
            atualizar_estado_jogos(detalhes, score, "Backtest histórico executado")
            registrar_mensagem("success", "Backtest histórico concluído com sucesso.")
            st.success("Backtest concluído com sucesso.")
        except Exception as erro:
            st.session_state.backtest_motor_elite_7 = None
            registrar_mensagem("error", f"Falha ao executar backtest: {erro}")
            st.error(f"Falha ao executar backtest: {erro}")

    resultado = st.session_state.get("backtest_motor_elite_7")
    if not resultado:
        return

    resumo = resultado["resumo"]
    col_base1, col_base2, col_base3 = st.columns(3)
    col_base1.metric("Concursos disponíveis", total_disponivel)
    col_base2.metric("Concursos analisados", resumo["concursos_analisados"])
    col_base3.metric("Jogos simulados", resumo["total_jogos"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Melhor resultado", f"{resumo['melhor_resultado']} acertos")
    col2.metric("Jogos 2+", resumo["jogos_2_mais"])
    col3.metric("Jogos 3+", resumo["jogos_3_mais"])

    col4, col5, col6, col7, col8 = st.columns(5)
    col4.metric("Taxa 2", f"{resumo['taxa_2']:.2f}%")
    col5.metric("Taxa 3", f"{resumo['taxa_3']:.2f}%")
    col6.metric("Taxa 4", f"{resumo['taxa_4']:.2f}%")
    col7.metric("Taxa 5", f"{resumo['taxa_5']:.2f}%")
    col8.metric("Taxa 6", f"{resumo['taxa_6']:.2f}%")

    detalhes = resultado.get("detalhes", pd.DataFrame())
    if isinstance(detalhes, pd.DataFrame) and not detalhes.empty:
        st.markdown("### Resultados por jogo")
        st.dataframe(detalhes, width="stretch", hide_index=True)
        st.download_button(
            "Exportar resultados CSV",
            data=exportar_resultados_backtest(resultado),
            file_name="backtest_motor_elite_7.csv",
            mime="text/csv",
        )


def render_ranking_melhores_jogos(df: pd.DataFrame) -> None:
    st.warning("Ranking estatístico não garante premiação.")
    quantidade_candidatos = st.selectbox(
        "Quantidade de candidatos",
        options=[100, 500, 1000],
        index=1,
    )
    top = st.selectbox(
        "Top",
        options=[5, 10, 20],
        index=1,
    )

    if st.button("Gerar Ranking", type="primary"):
        modulo_gerador = __import__("src.gerador_jogos", fromlist=["gerar_ranking_melhores_jogos"])
        st.session_state.ranking_melhores_jogos = modulo_gerador.gerar_ranking_melhores_jogos(
            df,
            quantidade_candidatos=int(quantidade_candidatos),
            top=int(top),
        )
        registrar_jogos_sessao(st.session_state.ranking_melhores_jogos, "Ranking dos Melhores Jogos")
        score_medio = float(st.session_state.ranking_melhores_jogos["Score Final"].mean()) if not st.session_state.ranking_melhores_jogos.empty else 0.0
        registrar_log_execucao("Ranking dos Melhores Jogos", _ultimo_concurso(df), score_medio)

    ranking = st.session_state.get("ranking_melhores_jogos")
    if ranking is not None and not ranking.empty:
        melhor_jogo = ranking.iloc[0]
        score_melhor = float(melhor_jogo.get("Score", melhor_jogo.get("Score Final", 0.0)))
        classificacao = melhor_jogo.get("Classificação", melhor_jogo.get("Classificacao", "Sem classificação"))
        st.metric(
            "Melhor jogo",
            melhor_jogo["Jogo"],
            f"Score {score_melhor:.2f} - {classificacao}",
        )
        st.dataframe(ranking, width="stretch", hide_index=True)
        st.download_button(
            "Baixar CSV",
            data=ranking.to_csv(index=False).encode("utf-8-sig"),
            file_name="ranking_melhores_jogos.csv",
            mime="text/csv",
        )

    st.divider()
    st.markdown("### Validação Histórica do Ranking")
    st.warning("Quanto maior a quantidade de candidatos e o Top, mais demorado será o processamento.")
    validação_concursos = st.selectbox(
        "Quantidade de concursos",
        options=[10, 50, 100, 300, 500],
        index=2,
        key="validação_ranking_concursos",
    )
    validação_candidatos = st.selectbox(
        "Quantidade de candidatos",
        options=[100, 500, 1000, 3000, 5000],
        index=1,
        key="validação_ranking_candidatos",
    )
    validação_top = st.selectbox(
        "Top",
        options=[5, 10, 20, 30, 50],
        index=1,
        key="validação_ranking_top",
    )

    if st.button("Validar Ranking Histórico", key="validar_ranking_historico"):
        modulo_gerador = __import__("src.gerador_jogos", fromlist=["validar_ranking_historico"])
        st.session_state.validacao_ranking_historico = modulo_gerador.validar_ranking_historico(
            df,
            quantidade_concursos=int(validação_concursos),
            quantidade_candidatos=int(validação_candidatos),
            top=int(validação_top),
        )

    validacao = st.session_state.get("validacao_ranking_historico")
    if validacao is not None:
        col1, col2, col3 = st.columns(3)
        col1.metric("Concursos analisados", validacao["concursos_analisados"])
        col2.metric("Total de jogos", validacao["total_jogos"])
        col3.metric("Melhor resultado", f"{validacao['melhor_resultado']} acertos")

        col4, col5 = st.columns(2)
        col4.metric("Jogos com 3+ acertos", validacao["jogos_3_mais"])
        col5.metric("Jogos com 4+ acertos", validacao["jogos_4_mais"])

        col6, col7 = st.columns(2)
        col6.metric("Taxa 3+ %", f"{validacao['taxa_3_mais']:.2f}%")
        col7.metric("Taxa 4+ %", f"{validacao['taxa_4_mais']:.2f}%")

        col8, col9, col10 = st.columns(3)
        col8.metric("Candidatos por concurso", validacao["quantidade_candidatos"])
        col9.metric("Top analisado", validacao["top"])
        col10.metric("Jogos por concurso", validacao["jogos_por_concurso"])
        col11, col12 = st.columns(2)
        col11.metric("Média Score Diversidade", f"{validacao.get('media_score_diversidade', 0.0):.2f}")
        col12.metric("Média Distância", f"{validacao.get('media_distancia', 0.0):.2f}")
        st.info(validacao["observacao"])


def render_correlacao_historica(df: pd.DataFrame) -> None:
    modulo_estatisticas = __import__(
        "src.estatisticas",
        fromlist=["pares_mais_frequentes", "trincas_mais_frequentes", "mapa_correlacao_dezenas"],
    )

    st.markdown("### Top 20 pares mais frequentes")
    st.dataframe(modulo_estatisticas.pares_mais_frequentes(df, limite=20), width="stretch", hide_index=True)

    st.markdown("### Top 20 trincas mais frequentes")
    st.dataframe(modulo_estatisticas.trincas_mais_frequentes(df, limite=20), width="stretch", hide_index=True)

    st.markdown("### Correlação entre dezenas")
    st.dataframe(modulo_estatisticas.mapa_correlacao_dezenas(df), width="stretch", hide_index=True)


def render_aprendizado_historico(df: pd.DataFrame) -> None:
    st.warning("Análise histórica identifica padrões passados e não garante resultados futuros.")

    if st.button("Analisar Padrões", type="primary"):
        modulo_gerador = __import__("src.gerador_jogos", fromlist=["analisar_padroes_vencedores"])
        st.session_state.aprendizado_historico = modulo_gerador.analisar_padroes_vencedores(df)

    aprendizado = st.session_state.get("aprendizado_historico")
    if aprendizado is None:
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Jogos analisados", aprendizado["jogos_analisados"])
    col2.metric("Soma média", f"{aprendizado['media_soma']:.2f}")
    col3.metric("Score médio", f"{aprendizado['media_score_final']:.2f}")

    col4, col5 = st.columns(2)
    col4.metric("Pares médios", f"{aprendizado['media_pares']:.2f}")
    col5.metric("Ímpares médios", f"{aprendizado['media_impares']:.2f}")

    st.markdown("### Distribuição média por faixa")
    faixas = pd.DataFrame(
        [
            {"Faixa": faixa, "Média": media}
            for faixa, media in aprendizado["faixas_medias"].items()
        ]
    )
    st.dataframe(faixas, width="stretch", hide_index=True)


def render_motor_elite_7(df: pd.DataFrame) -> None:
    st.warning("Processamento pesado. Use com cautela.")
    candidatos = st.selectbox(
        "Candidatos",
        options=[500, 1000, 5000, 10000, 50000],
        index=2,
        key="motor_elite_candidatos",
    )
    top = st.selectbox(
        "Top",
        options=[10, 20, 50, 100],
        index=2,
        key="motor_elite_top",
    )

    if st.button("Gerar jogos Motor Elite 7", type="primary"):
        try:
            with st.spinner("Gerando Motor Elite 7. Este processamento pode demorar."):
                st.session_state.motor_elite_7 = gerar_motor_elite_7(
                    df,
                    quantidade_candidatos=int(candidatos),
                    top=int(top),
                )
            registrar_jogos_sessao(st.session_state.motor_elite_7, "Motor Elite 7")
            registrar_log_execucao("Motor Elite 7", _ultimo_concurso(df), float(st.session_state.motor_elite_7["Score Final"].mean()) if not st.session_state.motor_elite_7.empty else 0.0)
            st.success("Jogos gerados com sucesso.")
        except Exception as erro:
            st.session_state.motor_elite_7 = None
            st.error(f"Falha ao gerar Motor Elite 7: {erro}")

    ranking = st.session_state.get("motor_elite_7")
    if ranking is not None and not ranking.empty:
        st.markdown("### Ranking dos jogos")
        st.dataframe(ranking, width="stretch", hide_index=True)
        st.download_button(
            "Exportar CSV Motor Elite 7",
            data=ranking.to_csv(index=False).encode("utf-8-sig"),
            file_name="motor_elite_7.csv",
            mime="text/csv",
        )

    st.divider()
    st.markdown("### Validação Elite")
    validação_concursos = st.selectbox(
        "Concursos",
        options=[10, 50, 100],
        index=0,
        key="validação_elite_concursos",
    )
    validação_candidatos = st.selectbox(
        "Candidatos",
        options=[10000, 50000],
        index=0,
        key="validação_elite_candidatos",
    )
    validação_top = st.selectbox(
        "Top",
        options=[10, 20, 50],
        index=0,
        key="validação_elite_top",
    )

    if st.button("Validar Motor Elite 7", key="validar_motor_elite"):
        try:
            with st.spinner("Validando Motor Elite 7. Este processamento pode demorar."):
                st.session_state.validação_motor_elite_7 = validar_motor_elite_7(
                    df,
                    quantidade_concursos=int(validação_concursos),
                    quantidade_candidatos=int(validação_candidatos),
                    top=int(validação_top),
                )
            st.success("Validação concluída com sucesso.")
        except Exception as erro:
            st.session_state.validação_motor_elite_7 = None
            st.error(f"Falha ao validar Motor Elite 7: {erro}")

    resultado = st.session_state.get("validação_motor_elite_7")
    if resultado is not None:
        col1, col2, col3 = st.columns(3)
        col1.metric("Melhor resultado", f"{resultado['melhor_resultado']} acertos")
        col2.metric("Jogos 3+", resultado["jogos_3_mais"])
        col3.metric("Jogos 4+", resultado["jogos_4_mais"])

        col4, col5 = st.columns(2)
        col4.metric("Jogos 5+", resultado["jogos_5_mais"])
        col5.metric("Jogos 6", resultado["jogos_6"])

        col6, col7, col8, col9 = st.columns(4)
        col6.metric("Taxa 3+", f"{resultado['taxa_3_mais']:.2f}%")
        col7.metric("Taxa 4+", f"{resultado['taxa_4_mais']:.2f}%")
        col8.metric("Taxa 5+", f"{resultado['taxa_5_mais']:.2f}%")
        col9.metric("Taxa 6", f"{resultado['taxa_6']:.2f}%")


def render_motor_elite_8() -> None:
    st.warning(
        "O Motor Elite 8 não tenta prever dezenas. "
        "Ele monta portfolios com cobertura matematica e baixa redundancia."
    )
    candidatos = st.selectbox(
        "Candidatos Monte Carlo",
        options=[10000, 50000, 100000],
        index=2,
        key="elite8_candidatos",
    )
    top_intermediario = st.selectbox(
        "Top intermediário",
        options=[500, 1000, 2000],
        index=1,
        key="elite8_top_intermediario",
    )

    if st.button("Gerar Portfolio Elite 8", type="primary"):
        try:
            with st.spinner("Gerando portfolio Elite 8 por cobertura."):
                st.session_state.motor_elite_8 = gerar_portfolio_elite8(
                    quantidade_candidatos=int(candidatos),
                    top_intermediario=int(top_intermediario),
                    top_filtrado=100,
                    top_final=20,
                    seed=8,
                )
            registrar_jogos_sessao(st.session_state.motor_elite_8, "Motor Elite 8")
            registrar_log_execucao("Motor Elite 8", _ultimo_concurso(carregar_base(CAMINHO_BASE_PADRAO)), float(st.session_state.motor_elite_8["Score"].mean()) if not st.session_state.motor_elite_8.empty else 0.0)
            st.success("Portfolio Elite 8 gerado com sucesso.")
        except Exception as erro:
            st.session_state.motor_elite_8 = None
            st.error(f"Falha ao gerar Motor Elite 8: {erro}")

    portfolio = st.session_state.get("motor_elite_8")
    if portfolio is not None and not portfolio.empty:
        st.markdown("### Top 20 jogos")
        st.dataframe(portfolio, width="stretch", hide_index=True)
        metricas = portfolio.iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Cobertura dezenas", f"{metricas['Cobertura dezenas']}/60")
        col2.metric("Cobertura pares", int(metricas["Cobertura pares"]))
        col3.metric("Cobertura somas", int(metricas["Cobertura somas"]))
        col4.metric("Cobertura padroes", int(metricas["Cobertura padroes"]))
        st.download_button(
            "Exportar CSV Elite 8",
            data=portfolio.to_csv(index=False).encode("utf-8-sig"),
            file_name="motor_elite_8_portfolio.csv",
            mime="text/csv",
        )


def render_motor_elite_9(df: pd.DataFrame) -> None:
    st.warning(
        "O Motor Elite 9 busca pico de premiação. "
        "Ele prioriza jogos com potencial de 4, 5 e 6 acertos, não a maior média geral."
    )
    col_a, col_b, col_c = st.columns(3)
    candidatos = col_a.number_input("Candidatos", min_value=1000, max_value=300000, value=20000, step=1000)
    geracoes = col_b.number_input("Geracoes", min_value=1, max_value=100, value=8, step=1)
    populacao = col_c.number_input("Populacao genetica", min_value=50, max_value=2000, value=200, step=50)
    col_d, col_e, col_f = st.columns(3)
    taxa_mutacao = col_d.slider("Taxa de mutacao", min_value=0.01, max_value=0.50, value=0.12, step=0.01)
    quantidade_final = col_e.number_input("Quantidade final", min_value=1, max_value=100, value=20, step=1)
    janela = col_f.number_input("Janela histórica", min_value=100, max_value=2000, value=1000, step=100)

    if st.button("Gerar Jogos Elite 9", type="primary"):
        try:
            with st.spinner("Gerando portfolio Elite 9 com Monte Carlo adaptativo e genetico."):
                st.session_state.motor_elite_9 = gerar_portfolio_elite9(
                    df,
                    quantidade_candidatos=int(candidatos),
                    geracoes=int(geracoes),
                    tamanho_populacao=int(populacao),
                    taxa_mutacao=float(taxa_mutacao),
                    quantidade_final=int(quantidade_final),
                    janela_historico=int(janela),
            )
            registrar_jogos_sessao(st.session_state.motor_elite_9, "Motor Elite 9")
            score_medio = float(st.session_state.motor_elite_9["Score final"].mean()) if not st.session_state.motor_elite_9.empty else 0.0
            registrar_log_execucao("Motor Elite 9", _ultimo_concurso(df), score_medio)
            atualizar_estado_jogos(st.session_state.motor_elite_9, score_medio, "Motor Elite 9 executado")
            registrar_mensagem("success", "Motor Elite 9 gerou jogos com sucesso.")
            st.success("Jogos Elite 9 gerados com sucesso.")
        except Exception as erro:
            st.session_state.motor_elite_9 = None
            registrar_mensagem("error", f"Falha ao gerar Elite 9: {erro}")
            st.error(f"Falha ao gerar Elite 9: {erro}")

    portfolio = st.session_state.get("motor_elite_9")
    if portfolio is not None and not portfolio.empty:
        st.markdown("### Top jogos Elite 9")
        st.dataframe(portfolio, width="stretch", hide_index=True)
        st.download_button(
            "Exportar CSV Elite 9",
            data=portfolio.to_csv(index=False).encode("utf-8-sig"),
            file_name="motor_elite_9.csv",
            mime="text/csv",
        )


def render_auditoria_elite_9() -> None:
    st.warning("Auditoria pesada. Para 1000 concursos com Elite 7/8/9, o processamento pode demorar bastante.")
    col_a, col_b, col_c = st.columns(3)
    concursos = col_a.number_input("Concursos", min_value=1, max_value=1000, value=50, step=10)
    jogos = col_b.number_input("Jogos por concurso", min_value=10, max_value=100, value=100, step=10)
    candidatos = col_c.number_input("Candidatos Elite 9", min_value=1000, max_value=300000, value=5000, step=1000)
    col_d, col_e, col_f = st.columns(3)
    geracoes = col_d.number_input("Geracoes Elite 9", min_value=1, max_value=100, value=4, step=1)
    populacao = col_e.number_input("Populacao Elite 9", min_value=50, max_value=1000, value=100, step=50)
    taxa = col_f.slider("Taxa mutacao Elite 9", min_value=0.01, max_value=0.50, value=0.12, step=0.01)
    incluir_elite7 = st.checkbox("Incluir Motor Elite 7", value=True)
    incluir_elite8 = st.checkbox("Incluir Motor Elite 8", value=True)

    if st.button("Executar Auditoria Elite 9", type="primary"):
        try:
            with st.spinner("Executando auditoria Elite 9."):
                st.session_state.auditoria_elite_9 = executar_auditoria_elite9(
                    quantidade_concursos=int(concursos),
                    jogos_por_concurso=int(jogos),
                    candidatos_elite9=int(candidatos),
                    geracoes_elite9=int(geracoes),
                    populacao_elite9=int(populacao),
                    taxa_mutacao_elite9=float(taxa),
                    incluir_elite7=bool(incluir_elite7),
                    incluir_elite8=bool(incluir_elite8),
                    log_progresso=False,
                )
            resultado = st.session_state.auditoria_elite_9
            resumo = resultado.get("resumo", pd.DataFrame()) if isinstance(resultado, dict) else pd.DataFrame()
            score = float(resumo["Score médio premiação por jogo"].mean()) if isinstance(resumo, pd.DataFrame) and not resumo.empty and "Score médio premiação por jogo" in resumo.columns else 0.0
            atualizar_estado_jogos(resumo, score, "Auditoria Elite 9/backtest executado")
            registrar_mensagem("success", "Auditoria Elite 9 concluída.")
            st.success("Auditoria Elite 9 concluída.")
        except Exception as erro:
            st.session_state.auditoria_elite_9 = None
            registrar_mensagem("error", f"Falha na auditoria Elite 9: {erro}")
            st.error(f"Falha na auditoria Elite 9: {erro}")

    resultado = st.session_state.get("auditoria_elite_9")
    if resultado:
        resumo_auditoria = resultado["resumo"]
        detalhes_auditoria = resultado["detalhes"]
        st.markdown("### Tabela comparativa")
        st.dataframe(resumo_auditoria, width="stretch", hide_index=True)
        if not resumo_auditoria.empty:
            st.bar_chart(resumo_auditoria.set_index("Motor")["Score médio premiação por jogo"])
            conclusoes = resumo_auditoria.iloc[0]
            st.info(
                f"{conclusoes['Conclusão média']} "
                f"{conclusoes['Conclusão pico']} "
                f"{conclusoes['Conclusão premiação']}"
            )
        st.download_button(
            "Exportar CSV resumo",
            data=resumo_auditoria.to_csv(index=False).encode("utf-8-sig"),
            file_name="auditoria_elite9_resumo.csv",
            mime="text/csv",
        )
        st.download_button(
            "Exportar CSV detalhado",
            data=detalhes_auditoria.to_csv(index=False).encode("utf-8-sig"),
            file_name="auditoria_elite9_detalhada.csv",
            mime="text/csv",
        )


def render_banco_mestre_elite_9() -> None:
    st.warning("Executa Top 20, Top 25 e Top 30 dezenas Elite 9 contra bancos aleatorios equivalentes.")
    if st.button("Executar Banco Mestre Elite 9", type="primary"):
        try:
            with st.spinner("Executando Banco Mestre Elite 9."):
                st.session_state.banco_mestre_elite_9 = executar_banco_mestre_elite9()
            resultado = st.session_state.banco_mestre_elite_9
            resumo = resultado.get("resumo", pd.DataFrame()) if isinstance(resultado, dict) else pd.DataFrame()
            score = float(resumo["Media de cobertura (%)"].mean()) if isinstance(resumo, pd.DataFrame) and not resumo.empty and "Media de cobertura (%)" in resumo.columns else 0.0
            atualizar_estado_jogos(resumo, score, "Banco Mestre Elite 9 executado")
            registrar_mensagem("success", "Banco Mestre Elite 9 concluido.")
            st.success("Banco Mestre Elite 9 concluido.")
        except Exception as erro:
            st.session_state.banco_mestre_elite_9 = None
            registrar_mensagem("error", f"Falha no Banco Mestre Elite 9: {erro}")
            st.error(f"Falha no Banco Mestre Elite 9: {erro}")

    resultado = st.session_state.get("banco_mestre_elite_9")
    if not resultado:
        return

    resumo_banco = resultado["resumo"]
    detalhes_banco = resultado["detalhes"]
    st.markdown("### Tabela comparativa")
    st.dataframe(resumo_banco, width="stretch", hide_index=True)
    if not resumo_banco.empty:
        melhor = resumo_banco.loc[resumo_banco["Melhor acerto"].astype(int).idxmax()]
        st.markdown("### Melhor banco encontrado")
        st.write(
            f"{melhor['Motor']} | {int(melhor['Tamanho banco'])} dezenas | "
            f"{int(melhor['Melhor acerto'])} acertos no concurso {int(melhor['Melhor concurso'])}"
        )
        st.code(str(melhor["Melhor banco"]))
        st.markdown("### Cobertura média")
        grafico = resumo_banco.pivot_table(
            index="Tamanho banco",
            columns="Motor",
            values="Media de cobertura (%)",
            aggfunc="first",
        )
        st.bar_chart(grafico)
        st.info(str(melhor["Conclusão automática"]))
    st.download_button(
        "Exportar CSV resumo",
        data=resumo_banco.to_csv(index=False).encode("utf-8-sig"),
        file_name="elite9_banco_mestre_resumo.csv",
        mime="text/csv",
    )
    st.download_button(
        "Exportar CSV detalhado",
        data=detalhes_banco.to_csv(index=False).encode("utf-8-sig"),
        file_name="elite9_banco_mestre_detalhado.csv",
        mime="text/csv",
    )


def _ultimo_concurso(df: pd.DataFrame) -> int:
    return int(df["Concurso"].astype(int).max()) if df is not None and not df.empty else 0


def _concurso_alvo(df: pd.DataFrame) -> int:
    return _ultimo_concurso(df) + 1


def render_top_1000_sessao() -> None:
    ranking = st.session_state.get("top_jogos_sessao", pd.DataFrame())
    st.markdown("### TOP 1000 JOGOS DA SESSAO")
    if not isinstance(ranking, pd.DataFrame) or ranking.empty:
        st.info("Nenhum jogo ranqueado nesta sessao ainda.")
        return
    ranking = ranking.sort_values("Score", ascending=False).head(1000).reset_index(drop=True)
    ranking.insert(0, "Posicao", range(1, len(ranking) + 1))
    st.dataframe(ranking, width="stretch", hide_index=True)
    st.download_button("Exportar Top 1000 CSV", ranking.to_csv(index=False).encode("utf-8-sig"), "top_1000_jogos_sessao.csv", "text/csv")
    st.download_button("Exportar Top 1000 Excel", dataframe_to_excel_bytes(ranking, "top_1000"), "top_1000_jogos_sessao.xlsx")
    st.download_button("Exportar Top 1000 PDF", dataframe_to_pdf_bytes(ranking, "TOP 1000 JOGOS DA SESSAO"), "top_1000_jogos_sessao.pdf", "application/pdf")


def executar_bolao_profissional(df: pd.DataFrame, tamanho: int, quantidade: int) -> None:
    try:
        with st.spinner(f"Gerando bolão profissional de {tamanho} dezenas."):
            pacote = gerar_bolao_profissional(df, tamanho, quantidade)
            st.session_state[f"bolao_pro_{tamanho}"] = pacote
            jogos = pacote.get("jogos", pd.DataFrame())
            registrar_jogos_sessao(jogos, f"Bolão PRO {tamanho}")
            coluna_score = "Score Final" if "Score Final" in jogos.columns else "Score"
            score_medio = float(jogos[coluna_score].mean()) if isinstance(jogos, pd.DataFrame) and not jogos.empty and coluna_score in jogos.columns else 0.0
            registrar_log_execucao(f"Bolão PRO {tamanho}", _ultimo_concurso(df), score_medio)
            atualizar_estado_jogos(jogos, score_medio, f"Bolão PRO {tamanho} dezenas gerado")
        registrar_mensagem("success", f"Bolão PRO {tamanho} dezenas gerado com sucesso.")
        st.success(f"Bolão PRO {tamanho} dezenas gerado com sucesso.")
    except Exception as erro:
        st.session_state[f"bolao_pro_{tamanho}"] = {}
        registrar_mensagem("error", f"Falha ao gerar bolão {tamanho} dezenas: {erro}")
        st.error(f"Falha ao gerar bolão {tamanho} dezenas: {erro}")


def render_motor_elite_x(df: pd.DataFrame) -> None:
    st.warning("Motor Elite X experimental: combina ranking estatístico, frequência, atraso, regularidade e repetição histórica.")
    col_a, col_b, col_c = st.columns(3)
    candidatos = col_a.number_input("Candidatos Elite X", min_value=100, max_value=10000, value=1000, step=100, key="elite_x_motor_candidatos")
    top = col_b.number_input("Top final Elite X", min_value=10, max_value=100, value=100, step=10, key="elite_x_motor_top")
    janela = col_c.number_input("Janela de analise", min_value=20, max_value=1000, value=100, step=20, key="elite_x_motor_janela")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("ELITE SCORE", f"{elite_score_sessao():.2f}/100")
    col2.metric("Concurso base", _ultimo_concurso(df))
    col3.metric("Candidatos", int(candidatos))
    col4.metric("Top", int(top))

    if st.button("Gerar MOTOR ELITE X", type="primary"):
        try:
            with st.spinner("Executando previsão estatística do Motor Elite X."):
                historico = df.sort_values("Concurso", ascending=False).head(int(janela))
                ranking = gerar_ranking_melhores_jogos(historico, quantidade_candidatos=int(candidatos), top=int(top))
                st.session_state.motor_elite_x = ranking
                registrar_jogos_sessao(ranking, "Motor Elite X")
                score_medio = float(ranking["Score Final"].mean()) if not ranking.empty else 0.0
                registrar_log_execucao("Motor Elite X", _ultimo_concurso(df), score_medio)
                atualizar_estado_jogos(ranking, score_medio, "Motor Elite X/previsão estatística executado")
            registrar_mensagem("success", "Motor Elite X executou a previsão estatística.")
            st.success("Motor Elite X gerado com sucesso.")
        except Exception as erro:
            st.session_state.motor_elite_x = pd.DataFrame()
            registrar_mensagem("error", f"Falha ao gerar Motor Elite X: {erro}")
            st.error(f"Falha ao gerar Motor Elite X: {erro}")

    ranking = st.session_state.get("motor_elite_x", pd.DataFrame())
    if isinstance(ranking, pd.DataFrame) and not ranking.empty:
        st.markdown("### IA de selecao de dezenas e score final")
        st.dataframe(ranking, width="stretch", hide_index=True)
        st.download_button("Exportar Elite X CSV", ranking.to_csv(index=False).encode("utf-8-sig"), "motor_elite_x.csv", "text/csv")
        st.download_button("Exportar Elite X Excel", dataframe_to_excel_bytes(ranking, "elite_x"), "motor_elite_x.xlsx")
        st.download_button("Exportar Elite X PDF", dataframe_to_pdf_bytes(ranking, "MOTOR ELITE X"), "motor_elite_x.pdf", "application/pdf")

    st.markdown("### Analises do motor")
    aba_freq, aba_atraso, aba_regularidade, aba_repeticao, aba_monte = st.tabs(
        ["Frequência", "Atraso", "Regularidade", "Repetição histórica", "Monte Carlo"]
    )
    with aba_freq:
        st.dataframe(analisar_frequencia_geral(df).head(30), width="stretch", hide_index=True)
    with aba_atraso:
        st.dataframe(analisar_atraso(df).head(30), width="stretch", hide_index=True)
    with aba_regularidade:
        st.dataframe(analisar_regularidade(df).head(30), width="stretch", hide_index=True)
    with aba_repeticao:
        ultimo = df.sort_values("Concurso", ascending=False).iloc[0]
        repeticao = pd.DataFrame(
            [{"Dezena": int(ultimo[coluna]), "Origem": f"Último concurso {int(ultimo['Concurso'])}"} for coluna in COLUNAS_DEZENAS]
        )
        st.dataframe(repeticao, width="stretch", hide_index=True)
    with aba_monte:
        if st.button("Executar simulacao Monte Carlo Elite X"):
            try:
                with st.spinner("Executando Monte Carlo Elite X."):
                    portfolio = gerar_portfolio_elite8(quantidade_candidatos=max(10000, int(candidatos) * 10), top_intermediario=500, top_filtrado=100, top_final=20, seed=random.randint(1, 999999))
                    st.session_state.monte_carlo_elite_x = portfolio
                    registrar_jogos_sessao(portfolio, "Monte Carlo Elite X")
                    score_medio = float(portfolio["Score"].mean()) if not portfolio.empty else 0.0
                    registrar_log_execucao("Monte Carlo Elite X", _ultimo_concurso(df), score_medio)
                    atualizar_estado_jogos(portfolio, score_medio, "Monte Carlo Elite X executado")
                registrar_mensagem("success", "Simulação Monte Carlo Elite X concluída.")
                st.success("Simulação Monte Carlo concluída.")
            except Exception as erro:
                st.session_state.monte_carlo_elite_x = pd.DataFrame()
                registrar_mensagem("error", f"Falha no Monte Carlo Elite X: {erro}")
                st.error(f"Falha no Monte Carlo Elite X: {erro}")
        portfolio = st.session_state.get("monte_carlo_elite_x", pd.DataFrame())
        if isinstance(portfolio, pd.DataFrame) and not portfolio.empty:
            st.dataframe(portfolio, width="stretch", hide_index=True)

    render_top_1000_sessao()


def _render_melhor_jogo_card(titulo: str, linha: object) -> None:
    if linha is None:
        render_card_resumo(titulo, "N/D", "Gere o dashboard PRO")
        return
    try:
        jogo = str(linha.get("Jogo", "N/D"))
        score = float(linha.get("Score Neural Elite X", linha.get("Score Final", linha.get("Score", 0.0))))
        confianca = str(linha.get("Confianca", "N/D"))
    except AttributeError:
        render_card_resumo(titulo, "N/D", "Sem dados")
        return
    render_card_resumo(titulo, jogo, f"Score Neural {score:.2f} | Confianca {confianca}")


def render_elite_x_pro(df: pd.DataFrame) -> None:
    st.warning("Elite X PRO usa estatística histórica, correlação e score neural. Não garante premiação.")

    st.markdown("### Dashboard Elite X PRO")
    top_sessao = st.session_state.get("top_jogos_sessao", pd.DataFrame())
    melhor_sessao = top_sessao.sort_values("Score", ascending=False).iloc[0] if isinstance(top_sessao, pd.DataFrame) and not top_sessao.empty else None

    if st.button("Atualizar dashboard Elite X PRO"):
        try:
            with st.spinner("Calculando melhores jogos históricos do Elite X PRO."):
                st.session_state.dashboard_elite_x_pro = dashboard_melhores_jogos(df, candidatos=1500)
            registrar_mensagem("success", "Dashboard Elite X PRO atualizado.")
            st.success("Dashboard Elite X PRO atualizado.")
        except Exception as erro:
            registrar_mensagem("error", f"Falha ao atualizar dashboard Elite X PRO: {erro}")
            st.error(f"Falha ao atualizar dashboard Elite X PRO: {erro}")

    dashboard = st.session_state.get("dashboard_elite_x_pro", {})
    col1, col2 = st.columns(2)
    with col1:
        _render_melhor_jogo_card("Melhor jogo da sessao", melhor_sessao)
    with col2:
        _render_melhor_jogo_card("Melhor jogo histórico", dashboard.get("Melhor jogo histórico"))
    col3, col4 = st.columns(2)
    with col3:
        _render_melhor_jogo_card("Melhor jogo ultimos 100", dashboard.get("Melhor jogo dos ultimos 100 concursos"))
    with col4:
        _render_melhor_jogo_card("Melhor jogo ultimos 500", dashboard.get("Melhor jogo dos ultimos 500 concursos"))

    st.divider()
    st.markdown("### Motor de inteligencia avancada")
    col_a, col_b, col_c = st.columns(3)
    candidatos = col_a.number_input("Candidatos PRO", min_value=500, max_value=100000, value=20000, step=500, key="elite_x_pro_candidatos")
    top = col_b.number_input("TOP jogos", min_value=100, max_value=1000, value=1000, step=100, key="elite_x_pro_top")
    janela = col_c.number_input("Janela histórica PRO", min_value=100, max_value=2964, value=min(1000, len(df)), step=100, key="elite_x_pro_janela")

    if st.button("Gerar Ranking TOP 1000 Elite X PRO", type="primary"):
        try:
            with st.spinner("Gerando TOP 1000 Elite X PRO."):
                ranking = gerar_ranking_elite_x_pro(
                    df,
                    quantidade_candidatos=int(candidatos),
                    top=int(top),
                    janela=int(janela),
                )
                st.session_state.elite_x_pro_ranking = ranking
                registrar_jogos_sessao(ranking, "Elite X PRO")
                score_medio = float(ranking["Score Neural Elite X"].mean()) if not ranking.empty else 0.0
                registrar_log_execucao("Elite X PRO", _ultimo_concurso(df), score_medio)
                atualizar_estado_jogos(ranking, score_medio, "Elite X PRO executou previsão estatística")
            registrar_mensagem("success", "Ranking Elite X PRO gerado.")
            st.success("Ranking Elite X PRO gerado.")
        except Exception as erro:
            st.session_state.elite_x_pro_ranking = pd.DataFrame()
            registrar_mensagem("error", f"Falha no Elite X PRO: {erro}")
            st.error(f"Falha no Elite X PRO: {erro}")

    ranking_pro = st.session_state.get("elite_x_pro_ranking", pd.DataFrame())
    if isinstance(ranking_pro, pd.DataFrame) and not ranking_pro.empty:
        col_score1, col_score2, col_score3, col_score4 = st.columns(4)
        col_score1.metric("Score Neural medio", f"{ranking_pro['Score Neural Elite X'].mean():.2f}")
        col_score2.metric("Melhor Score Neural", f"{ranking_pro['Score Neural Elite X'].max():.2f}")
        col_score3.metric("Jogos Elite", int((ranking_pro["Confianca"] == "Elite").sum()))
        col_score4.metric("Jogos Alta confianca", int((ranking_pro["Confianca"] == "Alta").sum()))
        st.dataframe(ranking_pro, width="stretch", hide_index=True)
        st.download_button("Exportar TOP 1000 PRO CSV", ranking_pro.to_csv(index=False).encode("utf-8-sig"), "elite_x_pro_top_1000.csv", "text/csv")
        st.download_button("Exportar TOP 1000 PRO Excel", dataframe_to_excel_bytes(ranking_pro, "elite_x_pro"), "elite_x_pro_top_1000.xlsx")
        st.download_button("Exportar TOP 1000 PRO PDF", dataframe_to_pdf_bytes(ranking_pro.head(120), "ELITE X PRO TOP 1000"), "elite_x_pro_top_1000.pdf", "application/pdf")

    st.divider()
    st.markdown("### SIMULAÇÃO ÚNICA — 20 DEZENAS")
    st.caption("Gera exatamente 1 conjunto de 20 dezenas e compara esse conjunto contra todos os concursos históricos, sem desdobrar em jogos de 6 dezenas.")
    if st.button("Executar simulação única de 20 dezenas", type="primary"):
        try:
            with st.spinner("Gerando 1 jogo unico de 20 dezenas e comparando contra toda a base."):
                simulacao_20 = simular_jogo_unico_20_dezenas(df)
                st.session_state.simulacao_unica_20_dezenas = simulacao_20
                caminho = Path("exports") / "teste_unico_20_dezenas.csv"
                caminho.parent.mkdir(parents=True, exist_ok=True)
                simulacao_20["detalhes"].to_csv(caminho, index=False, encoding="utf-8-sig")
                registrar_log_execucao("Simulação única 20 dezenas", _ultimo_concurso(df), simulacao_20["resumo"]["Score final do jogo"])
                atualizar_estado_jogos(simulacao_20["detalhes"], simulacao_20["resumo"]["Score final do jogo"], "Simulação única de 20 dezenas executada")
            registrar_mensagem("success", "Simulação única concluída e salva em exports/teste_unico_20_dezenas.csv.")
            st.success("Simulação única concluída e salva em exports/teste_unico_20_dezenas.csv.")
        except Exception as erro:
            registrar_mensagem("error", f"Falha na simulação única de 20 dezenas: {erro}")
            st.error(f"Falha na simulação única de 20 dezenas: {erro}")

    simulacao_20 = st.session_state.get("simulacao_unica_20_dezenas")
    if isinstance(simulacao_20, dict):
        resumo_20 = simulacao_20.get("resumo", {})
        detalhes_20 = simulacao_20.get("detalhes", pd.DataFrame())
        st.markdown(dezenas_html(simulacao_20.get("dezenas", [])), unsafe_allow_html=True)
        col_u1, col_u2, col_u3, col_u4 = st.columns(4)
        col_u1.metric("Concursos analisados", resumo_20.get("Total de concursos analisados", 0))
        col_u2.metric("Concursos com 6 acertos", resumo_20.get("Concursos com 6 acertos", 0))
        col_u3.metric("Concursos com 5 acertos", resumo_20.get("Concursos com 5 acertos", 0))
        col_u4.metric("Concursos com 4 acertos", resumo_20.get("Concursos com 4 acertos", 0))
        col_u5, col_u6, col_u7 = st.columns(3)
        col_u5.metric("Melhor pico", resumo_20.get("Melhor pico de acertos", 0))
        col_u6.metric("Concurso melhor desempenho", resumo_20.get("Concurso de melhor desempenho", 0))
        col_u7.metric("Score final", f"{float(resumo_20.get('Score final do jogo', 0.0)):.2f}")
        st.write(f"Dezenas acertadas no melhor concurso: **{resumo_20.get('Dezenas acertadas no melhor concurso', '') or 'Nenhuma'}**")
        if isinstance(detalhes_20, pd.DataFrame) and not detalhes_20.empty:
            st.dataframe(detalhes_20.sort_values(["Acertos dentro das 20", "Concurso"], ascending=[False, False]).head(50), width="stretch", hide_index=True)
            st.download_button(
                "Baixar teste unico 20 dezenas CSV",
                detalhes_20.to_csv(index=False).encode("utf-8-sig"),
                "teste_unico_20_dezenas.csv",
                "text/csv",
            )

    st.divider()
    aba_aprendizado, aba_correlacao, aba_banco, aba_boloes, aba_backtest = st.tabs(
        ["Aprendizado histórico", "Correlação", "Banco Mestre", "Bolões PRO", "Backtest 1000"]
    )
    with aba_aprendizado:
        aprendizado = aprendizado_historico(df)
        st.dataframe(pd.DataFrame(aprendizado).T.reset_index(names="Recorte"), width="stretch", hide_index=True)

    with aba_correlacao:
        correlacao = correlacao_dezenas(df, limite=150)
        st.dataframe(correlacao, width="stretch", hide_index=True)

    with aba_banco:
        tamanho_banco = st.selectbox("Tamanho do Banco Mestre", [15, 18, 20, 25, 30, 40], index=4)
        if st.button("Gerar Banco Mestre Inteligente"):
            try:
                with st.spinner("Gerando Banco Mestre Inteligente."):
                    st.session_state.banco_mestre_pro = banco_mestre_inteligente(df, tamanho=int(tamanho_banco))
                    score_medio = float(st.session_state.banco_mestre_pro["Score Mestre"].mean())
                    registrar_log_execucao("Banco Mestre PRO", _ultimo_concurso(df), score_medio)
                    atualizar_estado_jogos(st.session_state.banco_mestre_pro, score_medio, "Banco Mestre PRO carregado/atualizado")
                registrar_mensagem("success", "Banco Mestre Inteligente gerado.")
                st.success("Banco Mestre Inteligente gerado.")
            except Exception as erro:
                st.session_state.banco_mestre_pro = pd.DataFrame()
                registrar_mensagem("error", f"Falha ao gerar Banco Mestre: {erro}")
                st.error(f"Falha ao gerar Banco Mestre: {erro}")
        banco = st.session_state.get("banco_mestre_pro", pd.DataFrame())
        if isinstance(banco, pd.DataFrame) and not banco.empty:
            st.markdown(dezenas_html(banco["Dezena"].astype(int).tolist()), unsafe_allow_html=True)
            st.dataframe(banco, width="stretch", hide_index=True)
            st.download_button("Exportar Banco Mestre CSV", banco.to_csv(index=False).encode("utf-8-sig"), "banco_mestre_inteligente.csv", "text/csv")

    with aba_boloes:
        qtd_jogos = st.number_input("Jogos por bolão PRO", min_value=5, max_value=300, value=40, step=5, key="elite_x_pro_bolao_qtd")
        col_b15, col_b18, col_b20 = st.columns(3)
        if col_b15.button("Gerar bolão PRO 15 dezenas"):
            executar_bolao_profissional(df, 15, int(qtd_jogos))
        if col_b18.button("Gerar bolão PRO 18 dezenas"):
            executar_bolao_profissional(df, 18, int(qtd_jogos))
        if col_b20.button("Gerar bolão PRO 20 dezenas"):
            executar_bolao_profissional(df, 20, int(qtd_jogos))

        for tamanho in (15, 18, 20):
            pacote = st.session_state.get(f"bolao_pro_{tamanho}")
            if isinstance(pacote, dict) and isinstance(pacote.get("jogos"), pd.DataFrame) and not pacote["jogos"].empty:
                st.markdown(f"#### Bolão profissional {tamanho} dezenas")
                st.markdown(dezenas_html(pacote["banco"]["Dezena"].astype(int).tolist()), unsafe_allow_html=True)
                st.dataframe(pacote["jogos"], width="stretch", hide_index=True)
                st.download_button(
                    f"Exportar bolão {tamanho} CSV",
                    pacote["jogos"].to_csv(index=False).encode("utf-8-sig"),
                    f"bolao_pro_{tamanho}_dezenas.csv",
                    "text/csv",
                )

    with aba_backtest:
        st.warning("Backtest de 1000 concursos pode demorar. Use candidatos baixos para validação online.")
        col_bt1, col_bt2, col_bt3 = st.columns(3)
        bt_concursos = col_bt1.number_input("Concursos do backtest", min_value=10, max_value=1000, value=1000, step=10)
        bt_candidatos = col_bt2.number_input("Candidatos por concurso", min_value=50, max_value=2000, value=150, step=50)
        bt_top = col_bt3.number_input("Top por concurso", min_value=1, max_value=20, value=5, step=1)
        if st.button("Executar backtest Elite X PRO x Elite 9"):
            try:
                with st.spinner("Executando backtest comparativo."):
                    st.session_state.backtest_elite_x_pro = backtest_elite_x_pro(
                        df,
                        concursos=int(bt_concursos),
                        candidatos=int(bt_candidatos),
                        top=int(bt_top),
                    )
                resultado = st.session_state.backtest_elite_x_pro
                resumo_bt = resultado.get("resumo", pd.DataFrame())
                score_medio = float(resumo_bt["Score_medio"].mean()) if isinstance(resumo_bt, pd.DataFrame) and not resumo_bt.empty else 0.0
                registrar_log_execucao("Backtest Elite X PRO", _ultimo_concurso(df), score_medio)
                atualizar_estado_jogos(resumo_bt, score_medio, "Backtest Elite X PRO x Elite 9 executado")
                registrar_mensagem("success", "Backtest Elite X PRO concluido.")
                st.success("Backtest concluido.")
            except Exception as erro:
                st.session_state.backtest_elite_x_pro = {}
                registrar_mensagem("error", f"Falha no backtest Elite X PRO: {erro}")
                st.error(f"Falha no backtest Elite X PRO: {erro}")

        backtest = st.session_state.get("backtest_elite_x_pro")
        if isinstance(backtest, dict):
            resumo_bt = backtest.get("resumo", pd.DataFrame())
            detalhes_bt = backtest.get("detalhes", pd.DataFrame())
            evolucao_bt = backtest.get("evolucao", pd.DataFrame())
            melhor_bt = backtest.get("melhor", {})
            if isinstance(resumo_bt, pd.DataFrame) and not resumo_bt.empty:
                st.markdown("### Relatório final do backtest")
                st.dataframe(resumo_bt, width="stretch", hide_index=True)
                st.info(
                    "Melhor combinacao encontrada: "
                    f"{melhor_bt.get('Jogo', 'N/D')} | "
                    f"{melhor_bt.get('Acertos', 0)} acertos | "
                    f"{melhor_bt.get('Motor', 'N/D')} | concurso {melhor_bt.get('Concurso', 'N/D')}"
                )
                st.markdown("### Evolucao do score")
                st.dataframe(evolucao_bt, width="stretch", hide_index=True)
                st.download_button("Exportar resumo backtest CSV", resumo_bt.to_csv(index=False).encode("utf-8-sig"), "backtest_elite_x_pro_resumo.csv", "text/csv")
                st.download_button("Exportar detalhes backtest CSV", detalhes_bt.to_csv(index=False).encode("utf-8-sig"), "backtest_elite_x_pro_detalhes.csv", "text/csv")


def render_boloes(df: pd.DataFrame) -> None:
    st.markdown("### Bolões profissionais")
    quantidade = st.number_input("Quantidade de jogos do bolão", min_value=5, max_value=300, value=40, step=5, key="bolao_quantidade")
    col15, col18, col20 = st.columns(3)
    if col15.button("Gerar bolão 15 dezenas", type="primary"):
        executar_bolao_profissional(df, 15, int(quantidade))
    if col18.button("Gerar bolão 18 dezenas", type="primary"):
        executar_bolao_profissional(df, 18, int(quantidade))
    if col20.button("Gerar bolão 20 dezenas", type="primary"):
        executar_bolao_profissional(df, 20, int(quantidade))

    for tamanho in (15, 18, 20):
        pacote = st.session_state.get(f"bolao_pro_{tamanho}")
        if isinstance(pacote, dict) and isinstance(pacote.get("jogos"), pd.DataFrame) and not pacote["jogos"].empty:
            st.markdown(f"#### Bolão {tamanho} dezenas")
            st.markdown(dezenas_html(pacote["banco"]["Dezena"].astype(int).tolist()), unsafe_allow_html=True)
            jogos = pacote["jogos"]
            st.dataframe(jogos, width="stretch", hide_index=True)
            st.download_button(f"Exportar Bolão {tamanho} CSV", jogos.to_csv(index=False).encode("utf-8-sig"), f"bolao_{tamanho}_dezenas.csv", "text/csv")
            st.download_button(f"Exportar Bolão {tamanho} Excel", dataframe_to_excel_bytes(jogos, f"bolao_{tamanho}"), f"bolao_{tamanho}_dezenas.xlsx")
            st.download_button(f"Exportar Bolão {tamanho} PDF", dataframe_to_pdf_bytes(jogos, f"BOLÃO {tamanho} DEZENAS"), f"bolao_{tamanho}_dezenas.pdf", "application/pdf")


def render_exportacoes() -> None:
    st.markdown("### Exportações da sessão")
    opcoes = {
        "Top 1000 jogos": st.session_state.get("top_jogos_sessao", pd.DataFrame()),
        "Motor Elite X": st.session_state.get("motor_elite_x", pd.DataFrame()),
        "Elite X PRO": st.session_state.get("elite_x_pro_ranking", pd.DataFrame()),
        "Bolão 20 dezenas": st.session_state.get("bolao_20_dezenas", pd.DataFrame()),
        "Bolão PRO 15 dezenas": st.session_state.get("bolao_pro_15", {}).get("jogos", pd.DataFrame()) if isinstance(st.session_state.get("bolao_pro_15"), dict) else pd.DataFrame(),
        "Bolão PRO 18 dezenas": st.session_state.get("bolao_pro_18", {}).get("jogos", pd.DataFrame()) if isinstance(st.session_state.get("bolao_pro_18"), dict) else pd.DataFrame(),
        "Bolão PRO 20 dezenas": st.session_state.get("bolao_pro_20", {}).get("jogos", pd.DataFrame()) if isinstance(st.session_state.get("bolao_pro_20"), dict) else pd.DataFrame(),
        "Banco Mestre PRO": st.session_state.get("banco_mestre_pro", pd.DataFrame()),
        "Log de execução": pd.DataFrame(st.session_state.get("log_execucao", [])),
    }
    escolha = st.selectbox("Conjunto de dados", list(opcoes.keys()))
    dados = opcoes[escolha] if isinstance(opcoes[escolha], pd.DataFrame) else pd.DataFrame()
    if dados.empty:
        st.info("Nenhum dado disponível para exportar neste item.")
        return
    st.dataframe(dados, width="stretch", hide_index=True)
    nome = escolha.lower().replace(" ", "_")
    st.download_button("Exportar CSV", dados.to_csv(index=False).encode("utf-8-sig"), f"{nome}.csv", "text/csv")
    st.download_button("Exportar Excel", dataframe_to_excel_bytes(dados, nome[:31]), f"{nome}.xlsx")
    st.download_button("Exportar PDF", dataframe_to_pdf_bytes(dados, escolha.upper()), f"{nome}.pdf", "application/pdf")

    if st.button("Gerar arquivos de exportação", type="primary"):
        try:
            with st.spinner("Gerando CSV, Excel e relatório em exports."):
                pasta = Path("exports")
                pasta.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                caminho_csv = pasta / f"{nome}_{timestamp}.csv"
                caminho_xlsx = pasta / f"{nome}_{timestamp}.xlsx"
                caminho_pdf = pasta / f"{nome}_{timestamp}.pdf"
                dados.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
                caminho_xlsx.write_bytes(dataframe_to_excel_bytes(dados, nome[:31]))
                caminho_pdf.write_bytes(dataframe_to_pdf_bytes(dados, escolha.upper()))
                relatorio = (
                    f"Exportação gerada em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                    f"Conjunto: {escolha}\n"
                    f"Linhas: {len(dados)}\n"
                    f"CSV: {caminho_csv}\n"
                    f"Excel: {caminho_xlsx}\n"
                    f"Relatório: {caminho_pdf}"
                )
                st.session_state.relatorio_atual = relatorio
            registrar_mensagem("success", "Arquivos de exportação gerados em exports.")
            st.success("CSV, Excel e relatório gerados em exports.")
            st.code(st.session_state.relatorio_atual)
        except Exception as erro:
            registrar_mensagem("error", f"Falha ao gerar exportações: {erro}")
            st.error(f"Falha ao gerar exportações: {erro}")

    caminho_log = Path("exports") / "log_execucao_elite_x.csv"
    if caminho_log.exists():
        st.caption(f"Log persistido em {caminho_log}")


def render_elite_x_fechamento(df: pd.DataFrame) -> None:
    st.warning(
        "Este sistema não garante premiação. A Mega-Sena é jogo de azar. "
        "O Elite X apenas organiza apostas e melhora a cobertura combinatória."
    )
    col1, col2, col3 = st.columns(3)
    orcamento = col1.number_input("Orçamento disponível", min_value=0.0, value=100.0, step=10.0)
    valor_aposta = col2.number_input("Valor da aposta simples", min_value=0.01, value=5.0, step=0.5)
    candidatos = col3.number_input("Candidatos do fechamento", min_value=1000, max_value=100000, value=20000, step=1000)
    quantidade = int(float(orcamento) // float(valor_aposta)) if valor_aposta > 0 else 0
    st.metric("Quantidade de jogos calculada", quantidade)

    if st.button("Gerar fechamento Elite X", type="primary"):
        try:
            with st.spinner("Gerando fechamento inteligente a partir do Banco Mestre de 30 dezenas."):
                st.session_state.elite_x_fechamento = gerar_fechamento_elite_x(
                    df,
                    orcamento=float(orcamento),
                    valor_aposta_simples=float(valor_aposta),
                    quantidade_candidatos=int(candidatos),
                )
            registrar_jogos_sessao(st.session_state.elite_x_fechamento["jogos"], "Elite X Fechamento")
            registrar_log_execucao(
                "Elite X Fechamento",
                _ultimo_concurso(df),
                float(st.session_state.elite_x_fechamento["indicadores"].get("Score final", 0.0)),
            )
            atualizar_estado_jogos(
                st.session_state.elite_x_fechamento["jogos"],
                float(st.session_state.elite_x_fechamento["indicadores"].get("Score final", 0.0)),
                "Elite X fechamento/previsão estatística executado",
            )
            registrar_mensagem("success", "Fechamento Elite X gerado com sucesso.")
            st.success("Fechamento Elite X gerado com sucesso.")
        except Exception as erro:
            st.session_state.elite_x_fechamento = None
            registrar_mensagem("error", f"Falha ao gerar Elite X: {erro}")
            st.error(f"Falha ao gerar Elite X: {erro}")

    fechamento = st.session_state.get("elite_x_fechamento")
    if not fechamento:
        return

    banco = fechamento["banco_mestre"]
    jogos = fechamento["jogos"]
    indicadores = fechamento["indicadores"]
    st.markdown("### Banco Mestre de 30 dezenas")
    st.markdown(dezenas_html(banco), unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Cobertura de dezenas", f"{indicadores['Cobertura de dezenas']:.2f}%")
    col_b.metric("Cobertura de duplas", f"{indicadores['Cobertura de duplas']:.2f}%")
    col_c.metric("Cobertura de trincas", f"{indicadores['Cobertura de trincas']:.2f}%")
    col_d, col_e, col_f = st.columns(3)
    col_d.metric("Cobertura de quadras", f"{indicadores['Cobertura de quadras']:.2f}%")
    col_e.metric("Redundância", f"{indicadores['Redundancia']:.2f}%")
    col_f.metric("Score final", f"{indicadores['Score final']:.2f}")

    st.markdown("### Jogos finais para bolão")
    st.dataframe(jogos, width="stretch", hide_index=True)
    st.download_button(
        "Exportar CSV Elite X",
        data=exportar_fechamento_csv(fechamento),
        file_name="elite_x_fechamento.csv",
        mime="text/csv",
    )
    st.download_button("Exportar Excel Elite X", dataframe_to_excel_bytes(jogos, "elite_x"), "elite_x_fechamento.xlsx")
    st.download_button("Exportar PDF Elite X", dataframe_to_pdf_bytes(jogos, "ELITE X FECHAMENTO"), "elite_x_fechamento.pdf", "application/pdf")


def main() -> None:
    inicializar_estado()
    aplicar_css_institucional()
    corrigir_interface_visual()
    render_topo_institucional()
    render_menu_visual()
    render_mensagens_estado()

    if st.session_state.pop("base_oficial_atualizada", False):
        st.success("Base oficial atualizada com sucesso.")

    if st.button("Atualizar base oficial"):
        try:
            with st.spinner("Atualizando base oficial pela CAIXA."):
                atualizou = atualizar_base_local()
            if atualizou:
                obter_info_caixa_cached.clear()
                df_atualizado = carregar_base(CAMINHO_BASE_PADRAO)
                atualizar_estado_base(df_atualizado, "Base oficial atualizada pela CAIXA")
                registrar_mensagem("success", "Base oficial atualizada com sucesso.")
                st.session_state.base_oficial_atualizada = True
                st.rerun()
            else:
                registrar_mensagem("error", "Não foi possível atualizar pela CAIXA neste momento. Usando base local.")
                st.warning("Não foi possível atualizar pela CAIXA neste momento. Usando base local.")
        except Exception as erro:
            registrar_mensagem("error", f"Falha ao atualizar base oficial: {erro}")
            st.error(f"Falha ao atualizar base oficial: {erro}")

    df = obter_dados()
    if df is None:
        st.stop()

    resumo = resumo_base(df)
    cards_slot = st.container()
    base_slot = st.container()
    premiacao_slot = st.container()

    secao = render_secao_ativa()
    mais = dezenas_mais_sorteadas(df, limite=10)
    menos = dezenas_menos_sorteadas(df, limite=10)

    if secao == "Visão Geral":
        st.dataframe(mais, width="stretch", hide_index=True)
        st.dataframe(menos, width="stretch", hide_index=True)
        render_analise_avancada(df)
    elif secao == "Resultados":
        st.subheader("Resultados carregados")
        st.dataframe(df.head(30), width="stretch", hide_index=True)
        st.dataframe(mais, width="stretch", hide_index=True)
        st.dataframe(menos, width="stretch", hide_index=True)
        st.plotly_chart(grafico_frequencia(df), width="stretch")
        render_dezenas_quentes_frias(df)
    elif secao == "Motor Elite 9":
        render_motor_elite_9(df)
    elif secao == "Banco Mestre":
        render_banco_mestre_elite_9()
        st.divider()
        tamanho_banco = st.selectbox("Tamanho do Banco Mestre PRO", [15, 18, 20, 25, 30, 40], index=4, key="banco_mestre_principal_tamanho")
        if st.button("Gerar Banco Mestre PRO", type="primary"):
            try:
                with st.spinner("Gerando Banco Mestre PRO."):
                    banco = banco_mestre_inteligente(df, tamanho=int(tamanho_banco))
                    st.session_state.banco_mestre_pro = banco
                    score_medio = float(banco["Score Mestre"].mean()) if not banco.empty else 0.0
                    registrar_log_execucao("Banco Mestre PRO", _ultimo_concurso(df), score_medio)
                    atualizar_estado_jogos(banco, score_medio, "Banco Mestre PRO carregado/atualizado")
                registrar_mensagem("success", "Banco Mestre PRO gerado.")
                st.success("Banco Mestre PRO gerado.")
            except Exception as erro:
                st.session_state.banco_mestre_pro = pd.DataFrame()
                registrar_mensagem("error", f"Falha no Banco Mestre PRO: {erro}")
                st.error(f"Falha no Banco Mestre PRO: {erro}")
        banco = st.session_state.get("banco_mestre_pro", pd.DataFrame())
        if isinstance(banco, pd.DataFrame) and not banco.empty:
            st.markdown(dezenas_html(banco["Dezena"].astype(int).tolist()), unsafe_allow_html=True)
            st.dataframe(banco, width="stretch", hide_index=True)
    elif secao == "Elite X":
        render_motor_elite_x(df)
        st.divider()
        render_elite_x_fechamento(df)
        st.divider()
        render_elite_x_pro(df)
    elif secao == "Bolões":
        render_boloes(df)
    elif secao == "Auditorias":
        render_auditoria_elite_9()
        st.divider()
        render_backtest_historico(df)
    elif secao == "Exportações":
        render_exportacoes()
    elif secao == "Geração de Jogos":
        render_gerador_inteligente(df)
        render_ranking_melhores_jogos(df)
    elif secao in {"Previsão do Sorteio", "Previsão do Próximo Concurso"}:
        render_previsao_concurso_alvo(df)

    with cards_slot:
        render_cards_dashboard_v2(df)
    with base_slot:
        render_base_historica_status(df)
        with st.expander("Base histórica e fonte oficial", expanded=False):
            st.info(
                "Base histórica: dados obtidos da página oficial da CAIXA. "
                "Consulte a fonte oficial para validação."
            )
            st.link_button("Conferir resultados oficiais na CAIXA", FONTE_CAIXA_URL)
            st.caption("Este sistema utiliza estatística histórica e não possui vínculo oficial com a CAIXA.")
            col1, col2, col3 = st.columns(3)
            col1.metric("Concursos carregados", resumo["total_concursos"])
            col2.metric("Primeiro concurso", resumo["primeiro_concurso"])
            col3.metric("Último concurso", resumo["ultimo_concurso"])
    with premiacao_slot:
        render_painel_premiacao()

    st.divider()
    st.caption(
        "Este projeto não possui vínculo com a Caixa Econômica Federal. "
        "Use com responsabilidade."
    )


if __name__ == "__main__":
    main()
