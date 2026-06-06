from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

import pandas as pd


VALOR_POR_PALPITE = 1.0
CAMINHO_LOG_PAGAMENTOS = Path("exports") / "pagamentos.csv"
EMAIL_REGEX = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)


def calcular_valor_pagamento(quantidade_palpites: int) -> float:
    return round(max(1, int(quantidade_palpites)) * VALOR_POR_PALPITE, 2)


def email_cliente_valido(email: str) -> bool:
    return bool(EMAIL_REGEX.match(str(email or "").strip()))


def registrar_pagamento(
    concurso_alvo: int,
    quantidade_palpites: int,
    valor_total: float,
    status_pagamento: str,
    payment_id: str | int | None,
    jogos_liberados: int,
    funcao: str = "",
    email_pagador: str = "",
    conteudo_liberado: str = "",
) -> None:
    CAMINHO_LOG_PAGAMENTOS.parent.mkdir(parents=True, exist_ok=True)
    linha = {
        "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "funcao": str(funcao),
        "concurso_alvo": int(concurso_alvo),
        "quantidade_palpites": int(quantidade_palpites),
        "valor_total": round(float(valor_total), 2),
        "status_pagamento": str(status_pagamento),
        "payment_id": "" if payment_id is None else str(payment_id),
        "email_pagador": str(email_pagador),
        "jogos_liberados": int(jogos_liberados),
        "conteudo_liberado": str(conteudo_liberado),
    }
    novo = pd.DataFrame([linha])
    if CAMINHO_LOG_PAGAMENTOS.exists():
        try:
            atual = pd.read_csv(CAMINHO_LOG_PAGAMENTOS)
            novo = pd.concat([atual, novo], ignore_index=True, sort=False)
        except Exception:
            pass
    novo.to_csv(CAMINHO_LOG_PAGAMENTOS, index=False, encoding="utf-8-sig")
