#!/usr/bin/env python
# -*- coding: utf-8 -*-


import json
from pathlib import Path
from typing import Dict, Any, List

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, Input, Switch
from textual.containers import Container, Horizontal
from textual.widget import Widget


# --- 1. CONFIGURATION SCHEMA DEFINITION ---
# This schema drives the entire UI generation.
# Keys:
#   - 'type': Python data type ('str', 'int', 'bool')
#   - 'default': The default value for the field
#   - 'description': A label for the UI
CONFIG_SCHEMA: Dict[str, Dict[str, Any]] = {
    "application": {
        "name": {
            "type": "str",
            "default": "TUI Config App",
            "description": "Application Name",
        },
        "version": {"type": "str", "default": "1.0.0", "description": "Version"},
        "hot_reload_enabled": {
            "type": "bool",
            "default": True,
            "description": "Hot Reload",
        },
    },
    "settings": {
        "theme_name": {
            "type": "str",
            "default": "dark",
            "description": "Theme (e.g., 'dark' or 'light')",
        },
        "font_size": {"type": "int", "default": 14, "description": "Font Size (pt)"},
        "max_connections": {
            "type": "int",
            "default": 10,
            "description": "Max Connections",
        },
        "use_tls": {"type": "bool", "default": False, "description": "Require TLS/SSL"},
    },
}


class ConfigItem(Horizontal, can_focus=False):
    """A custom widget representing a single key-value configuration pair."""

    def __init__(self, key: str, config: Dict[str, Any], section_key: str) -> None:
        super().__init__()
        self.key = key
        self.config = config
        self.section_key = section_key
        self.input_widget: Widget | None = None
        self.styles.height = 3  # Ensure enough space for input widgets

    def compose(self) -> ComposeResult:
        """Dynamically create the input widget based on the schema type."""

        # Label (takes 1/3 of the space)
        yield Static(self.config["description"], classes="config-label")

        # Input Widget (takes 2/3 of the space)
        input_type = self.config["type"]
        default_value = self.config["default"]

        if input_type == "bool":
            # Boolean uses a Switch
            self.input_widget = Switch(
                value=default_value,
                id=f"input_{self.section_key}_{self.key}",
                classes="config-switch",
            )
        else:
            # String or Integer uses an Input
            type_mapping = {"str": "text", "int": "integer"}
            self.input_widget = Input(
                value=str(default_value),
                type=type_mapping.get(input_type, "text"),
                id=f"input_{self.section_key}_{self.key}",
                classes="config-input",
            )

        yield self.input_widget


class StructuredConfigEditorApp(App):
    """A Textual application for editing structured configuration based on a schema."""

    # 2. Define Textual CSS for styling the structured UI
    DEFAULT_CSS = """
    Screen {
        background: #1e1e1e;
    }

    #main-container {
        height: 1fr;
        padding: 0 2;
        overflow-y: scroll;
    }

    .section-header {
        height: 2;
        width: 100%;
        margin-top: 1;
        text-style: bold italic;
        background: #495057;
        color: #ffffff;
        padding: 0 1;
        text-align: left;
    }

    ConfigItem {
        padding: 0 1;
        margin-top: 1;
        align: center middle;
    }
    
    .config-label {
        width: 1fr;
        color: #adb5bd;
    }

    .config-input {
        width: 2fr;
        background: #252526;
        color: #f8f9fa;
        border: solid #6c757d;
        padding-left: 1;
    }
    
    .config-switch {
        width: 10;
        background: #252526;
        border: none;
        align: right middle;
    }

    #action-bar {
        height: 5;
        align: center middle;
        background: #343a40;
        border-top: solid #495057;
    }

    #action-bar Button {
        margin-right: 2;
        min-width: 15;
        border: round #6c757d;
        color: #ffffff;
    }
    
    #action-bar Button.validate {
        background: #007bff;
    }

    #action-bar Button.save {
        background: #28a745;
    }

    #status-bar {
        height: 1;
        background: #343a40;
        color: #ffffff;
        padding-left: 1;
        margin-bottom: 1;
    }
    
    .status-valid {
        background: #28a745;
    }
    
    .status-invalid {
        background: #dc3545;
    }
    """

    # 3. Define Key Bindings for user actions
    BINDINGS = [
        ("ctrl+s", "save_config", "Save (Ctrl+S)"),
        ("ctrl+v", "validate_config", "Validate (Ctrl+V)"),
        ("ctrl+q", "quit", "Quit (Ctrl+Q)"),
    ]

    status_message = Static("Ready to edit config.json...", id="status-bar")
    CONFIG_PATH = Path("config.json")  # Simulated file path

    def compose(self) -> ComposeResult:
        """Create child widgets based on the schema."""
        yield Header(name="Textual Structured Config Editor")

        # Main container for the dynamic UI
        with Container(id="main-container"):
            for section_key, section_data in CONFIG_SCHEMA.items():
                # Add a section header (e.g., "APPLICATION")
                yield Static(section_key.upper(), classes="section-header")

                # Add individual configuration items
                for key, config in section_data.items():
                    yield ConfigItem(key, config, section_key)

        # Action bar container for buttons
        with Horizontal(id="action-bar"):
            yield Button(
                "Validate Types",
                variant="primary",
                classes="validate",
                id="validate-button",
            )
            yield Button(
                "Save Changes", variant="success", classes="save", id="save-button"
            )

        # Status bar
        yield self.status_message
        yield Footer()

    def _collect_data(self) -> tuple[Dict[str, Any] | None, List[str]]:
        """
        Traverses the UI elements to collect data and validate types.

        Returns:
            A tuple of (config_data: dict | None, errors: list[str]).
        """
        config_data: Dict[str, Dict[str, Any]] = {}
        errors: List[str] = []

        # Iterate through the schema structure
        for section_key, section_data in CONFIG_SCHEMA.items():
            config_data[section_key] = {}
            for key, config in section_data.items():

                # Find the corresponding ConfigItem widget
                item_widget = self.query_one(f"#input_{section_key}_{key}")

                # Determine the value based on the widget type
                if isinstance(item_widget, Switch):
                    value = item_widget.value
                    data_type = "bool"
                elif isinstance(item_widget, Input):
                    raw_value = item_widget.value
                    data_type = config["type"]

                    try:
                        if data_type == "int":
                            value = int(raw_value)
                        elif data_type == "str":
                            value = raw_value
                        else:
                            value = raw_value  # Fallback
                    except ValueError:
                        errors.append(
                            f"Validation Error in '{config['description']}': Expected type '{data_type}', got '{raw_value}'."
                        )
                        continue  # Skip saving this value if invalid

                else:
                    # Should not happen
                    continue

                # Store the successfully collected and validated value
                config_data[section_key][key] = value

        return config_data if not errors else None, errors

    def action_validate_config(self) -> None:
        """Action handler for Ctrl+V and Validate button press."""
        _, errors = self._collect_data()

        if not errors:
            self.status_message.update(
                "Status: All fields validated successfully (types match schema)."
            )
            self.status_message.set_class(True, "status-valid")
            self.status_message.set_class(False, "status-invalid")
        else:
            # Display only the first error for brevity in the status bar
            error_msg = f"Validation Error: {errors[0]}"
            self.status_message.update(f"Status: {error_msg}")
            self.status_message.set_class(True, "status-invalid")
            self.status_message.set_class(False, "status-valid")

    def action_save_config(self) -> None:
        """Action handler for Ctrl+S and Save button press."""
        config_data, errors = self._collect_data()

        if config_data and not errors:
            # Successfully collected and validated data
            # In a real app, you would write this JSON string to self.CONFIG_PATH here.
            final_json = json.dumps(config_data, indent=4)

            # Simulated save operation
            print("--- SIMULATED CONFIG SAVE ---")
            print(final_json)
            print("-----------------------------")

            self.status_message.update(
                f"Status: Config saved (simulated) to {self.CONFIG_PATH}."
            )
            self.status_message.set_class(True, "status-valid")
            self.status_message.set_class(False, "status-invalid")
        else:
            self.status_message.update(
                "Status: Save failed. Please fix validation errors first."
            )
            self.status_message.set_class(True, "status-invalid")
            self.status_message.set_class(False, "status-valid")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Maps button presses to app actions."""
        if event.button.id == "validate-button":
            self.action_validate_config()
        elif event.button.id == "save-button":
            self.action_save_config()


if __name__ == "__main__":
    app = StructuredConfigEditorApp()
    app.run()
