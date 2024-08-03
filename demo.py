import sys
from typing import Any

from targurs import MyModel, DEMO_TARGURS
from targurs import parsed_arg_list_to_dict
from targurs import (
    Targurs,
    ParsedArg,
    Result,
    Success,
    Failure,
    CmdAction,
    Action,
    NoopAction,
)


def to_action(px: list[ParsedArg]) -> CmdAction:
    # Convert parsed arg list to **d and
    # create instance of our model
    # this part needs to be made more type-safe
    d: dict[str, Any] = parsed_arg_list_to_dict(px)
    m = MyModel(**d)

    def to_runner() -> None:
        print(f"Running {m}")

    return CmdAction(to_runner)


def demo(tx: Targurs, sx: list[str]) -> int:
    """
    A basic end-to-end demo.
    The point is to demonstrate that you have control over the actions and the parsing/extracting.
    and wire it together in a principled typesafe way.

    This will use the basic "eager" version and help to exit immediately with zero exit code,
    otherwise, try to run the "Cmd" action. If failure, map to exit code 1.

    """
    actions: list[Result[Action]] = []

    # Process "Eager Action first, then add CmdAction"
    rest: list[str] = sx
    for eager_action_flag in tx.actions:
        action, rest = eager_action_flag.to_action(rest)
        actions.append(Success(action))

    cmd_action: Result[Action] = tx.to_parsed_args(sx).map(to_action)
    actions.append(cmd_action)

    # Iterate over actions and exit
    for i, result_action in enumerate(actions):
        match result_action:
            case Success(act):
                match act:
                    case NoopAction():
                        pass
                    case _:
                        # this should have a try-catch
                        act()
                        return 0
            case Failure(ex):
                sys.stderr.write(f"Failed to run. {ex}")
                return 1
    else:
        # Not sure what the expected behavior is here.
        sys.stderr.write(f"Failed to run. No actions found.")
        return 2


def run_demo() -> int:
    sx0 = ["input.txt", "in.csv", "--filter-score", "1.23", "--alpha", "3.14"]
    sx1 = ["--version"]
    sx2 = ["--help"]
    for sx in (sx0, sx1, sx2):
        print(f"*** Running {sx}")
        exit_code = demo(DEMO_TARGURS, sx)
        print(f"Exit-code={exit_code}")
    return exit_code


run_demo()
