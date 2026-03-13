"""Adaptador Webex para el agente de patentes.

Este paquete implementa el canal Webex sin duplicar la logica del agente.
Su responsabilidad es recibir eventos de Webex, validarlos, reenviarlos a
`POST /chat` y devolver la respuesta markdown al espacio correspondiente.
"""
