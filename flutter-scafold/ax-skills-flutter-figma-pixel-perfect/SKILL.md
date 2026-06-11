---
name: ax-skills-flutter-figma-pixel-perfect
description: "Pixel-perfect verification for the Flutter (BLoC + Cubit) app — turns a Figma URL/node into an exact widget implementation and proves it matches by rendering, screenshotting, and pixel-diffing against the Figma export until parity is reached. Extracts the real spec from the Figma MCP (Dev Mode) instead of eyeballing, lands every value as a design-system token (never a raw literal), and verifies fidelity at runtime via the Dart & Flutter MCP server. Use when a Figma link/node must be built exactly, when the user says 'pixel perfect', 'match the Figma', 'exact design', 'same as the mockup', or when a built screen doesn't match the design. Pairs with ax-skills-flutter-ui (owns the design system) and ax-skills-flutter-verify (runtime)."
metadata:
  version: "1.0"
---

# Figma Pixel-Perfect Verification (Flutter, BLoC + Cubit)

Turn a Figma design into Flutter widgets that match it **exactly** — and verify that they do, rather than hoping. The default failure mode is to glance at a screenshot, recognize the rough shape, and emit plausible values: `EdgeInsets.all(16)` when it's really 14, `Color(0xFF3B82F6)` when it's really `0xFF2563EB`, `FontWeight.w600` when it's `w500`, a guessed `height`, a flattened `BoxShadow`, a skipped pressed state, an omitted prototype animation. Each miss is small; together they read unmistakably as "not the design." This skill replaces guessing with **extraction**, and replaces hope with **measurement**.

This is the verification layer *on top of* `ax-skills-flutter-ui`. The UI skill owns *how* the design system is built (token tiers, Atomic-Design components, page composition, Code Connect); this skill owns *proving a given frame matches its Figma source pixel-for-pixel*. Use them together: extract → build with DS tokens/components → render → diff → iterate.

## The prime directive: Figma is ground truth, your eyes are not

Two sources of truth, two different jobs:

- **Structured node data (from the Figma MCP) is the source of truth for every value you build with.** Colors, spacing, radii, type, effects, layout, states — read them from the data, never estimate them from how the image looks. A color picked off a rendered screenshot is already wrong (antialiasing, opacity flattening, compression).
- **The Figma image export is the source of truth for the final check.** You render your widget, screenshot it, and diff it against that export. The diff is what tells you the build is actually done.

If a value you need isn't in the data you've pulled, the move is to **pull more** — go deeper into the node tree, fetch the variant, resolve the variable — not to invent a number. And in this suite the extracted value does not go into the widget as a literal: **it lands as a design-system token** (`context.colors/spacing/text/radii/elevation/motion`). A raw hex or px in feature code is both a fidelity smell and a `ds` review failure — see `ax-skills-flutter-ui`.

## Workflow

1. Resolve the target node.
2. Extract the complete spec from Figma.
3. Translate it into Flutter with zero assumptions — through DS tokens and components.
4. Verify: render → screenshot → diff against the Figma export.
5. Iterate on the diff until it matches.

### Step 1 — Resolve the target

Get the `fileKey` and node id from the URL. A Figma link looks like `figma.com/design/<fileKey>/<name>?node-id=<nodeId>` (node ids in URLs use a dash, e.g. `12-345`, which is node `12:345`). If the user gave a node id without a URL, you also need the file key. If you can't tell which node, fetch the structure (next step) and confirm with the user before building.

### Step 2 — Extract the complete spec

The Figma MCP tools are deferred — load them first with `tool_search` (e.g. search "figma design context"), then call them. Before any `use_figma` call load the **`figma-use`** skill; before mapping components load **`figma-code-connect`** (same as `ax-skills-flutter-ui` → [helpers/figma-to-code.md](../ax-skills-flutter-ui/helpers/figma-to-code.md)). The tools that matter here:

- **`get_metadata`** — the node's structure/tree. Start here to find child node ids and the frame's exact dimensions.
- **`get_design_context`** — the detailed spec for a node: layout, sizing, fills, strokes, effects, typography. Your main source.
- **`get_variable_defs`** — the design tokens/variables in play. Resolve bound values to **token names** so you use `AppColors`/`AppSpacing`/… , not magic numbers.
- **`get_code_connect_map`** — whether nodes already map to real DS widgets. If a node is Code-Connected, **reuse that `App<Name>` component** instead of rebuilding it.
- **`get_screenshot`** — export the node as an image. **Save it** as `<frame>.figma.png`; it's the reference for Step 4. Export desktop and mobile frames separately if both exist.

Walk the tree depth-first and capture every property using [references/fidelity-checklist.md](references/fidelity-checklist.md) — the exhaustive, Flutter-specific list of what to pull and what each property becomes (auto-layout → `Row`/`Column`/`Flex`, padding → `EdgeInsets`, fills → `Color`/`gradient`, effects → `BoxShadow`, type → `TextStyle`, variants/states, prototype → animations) **and which DS token each value maps to**. Read it now. Export icons/illustrations as **SVG** assets and raster images at the right pixel ratio (see checklist §13) rather than approximating them.

### Step 3 — Translate with zero assumptions

Build from the extracted values, following the checklist mappings, and obey the UI skill's rules while you do it:

- **Every value lands as a token, not a literal.** If a fill/spacing/radius/type value is bound to a Figma variable, use the matching semantic token. If a needed value has *no* token, add the token (and flag the design gap in `docs/plan.md`) rather than hardcoding — never paste raw hex/px into a widget.
- **Reuse DS components.** If the data (or Code Connect) says a node is an existing `App<Name>`, use it — don't hand-roll a button that's already a Code-Connected DS atom. Build genuinely-missing pieces as DS components first (atoms→organisms), not inline in the page.
- **Build all interactive states** the component set defines — default, hover, focus, pressed, disabled, loading, error — styled from each variant's own data (web/desktop need hover+focus; mobile needs ≥48dp targets). This is also a `ds` review requirement.
- **Include the animations** — match the prototype's transition type, easing curve, and duration exactly via the `AppMotion` tokens.
- Assemble the screen as a **page = DS template + organisms**, bound to its bloc/cubit, with the shared state-view for async states (see `ax-skills-flutter-ui` → pages-and-composition).

### Step 4 — Verify: render → screenshot → diff

This is the core of the skill — what makes "pixel-perfect" a fact rather than a claim. It runs alongside `ax-skills-flutter-verify` (which confirms the screen *behaves*); this step confirms it *looks* identical.

1. **Render at the exact frame dimensions from Figma.** A 1440-wide desktop frame renders in a 1440 viewport; a 390-wide mobile frame in a 390 viewport. Two capture paths, prefer the first the project supports:
   - **Golden test (preferred, deterministic).** Pump the widget/page in a `testWidgets` golden at the frame's logical size and `devicePixelRatio`, in the matching theme mode, and write the PNG. Goldens are the suite's visual contract (`ax-skills-flutter-testing`), so the comparison image is reproducible in CI and free of OS chrome.
   - **Running app (whole screens / live state).** Launch via the Dart & Flutter MCP **`runtime_introspect`** (same server `ax-skills-flutter-verify` uses; web target is fastest), drive to the route at the frame's window size, and capture a screenshot.
2. **Screenshot each breakpoint separately** (desktop, mobile) — never infer one from the other; extract and verify each frame's own values.
3. **Diff** the rendered PNG against the Figma export from Step 2:
   ```bash
   python .claude/skills/ax-skills-flutter-figma-pixel-perfect/scripts/compare_images.py \
     --reference home.figma.png \
     --candidate home.rendered.png \
     --out-diff home.diff.png
   ```
   It prints a similarity score and the worst regions (as bounding boxes) and writes `home.diff.png` with mismatches painted over a dimmed copy of the reference. **View `home.diff.png`** — it shows you *where* to look. Deps: `pip install pillow numpy`; run `--help` for `--tolerance`/`--grid`.

### Step 5 — Iterate to parity

For each hotspot the diff flags, go **back to the Figma data** (not the image) to find the correct value, fix the widget — usually a wrong token or a hug/fill mistake — then re-render and re-diff. With the running-app path, **hot-reload** and re-capture in place; with goldens, re-run the golden. Repeat until the remaining differences are explained rather than wrong.

Distinguish real mismatches from noise:
- **Real** — and must be fixed: layout shifts, wrong colors, wrong sizes/spacing, wrong font weight or `height` (line-height), missing elements, wrong radii/shadows, a hug-vs-fill sizing error that only shows at one breakpoint.
- **Noise** — expected, don't chase to zero: subpixel antialiasing, platform font-rendering differences (Skia vs the Figma renderer), and genuinely dynamic content (real text/data that differs from the mock's placeholder). The `--tolerance` absorbs most antialiasing; for dynamic content, compare structure/position rather than exact pixels, or pump the golden with the mock's placeholder data.

A clean run is a high similarity score (typically **~98%+** for static UI) **and** a `diff.png` whose remaining specks are all explainable noise. A high score with a hotspot sitting on a real element is **not** done. When you finish, report the final score per breakpoint and theme mode, and note any intentionally-unmatched regions (e.g. live data) so the result is honest. Record the fidelity outcome alongside runtime verification in `docs/verify.md`.

## Why this discipline pays off

The verification loop is what separates this from a normal Figma-to-code pass. It turns vague "looks about right" into a number and a picture, catches the small misses that individually slip by but collectively break the design, and gives the user evidence the implementation matches. **Build from data, through tokens; prove it with the diff.**

## How this skill plugs into the rest

- **`ax-skills-flutter-ui`** owns the design system (tokens, components, Code Connect, the Figma-to-code workflow). This skill is the fidelity-verification arm of it — it consumes those tokens/components and proves a frame matches.
- **`ax-skills-flutter-verify`** confirms the screen *behaves* (states, navigation, no runtime errors) via the Dart MCP; this skill confirms it *looks* identical. Run both before review; record both in `docs/verify.md`.
- **`ax-skills-flutter-testing`** — the golden test you write for Step 4 is the durable visual contract; keep it in the suite so CI re-verifies fidelity.
- **`ax-skills-flutter-code-review`** — the `ds` category fails any value approximated as a raw literal instead of imported as a token; a clean diff plus token-backed values is what "imported, not eyeballed" looks like in review.

## Bundled resources
- [references/fidelity-checklist.md](references/fidelity-checklist.md) — exhaustive property-by-property extraction and **Figma → Flutter + DS-token** mapping guide. Read it during Step 2/3.
- `scripts/compare_images.py` — the image-diff tool used in Step 4 (deps: Pillow, numpy; `pip install pillow numpy`). Run `--help` for options like `--tolerance`.
