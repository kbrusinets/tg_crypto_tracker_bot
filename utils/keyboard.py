from typing import List
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from services.db.schemas import TrackingMapSchema


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


async def create_keyboard_with_trackings_pagination(trackings: List[TrackingMapSchema], page: int) -> ReplyKeyboardMarkup:
    for_buttons = [f"{tracking.wallet}{f' ({tracking.custom_name})' if tracking.custom_name else ''}" for
                   tracking in trackings[(page - 1) * 10:page * 10]]
    if page > 1:
        for_buttons.append(f'Page {page - 1}')
    if len(trackings) >= page * 10:
        for_buttons.append(f'Page {page + 1}')
    return create_keyboard_from_list(for_buttons)


async def create_keyboard_for_deleting(trackings: List[TrackingMapSchema], page: int) -> ReplyKeyboardMarkup:
    paging_keyboard = await create_keyboard_with_trackings_pagination(trackings=trackings, page=page)
    result = ReplyKeyboardMarkup(resize_keyboard=True)
    result.add('Remove all wallets.')
    for button in paging_keyboard.keyboard:
        result.add(button[0])
    return result


def create_yes_no_keyboard() -> ReplyKeyboardMarkup:
    return create_keyboard_from_list(['Yes', 'No'])
