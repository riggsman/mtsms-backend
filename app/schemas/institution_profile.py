from pydantic import BaseModel
from sqlalchemy import DateTime

class Institution_Profile_Response(BaseModel): 
    name:str
    address:str
    phone:str
    email:str
    type:int
    logo:str
    website:str
    registered_at:DateTime
  