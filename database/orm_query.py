from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Username, Document


async def orm_add_user(session: AsyncSession, user: User):
    session.add(user)
    await session.commit()


async def orm_get_user(session: AsyncSession, id: int):
    query = select(User).where(User.id == id)
    result = await session.execute(query)
    return result.scalar()


async def orm_get_all_users(session: AsyncSession):
    query = select(User)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_add_username(session: AsyncSession, data: Username):
    session.add(data)
    await session.commit()


async def orm_get_username(session: AsyncSession, username: str):
    query = select(Username).where(Username.username == username)
    result = await session.execute(query)
    return result.scalar()


async def orm_add_document(session: AsyncSession, document: Document):
    session.add(document)
    await session.commit()


async def orm_get_document(session: AsyncSession, document_name: str):
    query = select(Document).where(Document.filename == document_name)
    result = await session.execute(query)
    return result.scalar()


async def orm_get_all_documents(session: AsyncSession):
    query = select(Document)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_update_document(session: AsyncSession, document_name: str, voter: str, vote: str):
    query = update(Document).where(Document.filename == document_name).values(
         votes=func.json_set(
             Document.votes,
             f"$.{voter}",
             vote
         ),
         voted=Document.voted + 1
    )
    await session.execute(query)
    await session.commit()


async def orm_update_document_status_to_end(session: AsyncSession, document_name: str):
    query = update(Document).where(Document.filename == document_name).values(
         status=False
    )
    await session.execute(query)
    await session.commit()
