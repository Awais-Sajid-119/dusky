#!/usr/bin/env bash
# Arch Linux (EFI + Btrfs root) | Dusky Minimalist Boot & LUKS Setup
# FORENSICALLY AUDITED (SYSTEMD-BOOT / PLYMOUTH API COMPLIANT)
# PALETTE: Olive Leaf, Black Forest, Cornsilk, Sunlit Clay, Copperwood

set -Eeuo pipefail
export LC_ALL=C

# --- Configuration ---
readonly THEME_NAME="dusky"
readonly THEME_DIR="/usr/share/plymouth/themes/${THEME_NAME}"
readonly MKINITCPIO_CONF="/etc/mkinitcpio.conf.d/10-arch-btrfs-luks.conf"

# --- Helpers ---
fatal() { printf '\033[1;31m[FATAL]\033[0m %s\n' "$1" >&2; exit 1; }
info() { printf '\033[1;32m[INFO]\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m[WARN]\033[0m %s\n' "$1" >&2; }

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || fatal "Required command not found: $1"
}

# --- Pre-flight Checks ---
if (( EUID != 0 )); then
    fatal "Deployment halted: Root privileges are strictly required."
fi

info "Validating base dependencies..."
require_cmd pacman
require_cmd sed
require_cmd grep

# --- Execution ---
info "Ensuring Plymouth is installed..."
if ! pacman -Q plymouth >/dev/null 2>&1; then
    if ! pacman -S --needed --noconfirm plymouth; then
        fatal "The installation of 'plymouth' failed. Ensure it is in your pacstrap payload."
    fi
fi

require_cmd plymouth-set-default-theme

info "Deploying custom minimal theme: $THEME_NAME..."
mkdir -p "$THEME_DIR"

# Generate .plymouth configuration
# ConsoleLogBackgroundColor maps exactly to Black Forest (#283618)
cat << EOF > "${THEME_DIR}/${THEME_NAME}.plymouth"
[Plymouth Theme]
Name=Dusky Minimal
Description=Pure typographic LUKS prompt and splash (Earthy Palette).
ModuleName=script

[script]
ImageDir=${THEME_DIR}
ScriptFile=${THEME_DIR}/${THEME_NAME}.script
ConsoleLogBackgroundColor=0x283618
MonospaceFont=Cantarell 11
Font=Cantarell 11
EOF

# Generate .script file (The core visual logic)
cat << 'EOF' > "${THEME_DIR}/${THEME_NAME}.script"
# ==========================================================
# PALETTE MAPPING (4-Decimal Precision for Zero Color Drift)
# Black Forest (#283618) : 0.1569, 0.2118, 0.0941
# Cornsilk     (#fefae0) : 0.9961, 0.9804, 0.8784
# Sunlit Clay  (#dda15e) : 0.8667, 0.6314, 0.3686
# Copperwood   (#bc6c25) : 0.7373, 0.4235, 0.1451
# Olive Leaf   (#606c38) : 0.3765, 0.4235, 0.2196
# ==========================================================

# --- Background Setup (Black Forest) ---
Window.SetBackgroundTopColor(0.1569, 0.2118, 0.0941);
Window.SetBackgroundBottomColor(0.1569, 0.2118, 0.0941);

# --- Native Asset Generation ---
# Render a massive Full Block to bypass edge anti-aliasing, then sample a pure 1x1 Sunlit Clay pixel
global.pixel_image = Image.Text("█", 0.8667, 0.6314, 0.3686, 1.0, "Cantarell 48").Scale(1, 1);

# --- Logo & Animation Engine (Cornsilk) ---
global.logo_image = Image.Text("dusky", 0.9961, 0.9804, 0.8784, 1.0, "Cantarell 36");
global.logo_sprite = Sprite(global.logo_image);
global.logo_sprite.SetPosition(
    Window.GetWidth() / 2 - global.logo_image.GetWidth() / 2,
    Window.GetHeight() / 2 - global.logo_image.GetHeight() / 2,
    10 # Z-Index
);

global.animation_time = 0.0;
global.password_dialog_active = 0;

fun refresh_callback () {
    if (global.password_dialog_active == 0) {
        global.animation_time += 0.025;
        # Sine wave mapped to opacity: 0.6 to 1.0 for a subtle breath
        opacity = 0.8 + (0.2 * Math.Sin(global.animation_time * 2.0));
        global.logo_sprite.SetOpacity(opacity);
    } else {
        global.logo_sprite.SetOpacity(1.0);
    }
}
Plymouth.SetRefreshFunction(refresh_callback);

# --- Minimal Progress Line (3 pixels tall, Sunlit Clay) ---
global.progress_sprite = Sprite();
global.dialog_y = global.logo_sprite.GetY() + global.logo_image.GetHeight() + 45;
global.progress_sprite.SetPosition(0, global.dialog_y, 10);
global.progress_sprite.SetOpacity(0);

fun progress_callback (duration, progress) {
    if (global.password_dialog_active == 1) {
        global.progress_sprite.SetOpacity(0);
        return;
    }
    
    max_width = Window.GetWidth() * 0.3;
    bar_width = Math.Int(max_width * progress);
    if (bar_width < 1) bar_width = 1;
    
    scaled_bar = global.pixel_image.Scale(bar_width, 3);
    global.progress_sprite.SetImage(scaled_bar);
    global.progress_sprite.SetX(Window.GetWidth() / 2 - bar_width / 2);
    global.progress_sprite.SetOpacity(1);
}
Plymouth.SetBootProgressFunction(progress_callback);

# --- LUKS Password Prompt ---
global.prompt_sprite = Sprite();
global.prompt_sprite.SetPosition(Window.GetWidth() / 2, global.dialog_y, 20);
global.prompt_sprite.SetOpacity(0);

global.bullet_container = Sprite();
global.bullet_container.SetPosition(Window.GetWidth() / 2, global.dialog_y + 30, 20);
global.bullet_container.SetOpacity(0);

fun display_normal_callback () {
    global.password_dialog_active = 0;
    global.prompt_sprite.SetOpacity(0);
    global.bullet_container.SetOpacity(0);
}

fun display_password_callback (prompt_text, bullets) {
    global.password_dialog_active = 1;
    global.progress_sprite.SetOpacity(0);
    
    # Render prompt text (Cornsilk slightly muted via alpha channel for hierarchy)
    prompt_image = Image.Text(prompt_text, 0.9961, 0.9804, 0.8784, 0.8, "Cantarell 12");
    global.prompt_sprite.SetImage(prompt_image);
    global.prompt_sprite.SetX(Window.GetWidth() / 2 - prompt_image.GetWidth() / 2);
    global.prompt_sprite.SetOpacity(1);
    
    bullet_string = "";
    for (index = 0; index < bullets; index++) {
        bullet_string += "● ";
    }
    
    if (bullets > 0) {
        # Render Bullets (Copperwood)
        bullet_image = Image.Text(bullet_string, 0.7373, 0.4235, 0.1451, 1.0, "Cantarell 14");
        global.bullet_container.SetImage(bullet_image);
        global.bullet_container.SetX(Window.GetWidth() / 2 - bullet_image.GetWidth() / 2);
        global.bullet_container.SetY(global.prompt_sprite.GetY() + prompt_image.GetHeight() + 15);
        global.bullet_container.SetOpacity(1);
    } else {
        global.bullet_container.SetOpacity(0);
    }
}
Plymouth.SetDisplayNormalFunction(display_normal_callback);
Plymouth.SetDisplayPasswordFunction(display_password_callback);

# --- Systemd Message Broadcasting (Olive Leaf) ---
global.message_sprite = Sprite();
global.message_sprite.SetPosition(Window.GetWidth() / 2, Window.GetHeight() * 0.85, 5); # Lowest Z-Index

fun display_message_callback (text) {
    my_image = Image.Text(text, 0.3765, 0.4235, 0.2196, 1.0, "Cantarell 10");
    global.message_sprite.SetImage(my_image);
    global.message_sprite.SetX(Window.GetWidth() / 2 - my_image.GetWidth() / 2);
    global.message_sprite.SetOpacity(1);
}

fun hide_message_callback (text) {
    global.message_sprite.SetOpacity(0);
}

Plymouth.SetMessageFunction(display_message_callback);
Plymouth.SetHideMessageFunction(hide_message_callback);
Plymouth.SetUpdateStatusFunction(display_message_callback);

fun quit_callback () { global.logo_sprite.SetOpacity(1); }
Plymouth.SetQuitFunction(quit_callback);
EOF

chmod 0644 "${THEME_DIR}"/*

info "Patching mkinitcpio drop-in config to inject plymouth hook..."
if [[ -f "$MKINITCPIO_CONF" ]]; then
    if ! grep -q "^[^#]*HOOKS=.*plymouth" "$MKINITCPIO_CONF"; then
        sed -i --follow-symlinks -E 's/^([^#]*HOOKS=\([^)]*systemd)([[:space:]]*)/\1 plymouth /' "$MKINITCPIO_CONF"
        info "Injected modern plymouth hook into $MKINITCPIO_CONF"
    else
        info "plymouth hook already present."
    fi
else
    if grep -q "^[^#]*HOOKS=.*systemd" /etc/mkinitcpio.conf && ! grep -q "^[^#]*HOOKS=.*plymouth" /etc/mkinitcpio.conf; then
         sed -i -E 's/^([^#]*HOOKS=\([^)]*systemd)([[:space:]]*)/\1 plymouth /' /etc/mkinitcpio.conf
         info "Injected modern plymouth hook into /etc/mkinitcpio.conf"
    fi
fi

info "Setting default theme to ${THEME_NAME} and rebuilding initramfs..."
plymouth-set-default-theme -R "$THEME_NAME"

info "Dusky Plymouth deployment (Earthy Palette) and initramfs generation successful."
