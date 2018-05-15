#!/bin/sh

rm -f usage.tmp

echo "" >> usage.tmp
echo '```text' >> usage.tmp
python jam/startup.py --help >> usage.tmp
echo '```' >> usage.tmp
echo "" >> usage.tmp


sed '/## Usage/,/## Contributing/ {
//!d
/## Usage/r usage.tmp
}' README.md

rm -f usage.tmp
