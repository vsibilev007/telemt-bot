from aiogram.fsm.state import State, StatesGroup


class CreateUserFSM(StatesGroup):
    username = State()
    secret   = State()
    max_tcp  = State()
    expiration = State()
    quota    = State()
    max_ips  = State()
    confirm  = State()


class EditFieldFSM(StatesGroup):
    waiting_value = State()


class QuickAddFSM(StatesGroup):
    waiting_name = State()


class SearchUserFSM(StatesGroup):
    waiting_query = State()


class ProxyCheckFSM(StatesGroup):
    waiting_url = State()


class ConfigEditFSM(StatesGroup):
    waiting_toml = State()
