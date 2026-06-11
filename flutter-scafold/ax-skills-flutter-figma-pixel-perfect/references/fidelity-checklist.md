# Fidelity checklist: every property to extract, and how it maps to Flutter

This is the exhaustive list of what to pull from a Figma node and what each thing
becomes in **Flutter** — through this app's **design-system tokens**, not raw
literals. The mapping of *values* is identical regardless of stack; only the
syntax changes. Here the syntax is Flutter widgets + `ThemeExtension` tokens.

Two golden rules for everything below:

1. **Read the value from the node data, not from the rendered pixels.** If a
   property isn't present in the data you pulled, that's a signal to pull more
   (deeper node, a variant, the variable definition), not a license to guess.
2. **The value lands as a token, never a literal.** If Figma binds the value to a
   variable, use the matching semantic token (`context.colors/spacing/text/radii/
   elevation/motion`). If no token exists, *add* one (and flag the gap in
   `docs/plan.md`) — a raw `Color(0xFF…)` / `EdgeInsets.all(14)` in feature code
   is a `ds` review failure. See `ax-skills-flutter-ui`.

## Table of contents
1. Geometry & position
2. Auto-layout → Row/Column/Flex
3. Sizing (hug / fill / fixed)
4. Fills (color, gradient, image)
5. Strokes / borders
6. Corner radius
7. Effects (shadows, blur)
8. Typography
9. Opacity & blend
10. Variables / design tokens
11. Component variants & interactive states
12. Prototype interactions → animations
13. Assets (icons, images)
14. Responsive behavior (constraints & breakpoints)

---

## 1. Geometry & position
- **Width / height**: exact logical px → `SizedBox`/`width`/`height` (or a sizing
  rule from §3). Don't round 41 to 40.
- **Position**: in auto-layout, position is governed by the layout — don't
  hardcode offsets. For absolutely-positioned children (Figma "absolute position"
  inside auto-layout, or free layers), use a `Stack` + `Positioned` with the exact
  offsets derived from the parent's box.
- **Rotation**: `Transform.rotate(angle: …)` (radians — convert from Figma degrees).

## 2. Auto-layout → Row/Column/Flex
Auto-layout is the single biggest source of "close but wrong" output. Map it
precisely:
- **Direction**: horizontal → `Row`; vertical → `Column`; wrap enabled → `Wrap`.
- **Padding**: Figma exposes four independent values → wrap in `Padding` with
  `EdgeInsets.only(top:, right:, bottom:, left:)` (via spacing tokens). **Never
  assume symmetry** — don't collapse to `EdgeInsets.all`.
- **Item spacing (gap)** → `Row/Column(spacing: …)` (Flutter 3.27+) or `SizedBox`
  gaps between children, using a spacing token. "Space between" → `MainAxisAlignment.spaceBetween`.
- **Primary axis alignment** → `mainAxisAlignment` (min=start, center=center,
  max=end, space-between=spaceBetween, space-around/evenly accordingly).
- **Counter axis alignment** → `crossAxisAlignment` (min=start, center=center,
  max=end, baseline=baseline).
- **Primary-axis sizing** hug vs fixed → `mainAxisSize: MainAxisSize.min` (hug)
  vs `.max`/explicit size (fixed). See §3.

## 3. Sizing (hug / fill / fixed)
For each axis, a Figma layer is one of:
- **Fixed** → explicit `width`/`height` (`SizedBox`, or `Container` constraints).
- **Hug contents** → let intrinsic size apply; on the main axis use
  `MainAxisSize.min`. Don't wrap in something that forces it to stretch.
- **Fill container** → `Expanded` / `Flexible(flex:)` along the layout axis, or
  `double.infinity` width / `crossAxisAlignment.stretch` across it.
Getting hug-vs-fill wrong is why elements end up the wrong size at different
viewport widths even when the static screenshot looked fine. **Check both axes** —
this is the mismatch the diff most often catches at only one breakpoint.

## 4. Fills (color, gradient, image)
- **Solid**: exact hex + alpha → a `colors.*` semantic token. A fill at 80%
  opacity is `0xCC……` / `.withOpacity(0.8)` on the token, **not** the flattened
  color you see on screen. Prefer the token; only the *primitive* tier holds raw
  ARGB.
- **Gradient**: type (linear/radial/angular) → `LinearGradient`/`RadialGradient`/
  `SweepGradient` with **every stop's color (as tokens) + position** and the same
  angle/alignment (`begin`/`end`). Put gradients on a `BoxDecoration`.
- **Image fill**: export the image (see §13) → `DecorationImage`/`Image` with
  `BoxFit` matching the Figma scale mode (fill→`cover`, fit→`contain`,
  crop→explicit alignment/rect, tile→`ImageRepeat.repeat`).
- **Multiple fills**: Figma stacks fills; replicate with stacked `DecorationImage`/
  layered containers in the same order.

## 5. Strokes / borders
- **Color + weight** → `Border.all(color: token, width: …)` on a `BoxDecoration`,
  or `BorderSide`.
- **Align** affects box sizing: Figma "inside" matches Flutter's default border
  (painted within bounds); "outside"/"center" changes the visual size — account
  for it so total dimensions still match the frame.
- **Individual sides**: emit per-side `Border(top:/right:/…)` when only some sides
  have strokes — don't apply a full border.
- **Dash pattern**: Flutter has no native dashed border — use a `CustomPainter`
  (or a `dotted_border`-style helper) with the exact dash/gap; don't substitute a
  solid border.

## 6. Corner radius
- Single value → `BorderRadius.circular(token)`.
- **Mixed corners** → `BorderRadius.only(topLeft:, topRight:, bottomRight:,
  bottomLeft:)` with each corner's own radius token. Figma frequently has
  asymmetric radii; **don't collapse them.** Apply via `BoxDecoration` or
  `ClipRRect` (clip children when the design clips content).

## 7. Effects (shadows, blur)
- **Drop shadow** → `BoxShadow(color:, offset: Offset(x, y), blurRadius:,
  spreadRadius:)`. Pull all of x/y/blur/spread **and the shadow color's alpha** —
  spread and shadow alpha are the parts people drop. Prefer an `elevation` token.
- **Inner shadow** → Flutter has no built-in inner shadow; use a `CustomPainter`
  or an inset-shadow decoration helper. Don't silently omit it.
- **Multiple shadows** → a list of `BoxShadow`, same order.
- **Layer blur** → `ImageFiltered(imageFilter: ImageFilter.blur(...))`.
  **Background blur** → `BackdropFilter(filter: ImageFilter.blur(...))` (usually
  inside a `ClipRRect`).
- **Text shadows** → `TextStyle(shadows: [Shadow(...)])`.

## 8. Typography
Pull every one of these per text node — partial typography is the most common
fidelity miss. Map to a `text.*` token (`context.text.titleLarge`, …); use
`.copyWith` only for genuinely one-off overrides, never to re-declare a token's
own values:
- **Font family** + **weight** (Figma "Semibold" → `FontWeight.w600`).
- **Size** (logical px) → `fontSize`.
- **Line height**: Figma gives px or %. Flutter `height` is a **unitless multiple
  of fontSize**, so convert: `height = lineHeightPx / fontSize` (or the % as a
  ratio). "Auto" line height = the font's default → omit `height`; don't invent a
  number.
- **Letter spacing** (px) → `letterSpacing` (Flutter uses logical px, not %; if
  Figma gives %, multiply by fontSize).
- **Paragraph spacing** → spacing between text blocks (gap/`Padding`), not inside
  one `Text`.
- **Text align** horizontal → `textAlign`; vertical → alignment of the text's
  container (`Align`/`Center`/cross-axis alignment).
- **Text case** (uppercase/…) → transform the string or a styled wrapper; Flutter
  has no `text-transform`, so apply the case to the actual text.
- **Decoration** (underline/strikethrough) → `TextStyle(decoration: …)`.
- **Truncation / max lines** → `Text(maxLines:, overflow: TextOverflow.ellipsis)`.

## 9. Opacity & blend
- Layer **opacity** → `Opacity`/`FadeTransition` (distinct from fill alpha — both
  can apply; prefer baking alpha into the color token and reserve `Opacity` for a
  whole-layer fade).
- **Blend mode** → `BlendMode` via `ShaderMask`/`ColorFiltered`/a `BackdropFilter`,
  depending on what's blending.

## 10. Variables / design tokens
- Run `get_variable_defs`. If a fill, spacing, radius, type, elevation, or motion
  value is **bound to a variable**, prefer the **token** over the raw value — map
  it onto the three tiers (`Ref` primitives → `AppColors/AppSpacing/AppRadii/
  AppTypography/AppElevation/AppMotion` semantic → component tokens). Each Figma
  **mode** (Light/Dark/Brand) is one `ThemeExtension` instance, so the value flips
  automatically — verify the diff in each mode you target.
- If **Code Connect** mappings exist, a node may already correspond to a real DS
  widget — reuse that `App<Name>` instead of rebuilding it. Check before you build.
- Only fall back to a raw literal (in the *primitive* tier, never feature code)
  when no variable backs it — and record the design gap.

## 11. Component variants & interactive states
A Figma component set encodes states as variants. Build **all** of them, not just
the default frame — this is also a `ds` review requirement:
- default, hover, focus, pressed/active, disabled, selected, error, loading.
- Map to the widget's state handling: `WidgetStateProperty`/`WidgetState` resolvers
  (hovered/focused/pressed/disabled/selected), `MouseRegion`/`FocusableActionDetector`
  for hover+focus on web/desktop, an explicit loading/disabled prop, etc.
- The state styling (color/elevation/border changes) must come from **the variant's
  own data**, not from your guess of "what hover usually looks like."
- Ensure ≥48dp touch targets and a semantic label per the UI skill's a11y rules.

## 12. Prototype interactions → animations
If the node has prototype reactions, translate them rather than omitting motion:
- **Trigger** (on tap / hover / after delay / while pressing) → the matching
  gesture/state (`onTap`, hover state, `Future.delayed`, pressed state).
- **Action** + **transition**: Smart Animate → an implicit
  `AnimatedContainer`/`AnimatedFoo` (or an explicit `AnimationController`) on the
  changing properties; Move/Push/Slide → `SlideTransition`/a page transition;
  Dissolve → `FadeTransition`/`AnimatedOpacity`.
- **Easing** (linear, ease-in/out, custom cubic bézier) → the matching `Curve`
  (`Curves.easeInOut`, or `Cubic(a,b,c,d)` for a custom curve) — from an
  `AppMotion` token.
- **Duration** → the exact `Duration` (an `AppMotion` token), not a guess.
Replicate the curve and duration exactly; "feels about right" motion reads as
wrong next to the prototype.

## 13. Assets (icons, images)
- **Vector icons / illustrations** → export as **SVG**; render with
  `flutter_svg` (or the app's icon component) from `lib/design_system/foundations/`.
  Don't redraw an icon by hand or substitute a similar one from an icon pack —
  that's an assumption.
- **Raster images** → export at the right pixel ratio (`2x`/`3x` per Flutter's
  asset-resolution buckets) to stay crisp; preserve aspect ratio and the Figma
  scale mode (`BoxFit`).
- Keep the asset's intrinsic dimensions so layout math stays correct.

## 14. Responsive behavior (constraints & breakpoints)
- **Constraints** (left/right/center/scale per axis) describe how a layer reacts
  when its parent resizes — translate into the right `Expanded`/`Flexible`,
  `Align`/`Center`, `Spacer`, or `Positioned` offsets (not fixed pixels where
  Figma says "scale"/"stretch").
- If the design provides **multiple frames** (desktop / tablet / mobile) or
  responsive variants, implement each via the DS template's breakpoint switch
  (`AppBreakpoints`, single-column ↔ master-detail) and **verify each frame
  separately** in Step 4. Don't infer the mobile layout from the desktop one —
  extract the mobile frame's own values and diff its own export.
