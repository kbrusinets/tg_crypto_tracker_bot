import decimal


def float_to_str(f: float):
    ctx = decimal.Context()
    ctx.prec = 20
    dec = ctx.create_decimal(repr(f))
    return format(dec, 'f')

def trim_address(address: str):
    return address[:4] + '...' + address[-3:]