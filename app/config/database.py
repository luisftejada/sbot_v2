import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

user = os.environ.get("SBOTV2_USER", "user")
password = os.environ.get("SBOTV2_PASSWORD", "password")
env_file = os.environ.get("ENV_FILE_PATH", ".env")

load_dotenv(env_file, override=True)

DATABASE_URL = os.environ.get("DATABASE_SBOTV2_DB_URL", "")
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


commands_to_add_new_user = """
create database sbotv2_db;
create user 'user'@'%' identified by 'password';
grant all privileges on sbotv2_db.* to 'user'@'%';
flush privileges;

create database sbotv2_testdb;
grant all privileges on sbotv2_testdb.* to 'user'@'%';
flush privileges;
"""
