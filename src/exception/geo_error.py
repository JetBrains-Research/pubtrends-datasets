class GEOError(Exception):
    """
    Class for exceptions that are caused by problems with GEO.
    """

    def __init__(self, message: str):
        super().__init__(message)
