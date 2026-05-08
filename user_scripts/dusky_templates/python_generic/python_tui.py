#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Label, Input, Static
from textual.screen import ModalScreen
from textual.reactive import reactive
from textual.events import Resize
from textual import work

from rich.table import Table
from rich.text import Text
from rich.markup import escape

# =============================================================================
# MATUGEN THEME ENGINE (Deep Resolution)
# =============================================================================

def load_matugen_theme() -> dict[str, str]:
    colors = {}
    matugen_path = Path("~/.config/matugen/generated/dusky_tui.css").expanduser()
    
    if matugen_path.exists():
        try:
            with open(matugen_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("@define-color"):
                        parts = line.split()
                        if len(parts) >= 3:
                            name = parts[1]
                            val = parts[2].rstrip(";")
                            colors[name] = val
        except Exception:
            pass

    resolved_all = False
    while not resolved_all:
        resolved_all = True
        for k, v in colors.items():
            if v.startswith("@"):
                ref_name = v[1:]
                if ref_name in colors and not colors[ref_name].startswith("@"):
                    colors[k] = colors[ref_name]
                    resolved_all = False

    return {
        "bg": colors.get("window_bg_color", "#151218"),
        "fg": colors.get("window_fg_color", "#e8e0e8"),
        "accent": colors.get("accent_color", "#d9bafa"),
        "error": colors.get("error_color", "#ff5555"),
        "warning": colors.get("warning_color", "#f9e2af"),
        "success": colors.get("success_color", "#a6e3a1"),
        "muted": colors.get("surface_variant", "#4c4c4c")
    }

THEME = load_matugen_theme()

# =============================================================================
# SCHEMA & DATA DEFINITIONS (Python 3.14 Dataclasses)
# =============================================================================

@dataclass
class ConfigItem:
    label: str
    key: str
    scope: str
    type_: str
    default: any
    options: list[str] = field(default_factory=list)
    value: any = None

    def __post_init__(self):
        if self.value is None:
            self.value = self.default

# Extended tabs to demonstrate dynamic horizontal overflow
TABS = [
    "General", "Network", "Display", "System", "Audio", "Storage", 
    "Security", "Bluetooth", "Advanced", "Developer", "Appearance", "Power"
]

SCHEMA = {
    0: [
        ConfigItem("Enable Service", "service_enabled", "DEFAULT", "bool", True),
        ConfigItem("Timeout (ms)", "timeout", "DEFAULT", "int", 100),
        ConfigItem("Log Prefix", "log_prefix", "DEFAULT", "string", "myapp_"),
    ],
    1: [
        ConfigItem("Hostname", "hostname", "DEFAULT", "string", ""),
        ConfigItem("Protocol", "protocol", "network", "cycle", "tcp", ["tcp", "udp", "icmp"]),
    ],
    2: [
        ConfigItem("Border Size", "border_size", "display", "int", 2),
        ConfigItem("Blur Enabled", "blur_enabled", "display", "bool", True),
    ],
    3: [
        ConfigItem("Shadow Color", "color", "decoration", "cycle", "0xee1a1a1a", ["0xee1a1a1a", "0xff000000"]),
        ConfigItem("Restart Daemon", "restart", "action", "action", ""),
    ]
}

# Auto-populate empty schema tabs for testing
for i in range(4, len(TABS)):
    SCHEMA[i] = [ConfigItem(f"Test Item {i}", f"test_{i}", "test", "bool", False)]

# =============================================================================
# NATIVE TEXTUAL WIDGETS
# =============================================================================

class TabBar(Horizontal):
    """Dynamic Tab Bar that handles terminal width and injects « » arrows."""
    
    def compose(self) -> ComposeResult:
        yield Horizontal(id="tab-container")

    def rebuild_tabs(self, current_tab: int, scroll_offset: int, max_width: int) -> None:
        container = self.query_one("#tab-container")
        container.remove_children()
        
        used_width = 0
        
        # Left arrow injection
        if scroll_offset > 0:
            lbl = Label("« ", classes="tab-arrow")
            lbl.on_click = lambda: self.app.switch_tab(max(0, current_tab - 1))
            container.mount(lbl)
            used_width += 2

        for i in range(scroll_offset, len(TABS)):
            tab_name = TABS[i]
            is_last = (i == len(TABS) - 1)
            
            chunk_len = len(tab_name) + 2
            if not is_last:
                chunk_len += 3
                
            if used_width + chunk_len + 3 > max_width:
                # Right arrow injection if we run out of space
                lbl = Label("» ", classes="tab-arrow")
                lbl.on_click = lambda: self.app.switch_tab(min(len(TABS)-1, current_tab + 1))
                container.mount(lbl)
                break
                
            # Create native clickable tab
            classes = "tab active" if i == current_tab else "tab"
            tab_lbl = Label(f" {tab_name} ", classes=classes)
            
            def make_handler(idx=i):
                return lambda: self.app.switch_tab(idx)
            tab_lbl.on_click = make_handler()
            
            container.mount(tab_lbl)
            used_width += len(tab_name) + 2
            
            if not is_last:
                container.mount(Label(" | ", classes="tab-sep"))
                used_width += 3

class ConfigRow(Horizontal, can_focus=True):
    """A native focusable row representing one config item."""
    
    def __init__(self, item: ConfigItem):
        super().__init__(classes="config-row")
        self.item = item

    def compose(self) -> ComposeResult:
        yield Label(">", classes="row-cursor")
        yield Label(self.item.label, classes="row-label")
        yield Label(self.build_display(), id="row-value")

    def build_display(self) -> str:
        val_str = str(self.item.value)
        def_str = str(self.item.default)
        
        dot_color = THEME["error"] if val_str != def_str else THEME["warning"]
        dot = f"[{dot_color}]●[/]"
        
        display_val = escape(val_str)
        if self.item.type_ == "bool":
            display_val = f"[{THEME['success']}]ON[/]" if self.item.value else f"[{THEME['error']}]OFF[/]"
        elif self.item.type_ == "string":
            if val_str == "":
                display_val = f"[italic {THEME['muted']}]Unset[/]"
            else:
                display_val = f"[{THEME['fg']}]{display_val}[/]"
            # Escaping the pencil bracket so Rich doesn't try to parse [✎] as a style
            display_val = f"[{THEME['accent']}]\[✎][/] {display_val}"
        elif self.item.type_ == "action":
            display_val = f"[{THEME['accent']}]▶[/] press Enter"
        else:
            display_val = f"[{THEME['fg']}]{display_val}[/]"

        return f"{dot} : {display_val}"

    def update_display(self) -> None:
        self.query_one("#row-value", Label).update(self.build_display())

    def on_click(self) -> None:
        self.focus()
        if self.item.type_ in ("bool", "action", "string"):
            self.app.action_enter()

class AppFooter(Static):
    """Exact recreation of the Bash Script's 3-line bottom controls."""
    
    def render(self) -> Text:
        acc = THEME['accent']
        warn = THEME['warning']
        err = THEME['error']
        fg = THEME['fg']
        
        # All literal brackets MUST be escaped with a backslash to prevent MissingStyle errors
        txt = Text.from_markup(
            f" [{acc}]\[Tab][/] Category   [{acc}]\[r][/] Reset Item   [{acc}]\[R][/] Reset All   [{acc}]\[←/→ h/l][/] Adjust\n"
            f" [{acc}]\[Enter][/] Action   [{acc}]\[q][/] Quit   [{warn}]●[/][{acc}] Default[/]  [{err}]●[/][{acc}] Modified[/]\n"
        )
        
        status_msg = getattr(self.app, "status_msg", "")
        if status_msg:
            txt.append_text(Text.from_markup(f" [{acc}]Status:[/] [{err}]{escape(status_msg)}[/]"))
        else:
            txt.append_text(Text.from_markup(f" [{acc}]File:[/] [{fg}]~/.config/myapp/settings.conf[/]"))
            
        return txt

class TextInputOverlay(ModalScreen[str]):
    """Clean, centered modal for string entry."""
    
    def __init__(self, prompt: str, default: str):
        super().__init__()
        self.prompt_text = prompt
        self.default_text = default

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label(self.prompt_text, id="modal-title")
            yield Input(value=self.default_text)

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)
        
    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)

# =============================================================================
# MAIN APPLICATION LOGIC
# =============================================================================

class DuskyApp(App):
    CSS = f"""
    Screen {{ background: {THEME['bg']}; }}
    
    #main-box {{
        width: 100%;
        height: 100%;
        border: solid {THEME['muted']};
        border-title-color: {THEME['accent']};
        border-title-style: bold;
        border-title-align: center;
        background: {THEME['bg']};
        padding: 0 1;
    }}
    
    TabBar {{ height: 1; margin-bottom: 1; }}
    .tab {{ color: {THEME['muted']}; }}
    .tab.active {{ color: {THEME['bg']}; background: {THEME['accent']}; text-style: bold; }}
    .tab-sep {{ color: {THEME['muted']}; }}
    .tab-arrow {{ color: {THEME['warning']}; text-style: bold; }}
    
    #content-list {{ height: 1fr; margin-bottom: 1; overflow-y: auto; overflow-x: hidden; scrollbar-size: 0 0; }}
    
    .config-row {{ height: 1; }}
    .config-row:focus > .row-cursor {{ color: {THEME['accent']}; }}
    .config-row:focus > .row-label {{ text-style: bold; color: {THEME['fg']}; }}
    
    .row-cursor {{ width: 2; color: transparent; }}
    .row-label {{ width: 25; color: {THEME['fg']}; }}
    
    #footer {{ height: 3; dock: bottom; border-top: solid {THEME['muted']}; padding-top: 0; }}
    
    /* Modal CSS */
    TextInputOverlay {{ align: center middle; background: rgba(0, 0, 0, 0.7); }}
    #modal-dialog {{ width: 50; height: 7; background: {THEME['bg']}; border: solid {THEME['accent']}; padding: 1 2; }}
    #modal-title {{ color: {THEME['accent']}; margin-bottom: 1; }}
    Input {{ border: none; background: {THEME['bg']}; color: {THEME['fg']}; border-bottom: solid {THEME['accent']}; }}
    Input:focus {{ border: none; border-bottom: solid {THEME['accent']}; }}
    """

    status_msg = reactive("")
    current_tab = 0
    tab_scroll_offset = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="main-box"):
            yield TabBar()
            yield Vertical(id="content-list")
            yield AppFooter(id="footer")

    def on_mount(self) -> None:
        self.query_one("#main-box").border_title = " Generic System Config Editor v6.3 "
        self.switch_tab(0)

    def on_resize(self, event: Resize) -> None:
        """Handle terminal resizes natively to calculate tab overflow."""
        self.rebuild_tab_bar(event.size.width)

    def watch_status_msg(self, value: str) -> None:
        self.query_one("#footer", AppFooter).refresh()

    def notify_status(self, msg: str) -> None:
        self.status_msg = msg
        self.set_timer(3, self.clear_status)

    def clear_status(self) -> None:
        self.status_msg = ""

    def rebuild_tab_bar(self, width: int | None = None) -> None:
        try:
            max_w = (width or self.size.width) - 6
            self.query_one(TabBar).rebuild_tabs(self.current_tab, self.tab_scroll_offset, max_w)
        except Exception:
            pass

    def switch_tab(self, idx: int) -> None:
        self.current_tab = idx
        
        if idx < self.tab_scroll_offset:
            self.tab_scroll_offset = idx
        elif idx > self.tab_scroll_offset + 3: 
            self.tab_scroll_offset = max(0, idx - 3)

        self.rebuild_tab_bar()

        list_container = self.query_one("#content-list")
        list_container.remove_children()
        
        items = SCHEMA.get(idx, [])
        for item in items:
            list_container.mount(ConfigRow(item))
            
        if items:
            self.call_later(lambda: list_container.children[0].focus())

    def on_key(self, event) -> None:
        match event.key:
            case "q" | "Q" | "ctrl+c":
                self.exit()
            case "tab":
                self.switch_tab((self.current_tab + 1) % len(TABS))
            case "shift+tab":
                self.switch_tab((self.current_tab - 1 + len(TABS)) % len(TABS))
            case "j" | "J" | "down":
                self.action_focus_next()
            case "k" | "K" | "up":
                self.action_focus_previous()
            case "ctrl+d" | "page_down":
                self.page_jump(10)
            case "ctrl+u" | "page_up":
                self.page_jump(-10)
            case "g":
                self.focus_extreme(0)
            case "G":
                self.focus_extreme(-1)
            case "l" | "L" | "right":
                self.handle_adjust(1)
            case "h" | "H" | "left" | "backspace":
                self.handle_adjust(-1)
            case "r":
                self.handle_reset()
            case "R":
                self.handle_reset_all()
            case "enter":
                self.action_enter()

    def get_focused_row(self) -> ConfigRow | None:
        focused = self.screen.focused
        return focused if isinstance(focused, ConfigRow) else None

    def page_jump(self, offset: int) -> None:
        rows = list(self.query(ConfigRow))
        if not rows: return
        
        focused = self.get_focused_row()
        if not focused: return
        
        current_idx = rows.index(focused)
        new_idx = max(0, min(len(rows) - 1, current_idx + offset))
        rows[new_idx].focus()

    def focus_extreme(self, idx: int) -> None:
        rows = list(self.query(ConfigRow))
        if rows:
            rows[idx].focus()

    def handle_adjust(self, direction: int) -> None:
        row = self.get_focused_row()
        if not row: return
        item = row.item
        
        if item.type_ == "bool":
            item.value = not item.value
        elif item.type_ == "int":
            item.value += direction
        elif item.type_ == "cycle":
            try: idx = item.options.index(item.value)
            except ValueError: idx = 0
            item.value = item.options[(idx + direction) % len(item.options)]
        else:
            return
            
        row.update_display()
        self.notify_status(f"Updated {item.label}")

    def handle_reset(self) -> None:
        row = self.get_focused_row()
        if row:
            row.item.value = row.item.default
            row.update_display()
            self.notify_status(f"Reset {row.item.label}")

    def handle_reset_all(self) -> None:
        for row in self.query(ConfigRow):
            row.item.value = row.item.default
            row.update_display()
        self.notify_status("Reset all items in current tab")

    def action_enter(self) -> None:
        row = self.get_focused_row()
        if not row: return
        
        if row.item.type_ == "bool":
            self.handle_adjust(1)
        elif row.item.type_ == "string":
            self.prompt_string(row)
        elif row.item.type_ == "action":
            if row.item.key == "restart":
                self.notify_status("Simulating daemon restart...")

    @work
    async def prompt_string(self, row: ConfigRow) -> None:
        new_val = await self.push_screen(TextInputOverlay(f"Enter new {row.item.label}:", str(row.item.value)))
        if new_val is not None:
            row.item.value = new_val
            row.update_display()
            self.notify_status(f"Updated {row.item.label}")

if __name__ == "__main__":
    app = DuskyApp()
    app.run()
