"""GURUJEE Kivy entry point.

Buildozer requires main.py in source.dir (repo root). This file is the
Android app entry point — it imports and runs the Kivy launcher app defined
in launcher/main.py.
"""
from launcher.main import GurujeeApp

if __name__ == "__main__":
    GurujeeApp().run()
