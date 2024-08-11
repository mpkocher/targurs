import abc
from typing import Any, Generic, TypeVar, Callable, TypeAlias, Self
from dataclasses import dataclass

try:
    from typing import override
except ImportError:
    from typing_extensions import override

__all__ = [
    "Targurs",
    "Success",
    "Failure",
    "Result",
    "NotFound",
    "ParsedArg",
    "extractor",
    "MyModel",
    "parsed_arg_list_to_dict",
    "Positional",
    "FlagReqKeyValueArg",
    "FlagNonReqKeyValueArg",
    "FlagNonReqArg",
    "FlagHelpAction",
    "FlagVersionAction",
]

T = TypeVar("T")
R = TypeVar("R")


class NotFound(Exception):
    pass


class Either(abc.ABC, Generic[T]):
    value: T
    __match_args__ = ("value",)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.value}>"

    @abc.abstractmethod
    def is_success(self) -> bool: ...

    def is_failure(self) -> bool:
        return not self.is_success()


class Failure(Either[Exception]):
    def __init__(self, error: Exception, /):
        self.value = error

    def map(self, f: Callable[[T], R]) -> Self:
        # FIXME. this is a bad idea.
        return self

    def is_success(self) -> bool:
        return False


class Success(Either[T]):
    def __init__(self, value: T, /):
        self.value: T = value

    def map(self, f: Callable[[T], R]) -> "Success[R]":
        return Success(f(self.value))

    def is_success(self) -> bool:
        return True


Result: TypeAlias = Success[T] | Failure


class Action(abc.ABC):
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

    @abc.abstractmethod
    def __call__(self) -> None: ...


class NoopAction(Action):
    @override
    def __call__(self) -> None:
        pass


class VersionAction(Action):
    def __init__(self, version: str):
        self.version = version

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.version}>"

    @override
    def __call__(self) -> None:
        print(self.version)


class HelpAction(Action):
    def __init__(self, message: str):
        # FIXME. this should have the formatter and raw Arg
        # to generate the help message
        self.message = message

    @override
    def __call__(self) -> None:
        print(self.message)


class CmdAction(Action):
    def __init__(self, func: Callable[[], None]):
        self.func = func

    @override
    def __call__(self) -> None:
        self.func()


class ToAction(abc.ABC):
    @abc.abstractmethod
    def to_action(self, sx: list[str]) -> tuple[Action, list[str]]:
        """Return the action and rest of the commandline args"""
        ...


def identity(x: T) -> T:
    return x


class ParsedArg(Generic[T]):
    def __init__(self, ix: str, value: T, /):
        # identifier
        self.ix = ix
        self.value = value

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.ix}:{self.value} >"


def parsed_arg_list_to_dict(px: list[ParsedArg[T]]) -> dict[str, Any]:
    """
    Transform a list of parsed arg to dict. This is useful to
    working with dataclasses, or other classes that can support a
    **d mechanism.

    FIXME. This isn't type-safe
    """
    return {p.ix: p.value for p in px}


class Extractor(Generic[T], abc.ABC):
    """Have to do this as a class because functions can't support generic's yet?"""

    @abc.abstractmethod
    def __call__(self, sx: list[str]) -> tuple[Result[ParsedArg[T]], list[str]]: ...


class ExtractPositional(Extractor[T]):
    def __init__(self, ix: str, converter: Callable[[Any], T]):
        self.ix = ix
        self.converter = converter

    @override
    def __call__(self, sx: list[str]) -> tuple[Result[ParsedArg[T]], list[str]]:
        """ix is the identifier of the positional argument"""
        nx = len(sx)
        if sx:
            rest = [] if nx < 2 else sx[1:]
            # for mypy
            pa: Result[ParsedArg[T]]
            try:
                value: T = self.converter(sx[0])
                pa = Success(ParsedArg(self.ix, value))
            except Exception as ex:
                pa = Failure(ex)
            return pa, rest
        else:
            return Failure(NotFound(f"Unable to find {self.ix}")), sx


class ExtractNonReqFlag(Extractor[T]):
    """extract a non-required flag

    -d or --debug will set the "set_value" otherwise, the default value will be used.
    """

    def __init__(self, ix: str, flags: tuple[str, str], default: T, set_value: T):
        self.ix = ix
        self.flags = flags
        self.default = default
        self.set_value = set_value  # Value that will be set if the flag is provided

    @override
    def __call__(self, sx: list[str]) -> tuple[Result[ParsedArg[T]], list[str]]:
        rest: list[str] = []
        nx = len(sx)
        for i, s in enumerate(sx):
            if s in self.flags:
                rx = sx[i + 1] if (i + 1) < nx else []
                rest.extend(rx)
                return Success(ParsedArg[T](self.ix, self.set_value)), rest
            else:
                rest.append(s)

        # use default value
        return Success(ParsedArg[T](self.ix, self.default)), rest


class ExtractReqFlagAndValue(Extractor[T]):
    """
    Extract a required key-value flag arg

    -f, --min-score 1.23
    """

    def __init__(self, ix: str, flags: tuple[str, str], converter: Callable[[Any], T]):
        self.ix = ix
        self.flags = flags
        self.converter = converter

    @override
    def __call__(self, sx: list[str]) -> tuple[Result[ParsedArg[T]], list[str]]:
        rest: list[str] = []
        nx = len(sx)
        for i, s in enumerate(sx):
            if s in self.flags and (i + 1) < nx:
                try:
                    raw_value = sx[i + 1]
                    rx = s[i + 2 :] if (i + 2) < nx else []
                    rest.extend(rx)
                    value: T = self.converter(raw_value)
                    return Success(ParsedArg[T](self.ix, value)), rest
                except Exception as ex:
                    return Failure(ex), rest
            else:
                rest.append(s)

        return Failure(NotFound(f"Failed to find {self.flags}")), rest


class ExtractNonReqFlagAndValue(Extractor[T]):
    """
    Extract a required key-value flag arg

    -f, --min-score 1.23
    """

    def __init__(
        self, ix: str, flags: tuple[str, str], converter: Callable[[Any], T], default: T
    ):
        self.ix = ix
        self.flags = flags
        self.converter = converter
        self.default = default

    @override
    def __call__(self, sx: list[str]) -> tuple[Result[ParsedArg[T]], list[str]]:
        rest: list[str] = []
        nx = len(sx)
        for i, s in enumerate(sx):
            if s in self.flags and (i + 1) < nx:
                try:
                    raw_value = sx[i + 1]
                    rx = s[i + 2 :] if (i + 2) < nx else []
                    rest.extend(rx)
                    value: T = self.converter(raw_value)
                    return Success(ParsedArg[T](self.ix, value)), rest
                except Exception as ex:
                    return Failure(ex), rest
            else:
                rest.append(s)

        # Use default if not found
        return Success(ParsedArg[T](self.ix, self.default)), rest


class Arg(abc.ABC, Generic[T]):
    """
    Need explicit items here.

    ix: str id
    name: str Display name
    typed: type -> (conversion/casting/validation) F(Any) -> Either[T]
    description: str | None ->
    """

    def __init__(
        self,
        ix: str,
        name: str,
        *,
        description: str | None = None,
    ):
        self.ix = ix
        self.name = name
        self.description = description

    @abc.abstractmethod
    def extract(self, sx: list[str]) -> tuple[Result[ParsedArg[T]], list[str]]: ...


class Positional(Arg[T]):
    def __init__(
        self,
        ix: str,
        name: str,
        converter: Callable[[Any], T],
        *,
        description: None | str = None,
    ):
        super().__init__(ix, name, description=description)
        self.converter = converter
        self.extractor = ExtractPositional(self.ix, self.converter)

    @override
    def extract(self, sx: list[str]) -> tuple[Result[ParsedArg[T]], list[str]]:
        return self.extractor(sx)


class FlagNonReqArg(Arg[T]):
    """A non-required flag that has a default value

    -d or --debug will set debug=True

    This is primarily intended for bool usecases
    """

    def __init__(
        self,
        ix: str,
        flags: tuple[str, str],
        name: str,
        converter: Callable[[Any], T],  # FIXME this doesn't really make sense?
        default: T,
        set_value: T,
        *,
        description: str | None = None,
    ):
        super().__init__(ix, name, description=description)
        self.flags = flags
        self.default = default
        self.converter = converter
        self._extractor = ExtractNonReqFlag[T](self.ix, self.flags, default, set_value)

    @override
    def extract(self, sx: list[str]) -> tuple[Result[ParsedArg[T]], list[str]]:
        return self._extractor(sx)


class FlagNonReqKeyValueArg(Arg[T]):
    """A non-required key Flag that will set the value. If no value provided, then default value will be used.

    -f or --min-score 1.23 (with default:1.00)
    """

    def __init__(
        self,
        ix: str,
        flags: tuple[str, str],
        name: str,
        converter: Callable[[Any], T],
        default: T,
        *,
        description: str | None = None,
    ):
        super().__init__(ix, name, description=description)
        self.flags = flags
        self.default = default
        self.converter = converter
        self._extractor = ExtractNonReqFlagAndValue[T](
            ix, flags, self.converter, self.default
        )

    @override
    def extract(self, sx: list[str]) -> tuple[Result[ParsedArg[T]], list[str]]:
        result, rest = self._extractor(sx)
        match result:
            case Success(pa):
                return Success(pa), rest
            case Failure(ex) if isinstance(ex, NotFound):
                return Success(ParsedArg[T](self.ix, self.default)), rest
            case Failure(ex):
                return Failure(ex), rest


class FlagReqKeyValueArg(Arg[T]):
    """A required KV Flag

    -f or --filter-score 1.23
    """

    def __init__(
        self,
        ix: str,
        flags: tuple[str, str],
        name: str,
        converter: Callable[[Any], T],
        *,
        description: str | None = None,
    ):
        super().__init__(ix, name, description=description)
        self.flags = flags
        self.converter = converter
        self._extractor = ExtractReqFlagAndValue[T](ix, flags, converter)

    @override
    def extract(self, sx: list[str]) -> tuple[Result[ParsedArg[T]], list[str]]:
        return self._extractor(sx)


def __extract_driver(
    targ: list[Arg[T]], xs: list[str], either: list[Result[ParsedArg[T]]]
) -> tuple[list[Result[ParsedArg[T]]], list[str]]:
    if targ:
        et, rest = targ[0].extract(xs)
        either.append(et)
        return __extract_driver(targ[1:], rest, either)
    else:
        return either, xs


def extractor(targ: list[Arg[T]], xs: list[str]) -> Result[list[ParsedArg[T]]]:
    # bootstrapping
    results: list[Result[ParsedArg[T]]] = []

    rx, rest = __extract_driver(targ, xs, results)
    if rest:
        ex = ValueError(f"Unexpected argument(s) found {rest}")
        return Failure(ex)

    # Flatten results
    tx: list[ParsedArg[T]] = []
    for result in rx:
        match result:
            case Success(pa):
                tx.append(pa)
            case Failure() as var:
                return var

    return Success(tx)


class FlagAction(ToAction, FlagNonReqArg[T]):
    def __init__(
        self,
        ix: str,
        flags: tuple[str, str],
        name: str,
        default: T,
        set_value: T,
        *,
        description: str | None = None,
    ):
        super().__init__(
            ix,
            flags,
            name,
            converter=identity,
            default=default,
            set_value=set_value,
            description=description,
        )


class FlagNonReqArgAction(FlagAction[bool]):
    """Bool Flag Action"""

    def __init__(
        self,
        ix: str,
        flags: tuple[str, str],
        name: str,
        *,
        description: str | None = None,
    ):
        super().__init__(
            ix, flags, name, default=False, set_value=True, description=description
        )


class FlagHelpAction(FlagNonReqArgAction):
    def to_action(self, sx: list[str]) -> tuple[Action, list[str]]:
        result, rest = self.extract(sx)
        match result:
            case Success(pa):
                if pa.value is True:
                    return HelpAction(self.description or "Help"), rest
                else:
                    return NoopAction(), rest
            case Failure():
                return NoopAction(), rest


class FlagVersionAction(FlagNonReqArgAction):
    def __init__(
        self,
        ix: str,
        flags: tuple[str, str],
        name: str,
        version: str,
        *,
        description: str | None = None,
    ):
        super().__init__(ix, flags, name, description=description)
        self.version = version

    def to_action(self, sx: list[str]) -> tuple[Action, list[str]]:
        result, rest = self.extract(sx)
        match result:
            case Success(pa):
                if pa.value is True:
                    return VersionAction(self.version), rest
                else:
                    return NoopAction(), rest
            case Failure():
                return NoopAction(), rest


class Targurs:
    def __init__(
        self, args: list[Arg[Any]], actions: list[FlagAction[Any]] | None = None
    ):
        self.args = args
        self.actions = actions or []

    def to_parsed_args(self, sx: list[str]) -> Result[list[ParsedArg[T]]]:
        return extractor(self.args, sx)


@dataclass
class MyModel:
    input_txt: str
    input_csv: str
    alpha: float  # This is a required key-value flag
    filter_score: float = 0.95
    debug: bool = False

    def run(self) -> None:
        print(f"Running {self}")


DEMO_TARGURS = Targurs(
    [
        Positional("input_txt", "input TXT", str, description="Path to input txt"),
        Positional("input_csv", "input CSV", str, description="Path to CSV"),
        FlagReqKeyValueArg(
            "alpha",
            ("-a", "--alpha"),
            "alpha Score",
            float,
            description="Alpha Score",
        ),
        FlagNonReqKeyValueArg(
            "filter_score",
            ("-f", "--filter-score"),
            "Filter Score",
            float,
            1.23,
            description="Minimum Filter Score",
        ),
        FlagNonReqArg(
            "debug",
            ("-d", "--debug"),
            "DEBUG mode",
            bool,
            False,
            set_value=True,
            description="Enable Debug mode",
        ),
    ],
    actions=[
        FlagHelpAction(
            "help",
            ("-h", "--help"),
            "help message",
            description="Return Help",
        ),
        FlagVersionAction(
            "version",
            ("-v", "--version"),
            "App version",
            description="Return the version of the Application",
            version="1.0.1",
        ),
    ],
)
