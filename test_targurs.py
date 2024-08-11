"""Scrappy smoke tests"""

from typing import TypeAlias, NoReturn
from typing import Callable as F
from targurs import (
    extractor,
    DEMO_TARGURS,
    MyModel,
    parsed_arg_list_to_dict,
    Success,
    Failure,
)


def _apply(f: F[[list[str]], None]) -> F[[list[str]], F[[], None]]:
    # FIXME. this is perhaps trying to be too clever
    def g(sx: list[str]) -> F[[], None]:
        def h() -> None:
            return f(sx)
        return h

    return g


def test_success_map() -> None:
    s0 = Success(1)
    s1 = s0.map(lambda x: x + 1)
    assert s1.value == 2


def _test_basic_ok(sx: list[str]) -> None:
    r0 = extractor(DEMO_TARGURS.args, sx)
    assert isinstance(r0, Success)
    print(("r0", r0))

    # How to make this type-safe
    rd = r0.map(parsed_arg_list_to_dict)
    print(("rd", rd))
    assert isinstance(rd.value, dict)
    assert len(rd.value) == 5

    print(("rd", rd))
    c0 = MyModel(**(rd.value))
    assert c0.run() is None # type:ignore


_to_ok: F[[list[str]], F[[], None]] = _apply(_test_basic_ok)

test_basic_ok_00 = _to_ok(
    ["input.txt", "in.csv", "--filter-score", "1.23", "--alpha", "3.14"]
)
test_basic_ok_01 = _to_ok(["input.txt", "in.csv", "-f", "1.24", "-a", "3"])
test_basic_ok_02 = _to_ok(["input.txt", "in.csv", "--alpha", "10.0"])


def _test_basic_bad(sx: list[str]) -> None:
    r0 = extractor(DEMO_TARGURS.args, sx)
    assert r0.is_failure() is True


_to_bad = _apply(_test_basic_bad)

# Should be F[[], None]
test_bad_00: F[[], None] = _to_bad(["input.txt"])
test_bad_01 = _to_bad(["input.txt", "in.csv", "--debugx", "--filter-score", "1.23"])
test_bad_02 = _to_bad(["input.txt", "in.csv", "--filter-score", "1.23.bad"])
test_bad_03 = _to_bad(["input.txt", "in.csv", "--alpha", "1.23.bad"])
