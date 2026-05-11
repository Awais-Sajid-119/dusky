-- =============================================================================
-- HYPRLAND MAIN CONFIGURATION
-- User: [dusky]
-- System: UWSM Managed
-- =============================================================================

-- Hardcode the root path for local testing using the HOME environment variable
local hypr_root = os.getenv("HOME") .. "/.config/hypr"

-- ----------------------------------------------------- 
-- SOURCE FILES
-- -----------------------------------------------------

-- 1. MONITORS
dofile(hypr_root .. "/source/monitors.lua")

-- 2. PROGRAMS & ENVIRONMENT
dofile(hypr_root .. "/source/permissions.lua")

-- 3. PLUGINS (Commented out currently)
-- dofile(hypr_root .. "/source/plugins.lua")

-- 4. INPUT DEVICES
dofile(hypr_root .. "/source/input.lua")

-- 5. APPEARANCE
dofile(hypr_root .. "/source/appearance.lua")

-- 6. WINDOW RULES & WORKSPACES
dofile(hypr_root .. "/source/window_rules.lua")

-- 7. KEYBINDINGS
dofile(hypr_root .. "/source/keybinds.lua")

-- 8. AUTOSTART
dofile(hypr_root .. "/source/autostart.lua")

-- 9. Environment Variables
dofile(hypr_root .. "/source/environment_variables.lua")

-- 10. Workspace Rules
dofile(hypr_root .. "/source/workspace_rules.lua")

-- (Optional) If you ever want to re-enable local overrides or default apps, 
-- just uncomment these lines and ensure the files exist:
-- dofile(hypr_root .. "/edit_here/source/default_apps.lua")
-- dofile(hypr_root .. "/edit_here/hyprland.lua")
