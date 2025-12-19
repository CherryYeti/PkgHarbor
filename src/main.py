#!/usr/bin/env python3

import sys
import os



script_dir = os.path.dirname(os.path.realpath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from application import Application


def main():
    app = Application(application_id="com.cherryyeti.PkgHarbor")
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
