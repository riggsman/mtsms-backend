from pydantic import BaseModel


class Department_Response(BaseModel): 
    id:int
    name:str
    