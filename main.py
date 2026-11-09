import sys

from src import App


def main() -> None:
    # The app normally lives in %LOCALAPPDATA%, so elevation is not required.
    # Pass --elevate (or run the built patcher as administrator) when the
    # installation is under Program Files.
    if "--elevate" in sys.argv:
        try:
            from pyuac import isUserAdmin, runAsAdmin

            if not isUserAdmin():
                runAsAdmin()
                sys.exit(0)
        except Exception:
            pass

    App().mainloop()


if __name__ == "__main__":
    main()
