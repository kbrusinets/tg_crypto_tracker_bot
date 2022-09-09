import asyncio
import sys

from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.bot_command import BotCommand
from backend import Backend
from message_handlers.states import AddWalletStates, RenameWalletStates, DeleteWalletStates
from os import environ

API_TOKEN = environ.get('TG_NOTIFICATION_BOT_TG_TOKEN')
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
backend = Backend()


default_bot_commands_list = [
        BotCommand(command='/start', description='Start the bot / Rebuild the menu'),
        BotCommand(command='/add', description='Add wallet to track'),
        BotCommand(command='/rename', description='Rename the tracked wallet'),
        BotCommand(command='/remove', description='Stop tracking wallet(s)'),
    ]


async def default_bot_commands():
    await bot.set_my_commands(default_bot_commands_list)


async def cancel_commands():
    bot_commands = [
        BotCommand(command='/cancel', description='Cancel operation')
    ]
    await bot.set_my_commands(bot_commands)


@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    await default_bot_commands()
    current_state = await state.get_state()
    if current_state is None:
        return
    response = 'Cancelled.'
    if current_state in AddWalletStates.states_names:
        if current_state == AddWalletStates.naming_wallet.state:
            response = 'Wallet naming skipped.'
        else:
            response = 'Adding wallet cancelled.'
    elif current_state in RenameWalletStates.states_names:
        response = 'Renaming cancelled.'
    elif current_state in DeleteWalletStates.states_names:
        rsponse = 'Deleting cancelled.'
    await state.finish()
    await message.reply(response, reply_markup=types.ReplyKeyboardRemove())
    await default_bot_commands()


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await default_bot_commands()
    await message.reply(f"Hello! Use /help to get list of commands.")


@dp.message_handler(commands=['help'])
async def help_(message: types.Message):
    await default_bot_commands()
    lines = []
    for command in default_bot_commands_list:
        lines.append(f"{command.command} - {command.description}")
    await message.reply('\n'.join(lines))


async def monitor():
    await backend.start()
    async for notif in backend.monitor():
        text_message = await backend.format_notification(notif)
        if text_message:
            await bot.send_message(
                chat_id=notif.user_id,
                text=text_message,
                parse_mode="MarkdownV2",
                disable_web_page_preview=True
            )


if __name__ == '__main__':
    from message_handlers import dp

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.create_task(monitor())
    executor.start_polling(dp, skip_updates=True, loop=loop)
