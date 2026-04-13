from __future__ import annotations

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio

from .constants import APP_ID, DEFAULT_SCROLL_SPEED, DEFAULT_TEXT_SIZE


class Preferences:
    def __init__(self) -> None:
        self.settings = Gio.Settings.new(APP_ID)

    def get_scroll_speed(self) -> float:
        value = self.settings.get_double("scroll-speed")
        return value if value > 0 else DEFAULT_SCROLL_SPEED

    def set_scroll_speed(self, value: float) -> None:
        self.settings.set_double("scroll-speed", value)

    def get_text_size(self) -> int:
        value = self.settings.get_int("text-size")
        return value if value > 0 else DEFAULT_TEXT_SIZE

    def set_text_size(self, value: int) -> None:
        self.settings.set_int("text-size", value)

    def get_mirror_mode(self) -> bool:
        return self.settings.get_boolean("mirror-mode")

    def set_mirror_mode(self, enabled: bool) -> None:
        self.settings.set_boolean("mirror-mode", enabled)

    def get_fullscreen_on_start(self) -> bool:
        return self.settings.get_boolean("fullscreen-on-start")

    def set_fullscreen_on_start(self, enabled: bool) -> None:
        self.settings.set_boolean("fullscreen-on-start", enabled)
