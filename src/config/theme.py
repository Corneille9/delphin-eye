from __future__ import annotations

from dataclasses import dataclass, fields

from nicegui import ui


@dataclass(frozen=True)
class Theme:
    """Vivid palette: an electric blue lead, backed by saturated status colours.

    Every colour the UI paints comes from here: the CSS below only ever reads
    ``var(--color-*)``, and Quasar's own palette is aligned with it in
    ``apply_theme`` so ``color=primary``, ``type='positive'`` and friends land on
    the same values. The ``*_soft`` tints are backgrounds and the ``*_ink`` tones
    the text that sits on them, so the saturated hues stay readable.
    """

    primary: str = '#0B69FF'
    primary_dark: str = '#0047CC'
    primary_soft: str = '#E1ECFF'
    secondary: str = '#00A6FB'
    accent: str = '#FF8A00'
    accent_soft: str = '#FFEFD9'

    surface: str = '#FFFFFF'
    surface_muted: str = '#F1F5FA'
    background: str = '#F4F7FC'
    border: str = '#DCE4EF'
    text: str = '#101B2D'
    muted: str = '#5E7086'
    canvas: str = '#0B1622'

    validation: str = '#00BF63'
    validation_soft: str = '#DAF7E8'
    validation_ink: str = '#037A44'
    warning: str = '#FF8A00'
    warning_soft: str = '#FFEFD9'
    warning_ink: str = '#9A5200'
    danger: str = '#FF3B30'
    danger_soft: str = '#FFE4E1'
    danger_ink: str = '#B31E15'
    info: str = '#00A6FB'

    def as_css_vars(self) -> str:
        return ''.join(
            f'--color-{field.name.replace("_", "-")}: {getattr(self, field.name)};'
            for field in fields(self)
        )


THEME = Theme()


#: Colours the canvas overlay paints, kept next to the palette they belong to.
CANVAS_AUTO_COLOR = THEME.primary
CANVAS_MANUAL_COLOR = THEME.validation
CANVAS_SELECTED_COLOR = THEME.accent


GLOBAL_CSS = """
:root { __VARS__ }

*, *::before, *::after { box-sizing: border-box; }

html, body, #app {
    height: 100%;
    margin: 0;
    /* The shell fills the window and each pane scrolls on its own; letting the
       document scroll would push the bottom toolbar out of view. */
    overflow: hidden;
}

body {
    background: var(--color-surface);
    color: var(--color-text);
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
}

/* NiceGUI wraps every page in q-layout > q-page > .nicegui-content and gives
   that last one a 1rem padding and gap. A desktop shell has to sit flush
   against the window edges instead. */
.nicegui-layout, .q-page-container, .q-page, .nicegui-content {
    height: 100%;
    min-height: 0 !important;
}
.nicegui-content {
    padding: 0;
    gap: 0;
    align-items: stretch;
}
/* Same story inside scroll areas: the panes bring their own padding, and
   flex-start would stop the queue rows from filling the width. */
.nicegui-scroll-area .q-scrollarea__content {
    padding: 0;
    gap: 0;
    align-items: stretch;
}

/* ---------------------------------------------------------------- shell --- */

.app-shell {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--color-surface);
}
.app-body {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: row;
}
.app-pane {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--color-surface);
}
.app-pane-top    { flex-shrink: 0; border-bottom: 1px solid var(--color-border); }
.app-pane-left   { width: 260px; flex-shrink: 0; border-right: 1px solid var(--color-border); }
.app-pane-right  { width: 288px; flex-shrink: 0; border-left: 1px solid var(--color-border); }
.app-pane-main   { flex: 1; min-width: 0; }

.app-pane-header {
    flex-shrink: 0;
    padding: 12px 14px 10px;
    border-bottom: 1px solid var(--color-border);
}

/* --------------------------------------------------------- typography ----- */

.app-brand {
    font-size: 1rem;
    font-weight: 700;
    color: var(--color-text);
    letter-spacing: -0.02em;
}
.app-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--color-text);
    letter-spacing: -0.01em;
}
.app-muted {
    color: var(--color-muted);
    font-size: 0.8rem;
}
.app-caption {
    color: var(--color-muted);
    font-size: 0.72rem;
    line-height: 1.3;
}

/* -------------------------------------------------------------- badges ---- */

.app-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 2px 9px;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.app-badge-pending  { background: var(--color-surface-muted);   color: var(--color-muted); }
.app-badge-empty    { background: var(--color-warning-soft);    color: var(--color-warning-ink); }
.app-badge-detected { background: var(--color-validation-soft); color: var(--color-validation-ink); }
.app-badge-manual   { background: var(--color-primary-soft);    color: var(--color-primary-dark); }
.app-badge-failed   { background: var(--color-danger-soft);     color: var(--color-danger-ink); }

.status-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
}
/* Every status gets its own colour: an analysed image with no fin has to be
   distinguishable from one that was never analysed. */
.status-dot-pending  { background: #B7C7D3; }
.status-dot-empty    { background: var(--color-warning); }
.status-dot-detected { background: var(--color-validation); }
.status-dot-modified { background: var(--color-primary); }
.status-dot-failed   { background: var(--color-danger); }

/* --------------------------------------------------------------- queue ---- */

.app-queue-count {
    flex-shrink: 0;
    font-size: 0.66rem;
    font-weight: 700;
    color: var(--color-validation-ink);
    background: var(--color-validation-soft);
    border-radius: 999px;
    padding: 1px 6px;
}

.app-queue-item {
    cursor: pointer;
    padding: 6px 10px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.79rem;
    color: var(--color-text);
    transition: background 0.1s;
    user-select: none;
}
.app-queue-item:hover  { background: var(--color-surface-muted); }
.app-queue-item.active {
    background: var(--color-primary-soft);
    color: var(--color-primary-dark);
    font-weight: 600;
}

/* ------------------------------------------------------------- buttons ---- */
/* Variants below drive their own colours, so their buttons are built with
   `color=None`: a Quasar `color=` would add a `text-*`/`bg-*` class that wins
   the cascade (Quasar's utilities are `!important` inside a CSS layer). */

.q-btn:not(.q-btn--round) { border-radius: 8px !important; }
.q-btn { font-weight: 600; }

.q-btn.app-ghost { color: var(--color-muted); }
.q-btn.app-ghost:hover {
    background: var(--color-surface-muted);
    color: var(--color-text);
}

.q-btn.app-ghost-danger { color: var(--color-danger); }
.q-btn.app-ghost-danger:hover { background: var(--color-danger-soft); }

.q-btn.app-outline {
    border: 1px solid var(--color-border);
    color: var(--color-text);
    background: var(--color-surface);
}
.q-btn.app-outline:hover {
    background: var(--color-surface-muted);
    border-color: var(--color-primary);
    color: var(--color-primary-dark);
}

.q-btn.app-toggled {
    background: var(--color-primary-soft);
    border-color: var(--color-primary);
    color: var(--color-primary-dark);
}

.toolbar-sep {
    width: 1px;
    height: 22px;
    background: var(--color-border);
    flex-shrink: 0;
    align-self: center;
}

/* ------------------------------------------------------------- canvas ----- */

.app-canvas {
    flex: 1;
    min-height: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
    background:
        radial-gradient(circle at 50% 40%, rgba(70, 143, 175, 0.16), transparent 62%),
        var(--color-canvas);
}

/* ui.interactive_image hardcodes width/height: 100% on its <img>, which gives
   the wrapper no intrinsic size to resolve its aspect-ratio box against. Chrome
   falls back to the image's natural size, WebKit resolves it to zero and the
   photo never shows up. Letting the image size itself works in both - and makes
   the wrapper shrink-wrap the photo, so the SVG overlay lines up exactly. */
.app-canvas-image {
    max-width: 100%;
    max-height: 100%;
    aspect-ratio: auto !important;
}
.app-canvas-image > img {
    width: auto !important;
    height: auto !important;
    max-width: 100%;
    max-height: 100%;
    display: block;
}

.app-canvas-caption {
    background: rgba(6, 20, 30, 0.62);
    color: rgba(255, 255, 255, 0.92);
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 0.79rem;
    font-weight: 500;
    pointer-events: none;
    max-width: 55%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.app-canvas-hint {
    position: absolute;
    color: rgba(255, 255, 255, 0.3);
    font-size: 0.9rem;
    pointer-events: none;
}

/* ---------------------------------------------------------- scrollbars ---- */

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #C2D0DB; border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: var(--color-muted); }

@media (max-width: 1100px) {
    .app-hide-md { display: none !important; }
}
"""


def apply_theme(theme: Theme = THEME) -> None:
    """Install the palette for the current page.

    ``ui.colors`` is what actually reaches Quasar's ``--q-*`` variables, so
    ``color=primary``, ``ui.notify(type=...)`` and the progress bar pick up the
    palette instead of NiceGUI's defaults.
    """
    ui.colors(
        primary=theme.primary,
        secondary=theme.secondary,
        accent=theme.accent,
        dark=theme.text,
        positive=theme.validation,
        negative=theme.danger,
        info=theme.info,
        warning=theme.warning,
    )
    ui.add_head_html(f'<style>{GLOBAL_CSS.replace("__VARS__", theme.as_css_vars())}</style>')
