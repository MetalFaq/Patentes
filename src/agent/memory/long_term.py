"""Marcador de posicion para memoria de largo plazo.

Instrucciones:
- Usa este modulo para perfiles de usuario persistentes.
- Evita almacenar secretos o datos sensibles sin politicas claras.
- Mantene este componente simple hasta definir un almacenamiento real.
"""


class LongTermMemory:
    """Marcador de posicion minimo para almacenamiento clave-valor.

    Este objeto se reemplazara por un almacenamiento real cuando haya requisitos
    de persistencia mas avanzados.
    """

    def __init__(self):
        self._data = {}

    def get(self, user_id: str):
        """Devuelve el valor asociado a un usuario."""
        return self._data.get(user_id)

    def set(self, user_id: str, value):
        """Guarda un valor asociado a un usuario."""
        self._data[user_id] = value
