import uuid

from pydantic import BaseModel


class VoiceSessionOut(BaseModel):
    """Everything the browser needs to join its voice room.

    The token is a LiveKit room token scoped to exactly one room — it is not
    our API JWT, and it grants nothing beyond joining that room.
    """

    token: str
    url: str
    room_name: str
    conversation_id: uuid.UUID
