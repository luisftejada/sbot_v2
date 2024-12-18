class CoinexClientBaseError(Exception):
    UNDEFINED_ERROR = -1

    def __init__(self, data, path, params, code=UNDEFINED_ERROR):
        self.data = data
        self.code = code
        self.path = path
        self.params = params


class InsuficientBalance(CoinexClientBaseError):
    pass


def getErrorClass(code):
    match code:
        case 3109:
            return InsuficientBalance
        case _:
            return CoinexClientBaseError


def raiseError(code, data, path, params):
    errorClass = getErrorClass(code)
    raise errorClass(data, path, params, code=code)
