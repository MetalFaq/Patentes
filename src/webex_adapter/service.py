"""Orquestacion del adaptador Webex.

Instrucciones:
- Resuelve el flujo completo mensaje Webex -> POST /chat -> respuesta markdown.
- Aplica deduplicacion antes de llamar al backend.
- Mapea `personId` y `roomId` al esquema conversacional del backend Patentes.
- Asume que el webhook ya llego correctamente; si nunca se invoca este flujo, revisar reachability publica del endpoint.
- Registra informacion suficiente para diagnostico sin exponer secretos.
"""

from __future__ import annotations

import logging
from typing import Any

from webex_adapter.client import PatentesApiClient, WebexApiClient
from webex_adapter.config import WebexAdapterSettings
from webex_adapter.dedupe import EventClaim, WebexEventDedupeStore
from webex_adapter.schemas import (
    PatentesChatRequest,
    ProcessedEventResult,
    WebexMessage,
    WebexWebhookEvent,
)

logger = logging.getLogger(__name__)


class WebexBridgeService:
    """Coordina el procesamiento de eventos entrantes desde Webex."""

    def __init__(
        self,
        settings: WebexAdapterSettings,
        webex_client: WebexApiClient,
        patents_client: PatentesApiClient,
        dedupe_store: WebexEventDedupeStore,
        *,
        bot_identity: dict[str, Any],
    ):
        self.settings = settings
        self.webex_client = webex_client
        self.patents_client = patents_client
        self.dedupe_store = dedupe_store
        self.bot_person_id = bot_identity.get("id")
        emails = bot_identity.get("emails") or []
        self.bot_email = emails[0].lower() if emails else None

    def _room_type_for(self, message: WebexMessage, event: WebexWebhookEvent) -> str:
        room_type = (message.roomType or event.data.roomType or "").strip().lower()
        return room_type

    def _session_id_for(self, message: WebexMessage) -> str:
        room_type = (message.roomType or "").strip().lower()
        if room_type == "direct":
            return message.roomId
        return f"{message.roomId}:{message.personId}"

    def _message_text_for(self, message: WebexMessage) -> str:
        return (message.text or message.markdown or "").strip()

    async def process_event(self, event: WebexWebhookEvent) -> ProcessedEventResult:
        """Procesa un evento `messages.created` y publica la respuesta en Webex."""
        if event.resource != "messages" or event.event != "created":
            return ProcessedEventResult(
                status="ignored",
                reason="unsupported_event",
                event_id=event.id,
                message_id=event.data.id,
                room_id=event.data.roomId,
            )

        message_id = event.data.id
        event_key = f"message:{message_id}"
        self.dedupe_store.cleanup_expired(self.settings.dedupe_ttl_hours)
        claim = EventClaim(
            event_key=event_key,
            message_id=message_id,
            webhook_event_id=event.id,
            room_id=event.data.roomId,
            person_id=event.data.personId,
        )
        claimed = self.dedupe_store.claim(
            claim,
            metadata={"stage": "received", "resource": event.resource, "event": event.event},
        )
        if not claimed:
            logger.info("Evento Webex ignorado por duplicado o procesamiento activo | message=%s", message_id)
            return ProcessedEventResult(
                status="ignored",
                reason="duplicate_or_in_progress",
                event_id=event.id,
                message_id=message_id,
                room_id=event.data.roomId,
            )

        try:
            message = await self.webex_client.get_message(message_id)
            room_type = self._room_type_for(message, event)
            if room_type not in self.settings.allowed_room_types:
                self.dedupe_store.mark_completed(
                    event_key,
                    status="ignored",
                    metadata={"reason": "room_type_not_allowed", "room_type": room_type},
                )
                return ProcessedEventResult(
                    status="ignored",
                    reason="room_type_not_allowed",
                    event_id=event.id,
                    message_id=message.id,
                    room_id=message.roomId,
                )

            if self.bot_person_id and message.personId == self.bot_person_id:
                self.dedupe_store.mark_completed(
                    event_key,
                    status="ignored",
                    metadata={"reason": "self_message"},
                )
                return ProcessedEventResult(
                    status="ignored",
                    reason="self_message",
                    event_id=event.id,
                    message_id=message.id,
                    room_id=message.roomId,
                )

            if self.bot_email and message.personEmail and message.personEmail.lower() == self.bot_email:
                self.dedupe_store.mark_completed(
                    event_key,
                    status="ignored",
                    metadata={"reason": "self_message"},
                )
                return ProcessedEventResult(
                    status="ignored",
                    reason="self_message",
                    event_id=event.id,
                    message_id=message.id,
                    room_id=message.roomId,
                )

            message_text = self._message_text_for(message)
            if not message_text:
                self.dedupe_store.mark_completed(
                    event_key,
                    status="ignored",
                    metadata={"reason": "empty_message"},
                )
                return ProcessedEventResult(
                    status="ignored",
                    reason="empty_message",
                    event_id=event.id,
                    message_id=message.id,
                    room_id=message.roomId,
                )

            session_id = self._session_id_for(message)
            chat_payload = PatentesChatRequest(
                user_id=message.personId,
                session_id=session_id,
                message=message_text,
                channel="webex",
            )
            response = await self.patents_client.send_chat(chat_payload)
            await self.webex_client.send_markdown_message(message.roomId, response.text)

            self.dedupe_store.mark_completed(
                event_key,
                status="processed",
                metadata={
                    "reason": "processed",
                    "session_id": session_id,
                    "room_type": room_type,
                },
            )
            logger.info(
                "Evento Webex procesado | message=%s | session=%s | room=%s",
                message.id,
                session_id,
                message.roomId,
            )
            return ProcessedEventResult(
                status="processed",
                reason="processed",
                event_id=event.id,
                message_id=message.id,
                room_id=message.roomId,
                session_id=session_id,
            )
        except Exception:
            self.dedupe_store.release_claim(event_key)
            logger.exception("Fallo al procesar evento Webex | event=%s | message=%s", event.id, message_id)
            raise
