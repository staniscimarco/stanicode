"""Rasterize the editable brand master into actual Windows/desktop assets."""

from io import BytesIO
from pathlib import Path
import shutil
from PIL import Image
from playwright.sync_api import sync_playwright


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / 'branding/STANICODE_master.svg'
    svg = source.read_text(encoding='utf-8')
    icons = root / 'apps/desktop/src-tauri/icons'
    icons.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        executable = shutil.which('chromium') or shutil.which('google-chrome')
        browser = playwright.chromium.launch(**({'executable_path': executable, 'args': ['--no-sandbox']} if executable else {'channel': 'msedge'}))
        try:
            page = browser.new_page(viewport={'width': 1024, 'height': 1024})
            page.set_content('<style>html,body{margin:0;background:transparent}svg{width:1024px;height:1024px}</style>' + svg)
            image = Image.open(BytesIO(page.screenshot(omit_background=True))).convert('RGBA')
            for size in (16, 32, 48, 64, 128, 256, 512, 1024):
                image.resize((size, size), Image.Resampling.LANCZOS).save(icons / f'{size}.png')
            image.save(icons / 'icon.png')
            image.save(icons / 'icon.ico', sizes=[(s, s) for s in (16, 32, 48, 64, 128, 256)])
            # Installer imagery uses an opaque bitmap as required by NSIS.
            for name, width, height, lockup in (
                ('installer-sidebar.bmp', 164, 314, '<div style="padding:60px 8px 0;text-align:center"><div style="width:145px;height:145px">' + svg + '</div><strong style="font:700 15px Segoe UI,sans-serif;letter-spacing:2px">STANICODE</strong></div>'),
                ('installer-header.bmp', 150, 57, '<div style="display:flex;align-items:center;height:57px"><div style="width:46px;height:46px">' + svg + '</div><strong style="font:700 11px Segoe UI,sans-serif;letter-spacing:1px">STANICODE</strong></div>'),
            ):
                page.set_viewport_size({'width': width, 'height': height})
                page.set_content('<style>html,body{margin:0;background:#050a18;color:#e9edf6}svg{width:100%;height:100%}</style>' + lockup)
                Image.open(BytesIO(page.screenshot())).convert('RGB').save(icons / name)
        finally:
            browser.close()
    shutil.copy2(source, root / 'apps/desktop/public/brand.svg')
    contrast = svg.replace('<defs>', '<style>#extruded-edges,#luminous-outline{display:none}#upper-letterform,#central-letterform,#lower-letterform{fill:#000;stroke:#000}#central-letterform path{fill:#000}</style><defs>')
    (root / 'branding/STANICODE_high_contrast.svg').write_text(contrast, encoding='utf-8')
    print('Rendered SVG master into 8 PNG sizes, multi-resolution ICO, NSIS artwork and high-contrast vector.')


if __name__ == '__main__':
    main()
