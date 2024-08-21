from click import ParamType, Context, Parameter
from enum import Enum

class LogLevel(Enum):
    NOTSET = 0
    DEBUG = 10
    VERBOSE = 15
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

class LogParam(ParamType):
    name = "LogParam"

    def convert(self, value: int | str, param: Parameter | None, ctx: Context | None) -> int:
        if isinstance(value, int):
            return value

        # Convert string representation to int
        if not hasattr(LogLevel, value):
            self.fail(f"{value!r} is not a valid log level", param, ctx)

        return LogLevel[value].value

    def get_metavar(self, param: Parameter) -> str | None:
        # Print out the choices
        return "|".join(LogLevel._member_map_)
