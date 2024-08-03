# Targurs

Typed and minimal **Building blocks** for creating a Commandline argument parsing library in Python. 


## Requirements and Goals

- Declarative typed interface for parsing commandline arguments
- Core library for only parsing/transforming. It's *not* for building an application or commandline tool.
- Use `Result` (from rust), or `Either` (Scala) structure for handling success/errors.
- It's intend for people who don't want to use/wrap argparse or similar. (e.g., Pydantic, Attrs, dataclass)
- Try to make this as type-safe as possible.
- This is an *exploring and proof of concept state*. 

## Example 

Consider having a model or datastructure than can be translated into core fields (e.g., positional, flags) that can be interpreted and parsed.

For example, a dataclass.

```python
from dataclasses import dataclass

@dataclass
class MyModel:
    input_txt: str
    input_csv: str
    alpha: float  # Assume this is a required key-value flag, not a positional arg
    filter_score: float = 0.95
    debug: bool = False


def runner(m: MyModel) -> None:
    print(f"Mock running {m}")
```

A layer translates your dataclass/pydantic/attrs, etc... into structured semantics to describe the core pieces of your Commandline app.  

```python
from targurs import *

tx = Targurs(
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
            default=False,
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
```

## General Processing

- Your code takes dataclass/pydantic/attrs (`MyModel`) and translates to `list[Arg[T]]` 
- Grouping of `list[Arg[T]]` and then a separate list of help and version "Action" flags.
- internal processing of `(sx:list[str], ax:List[Arg[T]])` -> `list[Result[ParsedArg[T]]]` -> `Result[CmdAction]` (where CmdAction is wrapper of runnable of your )
- internal process of flag actions (help, version) to create HelpAction, VersionAction or NoopAction.
- internal process of creating a list of all actions
- You can decide to process the result action list. For example, exit after process version, or help. Or how to resolve when both help and version are NoopAction(s).

Targurs provides the core structures to parse argv and then return "actions".


Let's create an explicit example using a dataclass.

```python
from typing import Any
from dataclasses import dataclass
from targurs import CmdAction, ParsedArg, Result
from targurs import parsed_arg_list_to_dict

@dataclass
class MyModel:
    input_txt: str
    input_csv: str
    alpha: float  # Let's use this as a required key-value flag
    filter_score: float = 0.95
    debug: bool = False
    

def to_action(px: list[ParsedArg]) -> CmdAction:
    # Convert parsed arg list to **d and 
    # create instance of our model
    # this part needs to be made more type-safe
    d: dict[str, Any] = parsed_arg_list_to_dict(px)
    m = MyModel(**d)
    def to_runner() -> None:
        print(f"Running {m}")
    return CmdAction(to_runner)
```
The general processing (with some explicit type annotations/hints to help communicate the data flow):

```python
import sys

from targurs import Targurs, Result, Action, Success, Failure, NoopAction
from targurs import DEMO_TARGURS # Example instance manually translated/created from MyModel

sx = ["input.txt", "in.csv", "--filter-score", "1.23", "--alpha", "3.14"]

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
                        act()
                        return 0
            case Failure(ex):
                sys.stderr.write(f"Failed to run. {ex}")
                return 1
    else:
        # Not sure what the expected behavior is here.
        sys.stderr.write(f"Failed to run. No actions found.")
        return 2

def run_demo() -> None:
    sx0 = ["input.txt", "in.csv", "--filter-score", "1.23", "--alpha", "3.14"]
    sx1 = ["--version"]
    sx2 = ["--help"]
    for sx in (sx0, sx1, sx2):
        exit_code = demo(DEMO_TARGURS, sx)
        print(f"Exit-code={exit_code} for {sx}")

```


## Requirement Details

- Implement a minimal `Result` type with `Success[T] | Failure` 
- `--help` and `-h` are supported as an "Action"
- `--version` and `-v` are supported
- Positional arguments are supported
- Bool flags are supported `--debug` or `-d` will set value to `True` 
- "Value" Flags of `-x` and `--max-x` are supported. `--max-x 1234`
- Naming: `sx:list[str]` is the raw arguments from `sys.argv[1:]`
- Naming: "Optional" or similar is never used to avoid confusion. It's Required and Non-Required arguments.
- Naming: "Flags" are the fundamental noun to describe commandline argument (e.g., `-d`, `--debug`, `--score 1234`)
- Naming: FlagKey are key (e.g., '--debug'), while FlagKeyValue are `--score 3.14`
- Naming: Verbose naming of flags. 
- Naming: Prefixes of "Req" and "NonReq" are used for flag keys and flag key-values  
- Naming: An id of an argument is `ix`
- Naming: Argument flags are `tuple[str, str]` which are (short, long) (e.g., `(-d, --debug)`)).
- Naming: Action is a wrapped runnable of `Callable[[], None]`
- While a complete library to parse args is not the goal, there should be a demo of using a `dataclass` to build an application.

## Misc Thoughts

- Overall, I think this is an interesting experiment. 
- This would aim to be a small minimal library. The Python community doesn't really do small core building block libraries.  
- Fighting with the type checking in many places.
- Need to have consistency with your text editor or IDE and the static analysis tools (e.g., `mypy`). These can't be saying different things. This is more pronounced when you start pushing the type system even a little bit.
- Pattern matching in Python is a mixed bag. The scoping is odd and the lack of ability to assign a return value yields a very nested structure at times. 
- Questions: Is this a good approach to Python? Why not just use a different language with these requirements.  
- Questions: Using this approach for core libraries useful? Then allow non-core libraries to be a bit more loose with their type-ness. The motivation is that core libraries can still evolve by non-primary authors and that downstream changes can be made more quickly.
- Observation: Compared to the internals and style of argparse, click (written 10+ years ago), this is a very different approach.   

## References

- [Rust Result](https://doc.rust-lang.org/std/result/)
- [Scala Either](https://www.scala-lang.org/api/3.x/scala/util/Either.html)
- [Friction Points with argparse](https://github.com/mpkocher/pydantic-cli) 