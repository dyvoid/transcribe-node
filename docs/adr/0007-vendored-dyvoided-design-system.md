# ADR 0007: Vendor the dyvoided design system for the operator UI

- **Status:** Accepted
- **Date:** 2026-09-23

## Context

The operator UI (`static/index.html`) was styled with hand-picked hex colors, px sizes and
system fonts inline. The owner's other apps share one visual identity through the dyvoided design
system ([dyvoid/dyvoided-design-system](https://github.com/dyvoid/dyvoided-design-system)): a
token layer (colors, type, spacing, effects, motion) plus framework-agnostic `ds-*` component
classes, dark-first with a light theme as a peer. TranscribeNode should read as part of that family.

The UI is a single static HTML file served by FastAPI with no build step, and the project has no
Node toolchain. The design system ships plain CSS that needs no compilation.

## Decision

**Vendor a snapshot of the design system's CSS into `static/ds/`** (`styles.css`, `components.css`,
`tokens/*.css`), recorded with its source commit in `static/ds/VERSION`. The UI links
`/static/ds/styles.css` and uses `ds-*` classes directly. App-specific layout lives in the page's
own `<style>` block and references tokens only: no hardcoded hues or px font sizes, per the
design system's own rules.

- Not a git submodule or package: those would add a toolchain or a clone step to a project whose
  launcher is only `uv sync`. Updating is a manual copy-and-bump of `VERSION`.
- Vendored files are not edited in place. Gaps are patched in the page's `<style>` block (for
  example, a hairline on the neutral badge that is hard to see in light theme) and should be fixed
  upstream.
- Theme follows the OS `prefers-color-scheme` by setting `data-theme` on `<html>`.
- `<select>` elements stay native, wrapped in the `ds-select-field` chrome, rather than using the
  design system's scripted combobox. Native keeps platform keyboard and screen-reader behaviour
  with no extra script.
- Fonts (Familjen Grotesk, Hanken Grotesk, JetBrains Mono) load from Google Fonts using the design
  system's canonical link. Without network access the font stacks fall back to system fonts and the
  UI still works.

## Consequences

- The UI makes one external request: the Google Fonts stylesheet and font files. No audio,
  transcript or request data is involved, but the browser does contact Google. If that becomes
  unacceptable, self-host the woff2 files under `static/` and drop the link.
- Design-system updates don't arrive automatically; the snapshot can drift from upstream until
  someone re-copies it.
- The UI zones, panel lifecycle (ADR 0005) and API usage are unchanged; this is presentation only.
