from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)


class Shape(Base):
    __tablename__ = "shapes"

    id = Column(String, primary_key=True, index=True)
    type = Column(String, nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    radius = Column(Integer, nullable=True)
    text = Column(String, nullable=True)
    selectedBy = Column(ARRAY(String), nullable=False, server_default="{}")
