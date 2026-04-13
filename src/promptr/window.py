from __future__ import annotations

from pathlib import Path
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from .constants import (
    APP_NAME,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    SCROLL_TICK_MS,
)
from .document_loader import DocumentLoader, UnsupportedFormatError
from .preferences import Preferences


class DropArea(Gtk.Box):
    __gtype_name__ = "PromptrDropArea"

    def __init__(self, on_file: Callable[[Path], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.on_file = on_file
        self.set_margin_top(18)
        self.set_margin_bottom(8)
        self.set_margin_start(18)
        self.set_margin_end(18)
        self.add_css_class("card")
        self.add_css_class("drop-area")

        title = Gtk.Label(label="Drop a script here or use Open")
        title.add_css_class("title-4")
        title.set_xalign(0)
        self.append(title)

        subtitle = Gtk.Label(
            label="TXT, Markdown, DOCX, ODT, RTF supported. Pages works best after export to DOCX."
        )
        subtitle.set_wrap(True)
        subtitle.set_xalign(0)
        subtitle.add_css_class("dim-label")
        self.append(subtitle)

        target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        target.connect("drop", self._on_drop)
        self.add_controller(target)

    def _on_drop(self, _target: Gtk.DropTarget, value: GObject.Value, _x: float, _y: float) -> bool:
        file_list = value.get_value()
        if not file_list:
            return False

        files = file_list.get_files()
        if not files:
            return False

        path = files[0].get_path()
        if not path:
            return False

        self.on_file(Path(path))
        return True


class PromptrWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.preferences = Preferences()
        self.current_path: Path | None = None
        self.scroll_source_id: int | None = None
        self.is_scrolling = False
        self.scroll_speed = self.preferences.get_scroll_speed()
        self.text_size = self.preferences.get_text_size()

        self.set_title(APP_NAME)
        self.set_default_size(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

        self._install_css()
        self._build_ui()
        self._bind_keyboard_shortcuts()
        self._apply_saved_preferences()
        self._load_welcome_text()

        if self.preferences.get_fullscreen_on_start():
            self.fullscreen_button.set_active(True)

    def _install_css(self) -> None:
        css = Gtk.CssProvider()
        css.load_from_data(
            b"""
            .promptr-view {
                background: #111111;
                color: #f5f5f5;
                border-radius: 24px;
                padding: 18px;
            }

            .promptr-view text {
                background: transparent;
                color: inherit;
            }

            .drop-area {
                border-radius: 20px;
                padding: 16px;
            }

            .mirrored {
                transform: scaleX(-1);
            }

            .prompt-overlay-top {
                background-image: linear-gradient(
                    to bottom,
                    alpha(#111111, 0.96),
                    alpha(#111111, 0.0)
                );
                border-top-left-radius: 24px;
                border-top-right-radius: 24px;
            }

            .prompt-overlay-bottom {
                background-image: linear-gradient(
                    to top,
                    alpha(#111111, 0.96),
                    alpha(#111111, 0.0)
                );
                border-bottom-left-radius: 24px;
                border-bottom-right-radius: 24px;
            }

            .prompt-guide-line {
                background: alpha(#ffffff, 0.35);
                min-height: 2px;
                border-radius: 999px;
            }
            """
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self) -> None:
        self.toolbar_view = Adw.ToolbarView()
        self.set_content(self.toolbar_view)

        header = Adw.HeaderBar()
        self.toolbar_view.add_top_bar(header)

        open_button = Gtk.Button(icon_name="document-open-symbolic")
        open_button.set_tooltip_text("Open document")
        open_button.connect("clicked", self._on_open_clicked)
        header.pack_start(open_button)

        self.play_button = Gtk.ToggleButton(icon_name="media-playback-start-symbolic")
        self.play_button.set_tooltip_text("Play or pause")
        self.play_button.connect("toggled", self._on_play_toggled)
        header.pack_start(self.play_button)

        restart_button = Gtk.Button(icon_name="go-top-symbolic")
        restart_button.set_tooltip_text("Back to top")
        restart_button.connect("clicked", self._on_restart_clicked)
        header.pack_start(restart_button)

        self.fullscreen_button = Gtk.ToggleButton(label="Fullscreen")
        self.fullscreen_button.connect("toggled", self._on_fullscreen_toggled)
        header.pack_end(self.fullscreen_button)

        self.mirror_button = Gtk.ToggleButton(label="Mirror")
        self.mirror_button.connect("toggled", self._on_mirror_toggled)
        header.pack_end(self.mirror_button)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.toolbar_view.set_content(main_box)

        self.drop_area = DropArea(self.open_path)
        main_box.append(self.drop_area)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        controls.set_margin_start(18)
        controls.set_margin_end(18)
        controls.set_margin_top(6)
        controls.set_margin_bottom(12)
        main_box.append(controls)

        speed_label = Gtk.Label(label="Scroll speed")
        speed_label.set_xalign(0)
        controls.append(speed_label)

        self.speed_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.2, 15.0, 0.1)
        self.speed_scale.set_hexpand(True)
        self.speed_scale.set_digits(1)
        self.speed_scale.connect("value-changed", self._on_speed_changed)
        controls.append(self.speed_scale)

        size_label = Gtk.Label(label="Text size")
        size_label.set_xalign(0)
        controls.append(size_label)

        self.size_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 18, 120, 1)
        self.size_scale.set_hexpand(True)
        self.size_scale.set_digits(0)
        self.size_scale.connect("value-changed", self._on_size_changed)
        controls.append(self.size_scale)

        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_xalign(0)
        self.status_label.add_css_class("dim-label")
        self.status_label.set_margin_start(18)
        self.status_label.set_margin_end(18)
        self.status_label.set_margin_bottom(12)
        main_box.append(self.status_label)

        self.overlay = Gtk.Overlay()
        self.overlay.set_hexpand(True)
        self.overlay.set_vexpand(True)
        self.overlay.set_margin_start(18)
        self.overlay.set_margin_end(18)
        self.overlay.set_margin_bottom(18)
        main_box.append(self.overlay)

        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_hexpand(True)
        self.scrolled_window.set_vexpand(True)
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.overlay.set_child(self.scrolled_window)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        container.set_margin_top(260)
        container.set_margin_bottom(260)
        container.set_margin_start(42)
        container.set_margin_end(42)
        self.scrolled_window.set_child(container)

        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.text_view.set_monospace(False)
        self.text_view.set_top_margin(18)
        self.text_view.set_bottom_margin(18)
        self.text_view.set_left_margin(18)
        self.text_view.set_right_margin(18)
        self.text_view.add_css_class("promptr-view")
        container.append(self.text_view)

        self.buffer = self.text_view.get_buffer()

        self.guide_line = Gtk.Box()
        self.guide_line.set_halign(Gtk.Align.FILL)
        self.guide_line.set_valign(Gtk.Align.CENTER)
        self.guide_line.set_margin_start(42)
        self.guide_line.set_margin_end(42)
        self.guide_line.set_can_target(False)
        self.guide_line.add_css_class("prompt-guide-line")
        self.overlay.add_overlay(self.guide_line)

        self.top_fade = Gtk.Box()
        self.top_fade.set_halign(Gtk.Align.FILL)
        self.top_fade.set_valign(Gtk.Align.START)
        self.top_fade.set_size_request(-1, 140)
        self.top_fade.set_can_target(False)
        self.top_fade.add_css_class("prompt-overlay-top")
        self.top_fade.set_margin_start(42)
        self.top_fade.set_margin_end(42)
        self.overlay.add_overlay(self.top_fade)

        self.bottom_fade = Gtk.Box()
        self.bottom_fade.set_halign(Gtk.Align.FILL)
        self.bottom_fade.set_valign(Gtk.Align.END)
        self.bottom_fade.set_size_request(-1, 140)
        self.bottom_fade.set_can_target(False)
        self.bottom_fade.add_css_class("prompt-overlay-bottom")
        self.bottom_fade.set_margin_start(42)
        self.bottom_fade.set_margin_end(42)
        self.overlay.add_overlay(self.bottom_fade)

    def _bind_keyboard_shortcuts(self) -> None:
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(controller)

    def _apply_saved_preferences(self) -> None:
        self.speed_scale.set_value(self.scroll_speed)
        self.size_scale.set_value(self.text_size)
        self.mirror_button.set_active(self.preferences.get_mirror_mode())
        self._apply_text_size()

    def _load_welcome_text(self) -> None:
        self.buffer.set_text(
            "Promptr\n\n"
            "Open a document or drag one into the window.\n\n"
            "Keyboard shortcuts:\n"
            "• Space: play or pause\n"
            "• Up and Down: adjust scroll speed\n"
            "• Plus and Minus: adjust text size\n"
            "• Home: jump to top\n\n"
            "For Pages documents, export to DOCX first for best compatibility."
        )
        self._apply_text_size()
        GLib.idle_add(self._update_estimated_time)

    def _apply_text_size(self) -> None:
        start_iter = self.buffer.get_start_iter()
        end_iter = self.buffer.get_end_iter()

        table = self.buffer.get_tag_table()
        tag = table.lookup("promptr-size")

        if tag is None:
            tag = self.buffer.create_tag("promptr-size")

        tag.set_property("size-points", float(self.text_size))

        self.buffer.remove_tag(tag, start_iter, end_iter)
        self.buffer.apply_tag(tag, start_iter, end_iter)

    def _set_status(self, message: str) -> None:
        self.status_label.set_text(message)

    def open_path(self, path: Path) -> None:
        if not path.exists():
            self._set_status("That file no longer exists")
            return

        if not DocumentLoader.can_open(path):
            self._set_status(f"Unsupported format: {path.suffix}")
            return

        try:
            content = DocumentLoader.load(path)
        except UnsupportedFormatError as exc:
            self._set_status(str(exc))
            return
        except Exception as exc:
            self._set_status(f"Could not open file: {exc}")
            return

        if not content.strip():
            self._set_status("The document appears to be empty")
            return

        self.current_path = path
        self.buffer.set_text(content)
        self._apply_text_size()
        self._scroll_to_top()
        GLib.idle_add(self._update_estimated_time)

    def _scroll_to_top(self) -> None:
        adjustment = self.scrolled_window.get_vadjustment()
        adjustment.set_value(adjustment.get_lower())

    def _on_open_clicked(self, _button: Gtk.Button) -> None:
        dialog = Gtk.FileChooserNative(
            title="Open document",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
            accept_label="Open",
            cancel_label="Cancel",
        )

        file_filter = Gtk.FileFilter()
        file_filter.set_name("Supported documents")
        for pattern in (
            "*.txt",
            "*.md",
            "*.markdown",
            "*.rst",
            "*.log",
            "*.docx",
            "*.odt",
            "*.rtf",
            "*.pages",
        ):
            file_filter.add_pattern(pattern)
        dialog.add_filter(file_filter)
        dialog.connect("response", self._on_file_dialog_response)
        dialog.show()

    def _on_file_dialog_response(self, dialog: Gtk.FileChooserNative, response: int) -> None:
        if response == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            if file is not None:
                path = file.get_path()
                if path:
                    self.open_path(Path(path))
        dialog.destroy()

    def _on_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        if keyval == Gdk.KEY_space:
            self.play_button.set_active(not self.play_button.get_active())
            return True
        if keyval in {Gdk.KEY_Up, Gdk.KEY_KP_Up}:
            self.speed_scale.set_value(min(self.speed_scale.get_value() + 0.2, 15.0))
            return True
        if keyval in {Gdk.KEY_Down, Gdk.KEY_KP_Down}:
            self.speed_scale.set_value(max(self.speed_scale.get_value() - 0.2, 0.2))
            return True
        if keyval in {Gdk.KEY_plus, Gdk.KEY_equal, Gdk.KEY_KP_Add}:
            self.size_scale.set_value(min(self.size_scale.get_value() + 2, 120))
            return True
        if keyval in {Gdk.KEY_minus, Gdk.KEY_KP_Subtract}:
            self.size_scale.set_value(max(self.size_scale.get_value() - 2, 18))
            return True
        if keyval == Gdk.KEY_Home:
            self._scroll_to_top()
            return True
        return False

    def _on_speed_changed(self, scale: Gtk.Scale) -> None:
        self.scroll_speed = scale.get_value()
        self.preferences.set_scroll_speed(self.scroll_speed)
        self._update_estimated_time()

    def _on_size_changed(self, scale: Gtk.Scale) -> None:
        self.text_size = int(scale.get_value())
        self.preferences.set_text_size(self.text_size)
        self._apply_text_size()
        GLib.idle_add(self._update_estimated_time)

    def _on_play_toggled(self, button: Gtk.ToggleButton) -> None:
        self.is_scrolling = button.get_active()
        if self.is_scrolling:
            self.play_button.set_icon_name("media-playback-pause-symbolic")
            self._start_scrolling()
        else:
            self.play_button.set_icon_name("media-playback-start-symbolic")
            self._stop_scrolling()

    def _on_restart_clicked(self, _button: Gtk.Button) -> None:
        self._scroll_to_top()
        self._update_estimated_time()

    def _on_mirror_toggled(self, button: Gtk.ToggleButton) -> None:
        enabled = button.get_active()
        self.preferences.set_mirror_mode(enabled)
        if enabled:
            self.text_view.add_css_class("mirrored")
        else:
            self.text_view.remove_css_class("mirrored")
        self._update_estimated_time()

    def _on_fullscreen_toggled(self, button: Gtk.ToggleButton) -> None:
        enabled = button.get_active()
        self.preferences.set_fullscreen_on_start(enabled)
        if enabled:
            self.fullscreen()
        else:
            self.unfullscreen()
        GLib.idle_add(self._update_estimated_time)

    def _start_scrolling(self) -> None:
        if self.scroll_source_id is None:
            self.scroll_source_id = GLib.timeout_add(SCROLL_TICK_MS, self._scroll_tick)

    def _stop_scrolling(self) -> None:
        if self.scroll_source_id is not None:
            GLib.source_remove(self.scroll_source_id)
            self.scroll_source_id = None

    def _scroll_tick(self) -> bool:
        adjustment = self.scrolled_window.get_vadjustment()
        limit = adjustment.get_upper() - adjustment.get_page_size()
        next_value = min(adjustment.get_value() + self.scroll_speed, limit)
        adjustment.set_value(next_value)

        if next_value >= limit:
            self.play_button.set_active(False)
            self._set_status("Reached end of document")
            return False

        return True

    def _get_estimated_duration_seconds(self) -> float:
        adjustment = self.scrolled_window.get_vadjustment()
        total_scroll_distance = max(0.0, adjustment.get_upper() - adjustment.get_page_size())

        if self.scroll_speed <= 0:
            return 0.0

        pixels_per_second = self.scroll_speed * (1000.0 / SCROLL_TICK_MS)

        if pixels_per_second <= 0:
            return 0.0

        return total_scroll_distance / pixels_per_second

    def _format_duration(self, seconds: float) -> str:
        total_seconds = max(0, int(round(seconds)))
        minutes, secs = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        if minutes > 0:
            return f"{minutes}m {secs}s"
        return f"{secs}s"

    def _update_estimated_time(self) -> bool:
        seconds = self._get_estimated_duration_seconds()
        estimate = self._format_duration(seconds)

        if self.current_path:
            self._set_status(f"{self.current_path.name} • Estimated duration: {estimate}")
        else:
            self._set_status(f"Estimated duration: {estimate}")

        return False

    def close_request(self) -> bool:
        self._stop_scrolling()
        return False
