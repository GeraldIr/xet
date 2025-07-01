#!/usr/bin/python3

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Union
from fabric import Connection


CONFIG_FILE = ".xet"
VERSION = "1.0.0"

NL = "\n"


def get_config_path(g=False):
    """Return the config file path, supporting XDG_CONFIG_HOME for global config."""
    if g:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return os.path.join(xdg_config, CONFIG_FILE)
        else:
            return os.path.join(os.path.expanduser("~"), CONFIG_FILE)
    else:
        return CONFIG_FILE


def init_config(args):
    """Initialize a .xet file."""

    if os.path.exists(get_config_path(args.g)):
        print("Configuration already exists.")
        return
    with open(get_config_path(args.g), "w") as f:
        json.dump({}, f)


def parse_config(except_flags=None, only_flags=None, names=None, preset=None, g=False):
    """Parse .xet, handling entries and applying -e/-o/-n filters."""

    except_flags = set(except_flags) if except_flags else set()
    only_flags = set(only_flags) if only_flags else set()

    config_path = get_config_path(g=g)

    if not os.path.exists(config_path):
        print(f"Error: Config file '{config_path}' not found. Run 'xet init' first.")
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
    value: str = "", wrapper: str = None, end: str = None, padding: int = 0
):
    value = value if not end else value.rstrip(end)
    value = value if not padding else value[padding:-padding]
    return value if not wrapper else value.lstrip(wrapper).split(wrapper)[0]


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
    padding: int = 0,
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
            f"{tag}{' ' * padding}{wrapper if wrapper is not None else ''}{value}{wrapper if wrapper is not None else ''}{' ' * padding}{end}"
        )

    _set_file_lines(filepath=filepath, ssh=ssh, lines=lines)


def _get_tag_value(
    filepath: str = "",
    tag: str = "",
    occurences_slice: Union[str, list[int]] = ":",
    wrapper: str = None,
    end: str = "",
    padding: int = 0,
    verbosity: int = 0,
    ssh: str = None,
):
    if verbosity >= 2:
        print(
            f"Path: {filepath}\n"
            f"Tag: {tag}\n"
            f"Occurences: {occurences_slice if occurences_slice != ':' else 'All'}\n"
            f"{'Wrapper: ' + wrapper + NL if wrapper else ''}"
            f"{'End: ' + end + NL if end else ''}"
        )

    found_occurences = []

    lines = _get_file_lines(filepath=filepath, ssh=ssh)

    for i, line in enumerate(lines):
        if line.startswith(tag):
            found_occurences.append(i)

    filtered_occurences = _filter_occurences(
        occurences=found_occurences, filter=occurences_slice
    )

    for occurence_index in filtered_occurences:
        if verbosity >= 1:
            print(f"Line:\n{lines[occurence_index]}\nValue: ")

        print(
            _sanitize_value(
                value=lines[occurence_index].lstrip(tag),
                wrapper=wrapper,
                end=end,
                padding=padding,
            )
        )


def _set_lc_value(
    filepath: str = "",
    line: str = "",
    column: int = 0,
    wrapper: str = "",
    end: str = "",
    padding: int = 0,
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
        f"{lines[line][:column]}{' ' * padding}{wrapper if wrapper is not None else ''}{value}{wrapper if wrapper is not None else ''}{' ' * padding}{end}"
    )

    _set_file_lines(filepath=filepath, ssh=ssh, lines=lines)


def _get_lc_value(
    filepath: str = "",
    line: str = "",
    column: int = 0,
    wrapper: str = "",
    end: str = "",
    padding: int = 0,
    verbosity: int = 0,
    ssh: str = None,
):

    line -= 1
    column -= 1

    if verbosity >= 2:
        print(
            f"File: {filepath}\n"
            f"Regex: {line} \n"
            f"Column: {column}\n"
            f"{'Wrapper:' + wrapper + NL if wrapper else ''}"
            f"{'End: ' + end + NL if end else ''}"
        )

    lines = _get_file_lines(filepath=filepath, ssh=ssh)

    if verbosity >= 1:
        print(f"Line:\n{lines[line]}\nValue:")
    print(
        _sanitize_value(
            value=lines[line][column:], wrapper=wrapper, end=end, padding=padding
        )
    )


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
    if verbosity >= 2:
        print(
            f"File: {filepath}\n"
            f"Regex: {regex} \n"
            f"Group: {group if group else 'None'}\n"
            f"Occurences: {occurences_slice if occurences_slice != ':' else 'All'}\n"
            f"{'Wrapper: ' + wrapper + NL if wrapper else ''}"
        )

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
        if verbosity >= 1:
            print(f"Line:\n{lines[occurence_index]}\nValue:")
        if not group:
            print(occurence_match.string)
        else:
            print(
                _sanitize_value(
                    value=occurence_match.group(group), wrapper=wrapper, end=None
                )
            )


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
        padding = entry["padding"]
        _set_tag_value(
            filepath=filepath,
            tag=tag,
            occurences_slice=occurences,
            wrapper=wrapper,
            end=end,
            padding=padding,
            value=value,
            ssh=ssh,
        )
    elif type == "lc":
        line = entry["line"]
        column = entry["column"]
        end = entry["end"]
        padding = entry["padding"]
        _set_lc_value(
            filepath=filepath,
            line=line,
            column=column,
            wrapper=wrapper,
            end=end,
            padding=padding,
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
    """Set the value associated with a tag in files listed in .xet."""
    config = parse_config(
        except_flags=args.e, only_flags=args.o, names=args.n, g=args.g
    )
    for entry in config.values():
        _set_value(entry=entry, value=args.value)


def get_value(args):
    """Get the value associated with a tag in files listed in .xet."""
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
        if verbosity >= 2:
            print(name)
            print("----------------------------")
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue

        if type == "tag":
            tag = entry["tag"]
            occurences = entry["occurences"]
            end = entry["end"]
            padding = entry["padding"]
            _get_tag_value(
                filepath=filepath,
                tag=tag,
                occurences_slice=occurences,
                wrapper=wrapper,
                end=end,
                padding=padding,
                verbosity=verbosity,
                ssh=ssh,
            )
        elif type == "lc":
            line = entry["line"]
            column = entry["column"]
            end = entry["end"]
            padding = entry["padding"]
            _get_lc_value(
                filepath=filepath,
                line=line,
                column=column,
                wrapper=wrapper,
                end=end,
                padding=padding,
                verbosity=verbosity,
                ssh=ssh,
            )
        elif type == "regex":
            regex = entry["regex"]
            group = entry["group"]
            occurences = entry["occurences"]
            _get_regex_value(
                filepath=filepath,
                regex=regex,
                group=group,
                occurences_slice=occurences,
                wrapper=wrapper,
                verbosity=verbosity,
                ssh=ssh,
            )
        if verbosity >= 2:
            print("----------------------------")
        if verbosity >= 1:
            print()


def add_entry(args):
    """Add a new entry to .xet."""

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
            "padding": int(args.padding),
        }
    elif args.subcommand == "lc":
        config[args.name] |= {
            "line": int(args.line),
            "column": int(args.column),
            "end": args.end,
            "padding": int(args.padding),
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
    """Remove an entry from .xet based on the tag."""
    config = parse_config(g=args.g)

    config.pop(args.name)

    with open(get_config_path(g=args.g), mode="w") as f:
        json.dump(config, f, indent=4)


def edit_config(args):
    editor = os.environ.get("EDITOR", "nano")
    subprocess.run([editor, get_config_path(args.g)])


def main():
    parser = argparse.ArgumentParser(
        prog="xet", description="A CLI tool to manage values across multiple files."
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
        help="Use the global config.",
    )

    edit_parser = subparsers.add_parser(
        "edit", help="Opens the .xet in the standard editor."
    )
    edit_parser.set_defaults(func=edit_config)

    edit_parser.add_argument(
        "--global",
        "-g",
        dest="g",
        action="store_true",
        help="Edit global config.",
    )

    get_parser = subparsers.add_parser(
        "get", help="Get a value from files listed in the xet config."
    )
    get_parser.set_defaults(func=get_value)
    get_parser.add_argument(
        "--global",
        "-g",
        dest="g",
        action="store_true",
        help="Use the global config.",
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
        help="Include only entries with the given names.",
    )

    get_parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        help="Enable verbose output",
        action="count",
        default=0,
    )

    set_parser = subparsers.add_parser(
        "set", help="Set a value in files listed in the xet config."
    )
    set_parser.set_defaults(func=set_value)
    set_parser.add_argument("value", help="Value to set")

    set_parser.add_argument(
        "--global",
        "-g",
        dest="g",
        action="store_true",
        help="Use the global config.",
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
        help="Include only entries with the given names.",
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

    add_parser = subparsers.add_parser("add", help="Add a new entry to xet config")

    add_sub_parser = add_parser.add_subparsers(dest="subcommand")

    add_tag_parser = add_sub_parser.add_parser(
        "tag", help="Add a tag-type entry to the xet config."
    )

    add_lc_parser = add_sub_parser.add_parser(
        "lc", help="Add a line/column-type entry to the xet config."
    )

    add_regex_parser = add_sub_parser.add_parser(
        "regex",
        help="Match tags with regex instead of plaintext, also supports group matching the values place.",
    )

    add_sub_parsers = [add_tag_parser, add_lc_parser, add_regex_parser]

    list(map(lambda sub: sub.set_defaults(func=add_entry), add_sub_parsers))

    # non-unique positional arguments

    list(
        map(  # Add name argument to all add sub parsers
            lambda sub: sub.add_argument(
                "name", help="The name of the entry in the config."
            ),
            add_sub_parsers,
        )
    )

    list(
        map(  # Add Filepath argument to all add sub parsers
            lambda sub: sub.add_argument("filepath", help="Path to the file"),
            add_sub_parsers,
        )
    )

    # unique positional arguments

    # tag parser
    add_tag_parser.add_argument("tag", help="Tag identifying the line in the file.")

    # lc parser
    add_lc_parser.add_argument("line", help="The line at which the value is located")
    add_lc_parser.add_argument(
        "column", help="The column after which the value is located"
    )

    # regex parser
    add_regex_parser.add_argument(
        "regex",
        help="The regular expression, if no group is specified values are updated after any given match (like tags).",
    )

    # non-unique optional arguments

    list(  # Add global argument to all add sub parsers
        map(
            lambda sub: sub.add_argument(
                "--global",
                "-g",
                action="store_true",
                dest="g",
                help="Add to the global xet config.",
            ),
            add_sub_parsers,
        )
    )

    list(  # Add Padding argument to tag and lc add sub parsers
        map(
            lambda sub: sub.add_argument(
                "--padding",
                "-d",
                dest="padding",
                default=0,
                help="Amount of whitespace-padding which gets added after tag and before end.",
            ),
            [add_tag_parser, add_lc_parser],
        )
    )

    list(  # Add End argument to tag and lc add sub parsers
        map(
            lambda sub: sub.add_argument(
                "-e",
                "--end",
                dest="end",
                default="",
                help="Will be put after the value and its wrappers, will also be stripped in get mode if present.",
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
                help="Which occurence of the tag should be included, can be an integer, list of integers or the string 'all'",
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
                help="SSH Host to connect to, as found in openSSH config file.",
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
                help="Value will be wrapped in this character (useful for updating values in brackets or commas). Will also be stripped in get-mode.",
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
                help="<Preset Name> <Preset Value> presets can be set with xet preset <Preset Name>.",
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
        help="The group number which should be interpreted as the value. 0 means the entire match is interpreted as the value. Everything but the value itself is preserved, useful when values aren't at the end of a line",
    )

    """
    REMOVE PARSER
    """

    remove_parser = subparsers.add_parser("remove", help="Remove an entry from .xet")
    remove_parser.set_defaults(func=remove_entry)
    remove_parser.add_argument("name", help="Name of the entry to remove")

    remove_parser.add_argument(
        "--global",
        "-g",
        dest="g",
        action="store_true",
        help="Use the global config.",
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
        "preset", help="Set all values to a given preset."
    )
    preset_parser.set_defaults(func=set_presets)
    preset_parser.add_argument("preset", help="Name of the preset")

    preset_parser.add_argument(
        "--global",
        "-g",
        dest="g",
        action="store_true",
        help="Use the global config.",
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
