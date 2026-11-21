"""Ship the finished front page to the make.fun output folder.

Builds entry.png from build.py if it is missing, then copies it
byte-for-byte into $MAKEFUN_OUTPUT_DIR (default /output). Standard
library only; the rendering itself lives in build.py.
"""

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")


def ensure_entry():
    """Render entry.png in place when it is not already there."""
    target = os.path.join(HERE, "entry.png")
    if os.path.exists(target):
        return target
    sys.path.insert(0, HERE)
    import build

    build.main()
    return target


def deliver():
    os.makedirs(DEST, exist_ok=True)
    shutil.copyfile(ensure_entry(), os.path.join(DEST, "entry.png"))
    print("delivered entry.png to", DEST)


if __name__ == "__main__":
    deliver()
