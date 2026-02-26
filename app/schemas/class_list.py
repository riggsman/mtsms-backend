from pydantic import BaseModel

class ClassListResponse(BaseModel):
    firstname:str
    middlename:str
    lastname:str
    gender:str
    class_id:str

    class Config:
        from_attributes = True
