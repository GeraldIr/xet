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
  - `-w, --wrapper <char>`: Wrap the value with a character (e.g., quotes).
  - `-o, --occurences <indices>`: Specify which occurrences to modify (integer, list, or `all`).

#### Add a Line/Column-Based Entry

```sh
bump add lc <name> <filepath> <line> <column> [options]
```

- `<line>`: Line number (zero-based index).
- `<column>`: Column position after which the value is placed.
- Options: Same as tag-based entry.

#### Add a Regex-Based Entry

```sh
bump add regex <name> <filepath> <regex> [options]
```

- `<regex>`: Regular expression to match values.
- Options:
  - `-g, --group <int>`: Capture group number to update.
  - `-o, --occurences <indices>`: Specify which matches to modify.

### Get Values from Configured Files

```sh
bump get [-e <flags>] [-o <flags>]
```

- `-e, --except <flags>`: Exclude entries with specified flags.
- `-o, --only <flags>`: Include only entries with specified flags.

### Set Values in Configured Files

```sh
bump set <value> [-e <flags>] [-o <flags>]
```

- `<value>`: The new value to be set.
- Filtering options are the same as for `bump get`.

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

