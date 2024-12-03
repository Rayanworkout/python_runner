class MissingEnvironmentVariable(Exception):
    """Exception raised when an environment variable is missing."""

    pass


class MissingConfigurationVariable(Exception):
    """Exception raised when a configuration variable is missing from config file."""

    pass


class BadRecipientList(Exception):
    """Exception raised when the recipient list is not valid."""

    pass

class BadPythonInterpreter(Exception):
    """Exception raised when the recipient list is not valid."""

    pass
