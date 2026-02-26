from pydantic import BaseModel

class LevelResponse(BaseModel):
    id:str
    code:str
    level:str

    class Config:
        from_attributes = True

class LevelRequest(BaseModel):
    code:str
    level:str