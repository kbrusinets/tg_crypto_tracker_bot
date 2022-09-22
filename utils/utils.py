import decimal
from typing import Optional


def float_to_str(f: float):
    ctx = decimal.Context()
    ctx.prec = 20
    dec = ctx.create_decimal(repr(f))
    return format(dec, 'f')


def trim_address(address: str):
    return address[:4] + '...' + address[-3:]


def remove_trailing_zeros_from_address(address: str) -> Optional[str]:
    address = address.removeprefix('0x')
    if len(address) == 64:
        return '0x' + address[24:]
    return None
