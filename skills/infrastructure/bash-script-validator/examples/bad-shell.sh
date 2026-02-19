#!/bin/sh
#
# Example of a poorly-written POSIX sh script with bashisms and mistakes
#

# Missing: set -eu

# Bad: bashism - [[ ]] not POSIX
check_file() {
    if [[ ! -f $1 ]]; then   # Bashism + unquoted
        echo "not found"
    fi
}

# Bad: bash array (not POSIX)
files=("file1.txt" "file2.txt")

# Bad: bash-style string test
if [ "$var" == "value" ]; then   # == not POSIX, use =
    echo "match"
fi

# Bad: unquoted variable
for f in $files; do
    cat $f | grep pattern   # UUOC + unquoted
done

# Bad: backticks
result=`date`

# Bad: local without function context
local myvar="test"

echo $result   # Unquoted
