#!/bin/python3
import os
import sys
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(PROJECT_DIR, "images")


def main():

    days = float(sys.argv[1]) if len(sys.argv) > 1 else 0

    cutoff = time.time() - days * 86400

    removed = 0
    freed = 0

    for folder, dirs, files in os.walk(IMAGE_DIR, topdown=False):

        for name in files:

            path = os.path.join(folder, name)

            if os.path.getmtime(path) > cutoff:
                continue

            freed += os.path.getsize(path)
            os.remove(path)
            removed += 1

        if folder != IMAGE_DIR and not os.listdir(folder):
            os.rmdir(folder)

    print("removed {0} images, freed {1:.1f} MB".format(removed, freed / (1024 * 1024)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
