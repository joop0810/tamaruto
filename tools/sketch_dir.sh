#!/bin/bash
# Prints a directory that arduino-cli will accept as the TamaNaruto sketch.
#
# arduino-cli insists the sketch FOLDER is named after the .ino. A clone of this
# repo lands in whatever the repository is called (joop0810/tamaruto -> tamaruto/),
# and then "main file missing from sketch" stops every build. So when the folder
# name does not match, the sketch sources are copied into
# build/sketch/TamaNaruto/ and that is what gets compiled. Only the top-level
# sources are copied: the Arduino builder compiles nothing else from the root.
#
# Usage: SK="$(bash tools/sketch_dir.sh)"
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ "$(basename "$ROOT")" = "TamaNaruto" ]; then
  echo "$ROOT"
  exit 0
fi
SK="$ROOT/build/sketch/TamaNaruto"
rm -rf "$SK"
mkdir -p "$SK"
cp "$ROOT"/*.ino "$ROOT"/*.cpp "$ROOT"/*.h "$SK"/
echo "$SK"
