# Headless Flower Teleprompter

A reusable GNOME teleprompter scaffold built with GTK4 and libadwaita.

## Features

- Open text-based documents for teleprompting
- Auto-scroll with adjustable speed
- Adjustable text size
- Mirror mode for camera rigs
- Fullscreen reading mode
- Drag and drop file loading
- Preferences persisted with GSettings
- Extensible document loading layer

## Supported formats

Good native support:

- `.txt`
- `.md`
- `.markdown`
- `.rst`
- `.log`
- `.docx`
- `.odt`
- `.rtf`

Limited support:

- `.pages` — users should export to `.docx` first

## Project layout

```text
headlessflower-teleprompter/
├── data/
│   ├── com.headlessflower.Teleprompter.desktop
│   ├── com.headlessflower.Teleprompter.gschema.xml
│   ├── com.headlessflower.Teleprompter.metainfo.xml
│   └── icons/
├── scripts/
│   └── run-dev.sh
├── src/
│   └── headlessflower_teleprompter/
│       ├── __init__.py
│       ├── constants.py
│       ├── document_loader.py
│       ├── main.py
│       ├── preferences.py
│       └── window.py
├── .gitignore
├── org.gnome.Platform.json
├── pyproject.toml
└── README.md
```

## Linux runtime requirements

You need GTK4, libadwaita, and PyGObject available on the system.

On Fedora:

```bash
sudo dnf install python3-gobject gtk4 libadwaita
```

For DOCX support:

```bash
pip install python-docx
```

Optional but useful for conversion workflows:

```bash
sudo dnf install pandoc
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
./scripts/run-dev.sh
```

## Packaging notes

This scaffold uses:

- `pyproject.toml` for packaging
- `GSettings` for saved preferences
- Flatpak metadata starter files
- desktop entry and appstream metadata starter files

## Next ideas

- add a preferences dialog
- add rich text emphasis controls
- add dual-screen presenter mode
- add playlist or queue support for multiple scripts
- add paragraph pause markers and bookmarks
