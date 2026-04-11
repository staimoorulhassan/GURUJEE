"""GURUJEE TUI colour constants and global Textual CSS."""
from __future__ import annotations

# ------------------------------------------------------------------ #
# Colour palette                                                        #
# ------------------------------------------------------------------ #

BG: str = "#0a0a0a"
"""Near-black background used on all screens."""

PRIMARY_AMBER: str = "#f0a500"
"""Primary accent — focused borders, buttons, header text."""

ACCENT_ORANGE: str = "#ff6b00"
"""Secondary accent — active indicators, stream cursor."""

TEXT_PRIMARY: str = "#e0e0e0"
"""Default body text."""

TEXT_DIM: str = "#666666"
"""Disabled labels, timestamps, stub captions."""

# ------------------------------------------------------------------ #
# Global Textual stylesheet                                             #
# ------------------------------------------------------------------ #

GURUJEE_CSS: str = f"""
Screen {{
    background: {BG};
    color: {TEXT_PRIMARY};
}}

/* Focused widgets */
Input:focus {{
    border: tall {PRIMARY_AMBER};
}}

Button:focus {{
    background: {PRIMARY_AMBER};
    color: {BG};
}}

Button:hover {{
    background: {ACCENT_ORANGE};
    color: {BG};
}}

/* Active state indicator (e.g. agent status RUNNING) */
.active-indicator {{
    color: {ACCENT_ORANGE};
}}

/* Dim / stub labels */
.dim {{
    color: {TEXT_DIM};
}}

/* Chat bubbles */
#chat-log {{
    background: {BG};
    border: none;
    padding: 0 1;
}}

/* Agent status table */
#agent-table {{
    background: {BG};
    border: tall {PRIMARY_AMBER};
}}

/* Settings sections */
.settings-section-label {{
    color: {PRIMARY_AMBER};
    text-style: bold;
    padding: 1 0 0 1;
}}

/* Error / warning text */
.error-text {{
    color: #ff4444;
}}

.warning-text {{
    color: {ACCENT_ORANGE};
}}
"""
