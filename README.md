# bump
bump is a bash-script / CLI tool allowing you to bump multiple version numbers across your projects with a single command.

## Installation 

the bump file is a bash script, so:
- move it to your /usr/local/bin folder 
- run chmod +x /usr/local/bin/bump

now you should be able to call it from anywhere

## Usage

### bump.cfg

The bump.cfg file should be at the top-level of your project (where your .gitignore resides for instance) and each line should be formatted as such:

filepath@tag@flag

whereas the last @flag is optional.

Make sure the file ends with a new-line.

example:

pyproject.toml@version =
bindings/python/pyproject.toml@version =@bindings
deploy/values_development.yaml@appImageTag:
deploy/values_production.yaml@appImageTag:@prod


### calling bump

bump [-e flags (delimited by ,)] NEWVERSION

any file/tag combinations with a flag included in the -e option are skipped.

bump then iterates all the entries in the bump.cfg and replaces the version after the given tag with the new version (NEWVERSION).

examples:

bump 1.0.1
bump -e prod 1.0.1
