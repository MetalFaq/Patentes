"""Esquemas de solicitud para la API de chat.

Instrucciones:
- Mantene los campos de solicitud estables para no romper clientes.
- Evita campos ambiguos o no documentados.
- `channel` es opcional y solo se usa para trazabilidad del origen.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Mensaje de chat del usuario para el agente.

    Campos:
    - user_id: identificador del usuario.
    - session_id: identificador de sesion.
    - message: texto del mensaje del usuario.
    - channel: canal de origen (`api`, `ui`, `cli`, `webex`, etc.).
    """

    user_id: str = Field(..., description="Identificador unico de usuario")
    session_id: str = Field(..., description="Identificador de sesion")
    message: str = Field(..., description="Texto del mensaje del usuario")
    channel: str | None = Field(
        default=None,
        description="Canal de origen usado solo para trazabilidad",
    )
