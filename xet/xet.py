import argparse
import json
import os
import re
import subprocess
import sys
from colorama import Fore, Style
from typing import Union
from fabric import Connection


CONFIG_FILE = ".xet"
VERSION = "1.1.0"

NL = "\n"

VALUE_COLOR = Fore.RED
NAME_COLOR = Fore.GREEN
IDENTIFIER_COLOR = Fore.BLUE
PATH_COLOR = Fore.MAGENTA
SEP_COLOR = Fore.CYAN


def get_config_path(g=False):
    """Return the config file path, supporting XDG_CONFIG_HOME for global config"""
    if g:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return os.path.join(xdg_config, CONFIG_FILE)
        else:
            return os.path.join(os.path.expanduser("~"), CONFIG_FILE)
    else:
        return CONFIG_FILE


def init_config(args):
    """Initialize a .xet file"""

    if os.path.exists(get_config_path(args.g)):
        print("Configuration already exists")
        return
    with open(get_config_path(args.g), "w") as f:
        json.dump({}, f)


def parse_config(except_flags=None, only_flags=None, names=None, preset=None, g=False):
    """Parse .xet, handling entries and applying -e/-o/-n filters"""

    except_flags = set(except_flags) if except_flags else set()
    only_flags = set(only_flags) if only_flags else set()

    config_path = get_config_path(g=g)

    if not os.path.exists(config_path):
        print(f"Error: Config file '{config_path}' not found. Run 'xet init' first")
        sys.exit(1)
    with open(config_path, mode="r") as f:
        config: dict = json.load(f)

    if preset:
        preset_entries = [
            name for name in config.keys() if preset in config[name]["presets"]
        ]
        return {
            k: v
            for k, v in zip(preset_entries, [config[name] for name in preset_entries])
        }

    if names:
        names = [name for name in names if name in config]
        config = {k: v for k, v in zip(names, [config[name] for name in names])}

    filtered_config = {}

    for key, entry in config.items():
        flags = entry["flags"] if (entry and "flags" in entry) else None
        if flags:
            if except_flags and not any([flag in except_flags for flag in flags]):
                continue
            if only_flags and any([flag in only_flags for flag in flags]):
                continue
        elif only_flags:
            continue
        if entry["type"] == "lc":
            entry["column"] = entry["column"]
            entry["line"] = entry["line"]
        filtered_config[key] = entry

    return filtered_config


def _parse_index_or_slice(s):
    if ":" in s:
        parts = s.split(":")
        parts = [int(p) if p else None for p in parts]
        return slice(*parts)
    else:
        return int(s)


def _sanitize_value(
    value: str = "",
    wrapper: str = None,
    end: str = None,
):
    value = value if not end else value.rstrip(end)
    return value if not wrapper else value.lstrip(wrapper).split(wrapper)[0]


def _color_value(
    line: str = "",
    value: str = "",
):
    return (VALUE_COLOR + value + Style.RESET_ALL).join(line.split(value))


def _color_tag(line: str = "", tag: str = ""):
    return IDENTIFIER_COLOR + tag + Style.RESET_ALL + line.lstrip(tag)


def _filter_occurences(occurences: list, filter: str = ":"):
    filter = filter if filter else ":"
    if isinstance(filter, str):
        filtered_occurences = occurences[_parse_index_or_slice(filter)]
    elif isinstance(filter, list):
        filtered_occurences = [o for i, o in enumerate(occurences) if i in occurences]
    return filtered_occurences


def _get_file_lines(filepath: str = "", ssh: str = None):
    if ssh:
        with Connection(ssh) as c, c.sftp() as sftp:
            with sftp.open(filepath, "r") as remote_file:
                try:
                    return [
                        line.decode("utf-8") for line in remote_file.read().splitlines()
                    ]
                finally:
                    remote_file.close()
    else:
        with open(filepath, "r") as f:
            return f.read().splitlines()


def _set_file_lines(filepath: str = "", ssh: str = None, lines: list = []):
    if ssh:
        with Connection(ssh) as c, c.sftp() as sftp:
            with sftp.open(filepath, "w") as remote_file:
                try:
                    lines = [line + "\n" for line in lines]
                    remote_file.writelines(lines)
                finally:
                    remote_file.close()
    else:
        with open(filepath, "w") as f:
            lines = [line + "\n" for line in lines]
            f.writelines(lines)


def _set_tag_value(
    filepath: str = "",
    tag: str = "",
    occurences_slice: Union[str, list[int]] = ":",
    wrapper: str = None,
    end: str = "",
    value: str = "",
    ssh: str = None,
):
    found_occurences = []

    lines = _get_file_lines(filepath=filepath, ssh=ssh)

    for i, line in enumerate(lines):
        if line.startswith(tag):
            found_occurences.append(i)

    filtered_occurences = _filter_occurences(
        occurences=found_occurences, filter=occurences_slice
    )

    for occurence_index in filtered_occurences:
        if wrapper:
            after_wrapper = lines[occurence_index].lstrip(tag).split(wrapper)[2]
            end = after_wrapper + end
        lines[occurence_index] = (
            f"{tag}{wrapper if wrapper is not None else ''}{value}{wrapper if wrapper is not None else ''}{end}"
        )

    _set_file_lines(filepath=filepath, ssh=ssh, lines=lines)


def _get_tag_value(
    filepath: str = "",
    tag: str = "",
    occurences_slice: Union[str, list[int]] = ":",
    wrapper: str = None,
    end: str = "",
    verbosity: int = 0,
    ssh: str = None,
):

    found_occurences = []

    lines = _get_file_lines(filepath=filepath, ssh=ssh)

    for i, line in enumerate(lines):
        if line.startswith(tag):
            found_occurences.append(i)

    filtered_occurences = _filter_occurences(
        occurences=found_occurences, filter=occurences_slice
    )

    for occurence_index in filtered_occurences:
        sanitized_value = _sanitize_value(
            value=lines[occurence_index].lstrip(tag),
            wrapper=wrapper,
            end=end,
        )
        if verbosity >= 1:
            print(
                _color_tag(
                    line=_color_value(
                        line=lines[occurence_index],
                        value=sanitized_value,
                    ),
                    tag=tag,
                )
            )
        else:
            print(sanitized_value)


def _set_lc_value(
    filepath: str = "",
    line: str = "",
    column: int = 0,
    wrapper: str = "",
    end: str = "",
    value: str = "",
    ssh: str = None,
):

    lines = _get_file_lines(filepath=filepath, ssh=ssh)

    line -= 1
    column -= 1

    if len(lines) <= line:
        lines += [""] * ((line) - len(lines) + 1)

    if len(lines[line]) <= column:
        lines[line] += " " * (column - len(lines[line]) + 1)

    if wrapper:
        after_wrapper = lines[line][:column].split(wrapper)[2]
        end = after_wrapper + end

    lines[line] = (
        f"{lines[line][:column]}{wrapper if wrapper is not None else ''}{value}{wrapper if wrapper is not None else ''}{end}"
    )

    _set_file_lines(filepath=filepath, ssh=ssh, lines=lines)


def _get_lc_value(
    filepath: str = "",
    line: str = "",
    column: int = 0,
    wrapper: str = "",
    end: str = "",
    verbosity: int = 0,
    ssh: str = None,
):

    line -= 1
    column -= 1

    lines = _get_file_lines(filepath=filepath, ssh=ssh)

    sanitized_value = _sanitize_value(
        value=lines[line][column:],
        wrapper=wrapper,
        end=end,
    )

    if verbosity >= 1:
        print(
            _color_value(
                line=lines[line],
                value=sanitized_value,
            )
        )
    else:
        print(sanitized_value)


def _set_regex_value(
    filepath: str = "",
    regex: str = "",
    group: int = 0,
    occurences_slice: Union[str, list[int]] = ":",
    wrapper: str = "",
    value: str = "",
    ssh: str = None,
):
    lines = _get_file_lines(filepath=filepath, ssh=ssh)

    found_occurences = []

    for i, line in enumerate(lines):
        m = re.search(regex, line)
        if m:
            found_occurences.append((i, m))

    filtered_occurences = _filter_occurences(
        occurences=found_occurences, filter=occurences_slice
    )

    for occurence_index, occurence_match in filtered_occurences:
        if not group:
            lines[occurence_index] = (
                f"{occurence_match.string}{wrapper if wrapper is not None else ''}{value}{wrapper if wrapper is not None else ''}"
            )
        else:
            start = lines[occurence_index][0 : occurence_match.start(group)]
            end = lines[occurence_index][occurence_match.end(group) :]
            lines[occurence_index] = (
                f"{start}{wrapper if wrapper is not None else ''}{value}{wrapper if wrapper is not None else ''}{end}"
            )

    _set_file_lines(filepath=filepath, ssh=ssh, lines=lines)


def _get_regex_value(
    filepath: str = "",
    regex: str = "",
    group: int = 0,
    occurences_slice: Union[str, list[int]] = ":",
    wrapper: str = "",
    verbosity: int = 0,
    ssh: str = None,
):
    lines = _get_file_lines(filepath=filepath, ssh=ssh)

    found_occurences = []

    for i, line in enumerate(lines):
        m = re.search(regex, line)
        if m:
            found_occurences.append((i, m))

    filtered_occurences = _filter_occurences(
        occurences=found_occurences, filter=occurences_slice
    )

    for occurence_index, occurence_match in filtered_occurences:

        sanitized_value = (
            _sanitize_value(
                value=occurence_match.group(group), wrapper=wrapper, end=None
            )
            if group
            else occurence_match.string
        )

        if verbosity >= 1:
            print(
                _color_value(
                    line=lines[occurence_index],
                    value=sanitized_value,
                )
            )
        else:
            print(sanitized_value)


def _set_value(entry, value):
    type, filepath, wrapper, ssh = (
        entry["type"],
        entry["filepath"],
        entry["wrapper"],
        entry["ssh"],
    )

    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    if type == "tag":
        tag = entry["tag"]
        occurences = entry["occurences"]
        end = entry["end"]
        _set_tag_value(
            filepath=filepath,
            tag=tag,
            occurences_slice=occurences,
            wrapper=wrapper,
            end=end,
            value=value,
            ssh=ssh,
        )
    elif type == "lc":
        line = entry["line"]
        column = entry["column"]
        end = entry["end"]
        _set_lc_value(
            filepath=filepath,
            line=line,
            column=column,
            wrapper=wrapper,
            end=end,
            value=value,
            ssh=ssh,
        )
    elif type == "regex":
        regex = entry["regex"]
        group = entry["group"]
        occurences = entry["occurences"]
        _set_regex_value(
            filepath=filepath,
            regex=regex,
            group=group,
            occurences_slice=occurences,
            wrapper=wrapper,
            value=value,
            ssh=ssh,
        )


def set_presets(args):
    config = parse_config(preset=args.preset, g=args.g)

    for entry in config.values():
        _set_value(entry=entry, value=entry["presets"][args.preset])


def set_value(args):
    """Set the value associated with a tag in files listed in .xet"""
    config = parse_config(
        except_flags=args.e, only_flags=args.o, names=args.n, g=args.g
    )
    for entry in config.values():
        _set_value(entry=entry, value=args.value)


def get_value(args):
    """Get the value associated with a tag in files listed in .xet"""
    config = parse_config(
        except_flags=args.e, only_flags=args.o, names=args.n, g=args.g
    )
    for name, entry in config.items():
        type, filepath, wrapper, ssh, verbosity = (
            entry["type"],
            entry["filepath"],
            entry["wrapper"],
            entry["ssh"],
            args.verbosity,
        )
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue

        if verbosity >= 2:
            print(
                f"{NAME_COLOR + name}{SEP_COLOR + ':'}{PATH_COLOR + filepath}{SEP_COLOR + ':'}",
                end="",
            )
        if type == "tag":
            tag = entry["tag"]
            occurences = entry["occurences"]
            end = entry["end"]
            if verbosity >= 2:
                print(f"{IDENTIFIER_COLOR + tag}{SEP_COLOR + ':' + Style.RESET_ALL}")
            _get_tag_value(
                filepath=filepath,
                tag=tag,
                occurences_slice=occurences,
                wrapper=wrapper,
                end=end,
                verbosity=verbosity,
            )
        elif type == "lc":
            line = entry["line"]
            column = entry["column"]
            end = entry["end"]
            if verbosity >= 2:
                print(
                    f"{IDENTIFIER_COLOR + line}{SEP_COLOR + ':'}{IDENTIFIER_COLOR + column}{SEP_COLOR + ':' + Style.RESET_ALL}"
                )
            _get_lc_value(
                filepath=filepath,
                line=line,
                column=column,
                wrapper=wrapper,
                end=end,
                verbosity=verbosity,
                ssh=ssh,
            )
        elif type == "regex":
            regex = entry["regex"]
            group = entry["group"]
            occurences = entry["occurences"]
            if verbosity >= 2:
                print(f"{IDENTIFIER_COLOR + regex}{SEP_COLOR + ':' + Style.RESET_ALL}")
            _get_regex_value(
                filepath=filepath,
                regex=regex,
                group=group,
                occurences_slice=occurences,
                wrapper=wrapper,
                verbosity=verbosity,
                ssh=ssh,
            )


def add_entry(args):
    """Add a new entry to .xet"""

    config = parse_config(g=args.g)

    config[args.name] = {
        "type": args.subcommand,
        "filepath": args.filepath,
        "flags": args.flags,
        "wrapper": args.wrapper,
        "presets": {k: v for k, v in args.presets} if args.presets else None,
        "ssh": args.ssh,
    }

    if args.subcommand == "tag":
        config[args.name] |= {
            "tag": args.tag,
            "occurences": args.occurences if args.occurences else ":",
            "end": args.end,
        }
    elif args.subcommand == "lc":
        config[args.name] |= {
            "line": int(args.line),
            "column": int(args.column),
            "end": args.end,
        }
    elif args.subcommand == "regex":
        config[args.name] |= {
            "regex": args.regex,
            "group": int(args.group[0]) if args.group else None,
            "occurences": args.occurences if args.occurences else ":",
        }

    with open(get_config_path(g=args.g), mode="w") as f:
        json.dump(config, f, indent=4)


def remove_entry(args):
    """Remove an entry from .xet based on the tag"""
    config = parse_config(g=args.g)

    config.pop(args.name)

    with open(get_config_path(g=args.g), mode="w") as f:
        json.dump(config, f, indent=4)


def edit_config(args):
    editor = os.environ.get("EDITOR", "nano")
    subprocess.run([editor, get_config_path(args.g)])


def main():
    parser = argparse.ArgumentParser(
        prog="xet", description="A CLI tool to manage values across multiple files"
    )

    subparsers = parser.add_subparsers(
        dest="command", title="subcommands", required=True
    )

    parser.add_argument("--version", action="version", version=f"xet {VERSION}")

    init_parser = subparsers.add_parser("init", help="Initialize .xet")

    init_parser.set_defaults(func=init_config)

    init_parser.add_argument(
        "--global",
        "-g",
        dest="g",
        action="store_true",
        help="Use the global config",
    )

    edit_parser = subparsers.add_parser(
        "edit", help="Opens the .xet in the standard editor"
    )
    edit_parser.set_defaults(func=edit_config)

    edit_parser.add_argument(
        "--global",
        "-g",
        dest="g",
        action="store_true",
        help="Edit global config",
    )

    get_parser = subparsers.add_parser(
        "get",
        help=f"Get {VALUE_COLOR + 'values' + Style.RESET_ALL} from entries listed in the .xet",
    )
    get_parser.set_defaults(func=get_value)
    get_parser.add_argument(
        "--global",
        "-g",
        dest="g",
        action="store_true",
        help="Use the global config",
    )
    get_parser.add_argument(
        "--except", "-e", dest="e", nargs="+", help="Exclude entries with these flags"
    )
    get_parser.add_argument(
        "--only",
        "-o",
        dest="o",
        nargs="+",
        help="Include only entries with these flags",
    )
    get_parser.add_argument(
        "--names",
        "-n",
        dest="n",
        nargs="*",
        help=f"Include only entries with the given {NAME_COLOR + 'names' + Style.RESET_ALL}",
    )

    get_parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        help=f"Enable verbose output. -v outputs the entire line, -vv also outputs the entry {NAME_COLOR + 'name'} {PATH_COLOR + 'filepath' + Style.RESET_ALL} and {IDENTIFIER_COLOR + 'identifier/s' + Style.RESET_ALL}",
        action="count",
        default=0,
    )

    set_parser = subparsers.add_parser(
        "set",
        help=f"Set a {VALUE_COLOR + 'value' + Style.RESET_ALL} in files listed in the .xet",
    )
    set_parser.set_defaults(func=set_value)
    set_parser.add_argument(
        "value", help=f"{VALUE_COLOR + 'Value' + Style.RESET_ALL} to set"
    )

    set_parser.add_argument(
        "--global",
        "-g",
        dest="g",
        action="store_true",
        help="Use the global config",
    )
    set_parser.add_argument(
        "--except", "-e", dest="e", nargs="*", help="Exclude entries with these flags"
    )
    set_parser.add_argument(
        "--only",
        "-o",
        dest="o",
        nargs="*",
        help="Include only entries with these flags",
    )
    set_parser.add_argument(
        "--names",
        "-n",
        dest="n",
        nargs="*",
        help=f"Include only entries with the given {NAME_COLOR + 'names' + Style.RESET_ALL}",
    )

    set_parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        help="Enable verbose output",
        action="count",
        default=0,
    )

    """
    ADD PARSER AND SUB-PARSERS
    """

    add_parser = subparsers.add_parser("add", help="Add a new entry the .xet")

    add_sub_parser = add_parser.add_subparsers(dest="subcommand")

    add_tag_parser = add_sub_parser.add_parser(
        "tag",
        help=f"Add a {IDENTIFIER_COLOR + 'tag' + Style.RESET_ALL} identifier entry to the .xet",
    )

    add_lc_parser = add_sub_parser.add_parser(
        "lc",
        help=f"Add a {IDENTIFIER_COLOR + 'line/column' + Style.RESET_ALL} identifier entry to the .xet",
    )

    add_regex_parser = add_sub_parser.add_parser(
        "regex",
        help=f"Add a {IDENTIFIER_COLOR + 'regex' + Style.RESET_ALL} identifier entry to the .xet",
    )

    add_sub_parsers = [add_tag_parser, add_lc_parser, add_regex_parser]

    list(map(lambda sub: sub.set_defaults(func=add_entry), add_sub_parsers))

    # non-unique positional arguments

    list(
        map(  # Add name argument to all add sub parsers
            lambda sub: sub.add_argument(
                "name",
                help=f"The {NAME_COLOR + 'name' + Style.RESET_ALL} of the entry in the config",
            ),
            add_sub_parsers,
        )
    )

    list(
        map(  # Add Filepath argument to all add sub parsers
            lambda sub: sub.add_argument(
                "filepath", help=f"{PATH_COLOR + 'Path' + Style.RESET_ALL} of the file"
            ),
            add_sub_parsers,
        )
    )

    # unique positional arguments

    # tag parser
    add_tag_parser.add_argument(
        "tag",
        help=f"{IDENTIFIER_COLOR + 'Tag' + Style.RESET_ALL} identifying the line in the file",
    )

    # lc parser
    add_lc_parser.add_argument(
        "line",
        help=f"The {IDENTIFIER_COLOR + 'line' + Style.RESET_ALL} at which the value is located",
    )
    add_lc_parser.add_argument(
        "column",
        help=f"The {IDENTIFIER_COLOR + 'column' + Style.RESET_ALL} at which the value is located",
    )

    # regex parser
    add_regex_parser.add_argument(
        "regex",
        help=f"The {IDENTIFIER_COLOR + 'regular expression' + Style.RESET_ALL}, if no group is specified values are updated after any given match (like tags)",
    )

    # non-unique optional arguments

    list(  # Add global argument to all add sub parsers
        map(
            lambda sub: sub.add_argument(
                "--global",
                "-g",
                action="store_true",
                dest="g",
                help="Add to the global .xet",
            ),
            add_sub_parsers,
        )
    )

    list(  # Add End argument to tag and lc add sub parsers
        map(
            lambda sub: sub.add_argument(
                "-e",
                "--end",
                dest="end",
                default="",
                help=f"Will be written at the very end of the line",
            ),
            [add_tag_parser, add_lc_parser],
        )
    )

    list(  # Add Occurences argument to tag and regex add sub parsers
        map(
            lambda sub: sub.add_argument(
                "--occurences",
                "-o",
                nargs="*",
                dest="occurences",
                help=f"Which occurence of the {IDENTIFIER_COLOR + 'tag/match' + Style.RESET_ALL} should be included, can be an integer, list of integers or the string 'all'",
            ),
            [add_tag_parser, add_regex_parser],
        )
    )

    list(  # Add Flags argument to all add sub parsers
        map(
            lambda sub: sub.add_argument(
                "--flags", "-f", nargs="*", help="Optional flags for filtering"
            ),
            add_sub_parsers,
        )
    )

    list(  # Add ssh argument to all add sub parsers
        map(
            lambda sub: sub.add_argument(
                "--ssh",
                "-s",
                dest="ssh",
                help="SSH Host to connect to, as found in openSSH config file",
            ),
            add_sub_parsers,
        )
    )

    list(  # Add Verbosity argument to all add sub parsers
        map(
            lambda sub: sub.add_argument(
                "-v",
                "--verbose",
                dest="verbosity",
                help="Enable verbose output",
                action="count",
                default=0,
            ),
            add_sub_parsers,
        )
    )

    list(  # Add Wrapper argument to all add sub parsers
        map(
            lambda sub: sub.add_argument(
                "--wrapper",
                "-w",
                dest="wrapper",
                help=f"{VALUE_COLOR + 'Value' + Style.RESET_ALL} will be wrapped in this character (useful for updating values in brackets or commas)",
            ),
            add_sub_parsers,
        )
    )

    list(  # Add Preset argument to all add sub parsers
        map(
            lambda sub: sub.add_argument(
                "--preset",
                "-p",
                dest="presets",
                action="append",
                nargs=2,
                help=f"<Preset Name> <Preset {VALUE_COLOR + 'Value' + Style.RESET_ALL}> presets can be set with xet preset <Preset Name>",
            ),
            add_sub_parsers,
        )
    )

    # unique optional arguments

    # regex parser
    add_regex_parser.add_argument(
        "--capture-group",
        "-c",
        nargs=1,
        help=f"The group number which should be interpreted as the {VALUE_COLOR + 'value' + Style.RESET_ALL}. 0 means the entire match is interpreted as the {VALUE_COLOR + 'value'}. Everything but the {VALUE_COLOR + 'value' + Style.RESET_ALL} itself is preserved",
    )

    """
    REMOVE PARSER
    """

    remove_parser = subparsers.add_parser("remove", help="Remove an entry from .xet")
    remove_parser.set_defaults(func=remove_entry)
    remove_parser.add_argument(
        "name", help=f"{NAME_COLOR + 'Name' + Style.RESET_ALL} of the entry to remove"
    )

    remove_parser.add_argument(
        "--global",
        "-g",
        dest="g",
        action="store_true",
        help="Use the global config",
    )

    remove_parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        help="Enable verbose output",
        action="count",
        default=0,
    )

    """
    PRESET PARSER
    """
    preset_parser = subparsers.add_parser(
        "preset",
        help=f"Set all {VALUE_COLOR + 'values' + Style.RESET_ALL} to a given preset",
    )
    preset_parser.set_defaults(func=set_presets)
    preset_parser.add_argument("preset", help="Name of the preset")

    preset_parser.add_argument(
        "--global",
        "-g",
        dest="g",
        action="store_true",
        help="Use the global config",
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
