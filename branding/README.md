# Brand sources

`STANICODE_APPROVED_LOGO.png` and `STANICODE_app_icon_512.png` preserve the supplied references. `STANICODE_master.svg` is an editable geometric redraw of the monogram in the supplied cyan/blue/violet direction. All faces, outlines and extruded edges are vector paths with named groups and gradients; there is no embedded raster, expanded initials or registered-mark symbol. The redraw has not received a separate owner design approval.

The master has a transparent background and was rendered against dark and light panels for inspection. `STANICODE_high_contrast.svg` supplies a flat black variant on transparent background. `scripts/render_brand.py` renders the master into the actual app icon at 16/32/48/64/128/256/512/1024, a multi-resolution Windows ICO and NSIS header/sidebar bitmaps. It uses the build-only `requirements-branding.txt`, system Chromium on Linux or system Edge on the Windows build runner. No font or browser installation is required by the end user.

The actual desktop header uses the vector monogram; native window/taskbar and NSIS assets use its rasterizations. The original approved logo remains the marketing reference rather than being overwritten.
