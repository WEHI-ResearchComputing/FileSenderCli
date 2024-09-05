from typing import Union
from click import ParamType, Context, Parameter
from enum import Enum
import logging

class LogLevel(Enum):
    NOTSET = 0
    DEBUG = 10
    #: Used for verbose logging that the average user wouldn't want
    VERBOSE = 15
    INFO = 20
    #: Used for basic feedback that a CLI user would expect
    FEEDBACK = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    def configure_label(self):
        """
        Configures the logging module to understand this log level
        """
        logging.addLevelName(self.value, self.name)

def configure_extra_levels():
    """
    Configures the logging module to understand the additional log levels
    """
    for level in (LogLevel.VERBOSE, LogLevel.FEEDBACK):
        level.configure_label()

class LogParam(ParamType):
    name = "LogParam"

    def convert(self, value: Union[int, str], param: Union[Parameter, None], ctx: Union[Context, None]) -> int:
        if isinstance(value, int):
            return value

        # Convert string representation to int
        if not hasattr(LogLevel, value):
            self.fail(f"{value!r} is not a valid log level", param, ctx)

        return LogLevel[value].value

    def get_metavar(self, param: Parameter) -> Union[str, None]:
        # Print out the choices
        return "|".join(LogLevel._member_map_)
