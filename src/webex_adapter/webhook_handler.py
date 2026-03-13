"""Validacion del webhook Webex.

Instrucciones:
- Verifica la firma HMAC si hay secreto configurado.
- Valida el payload antes de delegar a `service.py`.
- Mantene este modulo centrado en transporte, no en logica del agente.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping

from pydantic import ValidationError

from webex_adapter.config import WebexAdapterSettings
from webex_adapter.schemas import ProcessedEventResult, WebexWebhookEvent
from webex_adapter.service import WebexBridgeService


class InvalidWebhookSignatureError(PermissionError):
    """La firma HMAC del webhook no coincide con el secreto configurado."""


def _verify_signature(raw_body: bytes, signature: str, secret: str) -> None:
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha1).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise InvalidWebhookSignatureError("Firma de webhook Webex invalida")


class WebexWebhookHandler:
    """Valida el webhook y delega su procesamiento al servicio principal."""

    def __init__(self, settings: WebexAdapterSettings, service: WebexBridgeService):
        self.settings = settings
        self.service = service

    async def handle(self, raw_body: bytes, headers: Mapping[str, str]) -> ProcessedEventResult:
        """Valida firma/payload y procesa el evento entrante."""
        if not raw_body:
            raise ValueError("Webhook Webex vacio")

        if self.settings.webex_webhook_secret:
            signature = headers.get("x-spark-signature") or headers.get("X-Spark-Signature")
            if not signature:
                raise InvalidWebhookSignatureError("Falta X-Spark-Signature en el webhook")
            _verify_signature(raw_body, signature, self.settings.webex_webhook_secret)

        try:
            event = WebexWebhookEvent.model_validate_json(raw_body)
        except ValidationError as exc:
            raise ValueError("Payload de webhook Webex invalido") from exc
        return await self.service.process_event(event)
