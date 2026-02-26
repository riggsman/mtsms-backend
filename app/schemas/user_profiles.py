from pydantic import BaseModel
from sqlalchemy import DateTime

class User_Profile_Response(BaseModel): 
    firstname:str
    middlename:str
    lastname:str
    gender:str
    address:str
    email:str
    phone:str
    clearance_level:str
    registered_at:DateTime