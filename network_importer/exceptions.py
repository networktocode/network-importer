class NetworkImporterException(Exception):
    """Network Importer Exception."""

    def __init__(self, reason, message, **kwargs):
        """Initialize exception class."""
        super(NetworkImporterException, self).__init__(kwargs)
        self.reason = reason
        self.message = message

    def __str__(self):
        """Modified string output."""
        return f"{self.__class__.__name__}: {self.reason} - {self.message}"
