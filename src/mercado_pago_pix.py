from __future__ import annotations

import json
from urllib import error, request
from uuid import uuid4


MERCADO_PAGO_API_URL = "https://api.mercadopago.com/v1/payments"


def criar_pagamento_pix(
    access_token: str,
    valor_total: float,
    descricao: str,
    email_pagador: str,
) -> dict:
    if not access_token:
        raise ValueError("MERCADO_PAGO_ACCESS_TOKEN nao configurado.")
    email_pagador = str(email_pagador or "").strip()
    if not email_pagador:
        raise ValueError("payer.email e obrigatorio para criar cobranca PIX.")

    payload = {
        "transaction_amount": round(float(valor_total), 2),
        "description": descricao,
        "payment_method_id": "pix",
        "payer": {"email": email_pagador},
    }
    dados = json.dumps(payload).encode("utf-8")
    requisicao = request.Request(
        MERCADO_PAGO_API_URL,
        data=dados,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(uuid4()),
        },
        method="POST",
    )
    return _executar_requisicao(requisicao)


def consultar_pagamento_pix(access_token: str, payment_id: str | int) -> dict:
    if not access_token:
        raise ValueError("MERCADO_PAGO_ACCESS_TOKEN nao configurado.")
    if not payment_id:
        raise ValueError("payment_id nao informado.")

    requisicao = request.Request(
        f"{MERCADO_PAGO_API_URL}/{payment_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    return _executar_requisicao(requisicao)


def extrair_dados_pix(resposta: dict) -> dict:
    transacao = resposta.get("point_of_interaction", {}).get("transaction_data", {})
    return {
        "payment_id": resposta.get("id"),
        "status": resposta.get("status", "unknown"),
        "qr_code": transacao.get("qr_code", ""),
        "qr_code_base64": transacao.get("qr_code_base64", ""),
        "ticket_url": transacao.get("ticket_url", ""),
    }


def _executar_requisicao(requisicao: request.Request) -> dict:
    try:
        with request.urlopen(requisicao, timeout=20) as resposta:
            conteudo = resposta.read().decode("utf-8")
    except error.HTTPError as exc:
        detalhe = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Mercado Pago retornou erro HTTP {exc.code}: {detalhe}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Falha de conexao com Mercado Pago: {exc}") from exc

    return json.loads(conteudo or "{}")
