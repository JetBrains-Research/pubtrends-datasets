class EntrezError(Exception):
    """
    Class for exceptions that are caused by problems with the Entrez APIs.
    """

    def __init__(self, message: str):
        super().__init__(message)
