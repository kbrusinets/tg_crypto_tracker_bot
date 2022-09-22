import re

from aiogram import types
from aiogram.dispatcher import FSMContext
from .states import DeleteWalletStates
from utils import keyboard as kb

from main import cancel_commands, backend, dp, default_bot_commands


@dp.message_handler(commands='remove')
async def deleting_wallet_start(message: types.Message):
    await DeleteWalletStates.choosing_chain.set()
    await cancel_commands()
    await message.reply("Select chain.", reply_markup=kb.create_keyboard_from_list(backend.get_chains_keys()))


@dp.message_handler(state=DeleteWalletStates.choosing_chain)
async def deleting_wallet_choosing_chain(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.text in backend.get_chains_keys() and 'chain_key' not in data:
            trackings = await backend.get_user_trackings(chain_key=message.text, user_id=message.chat.id)
            if len(trackings) == 0:
                await default_bot_commands()
                await state.finish()
                await message.reply(f"You track no wallets in {message.md_text}.",
                                    reply_markup=types.ReplyKeyboardRemove())
            else:
                data['chain_key'] = message.text
                await DeleteWalletStates.choosing_wallet.set()
                await message.reply("Choose or input wallet address. You can also input wallet name.",
                                    reply_markup=await kb.create_keyboard_for_deleting(
                                        trackings=trackings,
                                        page=1))
        elif message.text not in backend.get_chains_keys() and 'chain_key' not in data:
            await message.reply("Incorrect chain key. Try again.",
                                reply_markup=kb.create_keyboard_from_list(backend.get_chains_keys()))


@dp.message_handler(state=DeleteWalletStates.choosing_wallet)
async def deleting_wallet_choosing_wallet(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if re.search('^Page [\d]*$', message.text):
            page = int(re.search('^Page ([\d]*)$', message.text).group(1))
            trackings = await backend.get_user_trackings(chain_key=message.text, user_id=message.chat.id)
            await message.reply("Choose or input wallet address.",
                                reply_markup=await kb.create_keyboard_for_deleting(
                                    trackings=trackings,
                                    page=page))
        elif re.search('^(0x[a-fA-F0-9]{40})(\s\(.*\))*$', message.text):
            wallet = re.search('^(0x[a-fA-F0-9]{40})(\s\(.*\))*$', message.text).group(1)
            wallet_tracking = await backend.get_user_trackings(chain_key=data['chain_key'], user_id=message.chat.id, wallet_address=wallet)
            if not wallet_tracking:
                trackings = await backend.get_user_trackings(chain_key=data['chain_key'], user_id=message.chat.id)
                await message.reply(f"Error. Wallet {wallet} is not tracked. Choose another.",
                                    reply_markup=await kb.create_keyboard_for_deleting(trackings=trackings,
                                                                                       page=1))
            else:
                data['wallet'] = wallet_tracking[0].wallet
                data['custom_name'] = wallet_tracking[0].custom_name
                await DeleteWalletStates.deleting_wallet.set()
                await message.reply(
                    f"Are you sure you want to stop tracking wallet {data['wallet']}{f''' ({data['custom_name']})''' if data['custom_name'] else ''}?",
                    reply_markup=kb.create_yes_no_keyboard())
        elif message.text == 'Remove all wallets.':
            data['wallet'] = 'all'
            await DeleteWalletStates.deleting_wallet.set()
            await message.reply(
                f"Are you sure you want to stop tracking all wallets?",
                reply_markup=kb.create_yes_no_keyboard())
        else:
            wallet_tracking = await backend.get_user_trackings(chain_key=data['chain_key'], user_id=message.chat.id,
                                                         custom_name=message.text)
            if not wallet_tracking:
                trackings = await backend.get_user_trackings(chain_key=data['chain_key'], user_id=message.chat.id)
                await message.reply(f"Error. Wallet with name {message.text} is not tracked. Choose another.",
                                    reply_markup=await kb.create_keyboard_for_deleting(
                                        trackings=trackings,
                                        page=1))
            else:
                data['wallet'] = wallet_tracking[0].wallet
                data['custom_name'] = wallet_tracking[0].custom_name
                await DeleteWalletStates.deleting_wallet.set()
                await message.reply(
                    f"Are you sure you want to stop tracking wallet {data['wallet']}{f''' ({data['custom_name']})''' if data['custom_name'] else ''}?",
                    reply_markup=kb.create_yes_no_keyboard())


@dp.message_handler(state=DeleteWalletStates.deleting_wallet)
async def renaming_wallet_start(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.text == 'Yes':
            if data['wallet'] == 'all':
                await backend.stop_wallet_tracking(chain_key=data['chain_key'],
                                                   user_id=message.chat.id,
                                                   wallet_address=None
                                                   )
                response = "All wallets successfully removed from tracking."
            else:
                await backend.stop_wallet_tracking(chain_key=data['chain_key'],
                                                   user_id=message.chat.id,
                                                   wallet_address=data['wallet']
                                                   )
                response = f"Wallet {data['wallet']} successfully removed from tracking."
            await default_bot_commands()
            await state.finish()
            await message.reply(response, reply_markup=types.ReplyKeyboardRemove())
        elif message.text == 'No':
            await default_bot_commands()
            await state.finish()
            await message.reply(f"Deleting cancelled.", reply_markup=types.ReplyKeyboardRemove())
        else:
            await message.reply(
                f"Unknown response. Are you sure you want to stop tracking wallet {data['wallet']}{f''' ({data['custom_name']})''' if data['custom_name'] else ''}?",
                reply_markup=kb.create_yes_no_keyboard())