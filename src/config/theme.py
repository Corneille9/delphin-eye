from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui


@dataclass(frozen=True)
class Theme:
    primary: str = '#1f6feb'
    secondary: str = '#4b5563'
    border: str = '#d0d7de'
    background: str = '#f5f7fa'
    surface: str = '#ffffff'
    text: str = '#1f2328'
    muted: str = '#6b7280'
    validation: str = '#1f883d'
    warning: str = '#bf8700'
    danger: str = '#cf222e'
    info: str = '#0969da'
    selection: str = '#0b7285'

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
        )


THEME = Theme()


GLOBAL_CSS = """
:root { __VARS__ }
body { background: var(--color-background); color: var(--color-text); }
.app-surface { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 10px; }
.app-title { font-size: 1.15rem; font-weight: 600; color: var(--color-text); }
.app-muted { color: var(--color-muted); font-size: 0.85rem; }
.app-badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.app-badge-pending { background: #fff8c5; color: #7d4e00; }
.app-badge-validated { background: #dafbe1; color: var(--color-validation); }
.app-badge-rejected { background: #ffebe9; color: var(--color-danger); }
.app-badge-manual { background: #ddf4ff; color: var(--color-info); }
.app-queue-item { cursor: pointer; padding: 6px 10px; border-radius: 6px; display: flex; align-items: center; gap: 8px; font-size: 0.85rem; }
.app-queue-item:hover { background: #eef2f6; }
.app-queue-item.active { background: #ddeaff; color: var(--color-primary); font-weight: 600; }
.q-btn.app-primary { background: var(--color-primary) !important; color: #fff !important; }
.q-btn.app-outline { border: 1px solid var(--color-border) !important; color: var(--color-text) !important; }

@media (max-width: 1100px) {
    .app-hide-md { display: none !important; }
}
"""


def apply_theme(theme: Theme = THEME) -> None:
    css = GLOBAL_CSS.replace('__VARS__', theme.as_css_vars())
    ui.add_head_html(f'<style>{css}</style>')
