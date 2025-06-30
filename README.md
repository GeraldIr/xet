# Bump CLI Usage Guide

## Overview

Bump is a command-line tool for managing and modifying values in multiple files using a configuration file (`.bump`). It supports various methods of identifying and modifying values, including tags, line/column positions, and regular expressions.

## Installation

Ensure you have Python 3 installed. Place the script in a directory included in your system's `PATH` and make it executable:

```sh
chmod +x bump/bump 
cp bump/bump /usr/local/bin/bump
```
You can also just run the ```install.sh``` script which should do the same in most cases.


## Commands

### Initialize Configuration

```sh
bump init
```
- Options:
   - `-g, --global`: Global Mode. Creates a `.bump` file in the XDG_CONFIG_HOME folder instead of locally. 

Creates an empty `.bump` if it does not already exist.

Any bump command will use the `.bump` file in the immediate directory, unless the  `-g, --global` flag is set, then the global  `.bump` file will be used instead.

```sh
bump edit
```
- Options:
   - `-g, --global`: Edit the global `.bump` instead of the local one.

Opens `.bump` in your standard editor or nano.


### Add Entries to Configuration

#### Add a Tag-Based Entry

```sh
bump add tag <name> <filepath> <tag> [options]
```

- `<name>`: Identifier for the entry in `bump.cfg`.
- `<filepath>`: Path to the target file.
- `<tag>`: The string identifying the line to modify.
- Options:
   - `-f, --flags <flags>`: Optional flags for filtering.
   - `-w, --wrapper <char>`: Wrap the value with a character (e.g., quotes), also gets stripped in get mode.
   - `-o, --occurences <index or slice>`: Specify which occurrences to modify (string formatted like a list index in python, can be slices).
   - `-e, --end <str>`: Will get appended in the line after value and wrappers, also gets stripped in get mode.
   - `-d, --padding <int>`: Number of whitespace-padding which gets added after tag and before end. 
   - `-p, --preset <str> <str>`: Name and value of preset, option can be repeated to add multiple presets. 
   - `-s, --ssh <str>`: Hostname of ssh-host the file is found at, as found in openSSH config file.
   - `-g, --global`: Add the entry to the global `.bump`.


#### Add a Line/Column-Based Entry

```sh
bump add lc <name> <filepath> <line> <column> [options]
```
- `<line>`: Line number
- `<column>`: Column position after which the value is placed.
- Options:
   - `-f, --flags <flags>`: Optional flags for filtering.
   - `-w, --wrapper <char>`: Wrap the value with a character (e.g., quotes), also gets stripped in get mode.
   - `-e, --end <str>`: Will get appended in the line after value and wrappers, also gets stripped in get mode.
   - `-d, --padding <int>`: Amount of whitespace-padding which gets added after tag and before end.
   - `-p, --preset <str> <str>`: Name and value of preset, option can be repeated to add multiple presets.
   - `-s, --ssh <str>`: Hostname of ssh-host the file is found at, as found in openSSH config file.
   - `-g, --global`: Add the entry to the global `.bump`.

#### Add a Regex-Based Entry

```sh
bump add regex <name> <filepath> <regex> [options]
```

- `<regex>`: Regular expression to match values.
- Options:
   - `-f, --flags <flags>`: Optional flags for filtering.
   - `-c, --capture-group <int>`: Capture group number to update.
   - `-o, --occurences <index or slice>`: Specify which occurrences to modify (string formatted like a list index in python, can be slices).
   - `-w, --wrapper <char>`: Wrap the value with a character (e.g., quotes), also gets stripped in get mode.
   - `-p, --preset <str> <str>`: Name and value of preset, option can be repeated to add multiple presets.
   - `-s, --ssh <str>`: Hostname of ssh-host the file is found at, as found in openSSH config file.
   - `-g, --global`: Add the entry to the global `.bump`.

### Get Values from Configured Files

```sh
bump get [-e <flags>] [-o <flags>] [-n <names>]
```

Options:
   - `-e, --except <flags>`: Exclude entries with specified flags.
   - `-o, --only <flags>`: Include only entries with specified flags.
   - `-n, --names <names>`: Include only entries with specified names.
   - `-g, --global`: Use the global `.bump`.

### Set Values in Configured Files

```sh
bump set <value> [-e <flags>] [-o <flags>] [-n <names>]
```

- `<value>`: The new value to be set.
Options:
   - `-e, --except <flags>`: Exclude entries with specified flags.
   - `-o, --only <flags>`: Include only entries with specified flags.
   - `-n, --names <names>`: Include only entries with specified names.
   - `-g, --global`: Use the global `.bump`.

### Set Values to Preset

```sh
bump preset <preset>
```

- `<preset>`: Name of the preset to be set.
- Options:
   - `-g, --global`: Use the global `.bump`.

### Remove an Entry

```sh
bump remove <name>
```
- `<name>`: Name of the entry to be removed.
- Options:
   - `-g, --global`: Remove the specified entry from the global `.bump`.

Removes the specified entry from `.bump` file.

## Example Usage

1. **Initialize Configuration:**

   ```sh
   bump init
   ```

2. **Add a Tag-Based Entry:**

   ```sh
   bump add tag version ./config.txt VERSION= -w '"'
   ```

3. **Get Values:**

   ```sh
   bump get
   ```

4. **Set a New Value:**

   ```sh
   bump set "2.0.1"
   ```

5. **Remove an Entry:**

   ```sh
   bump remove version
   ```

