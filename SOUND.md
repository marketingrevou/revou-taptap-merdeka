# Sound — Tap Tap Merdeka

The race is a rhythm game wearing a sack-race costume. Everything below follows from
that one fact: the timing table in [README](README.md#difficulty) is a tempo, and the
job of the audio is to *play the player the tempo they need to win*.

Sound is additive and never load-bearing. The tap pad already carries the rhythm
visually (bright the moment you can hop, dim while airborne), so a muted player —
which on paid mobile traffic is most of them — loses nothing but polish.

## The tempo is not a taste decision

A tap sustains the combo if it lands inside the buffer window before touchdown or
within `PERFECT` after it. That makes the hop cycle, and therefore the music, a
derived quantity:

| | |
| --- | --- |
| Airborne | `HOP_TIME` 0.30 s |
| Forgiven early | `BUFFER` 0.10 s before landing |
| Combo window after landing | `PERFECT` 0.18 s |
| **Combo-sustaining cycle** | **0.20 – 0.48 s → 125 – 300 BPM** |
| Dead centre | 0.341 s → 176 BPM |

**Write the race cue at 160 BPM.** Quarter notes land 0.375 s apart: 0.175 s of early
slack, 0.105 s of late slack, and a brisk-but-natural march tempo rather than the
frantic 176 that centres the window perfectly. Cross-checked against the difficulty
table, 0.375 s sits inside the band that wins 100% of simulated races, with room for
the ±25% jitter a real thumb produces.

The trap: **anything at or below 125 BPM teaches a losing rhythm.** A 120 BPM track —
the default instinct for a cheerful march — puts the beat at 0.50 s, which is
*outside* the combo window and inside the 18%-win row. The player would tap in perfect
time with the music and lose. If a slower feel sounds better, write it as 80 BPM and
put the kendang on the **eighths**; the tap unit is what matters, not the number on the
session. The rule is simply: the most audible pulse in the mix must repeat every
0.20–0.48 s.

This applies **only to what plays during the race.** The menu bed is deliberately at
120 BPM — see [the menu tune](#the-menu-tune-is-hari-merdeka) — which is fine precisely
because there is nothing to tap on those screens and it carries no percussion. The rule
is about the pulse a player is tapping against, not about every tempo in the game.

Corollary — **do not sonify the CPU racers.** Their `r.wait` is 0.152–0.39 s plus a
rubber band, so their footfalls are deliberately off-grid and would smear the one cue
the player is trying to lock onto. `hop()` and `land()` already gate their SFX behind
`if(r.human)`; keep that.

## Palette

Kampung fair on 17 Agustus, scored like a 16-bit sports game. Two families of sound,
deliberately not blended:

- **Organic** — kendang, tanjidor brass, angklung, suling, and a real crowd. This is
  the world: bunting, dust, neighbours shouting.
- **Arcade** — short square/triangle blips for hop, combo and UI. This is the
  interface, and it already exists in `beep()`.

Keeping them separate is what lets the combo ladder cut through a busy crowd mix
without EQ gymnastics: the brass owns 300 Hz – 2 kHz, the blips own 600 Hz – 3 kHz but
last 90 ms, and the crowd is a wash underneath both.

**Phone speakers roll off below ~400 Hz.** A 60 Hz kick is inaudible on the device
almost every player is holding, so the pulse must carry in the mids — which is exactly
what a kendang does, and exactly what an 808 does not. High-pass every asset at 120 Hz;
it costs nothing and saves bytes.

Key: D major, pentatonic melody (D E F# A B), pelog-flavoured where it can be. One key
across every cue, so layers can enter and leave without a transition.

## Music: one cue, four layers

Five separate tracks for a 60-second session means a jarring cut every 15 seconds and
five times the bytes. Instead, **stems in one key that enter and leave**, so a state
change adds or drops a layer rather than cutting to a new cue — no crossfade, no
artefacts. The three race stems share the 160 BPM grid and lock to each other; the menu
bed plays alone, so it keeps the song's own tempo.

| Layer | File | Plays during | Content |
|---|---|---|---|
| **A** bed | `audio/bed.m4a` | title → email → picker | *Hari Merdeka*, first couplet — suling and angklung, 2/4 at 120 BPM. No pulse. 8.0 s. |
| — crowd | `audio/crowd.m4a` | **race only** | The kampung, underneath the race. 6.0 s. |
| **B** pulse | `audio/pulse.m4a` | countdown → race | Kendang + marching snare, quarter notes at 160. **This is the tap metronome.** 3.0 s. |
| **C** hook | `audio/hook.m4a` | race, from combo ≥ 4 | Tanjidor brass hook. A reward for finding the rhythm. 6.0 s. |
| **D** payoff | `audio/payoff.m4a` | results | Full band + suling + crowd roar. One-shot, 4 s, does not loop. |

**The menus are music only — no crowd.** The crowd arriving *is* the cue that the
race is about to start, which is worth more than atmosphere on a cover screen. It
also means the bed plays alone, which frees both its length and its tempo — see
below, because the tune needs its own tempo rather than the race's.

### The menu tune is "Hari Merdeka"

The first couplet, transcribed in `BED_RIFF` from the published *not angka*:

```
| 0 5. 5. 5. | 3 3 3 3 | 2 3 4 2 | 1  5. |   Tujuh belas Agustus tahun empat lima
| 0 5. 5. 5. | 5 5 5 5 | 4 5 6 4 | 3   .  |   itulah hari kemerdekaan kita
```

Two things the notation settles that guesswork could not, and both change the
arrangement:

- **It is in 2/4, not 4/4.** Every written bar is four beamed eighths. Read as 4/4
  the phrasing comes out wrong.
- **The dots under the pickup notes are octave-below markers**, not duration dots.
  Each phrase opens on the sol *beneath* the tonic and leaps up a fourth onto the
  downbeat, and that rising fourth is the whole march character of the thing.

Transposed to D major to sit with every other cue, so `1` = D4, `5.` = A3.

**Tempo: 120 BPM, which is the song's and not the game's.** The bed plays alone on
the menus, so unlike the race stems its tempo is unconstrained — and it should be,
because forcing a national march onto the race's 160 BPM grid runs it about 30%
fast and makes a tune every player knows sound rushed. Eight bars of 2/4 at 120 BPM
is 8.000 s. The race stems stay locked to each other at 6 and 3 s.

Extending to the full first section is adding rows 3–4 of the notation to
`BED_RIFF`, which doubles the stem to 16 s and about +43 KB.

> **Licensing.** H. Mutahar wrote this in 1946 and died in 2004, so under UU 28/2014
> (life + 70 years) it is in copyright until roughly **2074**. Commercial use on paid
> traffic needs a licence — in Indonesia, WAMI or LMKN. Routine clearance, but not
> free, and not automatic just because the song is a national one. **This is not
> cleared in-repo; it is an outstanding task before launch.**

The drum loop is 2 bars where the melody is 4. It is a drum pattern whose only
variation was the fill, and 3.0 s divides 6.0 s exactly, so the two stay
phase-locked forever — which is the whole reason the layers can be started
together once and then only gain-ridden.

Layer B enters bare for its first bar so the pulse is unambiguous before the
arrangement arrives. Layer C entering at combo 4 is the single best piece of
feedback available: the music *thickens* when the player is doing it right.

**The countdown.** `countdown = 3.05` ticks at 3/2/1 via `Math.ceil`, which is 60 BPM
and not a subdivision of 160. Rather than re-time it, put a kendang roll under the
final second that accelerates into the pulse, and land layer B's first downbeat exactly
on `sfxWhistle()`. If you'd rather make it strictly musical, `countdown = 3.0` with
ticks driven off 0.375 s beats gives a clean 8-beat count-in — but that means changing
`step()`, and the roll gets you the same feel for free.

## SFX, and where each one hooks in

Every cue below exists as a slice of `audio/sfx.m4a` under the name in the first column.
**HF** marks the ones worth regenerating with Higgsfield, where a real recording beats
synthesis — see [Higgsfield](#what-higgsfield-can-and-cannot-do).

| Cue | Hook in `index.html` | HF |
|---|---|---|
| `hop` — sack thump + cloth | `sfxHop`, from `hop()` | |
| `perfect` — **pitch climbs with `r.combo`** | `sfxPerfect`, from `hop()` | |
| `land` — dust scuff | `sfxLand`, from `land()` | ✓ |
| **`trip` — you tapped mid-air** | ⚠️ **none** — `tap()`, the `else` that zeroes the combo | ✓ |
| **`dud` — tapped while `r.lock > 0`** | ⚠️ **none** — `tap()`, `if(r.lock <= 0)` falls through silently | |
| `tick` — countdown | `beep(440, …)` in `step()` | |
| `roll` — kendang into the downbeat | new, last second of the countdown | |
| `whistle` — start | `sfxWhistle`, from `step()` | ✓ |
| Announcer "Merdeka!" | new, on the whistle — **not yet generated** | ✓✓ |
| `crowd` — looping bed | new, race state | ✓✓ |
| `lead` — crowd lift on taking first | `step()`, on a lead change | ✓ |
| `tape` — finish tape snap | `step()`, at `r.done && r.human` | ✓ |
| `payoff` — win music | `sfxWin`, from `endRace()` | |
| `lose` — not-first sting | `sfxLose`, from `endRace()` | |
| `prize` — reveal shimmer | ⚠️ **none** — `endRace()`, where `#prize-text` is set | |
| `ui-select` | `beep(700, …)` in `setPick()` | |
| `ui-confirm` | `beep(660, …)` ×3 (email, MULAI, GO) | |
| `ui-open` | `beep(620, …)` in `openModal()` | |

### The three gaps were the important part

All three are now wired; this is what they were and why they mattered.

**The trip was silent.** The game's only punishment — combo to zero and the next hop
locked — made no sound at all, so a player who mashed just got slower with no idea why.
The highest-value cue on the list: a short, dry, downward cloth *scuff* with a detuned
fifth under it, mixed at −10 dB, **hotter than the hop**, so it cuts through the pulse.

**The locked tap was silent too.** During `r.lock` (0.11–0.20 s) a tap did nothing
whatsoever. It now gets a muted −26 dB click — enough to say *heard you, not yet*,
without rewarding the mash.

**Lead changes had no hook at all.** The rubber band exists to keep races close and
none of that drama was audible. `step()` now watches whether the player is first and
fires `lead` on regaining it — `leading` starts `true`, because everyone is level on the
line and a cheer at the start would mean nothing.

### The combo ladder

`sfxPerfect` is currently a fixed two-note blip. Climb it instead — pentatonic, one
step per combo, resetting on break. `COMBO_MAX` is 12, which is exactly a 12-step
D-major-pentatonic ladder:

| Combo | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Hz | 587 | 659 | 740 | 880 | 988 | 1175 | 1319 | 1480 | 1760 | 1976 | 2349 | 2637 |

It tops out at 2.6 kHz — bright on a phone speaker without being shrill — and the
rising line does the teaching that the difficulty table can't.

## What Higgsfield can and cannot do

Worth being straight about this before you spend credits: **Higgsfield has no
standalone music or sound-effects generator.** Its own documentation says so — audio
comes bundled with video generation (WAN 2.5 native audio, Seed Audio for
multi-speaker scenes), and the ambience is generated *alongside dialogue* rather than
on its own. What *is* standalone is the voice side: six models for speech, voice swap
and translation, with mp3/wav output.

So the division of labour:

**Use Higgsfield for** — the announcer VO (a direct fit: standalone, Bahasa Indonesia,
emotional control, real audio files out), the crowd ambience bed, and one-shot foley.
These are beds and one-shots where a 5–10 s clip is the right length and looping is
either easy or unnecessary.

**Do not use Higgsfield for** — the 160 BPM loop or the short interface cues. You cannot
ask a video model for an exact tempo, an exact loop point, or four separate stems, and a
130 ms sack thump is not something a generative model does better than fifteen lines of
numpy. This is why the whole set is synthesised by `tools/make_audio.py` instead: exact
tempo, exact loop points, exact levels, four stems for free, and a rebuild in under a
second when a level is wrong.

If you want *generated* music rather than synthesised, a tempo-aware music tool
(Suno, Udio, Stable Audio) is the right instrument — you still get one stereo mix
rather than stems, and you still loop-edit it by hand.

**Where Higgsfield genuinely wins** is the organic layer, and it is worth doing: a real
crowd has a texture that filtered noise plus scattered bursts only approximates, and a
real MC shouting *"Merdeka!"* is not synthesisable at all. Generate those, drop them over
the same filenames, re-run `encode_audio.sh`. Everything else stays put.

### Getting audio out of Higgsfield

For foley and ambience the trick is to **describe a shot whose soundtrack is the asset
you want, and keep the frame deliberately boring** so the model spends its effort on
the audio. Then throw the video away.

Rules that matter in these prompts:

- Say **"static shot"** / locked-off camera, or you get whooshes and camera movement.
- Say **"no music, no dialogue"** on every foley prompt, or it scores the clip.
- Generate 3–4 takes per asset. Audio is the less-controlled of the two outputs.
- Mono is fine and halves the bytes; these are all point sources or washes.

```
Crowd bed (loop):
Static wide shot of a village street festival crowd on Indonesian Independence Day,
red and white bunting overhead, people clapping and cheering steadily, nobody in
close-up. Audio: continuous warm outdoor crowd ambience, steady clapping, distant
children laughing and a faint hand drum far away. No music, no dialogue.
```

```
Start whistle:
Close static shot of a referee's hand raising a metal whistle to his lips at a dusty
village sports field. Audio: one sharp metal whistle blast, then crowd murmur rising.
No music, no dialogue.
```

```
Sack landing:
Close static low-angle shot of a burlap sack landing on dry packed dirt, small dust
cloud. Audio: single soft burlap thud on dry earth, faint grit scuff. No music,
no dialogue.
```

```
Trip:
Close static low-angle shot of a burlap sack scuffing and dragging sideways on dry
dirt as someone stumbles. Audio: one dull cloth scuff dragging on grit, ending flat.
No music, no dialogue.
```

```
Finish tape:
Close static shot of a red and white paper ribbon stretched across a finish line
snapping apart. Audio: crisp paper ribbon snap, immediate crowd cheer erupting.
No music, no dialogue.
```

```
Crowd roar (win):
Static shot of a festival crowd erupting in celebration as confetti falls.
Audio: sudden crowd roar and applause peaking then settling into happy chatter.
No music, no dialogue.
```

For the announcer, use the voice models directly — no video needed. Male, 30s, warm,
the slightly clipped over-driven energy of a kampung MC on a cheap PA. Bahasa
Indonesia. Record each line separately so they can be triggered independently:

| Line | Fires on |
|---|---|
| "Siap… ya!" | countdown, at "1" |
| "Merdeka!" | the whistle |
| "Ayo, ayo, ayo!" | combo ≥ 8 |
| "Juara satu!" | `endRace()`, first place |
| "Wah, nyaris!" | `endRace()`, second or third |

Then strip the video and normalise. `ffmpeg` isn't installed here — `brew install
ffmpeg` first:

```bash
# pull the audio track out of a Higgsfield clip, mono, 44.1k
ffmpeg -i clip.mp4 -vn -ac 1 -ar 44100 -c:a pcm_s16le raw.wav

# trim to the useful part, high-pass, normalise, encode
ffmpeg -i raw.wav -af "highpass=f=120,loudnorm=I=-18:TP=-1.5" \
       -c:a aac -b:a 64k audio/whistle.m4a
```

## Encoding, budget and loading

**Format: AAC in `.m4a`.** It decodes everywhere including iOS Safari with no fallback
file — Opus-in-WebM does not, and a second format doubles the manifest for no gain.

**Use VBR, not CBR.** Under `-b` the size is exactly bitrate × duration, so the encoder
cannot spend less on the tonal angklung bed than on the broadband crowd wash — content
stops mattering at all. `afconvert -s 3 -u vbrq <q>` lets each asset cost what it needs;
the quality per asset lives in `tools/encode_audio.sh` and runs from q35 for the crowd
(a −26 dBFS wash nobody can hear artefacts in) to q70 for the drums, which carry the
tap grid and must not be smeared.

**The one-shots ship as a single sprite sheet.** A short AAC file is mostly container
overhead, and 14 requests on a paid-traffic page is 14 chances to not have arrived yet.
`audio/sfx.m4a` is all 14 cues concatenated with 50 ms of guard silence, and
`audio/sfx.json` maps each to `{at, dur}` for `start(when, offset, duration)`. This is
verified sample-exact through the AAC round trip — zero length delta, zero alignment
lag, guard gaps 50–70 dB below their cues — so the offsets need no runtime correction.

**Loop points: never take `loopEnd` from `buffer.duration`.** This one is worth reading
twice, because it looks right and is silently wrong. AAC pads to a whole number of
1024-sample frames, and **Chrome does not trim the trailing padding** — so a stem that
was rendered at exactly 6.000 s decodes as 6.0140 s, and `pulse` as 3.0067 s. Loop on
the decoded length and the tap grid slips 7–14 ms *every pass* — around 85 ms over a
20-second race, which is half the `PERFECT` window. The kendang would drift off the
rhythm it exists to teach.

So `audio/sfx.json` carries a `loops` map of the exact musical length per stem, computed
from the tempo rather than measured from the file, and the engine sets `loopEnd` from
that. (`sfx.m4a` happens to need no padding — 8.02 s at 48 kHz is exactly 376 frames —
but the sheet is read by explicit offset and duration anyway, so trailing padding cannot
affect it either way.)

Worth noting how this hid: an `afconvert` round trip reports the file as sample-exact,
because CoreAudio *does* honour the gapless metadata. Only a real browser shows it.
`tools/` has no test runner, but the check is a dozen lines of `decodeAudioData` in a
headless Chrome against `tools/serve.py` — worth rerunning if the encoder settings change.

**Start the stems once and only ride their gain.** Stopping and restarting a source to
"turn a layer on" is what makes layers drift out of phase. Start all four at a common
`t0`, hold the inaudible ones at zero gain, and `setTargetAtTime` to fade them.

**Budget: 200 KB.** The page ships ~940 KB of assets and this is paid traffic, where
load time is the funnel. What the synthesised set actually encodes to:

| | |
| --- | --- |
| `sfx.m4a` — 15 cues, 8.0 s, q60 | 60.9 KB |
| `bed.m4a` — 8 s, q40 | 43.0 KB |
| `hook.m4a` — 6 s, q55 | 44.1 KB |
| `crowd.m4a` — 6 s, q35 | 31.5 KB |
| `payoff.m4a` — 4 s, q55 | 30.7 KB |
| `pulse.m4a` — 3 s, q70 | 23.0 KB |
| **Total** | **233.2 KB** |

That is 17% over the 200 KB target. The target was set before the menus had a tune, and
the melody costs ~19 KB more than the ostinato it replaced — a fair trade, but it is a
trade, so the number stays at 200 rather than being quietly moved to match. It is what
the next addition has to argue against.

If the bytes are needed back, the cheapest is trimming `crowd` to 4 s (~10 KB), which is
imperceptible at −26 dBFS under a kendang. Note also that VBR quality is not a smooth
dial — `bed` encodes to the same size at q35 and q40, so q40 is free.

The first pass came in at **491 KB**, and only one of the three fixes was about bitrate.
Shipping `roar` and `win` at all was redundant — `sfx_win()` already mixes `sfx_roar()`
into itself and `stem_payoff()` is the results-card music, so the same crowd was being
paid for three times. Then the drum loop halved, and the noise wash came out of the bed.

**Adding the announcer VO will push this over budget** — five lines is ~30 KB. Put them
in the sprite sheet rather than as separate files, and re-check the total.

**Load it late and only on intent.** Nothing audio-related should touch the critical
path. Fetch the manifest when the player reaches the **email screen** — there is a
natural several-second pause there while they type, and it's the first moment they've
shown they intend to play. A player who bounces off the title never pays the bytes.
`AudioContext` cannot start before a gesture anyway, and the MULAI click is that
gesture, so the existing lazy `actx` creation in `beep()` is already correct.

**Persist the mute.** `setMuted()` currently resets to sound-on every load. Write it to
`localStorage` and read it at boot — a player who muted once and came back through a
second ad impression should stay muted.

## Levels

Mix to a −1 dBFS ceiling. Beds are matched by **RMS**, because that is what "sits under
the game" means; one-shots by **peak**, because what matters about them is whether they
cut through. This table is mirrored by `LEVELS` in `tools/make_audio.py`, which is
authoritative — keep the two in step.

| | | |
| --- | --- | --- |
| `pulse` | −20 RMS | the tap grid |
| `hook` | −21 RMS | |
| `bed` | −24 RMS | |
| `crowd` | −26 RMS | |
| `payoff` | −18 RMS | |
| `tape`, `win` | −6 peak | |
| `whistle` | −8 peak | −6 measured piercing on a phone speaker |
| **`trip`** | **−10 peak** | the punishment must cut through |
| `lose`, `prize` | −10 peak | |
| `perfect` | −12 peak | |
| `lead` | −16 peak | a reaction behind the race, not in front of it |
| `tick`, `roll` | −12 peak | |
| `hop` | −14 peak | |
| `land` | −15 peak | |
| `ui-*` | −14 to −16 peak | |
| `dud` | −26 peak | heard you, not yet |
| Announcer | −8 peak, ducking the music 3 dB | not yet generated |

Filter *before* normalising. Doing it the other way round — which the first version of
`make_audio.py` did — means the 120 Hz high-pass silently walks every level away from
its target, and every number above is wrong by however much low end came off. For the
same reason, only the tail gets faded: a 4 ms fade-in cost the ribbon snap in `tape` 4 dB
of its own attack, and every envelope already ramps from zero anyway.

## Generating the set

```bash
.venv/bin/python tools/make_audio.py    # synth -> audio/wav/*.wav + audio/sfx.json
tools/encode_audio.sh                   # -> audio/*.m4a, prints the running total
.venv/bin/python tools/make_preview.py  # -> audio/preview.html, the audition page
```

Nothing here calls a generative audio model. It is ~500 lines of numpy: kendang as a
pitch-swept membrane plus a mid-heavy slap, tanjidor brass as two detuned additive
voices under a lowpass, angklung with inharmonic partials, crowd as a filtered wash with
scattered voice-shaped bursts. That buys exact tempo, exact loop points, exact levels and
free iteration — all four of which a video model cannot give you.

`audio/preview.html` is the audition page: the tempo demo (which runs this file's real
hop/land/trip logic against the pulse so you can *hear* 160 BPM winning and 120 losing),
the four layers as live toggles, every cue as a pad, and the combo ladder.

## What is live, and what is left

1. ~~**Synthesise the set**~~ — 15 cues, 4 stems, one results cue, 214.5 KB.
2. ~~**The combo ladder**~~ — one cue, twelve playback rates.
3. ~~**The 160 BPM pulse**~~ and the four-layer plan.
4. ~~**Wire it into `index.html`**~~ — sample engine with the synth as fallback, all
   three silent gaps filled, mute persisted, loaded lazily at the email step.
5. **Swap in the Higgsfield organics** where a recording beats synthesis — `crowd`,
   `whistle`, `tape`, `land`, `trip`, `lead`. Same filenames, so it is
   `encode_audio.sh` and nothing else. This is the next real step.
6. **The announcer last.** It is the most memorable element and the most likely to grate
   on a replay, so it wants the most listening — and it is what Higgsfield is genuinely
   best at here. Budget for it: see the note under the manifest.

Two things deliberately *not* done. There is no announcer, so the countdown has no voice.
And the title screen has no music: audio is fetched at the email step, so a player who
bounces off the cover never pays for it — a deliberate trade of atmosphere for load time
on paid traffic. Moving it earlier is a one-line change to where `loadAudio()` is called.

---

Sources for the Higgsfield capability notes: [Higgsfield
Audio](https://higgsfield.ai/blog/higgsfield-audio) ·
[WAN 2.5 native audio](https://higgsfield.ai/blog/WAN-2.5-Text-to-Audio)
