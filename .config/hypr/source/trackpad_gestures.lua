-- -------------------------------------------------------------------------------------------------
-- TRACKPAD GESTURES
-- -------------------------------------------------------------------------------------------------
-- NOTE: Gestures fire once per recognized swipe, not continuously.
--       Volume/brightness step is 5% per swipe — do multiple quick swipes for larger changes.
--       Tap gestures are not supported by Hyprland natively (as of 0.55).
--       For your 3-finger tap QuickPanel: use ALT+V (already bound in keybinds).

-- ── 3-Finger Gestures ────────────────────────────────────────────────────────────────────────────

-- Left/Right: Native 1:1 smooth workspace switching (no plugin needed)
hl.gesture({
    fingers   = 3,
    direction = "horizontal",
    action    = "workspace",
})

hl.gesture({
    fingers   = 3,
    direction = "up",
    action    = function()
        hl.exec_cmd("")
    end,
})

-- Down: Toggle media pause/play
hl.gesture({
    fingers   = 3,
    direction = "down",
    action    = function()
        hl.exec_cmd(dusky_scripts .. "mako_osd/osd_router/osd_router.sh --play-pause")
    end,
})

-- ── 4-Finger Gestures ────────────────────────────────────────────────────────────────────────────

-- Left/Right: Volume control (5% per swipe, capped at 150% to prevent distortion)
hl.gesture({
    fingers   = 4,
    direction = "left",
    action    = function()
        hl.exec_cmd(dusky_scripts .. "mako_osd/osd_router/osd_router.sh --vol-down 10")
    end,
})

hl.gesture({
    fingers   = 4,
    direction = "right",
    action    = function()
        hl.exec_cmd(dusky_scripts .. "mako_osd/osd_router/osd_router.sh --vol-up 10")
    end,
})

hl.gesture({
    fingers   = 4,
    direction = "up",
    action    = function()
        hl.exec_cmd(dusky_scripts .. "mako_osd/osd_router/osd_router.sh --bright-up 10")
    end,
})

hl.gesture({
    fingers   = 4,
    direction = "down",
    action    = function()
        hl.exec_cmd(dusky_scripts .. "mako_osd/osd_router/osd_router.sh --bright-down 10")
    end,
})
