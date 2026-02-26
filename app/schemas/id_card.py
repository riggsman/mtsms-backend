from pydantic import BaseModel

class ID_Card_Response(BaseModel): 
    firstname:str
    middlename:str
    lastname:str
    dob:str
    gender:str
    class_id:str
    department_id:int
    academic_year_id:int
  