# Bump CLI Usage Guide

## Overview

Bump is a command-line tool for managing and modifying values in multiple files using a configuration file (`bump.cfg`). It supports various methods of identifying and modifying values, including tags, line/column positions, and regular expressions.

## Installation

Ensure you have Python 3 installed. Place the script in a directory included in your system's `PATH` and make it executable:

```sh
chmod +x bumpy/bump 
cp bumpy/bump /usr/local/bin/bump
```
You can also just run the ```install.sh``` script which should do the same in most cases.


## Commands

### Initialize Configuration

```sh
bump init
```

Creates an empty `bump.cfg` if it does not already exist.

Any bump command will use the bump.cfg file in the immediate directory, the future promises much more.

```sh
bump edit
```

Opens the `bump.cfg` in your standard editor or nano.


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

#### Add a Regex-Based Entry

```sh
bump add regex <name> <filepath> <regex> [options]
```

- `<regex>`: Regular expression to match values.
- Options:
   - `-f, --flags <flags>`: Optional flags for filtering.
   - `-g, --group <int>`: Capture group number to update.
   - `-o, --occurences <index or slice>`: Specify which occurrences to modify (string formatted like a list index in python, can be slices).
   - `-w, --wrapper <char>`: Wrap the value with a character (e.g., quotes), also gets stripped in get mode.
   - `-p, --preset <str> <str>`: Name and value of preset, option can be repeated to add multiple presets.
   - `-s, --ssh <str>`: Hostname of ssh-host the file is found at, as found in openSSH config file. 

### Get Values from Configured Files

```sh
bump get [-e <flags>] [-o <flags>] [-n <names>]
```

Options:
   - `-e, --except <flags>`: Exclude entries with specified flags.
   - `-o, --only <flags>`: Include only entries with specified flags.
   - `-n, --names <names>`: Include only entries with specified names. 

### Set Values in Configured Files

```sh
bump set <value> [-e <flags>] [-o <flags>] [-n <names>]
```

- `<value>`: The new value to be set.
Options:
   - `-e, --except <flags>`: Exclude entries with specified flags.
   - `-o, --only <flags>`: Include only entries with specified flags.
   - `-n, --names <names>`: Include only entries with specified names. 

### Set Values to Preset

```sh
bump preset <preset>
```

- `<preset>`: Name of the preset to be set.

### Remove an Entry

```sh
bump remove <name>
```

Removes the specified entry from `bump.cfg`.

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

