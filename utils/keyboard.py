from typing import List
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from main import backend


def create_cancel_keyboard() -> ReplyKeyboardMarkup:
    button_cancel = KeyboardButton('Cancel')
    kb_cancel = ReplyKeyboardMarkup(resize_keyboard=True)
    kb_cancel.add(button_cancel)
    return kb_cancel


def create_keyboard_from_list(keys: List) -> ReplyKeyboardMarkup:
    result = ReplyKeyboardMarkup(resize_keyboard=True)
    for key in keys:
        result.add(KeyboardButton(key))
    return result


async def create_keyboard_from_tracked_addresses(chain_key: str, user_id: int, page: int) -> ReplyKeyboardMarkup:
    trackings = await backend.get_user_trackings(chain_key=chain_key, user_id=user_id)
    for_buttons = [f"{tracking.wallet}{f' ({tracking.custom_name})' if tracking.custom_name else ''}" for
                   tracking in trackings[(page - 1) * 10:page * 10]]
    if page > 1:
        for_buttons.append(f'Page {page - 1}')
    if len(trackings) >= page * 10:
        for_buttons.append(f'Page {page + 1}')
    return create_keyboard_from_list(for_buttons)


async def create_keyboard_for_deleting(chain_key: str, user_id: int, page: int) -> ReplyKeyboardMarkup:
    paging_keyboard = await create_keyboard_from_tracked_addresses(chain_key=chain_key, user_id=user_id, page=page)
    result = ReplyKeyboardMarkup(resize_keyboard=True)
    result.add('Remove all wallets.')
    for button in paging_keyboard.keyboard:
        result.add(button[0])
    return result


def create_yes_no_keyboard() -> ReplyKeyboardMarkup:
    return create_keyboard_from_list(['Yes', 'No'])
