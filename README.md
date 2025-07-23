[![build](https://github.com/GeraldIr/xet/actions/workflows/python-publish.yml/badge.svg)](https://github.com/GeraldIr/xet/actions/workflows/python-publish.yml)
![version](https://img.shields.io/pypi/v/xet)

# xet CLI Usage Guide

## Overview

xet is a command-line tool for managing and modifying values in multiple files using a configuration file (`.xet`). It supports various methods of identifying and modifying values, including tags, line/column positions, and regular expressions.
You can create presets and change between them on the fly.

## Installation


```sh
pipx install xet
```
or
```sh
pip install xet
```


## Commands

### Configuration

#### Initialize Configuration

```sh
xet init
```
- Options:
   - `-g, --global`: Global Mode. Creates a `.xet` file in the XDG_CONFIG_HOME folder instead of locally.

Creates an empty `.xet` if it does not already exist.

Any xet command will use the `.xet` file in the immediate directory, if there is no local `.xet` the global  `.xet` file will be used instead. You can force the usage of the global `.xet` using the `-g, --global` flag.

#### Open .xet in editor

```sh
xet edit
```
- Options:
   - `-g, --global`: Edit the global `.xet` instead of the local one.

Opens `.xet` in your standard editor or nano.

#### Clarify .xet directory

```sh
xet which
```

Shows the absolute path to the default `.xet` that will be used if any xet command is run.

#### Print .xet entries

```sh
xet show [options]
```

Options:
   - `-e, --except <flags>`: Exclude entries with specified flags.
   - `-o, --only <flags>`: Include only entries with specified flags.
   - `-n, --names <names>`: Include only entries with specified names.
   - `-p, --path <path>`: Include only entries with specified path.
   - `-g, --global`: Use the global `.xet`.

Shows the `.xet` entries with the given optional filters applied.


#### Add Entries to Configuration

##### Add a Tag-Based Entry

```sh
xet add tag <name> <filepath> <tag> [options]
```

- `<name>`: Identifier for the entry in `xet.cfg`.
- `<filepath>`: Path to the target file.
- `<tag>`: The string identifying the line to modify.
- Options:
   - `-f, --flags <flags>`: Optional flags for filtering.
   - `-w, --wrapper <char>`: Wrap the value with a character (e.g., quotes), also gets stripped in get mode.
   - `-o, --occurences <index or slice>`: Specify which occurrences to modify (string formatted like a list index in python, can be slices).
   - `-e, --end <str>`: Will get appended in the line after value and wrappers, also gets stripped in get mode.
   - `-p, --preset <str> <str>`: Name and value of preset, option can be repeated to add multiple presets.
   - `-s, --ssh <str>`: Hostname of ssh-host the file is found at, as found in openSSH config file.
   - `-g, --global`: Add the entry to the global `.xet`.


##### Add a Line/Column-Based Entry

```sh
xet add lc <name> <filepath> <line> <column> [options]
```
- `<line>`: Line number
- `<column>`: Column position after which the value is placed.
- Options:
   - `-f, --flags <flags>`: Optional flags for filtering.
   - `-w, --wrapper <char>`: Wrap the value with a character (e.g., quotes), also gets stripped in get mode.
   - `-e, --end <str>`: Will get appended in the line after value and wrappers, also gets stripped in get mode.
   - `-p, --preset <str> <str>`: Name and value of preset, option can be repeated to add multiple presets.
   - `-s, --ssh <str>`: Hostname of ssh-host the file is found at, as found in openSSH config file.
   - `-g, --global`: Add the entry to the global `.xet`.

##### Add a Regex-Based Entry

```sh
xet add regex <name> <filepath> <regex> [options]
```

- `<regex>`: Regular expression to match values.
- Options:
   - `-f, --flags <flags>`: Optional flags for filtering.
   - `-c, --capture-group <int>`: Capture group number to update.
   - `-o, --occurences <index or slice>`: Specify which occurrences to modify (string formatted like a list index in python, can be slices).
   - `-w, --wrapper <char>`: Wrap the value with a character (e.g., quotes), also gets stripped in get mode.
   - `-p, --preset <str> <str>`: Name and value of preset, option can be repeated to add multiple presets.
   - `-s, --ssh <str>`: Hostname of ssh-host the file is found at, as found in openSSH config file.
   - `-g, --global`: Add the entry to the global `.xet`.

#### Update Entries

```sh
xet update <key> <value> [options]
```
- `<key>`: The key of the property to update ('name' will update the key of the entry).
- `<value>`: The new value for the property.
Options:
   - `-e, --except <flags>`: Exclude entries with specified flags.
   - `-o, --only <flags>`: Include only entries with specified flags.
   - `-n, --names <names>`: Include only entries with specified names.
   - `-p, --path <path>`: Include only entries with specified path.
   - `-g, --global`: Use the global `.xet`.

Updates the value of a property across filtered entries in the `.xet`.

#### Remove Entries

```sh
xet remove [options]
```

Options:
   - `-e, --except <flags>`: Exclude entries with specified flags.
   - `-o, --only <flags>`: Include only entries with specified flags.
   - `-n, --names <names>`: Include only entries with specified names.
   - `-p, --path <path>`: Include only entries with specified path.
   - `-g, --global`: Use the global `.xet`.

Removes the specified entries from the `.xet`.

#### Snapshot

```sh
xet snapshot <preset> [options]
```
- `<preset>`: The name of the new preset.
Options:
   - `--first`: When there is divergent values in seperate occurences in an entry, use the first value for the preset.
   - `--split`: When there is divergent values in seperate occurences in an entry, split the entry such that no divergences remain.
   - `-e, --except <flags>`: Exclude entries with specified flags.
   - `-o, --only <flags>`: Include only entries with specified flags.
   - `-n, --names <names>`: Include only entries with specified names.
   - `-p, --path <path>`: Include only entries with specified path.
   - `-g, --global`: Use the global `.xet`.


Adds a preset to the filtered entries using their current values.

### Modifying Values

#### Get Values from Configured Files

```sh
xet get [options]
```

Options:
   - `-e, --except <flags>`: Exclude entries with specified flags.
   - `-o, --only <flags>`: Include only entries with specified flags.
   - `-n, --names <names>`: Include only entries with specified names.
   - `-p, --path <path>`: Include only entries with specified path.
   - `-g, --global`: Use the global `.xet`.


#### Set Values in Configured Files

```sh
xet set <value> [options]
```

- `<value>`: The new value to be set.
Options:
   - `-e, --except <flags>`: Exclude entries with specified flags.
   - `-o, --only <flags>`: Include only entries with specified flags.
   - `-n, --names <names>`: Include only entries with specified names.
   - `-p, --path <path>`: Include only entries with specified path.
   - `-g, --global`: Use the global `.xet`.

#### Set Values to Preset

```sh
xet preset <preset>
```

- `<preset>`: Name of the preset to be set.
- Options:
   - `-g, --global`: Use the global `.xet`.

### History

#### Undo

```sh
xet undo
```

Undoes the changes of the last command.

#### Redo

```sh
xet redo
```

Redoes the last undone changes.

#### Forget

```sh
xet forget
```

Reset history file.

## Example Usage

1. **Initialize Configuration:**

   ```sh
   xet init
   ```

2. **Add a Tag-Based Entry:**

   ```sh
   xet add tag version ./config.txt VERSION= -w '"'
   ```

3. **Get Values:**

   ```sh
   xet get
   ```

4. **Set a New Value:**

   ```sh
   xet set "2.0.1"
   ```

5. **Remove an Entry:**

   ```sh
   xet remove version
   ```
