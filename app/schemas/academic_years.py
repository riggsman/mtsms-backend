from pydantic import BaseModel
from sqlalchemy import DateTime

class Academic_Response(BaseModel): 
    id:int
    short_year:str
    long_year:str

class Academic_Term_Response(BaseModel): 
    id:int
    term:str
    semester:str