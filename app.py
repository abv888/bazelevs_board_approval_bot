import os
import asyncio

from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery
from dotenv import load_dotenv, find_dotenv

from keyboards.document_inline_keyboard import get_callback_buttons

load_dotenv(find_dotenv())

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Username, User, Document
from database.orm_query import (orm_add_username, orm_get_username, orm_get_user, orm_add_user, orm_get_all_users,
                                orm_add_document, orm_update_document, orm_get_document, orm_get_all_documents,
                                orm_update_document_status_to_end)

from common.bot_command_list import private
from database.engine import drop_db, create_db, session_maker
from middlewares.db import DataBaseSession

bot = Bot(token=os.getenv('TOKEN'))

dp = Dispatcher()


@dp.message(Command('start'))
async def start_handler(message: types.Message, session: AsyncSession):
    user_username = await orm_get_username(session=session, username=message.from_user.username)
    if user_username is None:
        await message.answer("Нет доступа")
    else:
        user = await orm_get_user(session=session, id=message.from_user.id)
        if user is None:
            await orm_add_user(session=session, user=User(id=message.from_user.id,
                                                          full_name=message.from_user.full_name,
                                                          username=message.from_user.username))
            await message.answer(text="Добро пожаловать в бот согласования документов. Вам доступен полный функционал")
        else:
            await message.answer(text="Добро пожаловать в бот согласования документов")


@dp.message(Command('help'))
async def help_handler(message: types.Message):
    await message.answer(text="/start - Запустить бота \n"
                              "/help - Выдать список командс с обьяснением \n"
                              "/adduser - Добавить нового члена совета директоров \n"
                              "/new - Добавить новый документ для согласования \n"
                              "/status -: Показать статус текущего согласования"
                         )


@dp.message(Command('adduser'))
async def add_user_handler(message: types.Message, session: AsyncSession):
    user = await orm_get_user(session=session, id=message.from_user.id)
    if user is None:
        await message.answer("Нет доступа")
    else:
        status = True
        for document in await orm_get_all_documents(session=session):
            if document.status:
                status = False
        if status:
            await message.answer(
                text="Пришлите никнейм пользователя для добавления в совет директоров в формате @username")
        else:
            await message.answer(text="Идет согласование. В данный момент невозможно добавить участника")


@dp.message(F.text.contains("@"))
async def get_username_handler(message: types.Message, session: AsyncSession):
    user = await orm_get_user(session=session, id=message.from_user.id)
    if user is None:
        await message.answer("Нет доступа")
    else:
        username = message.text[1:]
        new_username = Username(username=username)
        status = True
        for document in await orm_get_all_documents(session=session):
            if document.status:
                status = False
        if status:
            await orm_add_username(session, new_username)
            await message.answer(f"Пользователь {message.text} успешно добавлен в список директоров")
        else:
            await message.answer(text="Идет согласование. В данный момент невозможно добавить участника")


@dp.message(Command('new'))
async def new_document_handler(message: types.Message, session: AsyncSession):
    user = await orm_get_user(session=session, id=message.from_user.id)
    if user is None:
        await message.answer("Нет доступа")
    else:
        await message.answer(text="Пришлите документ для согласования")


@dp.message(F.document)
async def get_document_handler(message: types.Message, session: AsyncSession):
    user = await orm_get_user(session=session, id=message.from_user.id)
    if user is None:
        await message.answer("Нет доступа")
    else:
        status = True
        for document in await orm_get_all_documents(session=session):
            if document.filename == message.document.file_name:
                status = False
        if status:
            votes_dict = dict()
            for user in await orm_get_all_users(session=session):
                if user.id != message.from_user.id:
                    votes_dict[user.full_name] = ""
            vote = "approve"
            votes_dict[message.from_user.full_name] = vote
            document = Document(
                file_id=message.document.file_id,
                filename=message.document.file_name,
                sender_id=message.from_user.id,
                message_id=message.message_id,
                votes=votes_dict,
                voted=1,
                status=True
            )
            await orm_add_document(session=session, document=document)
            for user in await orm_get_all_users(session=session):
                if user.id != message.from_user.id:
                    await bot.send_document(
                        chat_id=user.id,
                        document=message.document.file_id,
                        reply_markup=get_callback_buttons(btns={
                            'Согласовать': f'approve',
                            'Не согласовать': f'reject',
                            'Воздержаться': f'hold'
                        })
                    )
        else:
            await message.answer(text="Документ с таким именем уже существует.")


@dp.callback_query(lambda query: query.data in ['approve', 'reject', 'hold'])
async def vote_callback(query: CallbackQuery, session: AsyncSession):
    doc = await orm_get_document(session=session, document_name=query.message.document.file_name)
    if doc is None:
        pass
    else:
        vote = ""
        if query.data == 'approve':
            vote = "Согласовал"
        elif query.data == 'reject':
            vote = "Не согласовал"
        elif query.data == 'hold':
            vote = "Воздержался"
        votes = dict(doc.votes)
        if votes[f'{query.from_user.full_name}'] == "":
            await orm_update_document(
                session=session,
                document_name=query.message.document.file_name,
                voter=query.from_user.full_name,
                vote=query.data)
            await bot.send_message(
                doc.sender_id,
                text=f"<b>{query.from_user.full_name}</b> - <b>{vote}</b>",
                reply_to_message_id=doc.message_id,
                parse_mode=ParseMode.HTML
            )
        else:
            await bot.send_message(
                query.from_user.id,
                text="Ваш голос уже учтен"
            )
    document = await orm_get_document(session=session, document_name=query.message.document.file_name)
    if document is None:
        pass
    else:
        if document.voted == len(await orm_get_all_users(session=session)):
            await orm_update_document_status_to_end(session=session, document_name=query.message.document.file_name)
            final_votes = dict(document.votes)
            final_votes_string = ""
            approved_string = ""
            hold_string = ""
            rejected_string = ""
            for voter in final_votes.keys():
                if final_votes[voter] == "approve":
                    approved_string += f"{voter}\n"
                elif final_votes[voter] == "hold":
                    hold_string += f"{voter}\n"
                elif final_votes[voter] == "reject":
                    rejected_string += f"{voter}\n"
            if approved_string != "":
                final_votes_string += "<b>Согласовали:\n</b>" + approved_string + "\n"
            if hold_string != "":
                final_votes_string += "<b>Воздержались\n</b>" + hold_string + "\n"
            if rejected_string != "":
                final_votes_string += "<b>Не согласовали\n</b>" + rejected_string
            await bot.send_message(
                document.sender_id,
                text="Согласование окончено"
            )
            await bot.send_message(
                document.sender_id,
                text=final_votes_string,
                parse_mode=ParseMode.HTML,
                reply_to_message_id=document.message_id
            )


@dp.message(Command('status'))
async def status_handler(message: types.Message, session: AsyncSession):
    user = await orm_get_user(session=session, id=message.from_user.id)
    if user is None:
        await message.answer("Нет доступа")
    else:
        flag = False
        all_users_count = len(await orm_get_all_users(session=session))
        for document in await orm_get_all_documents(session=session):
            if document.status:
                if document.sender_id == message.from_user.id:
                    flag = True
                    result_status = (
                            "Документ в согласовании\n" +
                            f"Проголосовало - <b>{document.voted}</b> из <b>{all_users_count}</b> членов совета"
                    )
                    await bot.send_message(
                        message.from_user.id,
                        result_status,
                        reply_to_message_id=document.message_id,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    flag = True
                    await bot.send_message(
                        message.from_user.id,
                        f"Документ <b>{document.filename}</b> в согласовании\n"
                        f"Проголосовало - <b>{document.voted}</b> из <b>{all_users_count}</b> членов совета",
                        parse_mode=ParseMode.HTML
                    )

        if not flag:
            await bot.send_message(
                message.from_user.id,
                "Сейчас нет документов на согласовании"
            )


async def on_startup(bot):
    run_param = False
    if run_param:
        await drop_db()

    await create_db()


async def on_shutdown(bot):
    print('Bot shut down...')


async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.update.middleware(DataBaseSession(session_pool=session_maker))

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(commands=private)
    await dp.start_polling(bot)


asyncio.run(main())
