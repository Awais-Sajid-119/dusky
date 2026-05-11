-- -------------------------------------------------------------------------------------------------
-- 1. KEYBOARD, MOUSE, & TOUCHPAD
-- -------------------------------------------------------------------------------------------------
hl.config({
    input = {
        -- --- Keyboard ---
        kb_layout = "us",
        kb_options = "",
        resolve_binds_by_sym = false,
        numlock_by_default = true,
        repeat_rate = 35,
        repeat_delay = 250,

        -- --- Mouse & Pointer ---
        follow_mouse = 1,
        sensitivity = 0.0,
        accel_profile = "adaptive",
        force_no_accel = false,
        left_handed = false,
        mouse_refocus = true,

        -- --- Scrolling ---
        natural_scroll = false,
        scroll_method = "2fg",
        scroll_button = 0,
        scroll_button_lock = false,

        -- --- Touchpad (Subcategory of Input) ---
        touchpad = {
            natural_scroll = true,
            disable_while_typing = true,
            tap_to_click = true,
            clickfinger_behavior = false,
            
            -- CRITICAL FIX: drag_lock is now an integer in 0.55+ (0 = disabled, 1 = timeout, 2 = sticky)
            drag_lock = 0
        }
    },

    -- ---------------------------------------------------------------------------------------------
    -- 2. CURSOR BEHAVIOR & RENDERING
    -- ---------------------------------------------------------------------------------------------
    cursor = {
        sync_gsettings_theme = true,
        no_hardware_cursors = 2,
        use_cpu_buffer = 2,
        hide_on_key_press = false,
        inactive_timeout = 0,
        warp_on_change_workspace = 0,
        no_break_fs_vrr = 2,
        zoom_factor = 1.0
    },

    -- ---------------------------------------------------------------------------------------------
    -- 3. GESTURE PHYSICS (Tuning)
    -- ---------------------------------------------------------------------------------------------
    gestures = {
        workspace_swipe_distance = 300,
        workspace_swipe_cancel_ratio = 0.5,
        workspace_swipe_invert = true,
        workspace_swipe_create_new = true,
        workspace_swipe_forever = false
    },

    -- ---------------------------------------------------------------------------------------------
    -- 4. NEW GESTURE BINDINGS (0.55+ Overhaul)
    -- ---------------------------------------------------------------------------------------------
    gesture = {
        -- --- 3-Finger Gestures (Navigation) ---
        
        -- Replicates native 1:1 smooth swiping between workspaces (Highly Intuitive)
        "3, horizontal, workspace",
        
        -- Swipe up for Overview / Mission Control (hyprexpo)
        "3, up, hyprexpo:expo, toggle",
        
        -- Swipe down to drop into a Special Workspace (Scratchpad/Terminal)
        "3, down, togglespecialworkspace",

        -- --- 4-Finger Gestures (Media & Brightness) ---
        
        -- Horizontal for Brightness
        "4, left, exec, brightnessctl -e4 -n2 set 10%-",
        "4, right, exec, brightnessctl -e4 -n2 set 10%+",

        -- Vertical for Volume
        "4, up, exec, wpctl set-volume -l 1.5 @DEFAULT_AUDIO_SINK@ 10%+",
        "4, down, exec, wpctl set-volume @DEFAULT_AUDIO_SINK@ 10%-"
    }
})
