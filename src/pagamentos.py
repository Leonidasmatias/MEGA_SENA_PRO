from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


VALOR_POR_PALPITE = 1.0
CAMINHO_LOG_PAGAMENTOS = Path("exports") / "pagamentos.csv"


def calcular_valor_pagamento(quantidade_palpites: int) -> float:
    return round(max(1, int(quantidade_palpites)) * VALOR_POR_PALPITE, 2)


def registrar_pagamento(
    concurso_alvo: int,
    quantidade_palpites: int,
    valor_total: float,
    status_pagamento: str,
    payment_id: str | int | None,
    jogos_liberados: int,
) -> None:
    CAMINHO_LOG_PAGAMENTOS.parent.mkdir(parents=True, exist_ok=True)
    linha = {
        "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "concurso_alvo": int(concurso_alvo),
        "quantidade_palpites": int(quantidade_palpites),
        "valor_total": round(float(valor_total), 2),
        "status_pagamento": str(status_pagamento),
        "payment_id": "" if payment_id is None else str(payment_id),
        "jogos_liberados": int(jogos_liberados),
    }
    df = pd.DataFrame([linha])
    df.to_csv(
        CAMINHO_LOG_PAGAMENTOS,
        mode="a",
        header=not CAMINHO_LOG_PAGAMENTOS.exists(),
        index=False,
        encoding="utf-8-sig",
    )
