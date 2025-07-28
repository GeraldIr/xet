import argparse
import json
import os
import re
import subprocess
from copy import deepcopy
from typing import Union

import diff_match_patch as dmp
from colorama import Fore, Style
from fabric import Connection

VERSION = "1.2.0"
CONFIG_FILE = ".xet"
HISTORY_FILE = ".xet_history"

DMP = dmp.diff_match_patch()

NL = "\n"

VALUE_COLOR = Fore.RED
NAME_COLOR = Fore.GREEN
IDENTIFIER_COLOR = Fore.BLUE
PATH_COLOR = Fore.MAGENTA
SEP_COLOR = Fore.CYAN


def _get_config_path(g=False, init=False):
    """Return the config file path, supporting XDG_CONFIG_HOME for global config"""

    if g or (not os.path.exists(CONFIG_FILE) and not init):
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return os.path.join(xdg_config, CONFIG_FILE)
        else:
            return os.path.join(os.path.expanduser("~"), CONFIG_FILE)
    else:
        return CONFIG_FILE


def get_history_path():
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return os.path.join(xdg_config, HISTORY_FILE)
    else:
        return os.path.join(os.path.expanduser("~"), HISTORY_FILE)


def get_abs_config_path(g=False, init=False):
    return os.path.abspath(_get_config_path(g=g, init=init))


def init_config(args):
    """Initialize a .xet file"""

    if os.path.exists(get_abs_config_path(args.g, init=True)):
        print("Configuration already exists")
        return
    with open(get_abs_config_path(args.g, init=True), "w") as f:
        json.dump({}, f)


def filter_config(
    except_flags=None,
    only_flags=None,
    names=None,
    preset=None,
    path=None,
    g=False,
):
    """Parse .xet, handling entries and applying -e/-o/-n/-p filters"""

    config_path = get_abs_config_path(g=g)

    if not os.path.exists(config_path):
        print(f"Error: Config file '{config_path}' not found. Run 'xet init' first")
        return
    with open(config_path) as f:
        config: dict = json.load(f)

    except_flags = set(except_flags) if except_flags else set()
    only_flags = set(only_flags) if only_flags else set()

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

    if path:
        path_entries = [
            name for name in config.keys() if config[name]["filepath"] in path
        ]
        config = {
            k: v for k, v in zip(path_entries, [config[name] for name in path_entries])
        }

    filtered_config = {}

    for key, entry in config.items():
        flags = entry["flags"] if (entry and "flags" in entry) else None
        if flags:
            if except_flags and any([flag in flags for flag in except_flags]):
                continue
            if only_flags and not any([flag in flags for flag in only_flags]):
                continue
        elif only_flags:
            continue

        filtered_config[key] = entry

    return filtered_config.keys()


def parse_config(
    except_flags=None, only_flags=None, names=None, preset=None, path=None, g=False
):
    config_path = get_abs_config_path(g=g)

    if not os.path.exists(config_path):
        print(f"Error: Config file '{config_path}' not found. Run 'xet init' first")
        return
    with open(config_path) as f:
        config: dict = json.load(f)

    filtered_keys = filter_config(
        except_flags=except_flags,
        only_flags=only_flags,
        names=names,
        preset=preset,
        path=path,
        g=g,
    )

    return {k: v for k, v in config.items() if k in filtered_keys}


def load_config(g=False):
    config_path = get_abs_config_path(g=g)

    if not os.path.exists(config_path):
        print(f"Error: Config file '{config_path}' not found. Run 'xet init' first")
        return
    with open(config_path) as f:
        return f.readlines()


def parse_index_or_slice(s):
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
    value = value if not end else value[: value.rfind(end)]
    return value if not wrapper else value.lstrip(wrapper).split(wrapper)[0]


def _color_value(
    line: str = "",
    value: str = "",
):
    return (VALUE_COLOR + value + Style.RESET_ALL).join(line.split(value))


def _color_tag(line: str = "", tag: str = ""):
    return IDENTIFIER_COLOR + tag + Style.RESET_ALL + re.sub(tag, "", line, count=1)


def _filter_occurences(occurences: list, filter: str = ":"):
    filter = filter if filter else ":"
    if isinstance(filter, str):
        filtered_occurences = occurences[parse_index_or_slice(filter)]
    elif isinstance(filter, list):
        if len(filter) == 1:
            filtered_occurences = occurences[parse_index_or_slice(filter[0])]
        else:
            filtered_occurences = [
                o for i, o in enumerate(occurences) if str(i) in filter
            ]
    return (
        filtered_occurences
        if isinstance(filtered_occurences, list)
        else [filtered_occurences]
    )


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
        with open(filepath) as f:
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


def _set_tag_values(
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

    old_lines = deepcopy(lines)

    for i, line in enumerate(lines):
        if line.startswith(tag):
            found_occurences.append(i)

    filtered_occurences = _filter_occurences(
        occurences=found_occurences, filter=occurences_slice
    )

    for occurence_index in filtered_occurences:
        if wrapper:
            after_wrapper = re.sub(tag, "", lines[occurence_index], count=1).split(
                wrapper
            )[2]
            re.sub(tag, "", lines[occurence_index], count=1)
            end = after_wrapper + end
        lines[occurence_index] = (
            f"{tag}{wrapper if wrapper is not None else ''}{value}"
            f"{wrapper if wrapper is not None else ''}{end}"
        )

    _set_file_lines(filepath=filepath, ssh=ssh, lines=lines)

    return old_lines, lines


def _get_tag_values(
    filepath: str = "",
    tag: str = "",
    occurences_slice: Union[str, list[int]] = ":",
    wrapper: str = None,
    end: str = "",
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

    return [
        (
            lines[occurence_index],
            _sanitize_value(
                value=re.sub(tag, "", lines[occurence_index], count=1),
                wrapper=wrapper,
                end=end,
            ),
        )
        for occurence_index in filtered_occurences
    ]


def _print_tag_values(sanitized_values, tag, verbosity):
    for line, value in sanitized_values:
        if verbosity >= 1:
            print(
                _color_tag(
                    line=_color_value(
                        line=line,
                        value=value,
                    ),
                    tag=tag,
                )
            )
        else:
            print(value)


def _set_lc_values(
    filepath: str = "",
    line: str = "",
    column: int = 0,
    wrapper: str = "",
    end: str = "",
    value: str = "",
    ssh: str = None,
):
    lines = _get_file_lines(filepath=filepath, ssh=ssh)

    old_lines = deepcopy(lines)

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
        f"{lines[line][:column]}{wrapper if wrapper is not None else ''}{value}"
        f"{wrapper if wrapper is not None else ''}{end}"
    )

    _set_file_lines(filepath=filepath, ssh=ssh, lines=lines)

    return old_lines, lines


def _get_lc_values(
    filepath: str = "",
    line: str = "",
    column: int = 0,
    wrapper: str = "",
    end: str = "",
    ssh: str = None,
):
    line -= 1
    column -= 1

    lines = _get_file_lines(filepath=filepath, ssh=ssh)

    return [
        (
            lines[line],
            _sanitize_value(
                value=lines[line][column:],
                wrapper=wrapper,
                end=end,
            ),
        )
    ]


def _print_lc_values(sanitized_value, verbosity):
    line, value = sanitized_value[0]
    if verbosity >= 1:
        print(
            _color_value(
                line=line,
                value=value,
            )
        )
    else:
        print(value)


def _set_regex_values(
    filepath: str = "",
    regex: str = "",
    group: int = 0,
    occurences_slice: Union[str, list[int]] = ":",
    wrapper: str = "",
    value: str = "",
    ssh: str = None,
):
    lines = _get_file_lines(filepath=filepath, ssh=ssh)

    old_lines = deepcopy(lines)

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
                f"{occurence_match.string[ : occurence_match.regs[0][1]]}"
                f"{wrapper if wrapper is not None else ''}"
                f"{value}{wrapper if wrapper is not None else ''}"
            )
        else:
            start = lines[occurence_index][0 : occurence_match.start(group)]
            end = lines[occurence_index][occurence_match.end(group) :]
            lines[occurence_index] = (
                f"{start}{wrapper if wrapper is not None else ''}"
                f"{value}{wrapper if wrapper is not None else ''}{end}"
            )

    _set_file_lines(filepath=filepath, ssh=ssh, lines=lines)

    return old_lines, lines


def _get_regex_values(
    filepath: str = "",
    regex: str = "",
    group: int = 0,
    occurences_slice: Union[str, list[int]] = ":",
    wrapper: str = "",
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

    return [
        (
            lines[occurence_index],
            (
                _sanitize_value(value=occurence_match.group(group), wrapper=wrapper)
                if group
                else _sanitize_value(
                    value=occurence_match.string[occurence_match.regs[0][1] :],
                    wrapper=wrapper,
                )
            ),
        )
        for occurence_index, occurence_match in filtered_occurences
    ]


def _print_regex_values(sanitized_value, verbosity):
    for line, value in sanitized_value:
        if verbosity >= 1:
            print(
                _color_value(
                    line=line,
                    value=value,
                )
            )
        else:
            print(value)


def _set_values(entry, value):
    type, filepath, wrapper, ssh = (
        entry["type"],
        os.path.abspath(entry["filepath"]),
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
        return _set_tag_values(
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
        return _set_lc_values(
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
        return _set_regex_values(
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

    patch = [
        (
            os.path.abspath(entry["filepath"]),
            DMP.patch_toText(
                DMP.patch_make(
                    a=NL.join(new_lines),
                    b=DMP.diff_main(NL.join(new_lines), NL.join(old_lines)),
                )
            ),
        )
        for entry, old_lines, new_lines in [
            (entry, *_set_values(entry=entry, value=entry["presets"][args.preset]))
            for entry in config.values()
        ]
    ]

    _add_to_history(patch=patch)


def set_value(args):
    """Set the value associated with a tag in files listed in .xet"""
    config = parse_config(
        except_flags=args.e,
        only_flags=args.o,
        names=args.n,
        path=args.p,
        g=args.g,
    )

    patch = [
        (
            os.path.abspath(entry["filepath"]),
            DMP.patch_toText(
                DMP.patch_make(
                    a=NL.join(new_lines),
                    b=DMP.diff_main(NL.join(new_lines), NL.join(old_lines)),
                )
            ),
        )
        for entry, old_lines, new_lines in [
            (entry, *_set_values(entry=entry, value=args.value))
            for entry in config.values()
        ]
    ]

    _add_to_history(patch=patch)


def _get_values(entry):
    type, filepath, wrapper, ssh = (
        entry["type"],
        os.path.abspath(entry["filepath"]),
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
        return _get_tag_values(
            filepath=filepath,
            tag=tag,
            occurences_slice=occurences,
            wrapper=wrapper,
            end=end,
        )

    elif type == "lc":
        line = entry["line"]
        column = entry["column"]
        end = entry["end"]
        return _get_lc_values(
            filepath=filepath,
            line=line,
            column=column,
            wrapper=wrapper,
            end=end,
            ssh=ssh,
        )

    elif type == "regex":
        regex = entry["regex"]
        group = entry["group"]
        occurences = entry["occurences"]

        return _get_regex_values(
            filepath=filepath,
            regex=regex,
            group=group,
            occurences_slice=occurences,
            wrapper=wrapper,
            ssh=ssh,
        )


def get_value(args):
    """Get the value associated with a tag in files listed in .xet"""
    config = parse_config(
        except_flags=args.e, only_flags=args.o, names=args.n, path=args.p, g=args.g
    )
    for name, entry in config.items():
        type, filepath, verbosity = (
            entry["type"],
            os.path.abspath(entry["filepath"]),
            args.verbosity,
        )
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue

        if verbosity >= 2:
            print(
                (
                    f"{NAME_COLOR + name}{SEP_COLOR + ':'}"
                    f"{PATH_COLOR + filepath}{SEP_COLOR + ':'}"
                ),
                end="",
            )
        if type == "tag":
            tag = entry["tag"]
            if verbosity >= 2:
                print(f"{IDENTIFIER_COLOR + tag}{SEP_COLOR + ':' + Style.RESET_ALL}")
            _print_tag_values(
                _get_values(entry=entry),
                tag=tag,
                verbosity=verbosity,
            )
        elif type == "lc":
            line = entry["line"]
            column = entry["column"]
            if verbosity >= 2:
                print(
                    f"{IDENTIFIER_COLOR + line}{SEP_COLOR + ':'}\
                    {IDENTIFIER_COLOR + column}{SEP_COLOR + ':' + Style.RESET_ALL}"
                )
            _print_lc_values(
                _get_values(entry=entry),
                verbosity=verbosity,
            )
        elif type == "regex":
            regex = entry["regex"]
            if verbosity >= 2:
                print(f"{IDENTIFIER_COLOR + regex}{SEP_COLOR + ':' + Style.RESET_ALL}")
            _print_regex_values(
                _get_values(entry=entry),
                verbosity=verbosity,
            )


def add_entry(args):
    """Add a new entry to .xet"""

    config = parse_config(g=args.g)

    old_config = deepcopy(load_config(g=args.g))

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
    with open(get_abs_config_path(g=args.g), mode="w") as f:
        json.dump(config, f, indent=4)

    new_config = load_config(g=args.g)

    patch = [
        (
            get_abs_config_path(),
            DMP.patch_toText(
                DMP.patch_make(
                    a=NL.join(new_config),
                    b=DMP.diff_main(NL.join(new_config), NL.join(old_config)),
                )
            ),
        )
    ]

    _add_to_history(patch=patch)


def _update_name(args):
    config = parse_config(
        except_flags=args.e, only_flags=args.o, names=args.n, path=args.p, g=args.g
    )

    if len(config) != 1:
        print("Filter parameters returned more/less than one entry for name change")

    if args.updateValue in config:
        print(
            f"Key {IDENTIFIER_COLOR + args.updateValue + Style.RESET_ALL}"
            "already present in .xet"
        )
        return config

    oldKey = next(iter(config.keys()))

    config[args.updateValue] = config[oldKey]
    config.pop(oldKey)

    return config


def _update_property(args, property: str = None, updatedValue: str = ""):
    """Update the given property of entries"""

    config = parse_config(
        except_flags=args.e, only_flags=args.o, names=args.n, path=args.p, g=args.g
    )

    for key, entry in config.items():
        if property not in entry:
            print(f"Entry: {key} does not have property {property}")
            continue
        entry[property] = updatedValue

    return config


def update_entry(args):
    """Update entries in the .xet"""

    config = parse_config(args.g)
    old_config = deepcopy(load_config(g=args.g))

    if args.updateKey == "type":
        print("Type cannot be updated, create a new entry")
    elif args.updateKey == "name":
        config = _update_name(args=args)
    else:
        config = _update_property(
            args=args, property=args.updateKey, updatedValue=args.updateValue
        )

    with open(get_abs_config_path(g=args.g), mode="w") as f:
        json.dump(config, f, indent=4)

    new_config = load_config(g=args.g)

    patch = [
        (
            get_abs_config_path(),
            DMP.patch_toText(
                DMP.patch_make(
                    a=NL.join(new_config),
                    b=DMP.diff_main(NL.join(new_config), NL.join(old_config)),
                )
            ),
        )
    ]

    _add_to_history(patch=patch)


def remove_entry(args):
    """Remove an entry from .xet based on the tag"""
    config = parse_config(g=args.g)

    delete_keys = filter_config(
        except_flags=args.e,
        only_flags=args.o,
        names=args.n,
        path=args.p,
        g=args.g,
    )

    old_config = deepcopy(load_config(g=args.g))

    for key in delete_keys:
        config.pop(key)

    with open(get_abs_config_path(g=args.g), mode="w") as f:
        json.dump(config, f, indent=4)

    new_config = load_config(g=args.g)

    patch = [
        (
            get_abs_config_path(),
            DMP.patch_toText(
                DMP.patch_make(
                    a=NL.join(new_config),
                    b=DMP.diff_main(NL.join(new_config), NL.join(old_config)),
                )
            ),
        )
    ]

    _add_to_history(patch=patch)


def edit_config(args):
    """Edit .xet with default editor"""
    editor = os.environ.get("EDITOR")
    if editor:
        subprocess.run([editor, get_abs_config_path(args.g)])
    else:
        print("No default editor found.")


def which_config(args):
    """Outputs the .xet that gets defaulted to in the current directory"""
    print(get_abs_config_path())


def show_config(args):
    """Outputs the .xet entries with all given filters applied"""
    print(
        json.dumps(
            parse_config(
                except_flags=args.e,
                only_flags=args.o,
                names=args.n,
                path=args.p,
                g=args.g,
            ),
            indent=4,
        )
    )


def _init_history():
    history = {"past": [], "future": []}

    with open(get_history_path(), mode="w") as f:
        json.dump(history, f, indent=4)


def _load_history():
    if not os.path.exists(get_history_path()):
        _init_history()

    with open(get_history_path()) as f:
        history: dict = json.load(f)

    return history


def _add_to_history(patch: list):
    history = _load_history()

    history["past"].insert(0, patch)

    history["future"] = []

    with open(get_history_path(), mode="w") as f:
        json.dump(history, f, indent=4)


def forget(args):
    _init_history()


def undo(args):
    history = _load_history()

    if len(history["past"]) == 0:
        print("Nothing to undo")
        return

    to_undo = history["past"].pop(0)

    to_future = []
    for filepath, patch in to_undo:
        with open(filepath) as f:
            text = f.read()

        patched_text, _ = DMP.patch_apply(patches=DMP.patch_fromText(patch), text=text)

        with open(filepath, mode="w") as f:
            f.write(patched_text)

        to_future.append(
            (
                filepath,
                DMP.patch_toText(
                    DMP.patch_make(
                        a=patched_text,
                        b=DMP.diff_main(patched_text, text),
                    )
                ),
            )
        )

    history["future"].append(to_future)

    with open(get_history_path(), mode="w") as f:
        json.dump(history, f, indent=4)


def redo(args):
    history = _load_history()

    if len(history["future"]) == 0:
        print("Nothing to redo")
        return

    to_redo = history["future"].pop(0)

    to_past = []

    for filepath, patch in to_redo:
        with open(filepath) as f:
            text = f.read()

        patched_text, _ = DMP.patch_apply(patches=DMP.patch_fromText(patch), text=text)

        with open(filepath, mode="w") as f:
            f.write(patched_text)

        to_past.append(
            (
                filepath,
                DMP.patch_toText(
                    DMP.patch_make(
                        a=patched_text,
                        b=DMP.diff_main(patched_text, text),
                    )
                ),
            )
        )

    history["past"].insert(0, to_past)

    with open(get_history_path(), mode="w") as f:
        json.dump(history, f, indent=4)


def enumerate_slice(slice: slice, length: int):
    return list(range(length))[slice]


def snapshot(args):
    old_config = deepcopy(load_config(g=args.g))

    config = parse_config(
        except_flags=args.e,
        only_flags=args.o,
        names=args.n,
        path=args.p,
        g=args.g,
    )

    if args.split:
        split_config = {}
        for name, entry in config.items():
            values = [value for _, value in _get_values(entry=entry)]
            if len(set(values)) != 1:
                for value in sorted(set(values), key=values.index):
                    new_entry = deepcopy(entry)
                    new_entry["occurences"] = [
                        str(i) for i, x in enumerate(values) if x == value
                    ]
                    split_config[name + "_" + value] = new_entry
            else:
                split_config[name] = entry
        config = split_config

    for name, entry in config.items():
        values = [value for _, value in _get_values(entry=entry)]

        if len(set(values)) != 1:
            if args.first:
                values = [values[0]]
            else:
                print(
                    f"Cannot snapshot entry {name},"
                    "divergent occurence values detected."
                    "Use --split or --first."
                )
                continue

        if not entry["presets"]:
            entry["presets"] = {}

        entry["presets"][args.preset] = values[0]

    with open(get_abs_config_path(g=args.g), mode="w") as f:
        json.dump(config, f, indent=4)

    new_config = load_config(g=args.g)

    patch = [
        (
            get_abs_config_path(),
            DMP.patch_toText(
                DMP.patch_make(
                    a=NL.join(new_config),
                    b=DMP.diff_main(NL.join(new_config), NL.join(old_config)),
                )
            ),
        )
    ]

    _add_to_history(patch=patch)


def main(args=None):
    parser = argparse.ArgumentParser(
        prog="xet",
        description="A CLI tool to manage values across multiple files, projects\
                    and even machines",
    )

    subparsers = parser.add_subparsers(
        dest="command", title="subcommands", required=True
    )

    parser.add_argument("--version", action="version", version=f"xet {VERSION}")

    init_parser = subparsers.add_parser("init", help="Initialize .xet")

    init_parser.set_defaults(func=init_config)

    edit_parser = subparsers.add_parser(
        "edit", help="Opens the .xet in the standard editor"
    )
    edit_parser.set_defaults(func=edit_config)

    """WHICH PARSER"""
    path_parser = subparsers.add_parser("which", help="Prints path of .xet")
    path_parser.set_defaults(func=which_config)

    """SHOW PARSER"""
    show_parser = subparsers.add_parser(
        "show",
        help="Show entries listed in the .xet",
    )
    show_parser.set_defaults(func=show_config)

    """GET PARSER"""
    get_parser = subparsers.add_parser(
        "get",
        help=f"Get {VALUE_COLOR + 'values' + Style.RESET_ALL} from entries\
        listed in the .xet",
    )
    get_parser.set_defaults(func=get_value)

    get_parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        help=f"Enable verbose output. -v outputs the entire line, -vv also outputs the\
            entry {NAME_COLOR + 'name'} {PATH_COLOR + 'filepath' + Style.RESET_ALL}\
            and {IDENTIFIER_COLOR + 'identifier/s' + Style.RESET_ALL}",
        action="count",
        default=0,
    )

    """SET PARSER"""

    set_parser = subparsers.add_parser(
        "set",
        help=f"Set a {VALUE_COLOR + 'value' + Style.RESET_ALL}\
            in files listed in the .xet",
    )
    set_parser.set_defaults(func=set_value)
    set_parser.add_argument(
        "value", help=f"{VALUE_COLOR + 'Value' + Style.RESET_ALL} to set"
    )

    """
    ADD PARSER AND SUB-PARSERS
    """

    add_parser = subparsers.add_parser("add", help="Add a new entry the .xet")

    add_sub_parser = add_parser.add_subparsers(dest="subcommand")

    add_tag_parser = add_sub_parser.add_parser(
        "tag",
        help=f"Add a {IDENTIFIER_COLOR + 'tag' + Style.RESET_ALL}\
              identifier entry to the .xet",
    )

    add_lc_parser = add_sub_parser.add_parser(
        "lc",
        help=f"Add a {IDENTIFIER_COLOR + 'line/column' + Style.RESET_ALL}\
              identifier entry to the .xet",
    )

    add_regex_parser = add_sub_parser.add_parser(
        "regex",
        help=f"Add a {IDENTIFIER_COLOR + 'regex' + Style.RESET_ALL}\
              identifier entry to the .xet",
    )

    add_sub_parsers = [add_tag_parser, add_lc_parser, add_regex_parser]

    list(map(lambda sub: sub.set_defaults(func=add_entry), add_sub_parsers))

    # non-unique positional arguments

    list(
        map(  # Add name argument to all add sub parsers
            lambda sub: sub.add_argument(
                "name",
                help=f"The {NAME_COLOR + 'name' + Style.RESET_ALL}\
                      of the entry in the config",
            ),
            add_sub_parsers,
        )
    )

    list(
        map(  # Add Filepath argument to all add sub parsers
            lambda sub: sub.add_argument(
                "filepath",
                help=f"{PATH_COLOR + 'Path' + Style.RESET_ALL}\
                      of the file",
            ),
            add_sub_parsers,
        )
    )

    # unique positional arguments

    # tag parser
    add_tag_parser.add_argument(
        "tag",
        help=f"{IDENTIFIER_COLOR + 'Tag' + Style.RESET_ALL}\
              identifying the line in the file",
    )

    # lc parser
    add_lc_parser.add_argument(
        "line",
        help=f"The {IDENTIFIER_COLOR + 'line' + Style.RESET_ALL}\
              at which the value is located",
    )
    add_lc_parser.add_argument(
        "column",
        help=f"The {IDENTIFIER_COLOR + 'column' + Style.RESET_ALL}\
              at which the value is located",
    )

    # regex parser
    add_regex_parser.add_argument(
        "regex",
        help=f"The {IDENTIFIER_COLOR + 'regular expression' + Style.RESET_ALL}\
            , if no group is specified values are updated after any given\
            match (like tags)",
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
                help="Will be written at the very end of the line",
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
                help=f"Which occurence of the \
                    {IDENTIFIER_COLOR + 'tag/match' + Style.RESET_ALL}\
                    should be included, can be an integer,\
                    list of integers or the string 'all'",
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
                help=f"{VALUE_COLOR + 'Value' + Style.RESET_ALL}\
                      will be wrapped in this character",
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
                help=f"<Preset Name> <Preset {VALUE_COLOR + 'Value' + Style.RESET_ALL}>\
                      presets can be set with xet preset <Preset Name>",
            ),
            add_sub_parsers,
        )
    )

    # unique optional arguments

    # regex parser
    add_regex_parser.add_argument(
        "--capture-group",
        "-c",
        dest="group",
        nargs=1,
        help=f"The group number of the\
                {VALUE_COLOR + 'value' + Style.RESET_ALL}.\
                0 means the entire match is interpreted as the\
                {VALUE_COLOR + 'value' + Style.RESET_ALL}.",
    )

    """
    UPDATE PARSER
    """

    update_parser = subparsers.add_parser("update", help="Update entries in the .xet")

    update_parser.add_argument(
        "updateKey",
        help=(
            "The key to be updated in the chosen entries"
            f"('{NAME_COLOR + 'name' + Style.RESET_ALL}' changes the key of the entry)"
        ),
    )

    update_parser.add_argument(
        "updateValue", help="The new value of the given key for the chosen entries"
    )

    update_parser.set_defaults(func=update_entry)

    # unique positional arguments

    """
    REMOVE PARSER
    """

    remove_parser = subparsers.add_parser("remove", help="Remove an entry from .xet")
    remove_parser.set_defaults(func=remove_entry)

    """
    PRESET PARSER
    """
    preset_parser = subparsers.add_parser(
        "preset",
        help=f"Set all {VALUE_COLOR + 'values' + Style.RESET_ALL} to a given preset",
    )
    preset_parser.set_defaults(func=set_presets)
    preset_parser.add_argument("preset", help="Name of the preset")

    """
    SNAPSHOT PARSER
    """

    snapshot_parser = subparsers.add_parser(
        "snapshot",
        help=f"Creates a snapshot of the {VALUE_COLOR + 'values' + Style.RESET_ALL}\
            of the filtered entries and adds a preset",
    )

    snapshot_parser.set_defaults(func=snapshot)
    snapshot_parser.add_argument("preset", help="Name of the snapshot preset")

    snapshot_parser.add_argument("--split", action="store_true", dest="split")
    snapshot_parser.add_argument("--first", action="store_true", dest="first")

    """UNDO/REDO PARSERS"""

    undo_parser = subparsers.add_parser(
        "undo",
        help="Undo the last xet command",
    )
    undo_parser.set_defaults(func=undo)

    redo_parser = subparsers.add_parser(
        "redo",
        help="Redo the last undone xet command",
    )
    redo_parser.set_defaults(func=redo)

    forget_parser = subparsers.add_parser(
        "forget",
        help="Reset the xet history",
    )
    forget_parser.set_defaults(func=forget)

    # NON-UNIQUE ARGUMENTS OVERALL

    list(  # Add only argument to update path sub parsers
        map(
            lambda sub: sub.add_argument(
                "--only",
                "-o",
                dest="o",
                nargs="*",
                help="Include only entries with these flags",
            ),
            [
                remove_parser,
                update_parser,
                get_parser,
                set_parser,
                show_parser,
                snapshot_parser,
            ],
        )
    )

    list(  # Add except argument to update path sub parsers
        map(
            lambda sub: sub.add_argument(
                "--except",
                "-e",
                dest="e",
                nargs="+",
                help="Exclude entries with these flags",
            ),
            [
                remove_parser,
                update_parser,
                get_parser,
                set_parser,
                show_parser,
                snapshot_parser,
            ],
        )
    )

    list(  # Add name argument to update path sub parsers
        map(
            lambda sub: sub.add_argument(
                "--names",
                "-n",
                dest="n",
                nargs="*",
                help=f"Include only entries with the given\
                    {NAME_COLOR + 'names' + Style.RESET_ALL}",
            ),
            [
                remove_parser,
                update_parser,
                get_parser,
                set_parser,
                show_parser,
                snapshot_parser,
            ],
        )
    )
    list(  # Add path argument to update path sub parsers
        map(
            lambda sub: sub.add_argument(
                "-p",
                "--path",
                dest="p",
                nargs="+",
                help=f"Include only entries with these\
                    {PATH_COLOR + 'paths' + Style.RESET_ALL}",
            ),
            [
                remove_parser,
                update_parser,
                get_parser,
                set_parser,
                show_parser,
                snapshot_parser,
            ],
        )
    )

    list(  # Add global argument to parsers
        map(
            lambda sub: sub.add_argument(
                "--global",
                "-g",
                action="store_true",
                dest="g",
                help="Use the global .xet",
            ),
            [
                update_parser,
                get_parser,
                set_parser,
                show_parser,
                edit_parser,
                init_parser,
                remove_parser,
                preset_parser,
                snapshot_parser,
            ],
        )
    )

    exec = parser.parse_args(args=args)
    exec.func(exec)


if __name__ == "__main__":
    main()
