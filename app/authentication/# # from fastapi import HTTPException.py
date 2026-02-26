# # from fastapi import HTTPException
# # from sqlalchemy import create_engine
# # from sqlalchemy.orm import sessionmaker
# # from app.database.base import DefaultBase, DefaultSessionLocal
# # from app.models.tenant import Tenant
# # from sqlalchemy.ext.declarative import declarative_base

# # import mysql.connector
# # from mysql.connector import Error


# # from app.conf.config import settings

# # BaseModel_Base = declarative_base()

# # tenant_engine = {}
# # db = DefaultSessionLocal()
# # tenant_name = db.query(Tenant).filter(Tenant.name).all()
# # if tenant_name:
# #      tenant_engine = tenant_name.name

# # tenantSession = ""
# # def get_tenant_db(tenant_name:str):
# #     if tenant_name not in tenant_engine: 
# #         # db = DefaultSessionLocal()
# #         # tenant = db.query(Tenant).filter(Tenant.name == tenant_name).first()
# #          raise HTTPException(status_code=404, detail=f"Tenant database not found.")  
# #         # tenant_engine[tenant_id] = create_engine(tenant_db_url)
# #         # db.close()
# #     else:
# #                 try:
# #                     # # Connect to MySQL Server
# #                     # host="localhost"
# #                     # connection = mysql.connector.connect(
# #                     #     host=host,
# #                     #     user="root",
# #                     #     password=""
# #                     # )

# #                     # cursor = connection.cursor()

# #                     # # Create database if it doesn't exist
# #                     # cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{tenant_name}`")
# #                     # print(f"Database '{tenant_name}' created successfully.")


# #                     tenant_engine[tenant_name] = create_engine(f"mysql+pymysql://root:@localhost/{tenant_name}")
# #                     TenantSessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=tenant_engine[tenant_name])
# #                     tenantSession = TenantSessionLocal
# #                     # BaseModel_Base = declarative_base()
# #                     BaseModel_Base.metadata.create_all(bind=tenant_engine[tenant_name])
# #                     # cursor.close()
# #                     # connection.close()
# #                     # return TenantSessionLocal()

# #                     # # Return the new database connection URL
# #                     # return {
# #                     # "message":f"mysql+pymysql://{user}:{password}@{host}/{db_name}"
# #                     # }
# #                     print("TENANT DATABASE FOUND!")
# #                     print(f"TENANT DATABASE FOUND! {tenant_engine[tenant_name]}")
# #                 except Error as e:
# #                     print("Error while connecting to MySQL:", e)
# #                     return None
                
# #         # tenant_db_url = "pymysql+mysql://root@localhost:test"
# #     #     tenant_engine[tenant_name] = create_engine(tenant.database_url)
# #     # TenantSessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=tenant_engine[tenant_name])
# #     return TenantSessionLocal()




from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# from app.database.base import DefaultSessionLocal
# from app.dependencies.tenantDependency import get_tenant
from app.database.base import get_db_session
from app.models.tenant import Tenant

import mysql.connector
from mysql.connector import Error
from sqlalchemy.ext.declarative import declarative_base

# from app.models.user import User
BaseModel_Base = declarative_base()

tenant_engine = {}

# def get_tenant_db(tenant_name: str):
#     if tenant_name not in tenant_engine:
#         raise HTTPException(status_code=404, detail=f"Tenant database not found.")
    
#     try:
#         tenant_engine[tenant_name] = create_engine(f"mysql+pymysql://root:@localhost/{tenant_name}")
#         TenantSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=tenant_engine[tenant_name])
#         BaseModel_Base.metadata.create_all(bind=tenant_engine[tenant_name])
#         print(f"TENANT DATABASE FOUND! {tenant_engine[tenant_name]}")
#     except Exception as e:
#         print("Error while connecting to MySQL:", e)
#         raise HTTPException(status_code=500, detail="Database connection error")
    
#     return TenantSessionLocal()

# def get_db():
#     db = DefaultSessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# def get_tenant_session(tenant_name: str = Depends(get_tenant)):
#     tenant_session = get_tenant_db(tenant_name)
#     try:
#         yield tenant_session
#     finally:
#         tenant_session.close()


async def create_tenant_database(db_name, user:str | None ="root", password:str | None =""):
    try:
        # Connect to MySQL Server
        host="localhost"
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password
        )

        cursor = connection.cursor()

        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        print(f"Database '{db_name}' created successfully.")

        engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}/{db_name}")
        BaseModel_Base.metadata.create_all(bind=engine)

        cursor.close()
        connection.close()
        print(f"mysql+pymysql://{user}:{password}@{host}/{db_name}")
        # # Return the new database connection URL
        return f"mysql+pymysql://{user}:{password}@{host}/{db_name}"
    
        

    except Error as e:
        print("Error while connecting to MySQL:", e)
        return None

def get_tenant_db(tenant_name: str, db:Session = Depends(get_db_session())):
    # default_db = get_db_session()
    tenant = db.query(Tenant).filter(Tenant.name).first()
    if not tenant:#tenant_name not in tenant_engine:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_name} databases not found.")

    try:
        # Create or retrieve the engine for the tenant
        tenant_engine[tenant.name] = create_engine(f"mysql+pymysql://root:@localhost/{tenant.name}")
        TenantSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=tenant_engine[tenant_name])
        BaseModel_Base.metadata.create_all(bind=tenant_engine[tenant_name])
        print(f"TENANT DATABASE FOUND! {tenant_engine[tenant_name]}")
        return TenantSessionLocal
    except Exception as e:
        print("Error while connecting to MySQL:", e)
        raise HTTPException(status_code=500, detail="Database connection error")