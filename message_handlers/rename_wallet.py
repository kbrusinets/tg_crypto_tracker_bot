import re

from aiogram import types
from aiogram.dispatcher import FSMContext, filters
from .states import RenameWalletStates
from utils import keyboard as kb

from main import cancel_commands, backend, dp, default_bot_commands


@dp.message_handler(commands='rename')
async def renaming_wallet_start(message: types.Message):
    await RenameWalletStates.choosing_chain.set()
    await cancel_commands()
    await message.reply("Select chain.", reply_markup=kb.create_keyboard_from_list(backend.get_chains_keys()))


@dp.message_handler(state=RenameWalletStates.choosing_chain)
async def renaming_wallet_choosing_chain(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.text in backend.get_chains_keys() and 'chain_key' not in data:
            data['chain_key'] = message.text
            await RenameWalletStates.choosing_wallet.set()
            await message.reply("Choose or input wallet address. You can also input wallet name.",
                                reply_markup=await kb.create_keyboard_from_tracked_addresses(
                                    chain_key=data['chain_key'],
                                    user_id=message.chat.id,
                                    page=1))
        elif message.text not in backend.get_chains_keys() and 'chain_key' not in data:
            await message.reply("Incorrect chain key. Try again.", reply_markup=kb.create_keyboard_from_list(backend.get_chains_keys()))


@dp.message_handler(state=RenameWalletStates.choosing_wallet)
async def renaming_wallet_choosing_wallet(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if re.search('^Page [\d]*$', message.text):
            page = int(re.search('^Page ([\d]*)$', message.text).group(1))
            await message.reply("Choose or input wallet address.",
                                reply_markup=await kb.create_keyboard_from_tracked_addresses(chain_key=data['chain_key'],
                                                                                       user_id=message.chat.id,
                                                                                       page=page))
        elif re.search('^(0x[a-fA-F0-9]{40})(\s\(.*\))*$', message.text):
            wallet = re.search('^(0x[a-fA-F0-9]{40})(\s\(.*\))*$', message.text).group(1)
            trackings = await backend.get_user_trackings(chain_key=data['chain_key'], user_id=message.chat.id, wallet_address=wallet)
            if not trackings:
                await message.reply(f"Error. Wallet {wallet} is not tracked. Choose another.",
                                    reply_markup=await kb.create_keyboard_from_tracked_addresses(chain_key=data['chain_key'],
                                                                                           user_id=message.chat.id,
                                                                                           page=1))
            else:
                data['wallet'] = trackings[0].wallet
                await message.reply(
                    f"Enter a new name for {trackings[0].wallet}{f' ({trackings[0].custom_name})' if trackings[0].custom_name else ''}")
                await RenameWalletStates.renaming_wallet.set()
        else:
            trackings = await backend.get_user_trackings(chain_key=data['chain_key'], user_id=message.chat.id,
                                                        custom_name=message.text)
            if not trackings:
                await message.reply(f"Error. Wallet with name {message.text} is not tracked. Choose another.",
                                    reply_markup=await kb.create_keyboard_from_tracked_addresses(chain_key=data['chain_key'],
                                                                                           user_id=message.chat.id,
                                                                                           page=1))
            else:
                data['wallet'] = trackings[0].wallet
                await message.reply(
                    f"Enter a new name for {trackings[0].wallet}{f' ({trackings[0].custom_name})' if trackings[0].custom_name else ''}")
                await RenameWalletStates.renaming_wallet.set()


@dp.message_handler(state=RenameWalletStates.renaming_wallet)
async def renaming_wallet_start(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        await backend.give_wallet_a_name(chain_key=data['chain_key'],
                                         user_id=message.chat.id,
                                         wallet_address=data['wallet'],
                                         wallet_name=message.text
                                         )
        await default_bot_commands()
        await state.finish()
        await message.reply(f"Wallet {data['wallet']} successfully renamed to {message.text}", reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(filters.RegexpCommandsFilter(regexp_commands=['rn_(.+)_(0x[a-fA-F0-9]{40})']))
async def renaming_regex_wallet(message: types.Message, regexp_command, state: FSMContext):
    await cancel_commands()
    chain_key = regexp_command.group(1)
    wallet = regexp_command.group(2)
    if chain_key not in backend.get_chains_keys():
        await message.reply('Incorrect chain key.', reply_markup=types.ReplyKeyboardRemove())
    else:
        trackings = await backend.get_user_trackings(chain_key=chain_key, user_id=message.chat.id,
                                                     wallet_address=wallet)
        if not trackings:
            await message.reply(f"Error. Wallet {wallet} is not tracked.", reply_markup=types.ReplyKeyboardRemove())
        else:
            async with state.proxy() as data:
                data['chain_key'] = chain_key
                data['wallet'] = wallet
            await cancel_commands()
            await RenameWalletStates.renaming_wallet.set()
            await message.reply(
                f"Enter a new name for {wallet}{f' ({trackings[0].custom_name})' if trackings[0].custom_name else ''}")
