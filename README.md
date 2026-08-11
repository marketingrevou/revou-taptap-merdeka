# Tap Tap Merdeka — Balap Karung

A tap-to-hop sack race. You pick one of the four racers, the other three are run by
the computer, and the field scrolls left → right until the finish gate comes into view.

The menus and HUD are dressed as the RevoU *Data Analytics with AI* Merdeka creative
— see [Design](#design) for where the art and tokens come from.

## Play

Open `index.html` in a browser — that's it, no build step and no server needed.

If you'd rather serve it (some browsers are stricter about local files):

```bash
python3 -m http.server 8123
```

then open http://localhost:8123.

**Controls:** tap/click anywhere, or press `Space` / `↑` / `Enter`.

## How the race works

Each tap starts one hop: the racer is airborne for `HOP_TIME` and covers `HOP_DIST`
of track. What separates a good run from a bad one is *when* you tap:

| Timing | Result |
| --- | --- |
| Within `PERFECT` (0.20 s) of landing | combo +1, each step up to ~34% longer |
| Later than that | plain hop, combo resets |
| While still in the air (outside the 0.10 s landing buffer) | you trip: combo resets and the next hop is locked briefly |

Rhythm pays: a steady 3 taps/second finishes in ~10 s where mashing takes ~18.5 s
and only wins about a third of the time.

## Difficulty

Keep a rhythm of roughly 2.1 taps a second or better and the race is yours; drop
below that and the pack takes it. Measured over 20–40 simulated races per cadence
(*jitter* rows vary each tap by ±25%, closer to how a person actually taps):

| Your tapping | Wins | Losses are by |
| --- | --- | --- |
| 0.35 s between taps | 100% | — |
| 0.43 s | 100% | — |
| 0.47 s | 100% | — |
| jitter around 0.43 s | 98% | 0.00 s |
| jitter around 0.47 s | 85% | 0.03 s — photo finish |
| 0.53 s | 18% | 0.39 s |
| jitter around 0.53 s | 15% | 0.48 s |
| 0.60 s | 5% | 1.5 s |
| mashing as fast as possible | 35% | 0.21 s |

The three CPU racers each draw a random skill level, then a rubber band nudges
their pace toward yours — it eases off a little when you fall behind and chases
when you lead, so races finish close instead of being decided in the first
straight. Nearly every loss above is under a second.

All of the tuning lives in the constants at the top of the `<script>` block in
`index.html` (`RACE_LEN`, `HOP_TIME`, `HOP_DIST`, `PERFECT`, `BUFFER`, `COMBO_MAX`),
plus the CPU pace in `makeRacers()` (`r.skill`, `r.wait`) and the rubber-band
coefficients in `step()`. Raise `r.wait` to make the opponents easier, lower it to
make them meaner.

## Design

Everything outside the race field follows the Figma frame
`DA Mystery Discount Box` (`1749:2350`) in [Meta Ads Brief][figma] — the red radial
backdrop, the **TAPTAP MERDEKA!** wordmark, the RevoU mark and the gold discount
badge. The title screen is that frame, rebuilt responsively; the picker, the results
card and the drawn race HUD reuse its parts.

Two things in the frame are deliberately *not* on the title screen: the
"Data Analytics with AI" course line and the chart-and-magnifier icon that overlaps
the badge. A cover that has to hold a start button reads better without them.

[figma]: https://www.figma.com/design/Ts1GpfXwfW0zRr6YgSoG5v/Meta-Ads-Brief?node-id=1749-2350

The tokens live in `:root` at the top of the `<style>` block, and are mirrored as
canvas constants (`MERAH`, `KUNING_1/2`, `EMAS_BAYANG`, `INK`, `FONT`) at the top of
the `<script>` block so the drawn HUD and the DOM chrome cannot drift apart:

| | |
| --- | --- |
| Backdrop | `radial-gradient(ellipse 88.5% 96.9% at 50% 50%, #f35e64, #e83f45 50%, #dd1f26)` |
| Red / ink | `#dd1f26` · `#311f17` |
| Gold badge | `#fff3b6 → #ffde3b`, 10px white keyline, 7px radius, `0 9px 0 #685020` |
| Type | IBM Plex Sans Bold, `line-height: 1.1` |

Two classes carry the whole look. `.badge` is the gold card — used for the discount
badge, the nameplate and the results card — and `badgePanel()` in the script is its
canvas twin, so the in-race HUD panel is the same object. `.display` is the outlined
heading treatment, built from stacked `text-shadow`s rather than
`-webkit-text-stroke`: the stroke is centred on the glyph edge, and at this weight it
swallows the red fill.

The title lockup scales off a single custom property, `--w` (the wordmark width),
with every other size expressed as its ratio inside the 744×382 lockup — so the
whole thing grows and shrinks as one piece instead of each part clamping on its own.
The wordmark is the widest element; the badge under it runs about .9 × `--w`, since
`Rp5,000,000!` sets its own width rather than the artwork's. Below 900px wide (or
520px tall) the lockup collapses to one centred column and the hero character drops
out.

If the course line or the icon ever come back, re-check the `--w` caps: the icon
hangs off the badge's left edge, which pushed that row to ~1.25 × `--w` and made it,
not the wordmark, the first thing to overflow.

Assets sit in `assets/` (backdrop, both wordmark halves, logo, badge art) and
`fonts/` — one 40 KB IBM Plex Sans variable woff2 covering weights 100–700,
self-hosted so `index.html` still opens straight off the filesystem.

## Portrait

The race is a horizontal chase, so a tall screen is the wrong shape for it twice
over: it spends its height on sky, and it hides the track the drama lives on.
Fitting the world into 9:16 left only ~560 world px across — you could not see the
pack you were racing. So on anything narrower than `BAND_ASPECT` (3:2) the race is
**letterboxed into a band** and the leftover strips are given jobs. On a 375×812
phone:

| | |
| --- | --- |
| Top strip, 169px | place / time / combo panel and the progress rail |
| Band, 375×250 | the race — **1080 world px across**, up from 560 |
| Bottom strip, 393px | the tap pad, sat in thumb reach |

`resize()` derives `W`/`H`/`SS` from the *band* rather than the viewport, so the
scene keeps landscape's proportions and every drawing function is unchanged.
`bandSpace()` and `screenSpace()` switch the canvas transform between the two
coordinate systems: the scene and the countdown/combo overlays draw in band space
(clipped to the band), while the docked chrome and tap pad draw in screen pixels at
`HS`, because band-relative sizes would render them postage-stamp small inside a
250px strip. Landscape is untouched — the band is the whole viewport, `HS` resolves
to the old `SS/720` scale, and the HUD lands on exactly the same pixels as before.

`#backdrop` sits *behind* the canvas and is always on, so it fills the strips; in
return `render()` skips the scene entirely on the menus, where the backdrop is all
you see anyway. Safe-area insets are read off the hidden `#safe` probe — `env()`
does not resolve through `getComputedStyle` on a custom property, but it does on a
real declaration.

The tap pad doubles as a rhythm cue: full brightness the moment the racer lands and
is ready for the next hop, dimmed while airborne or tripped. Taps still register
anywhere on screen, strips included.

There is deliberately no "please rotate your phone" nag. Telling a player on paid
traffic that their phone is the wrong shape is a drop-off, not a fix.

## Animation

Three poses per character on the race field, driven by the racer's state:

- **Stand ⇄ Ready** — idle sway at the start line and after finishing
- **Ready** — grounded during the race, coiled for the next hop
- **Jump** — airborne

The `Jump` art is drawn higher in the source sheet than the other two poses, and the
sprite exporter keeps a *shared vertical crop* per character, so switching to `Jump`
lifts the racer off the ground on its own. A small sine arc is added on top for the
in-between motion.

## Sprites

Two sets, for two jobs.

**Race field** — `Stand.png`, `Ready.png` and `Jump.png` are sheets of all four
characters in the flat vector style. The exporter keys out the background *and* the
cast shadow — both sit on the same line in RGB space between the pink backdrop and
the shadow tone — then isolates each racer as a connected component (a cap brim
overhangs its neighbour, so a plain column cut would clip it) and writes
`sprites/<name>_<pose>.png`.

**Menus** — `sprites/<name>_hero.png` are the 3D portraits from the campaign
creative, downscaled from `images/`. The picker, the nameplate and the results board
use these; the race does not, because there is only the one pose. Each render is
already a tight cutout with the sack flush to the bottom edge, so a bottom-anchored
draw lines all four up on the same ground line.

To regenerate either set:

```bash
python3 -m venv .venv && .venv/bin/pip install Pillow numpy scipy
.venv/bin/python tools/extract_sprites.py      # race poses, from the sheets
.venv/bin/python tools/make_hero_sprites.py    # menu portraits, from images/
```

Character order in the sheets is `bapak, ibu, adik, kakak`, left to right, and
`images/karakter-01…04` follows the same order. `sprites/<name>_front.png` is the
old flat-vector picker art, now superseded by `_hero` — still produced by
`extract_sprites.py`, no longer referenced by the page.
