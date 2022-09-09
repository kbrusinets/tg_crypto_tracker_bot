import re

from aiogram import types
from aiogram.dispatcher import FSMContext, filters
from .states import AddWalletStates

from main import dp, backend, cancel_commands, default_bot_commands
from utils import keyboard as kb

wallet_regex = re.compile('^0x[a-fA-F0-9]{40}$')


@dp.message_handler(commands='add')
async def adding_wallet_start(message: types.Message):
    await AddWalletStates.choosing_chain.set()
    await cancel_commands()
    await message.reply("Select chain.", reply_markup=kb.create_keyboard_from_list(backend.get_chains_keys()))


@dp.message_handler(state=AddWalletStates.choosing_chain)
async def adding_wallet_choosing_chain(message: types.Message, state: FSMContext):
    if message.text in backend.get_chains_keys():
        async with state.proxy() as data:
            data['chain_key'] = message.text
        await AddWalletStates.choosing_wallet.set()
        await message.reply("Enter wallet address.", reply_markup=kb.create_cancel_keyboard())
    else:
        await message.reply('Incorrect chain key. Try again.', reply_markup=kb.create_keyboard_from_list(backend.get_chains_keys()))


@dp.message_handler(state=AddWalletStates.choosing_wallet)
async def adding_wallet_choosing_wallet(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if wallet_regex.match(message.text):
            wallet_added = await backend.add_wallet_tracking(chain_key=data['chain_key'], user_id=message.chat.id, wallet_address=message.text)
            if wallet_added:
                data['wallet_address'] = message.text
                await AddWalletStates.naming_wallet.set()
                await message.reply(f'Wallet {message.text} in {data["chain_key"]} chain has been successfully added to track. Give it a name. "Cancel" to skip.', reply_markup=kb.create_cancel_keyboard())
            else:
                existing_wallet_name = await backend.get_wallet_name(chain_key=data['chain_key'], user_id=message.chat.id, wallet_address=message.text)
                await message.reply(f'Error. Wallet is already being tracked{f" ({existing_wallet_name})" if existing_wallet_name else ""}. Enter another address.', reply_markup=kb.create_cancel_keyboard())
        else:
            await message.reply('Incorrect wallet address. Try again.', reply_markup=kb.create_cancel_keyboard())


@dp.message_handler(state=AddWalletStates.naming_wallet)
async def adding_wallet_choosing_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        wallet_named = await backend.give_wallet_a_name(
            chain_key=data['chain_key'],
            user_id=message.chat.id,
            wallet_address=data['wallet_address'],
            wallet_name=message.text
        )
        if wallet_named:
            await default_bot_commands()
            await state.finish()
            await message.reply(f'Wallet {data["wallet_address"]} successfully named "{message.text}".', reply_markup=types.ReplyKeyboardRemove())
        else:
            await message.reply('You already use this name. Choose another one. "Cancel" to skip.', reply_markup=kb.create_cancel_keyboard())


@dp.message_handler(filters.RegexpCommandsFilter(regexp_commands=['add_(.+)_(0x[a-fA-F0-9]{40})']))
async def adding_regex_wallet(message: types.Message, regexp_command, state: FSMContext):
    await cancel_commands()
    chain_key = regexp_command.group(1)
    wallet = regexp_command.group(2)
    if chain_key not in backend.get_chains_keys():
        await message.reply('Incorrect chain key.', reply_markup=types.ReplyKeyboardRemove())
    else:
        if wallet_regex.match(wallet):
            wallet_added = await backend.add_wallet_tracking(chain_key=chain_key, user_id=message.chat.id,
                                                             wallet_address=wallet)
            if wallet_added:
                async with state.proxy() as data:
                    data['chain_key'] = chain_key
                    data['wallet_address'] = wallet
                await cancel_commands()
                await AddWalletStates.naming_wallet.set()
                await message.reply(
                    f'Wallet {wallet} in {chain_key} chain has been successfully added to track. Give it a name. "Cancel" to skip.',
                    reply_markup=kb.create_cancel_keyboard())
            else:
                existing_wallet_name = await backend.get_wallet_name(chain_key=chain_key,
                                                                     user_id=message.chat.id,
                                                                     wallet_address=wallet)
                await message.reply(
                    f'Error. Wallet is already being tracked{f" ({existing_wallet_name})" if existing_wallet_name else ""}',
                    reply_markup=types.ReplyKeyboardRemove())
        else:
            await message.reply('Incorrect wallet address.', reply_markup=types.ReplyKeyboardRemove())
