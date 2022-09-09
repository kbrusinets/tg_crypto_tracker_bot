from aiogram.dispatcher.filters.state import StatesGroup, State


class AddWalletStates(StatesGroup):
    choosing_chain = State()
    choosing_wallet = State()
    naming_wallet = State()


class RenameWalletStates(StatesGroup):
    choosing_chain = State()
    choosing_wallet = State()
    renaming_wallet = State()


class DeleteWalletStates(StatesGroup):
    choosing_chain = State()
    choosing_wallet = State()
    deleting_wallet = State()