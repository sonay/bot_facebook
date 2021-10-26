class PrivateAccountException(Exception):
    """ Raised to signal account page is not public """


class TemporarilyBannedException(Exception):
    """ Raised when Facebook Santa sees us being naughty """
