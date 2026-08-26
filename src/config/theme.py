from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui


@dataclass(frozen=True)
class Theme:
    primary: str = '#2563EB'
    secondary: str = '#475569'
    border: str = '#E2E8F0'
    background: str = '#F1F5F9'
    surface: str = '#FFFFFF'
    text: str = '#0F172A'
    muted: str = '#64748B'
    validation: str = '#16A34A'
    warning: str = '#D97706'
    danger: str = '#DC2626'
    info: str = '#0EA5E9'
    selection: str = '#2563EB'

    def as_css_vars(self) -> str:
        return (
            f'--color-primary: {self.primary};'
            f'--color-secondary: {self.secondary};'
            f'--color-border: {self.border};'
            f'--color-background: {self.background};'
            f'--color-surface: {self.surface};'
            f'--color-text: {self.text};'
            f'--color-muted: {self.muted};'
            f'--color-validation: {self.validation};'
            f'--color-warning: {self.warning};'
            f'--color-danger: {self.danger};'
            f'--color-info: {self.info};'
            f'--color-selection: {self.selection};'
            # Override Quasar's built-in color variables so .props('color=primary/positive/negative') works
            f'--q-primary: {self.primary};'
            f'--q-secondary: {self.secondary};'
            f'--q-positive: {self.validation};'
            f'--q-negative: {self.danger};'
            f'--q-info: {self.info};'
            f'--q-warning: {self.warning};'
            f'--q-dark: {self.text};'
        )


THEME = Theme()


GLOBAL_CSS = """
:root { __VARS__ }

*, *::before, *::after { box-sizing: border-box; }

body {
    background: var(--color-background);
    color: var(--color-text);
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
}

.app-surface {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.04);
}

.app-brand {
    font-size: 1rem;
    font-weight: 700;
    color: var(--color-primary);
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
.app-badge-pending  { background: #F1F5F9; color: #475569; }
.app-badge-empty    { background: #FEF3C7; color: #92400E; }
.app-badge-detected { background: #DCFCE7; color: #166534; }
.app-badge-manual   { background: #DBEAFE; color: #1E40AF; }
.app-badge-failed   { background: #FEE2E2; color: #991B1B; }

.status-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
}
/* Every status gets its own colour: an analysed image with no fin has to be
   distinguishable from one that was never analysed. */
.status-dot-pending  { background: #CBD5E1; }
.status-dot-empty    { background: #F59E0B; }
.status-dot-detected { background: #22C55E; }
.status-dot-modified { background: #3B82F6; }
.status-dot-failed   { background: #EF4444; }

.app-queue-count {
    flex-shrink: 0;
    font-size: 0.66rem;
    font-weight: 700;
    color: #166534;
    background: #DCFCE7;
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
.app-queue-item:hover  { background: #F1F5F9; }
.app-queue-item.active {
    background: #EFF6FF;
    color: var(--color-primary);
    font-weight: 600;
}


.q-btn:not(.q-btn--round) { border-radius: 8px !important; }

.q-btn.app-ghost {
    color: var(--color-muted) !important;
}
.q-btn.app-ghost:hover {
    background: #F1F5F9 !important;
    color: var(--color-text) !important;
}

.q-btn.app-outline {
    border: 1.5px solid var(--color-border) !important;
    color: var(--color-text) !important;
    background: transparent !important;
}
.q-btn.app-outline:hover { background: #F8FAFC !important; }

.toolbar-sep {
    width: 1px;
    height: 22px;
    background: var(--color-border);
    flex-shrink: 0;
    align-self: center;
}

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: var(--color-muted); }

@media (max-width: 1100px) {
    .app-hide-md { display: none !important; }
}
"""


CANVAS_IMAGE_CSS = """
/* ui.interactive_image hardcodes width/height: 100% on its <img>, which gives
   the wrapper no intrinsic size to resolve its aspect-ratio box against. Chrome
   falls back to the image's natural size, WebKit resolves it to zero and the
   photo never shows up. Letting the image size itself works in both. */
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
"""


def apply_theme(theme: Theme = THEME) -> None:
    css = GLOBAL_CSS.replace('__VARS__', theme.as_css_vars())
    ui.add_head_html(f'<style>{css}{CANVAS_IMAGE_CSS}</style>')
