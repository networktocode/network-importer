class NetworkImportException(Exception):
    def __init__(self, reason, message, **kwargs):
        super(NetworkImportException, self).__init__(kwargs)
        self.reason = reason
        self.message = message

    def __str__(self):
        return f"{self.__class__.__name__}: {self.reason} - {self.message}"