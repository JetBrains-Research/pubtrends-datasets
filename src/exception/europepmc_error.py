class EuropePMCError(Exception):
    """
    Class for exceptions that are caused by problems with the EuropePMC API.
    """
    def __init__(self, message: str):
        super().__init__(self, message)