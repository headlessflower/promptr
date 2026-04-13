from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio

from .constants import APP_ID
from .window import PromptrWindow


class PromptrApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.connect("activate", self.on_activate)
        self.connect("open", self.on_open)

    def _get_or_create_window(self) -> PromptrWindow:
        window = self.props.active_window
        if window is None:
            window = PromptrWindow(self)
        return window

    def on_activate(self, _app: Adw.Application) -> None:
        self._get_or_create_window().present()

    def on_open(
        self, _app: Adw.Application, files: list[Gio.File], _n_files: int, _hint: str
    ) -> None:
        window = self._get_or_create_window()
        if files:
            path = files[0].get_path()
            if path:
                from pathlib import Path

                window.open_path(Path(path))
        window.present()


def main() -> int:
    app = PromptrApplication()
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
