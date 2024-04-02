from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Integer, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    created: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now())
    updated: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now(), onupdate=datetime.now())


class Username(Base):
    __tablename__ = 'usernames'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    username = Column('username', String)


class User(Base):
    __tablename__ = 'users'

    id = Column('id', Integer, primary_key=True)
    full_name = Column('fullname', String)
    username = Column('username', String)


class Document(Base):
    __tablename__ = 'documents'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    file_id = Column('file_id', String)
    filename = Column('filename', String)
    sender_id = Column('sender_id', Integer, ForeignKey('users.id'))
    message_id = Column('message_id', Integer)
    votes = Column('votes', JSON)
    voted = Column('voted', Integer)
    status = Column('status', Boolean)
