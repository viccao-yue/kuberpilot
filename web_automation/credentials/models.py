from pydantic import BaseModel, SecretStr


class Credential(BaseModel):
    username: str
    password: SecretStr
