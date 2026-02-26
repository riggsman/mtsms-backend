from pydantic import BaseModel
from sqlalchemy import DateTime

class Student_Profile_Response(BaseModel): 
    firstname:str
    middlename:str
    lastname:str
    dob:str
    gender:str
    address:str
    email:str
    phone:str
    class_id:str
    department_id:int
    academic_year_id:int
    enrollment_year:DateTime