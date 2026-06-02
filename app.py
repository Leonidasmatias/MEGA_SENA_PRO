from __future__ import annotations

import pandas as pd
import streamlit as st

from src.carregar_dados import CAMINHO_BASE_PADRAO, carregar_base, carregar_upload
from src.estatisticas import (
    dezenas_atrasadas,
    dezenas_mais_sorteadas,
    dezenas_menos_sorteadas,
    estatistica_pares_impares,
    estatistica_soma_dezenas,
    padrao_jogo,
    resumo_base,
)
from src.gerador_jogos import gerar_jogo
from src.visualizacoes import grafico_frequencia


st.set_page_config(
    page_title="Mega Sena Analytics",
    page_icon="🎲",
    layout="wide",
)


def mostrar_jogo(dezenas: list[int]) -> None:
    colunas = st.columns(6)
    for coluna, dezena in zip(colunas, dezenas):
        coluna.markdown(
            f"""
            <div style="
                background:#0f8f4f;
                color:white;
                border-radius:8px;
                padding:14px 0;
                text-align:center;
                font-size:24px;
                font-weight:800;
            ">{dezena:02d}</div>
            """,
            unsafe_allow_html=True,
        )


def obter_dados() -> pd.DataFrame | None:
    upload = st.file_uploader(
        "Upload opcional de CSV histórico",
        type=["csv"],
        help="Use colunas: Concurso, Data, D1, D2, D3, D4, D5, D6.",
    )

    try:
        if upload is not None:
            return carregar_upload(upload)
        return carregar_base(CAMINHO_BASE_PADRAO)
    except FileNotFoundError:
        st.error(
            "Arquivo dados/mega_sena_historico.csv não encontrado. "
            "Inclua a base histórica no projeto antes do deploy."
        )
    except Exception as erro:
        st.error(f"Não foi possível carregar a base histórica: {erro}")
    return None


def render_analise_avancada(df: pd.DataFrame) -> None:
    atrasadas = dezenas_atrasadas(df)
    pares_impares = estatistica_pares_impares(df)
    soma_dezenas = estatistica_soma_dezenas(df)
    padrao = padrao_jogo(df)

    st.markdown("### Ranking de dezenas atrasadas")
    st.dataframe(atrasadas.head(20), width="stretch", hide_index=True)

    st.markdown("### Estatística de pares e ímpares")
    col_par, col_impar = st.columns(2)
    col_par.metric("Média de pares por concurso", f"{padrao['média de pares']:.2f}")
    col_impar.metric("Média de ímpares por concurso", f"{padrao['média de ímpares']:.2f}")
    st.dataframe(pares_impares.head(30), width="stretch", hide_index=True)

    st.markdown("### Soma das dezenas")
    col_soma1, col_soma2, col_soma3 = st.columns(3)
    col_soma1.metric("Soma média", f"{soma_dezenas['média']:.2f}")
    col_soma2.metric("Soma mínima", soma_dezenas["mínima"])
    col_soma3.metric("Soma máxima", soma_dezenas["máxima"])
    st.dataframe(soma_dezenas["por_concurso"].head(30), width="stretch", hide_index=True)

    st.markdown("### Padrão geral de jogo")
    resumo_padrao = pd.DataFrame(
        [
            {
                "Média da soma": round(float(padrao["média da soma"]), 2),
                "Média de pares": round(float(padrao["média de pares"]), 2),
                "Média de ímpares": round(float(padrao["média de ímpares"]), 2),
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


def main() -> None:
    st.title("Mega Sena Analytics")
    st.caption(
        "Análise estatística da Mega-Sena com base histórica local. "
        "As sugestões são estatísticas e não garantem premiação."
    )

    df = obter_dados()
    if df is None:
        st.stop()

    resumo = resumo_base(df)
    col1, col2, col3 = st.columns(3)
    col1.metric("Concursos carregados", resumo["total_concursos"])
    col2.metric("Primeiro concurso", resumo["primeiro_concurso"])
    col3.metric("Último concurso", resumo["ultimo_concurso"])

    st.subheader("Concursos carregados")
    st.dataframe(df.head(30), width="stretch", hide_index=True)

    st.subheader("Análise estatística")
    mais = dezenas_mais_sorteadas(df, limite=10)
    menos = dezenas_menos_sorteadas(df, limite=10)

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Dezenas mais sorteadas",
            "Dezenas menos sorteadas",
            "Gráfico geral",
            "Análise Avançada",
        ]
    )
    with tab1:
        st.dataframe(mais, width="stretch", hide_index=True)
    with tab2:
        st.dataframe(menos, width="stretch", hide_index=True)
    with tab3:
        st.plotly_chart(grafico_frequencia(df), width="stretch")
    with tab4:
        render_analise_avancada(df)

    st.subheader("Gerador de jogos")
    st.write("Gere jogos com 6 dezenas combinando frequência histórica e aleatoriedade.")

    if "jogo_gerado" not in st.session_state:
        st.session_state.jogo_gerado = gerar_jogo(df)

    if st.button("Gerar novo jogo", type="primary"):
        st.session_state.jogo_gerado = gerar_jogo(df)

    mostrar_jogo(st.session_state.jogo_gerado)

    st.divider()
    st.caption(
        "Este projeto não possui vínculo com a Caixa Econômica Federal. "
        "Use com responsabilidade."
    )


if __name__ == "__main__":
    main()
