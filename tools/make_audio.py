"""Synthesise the whole sound set for Tap Tap Merdeka.

Writes 48 kHz mono WAVs into audio/wav/, which tools/encode_audio.sh turns into
the .m4a files the page loads. See SOUND.md for the design these implement --
in particular why the music is 160 BPM and nothing else.

    .venv/bin/python tools/make_audio.py

Everything is high-passed at 120 Hz: phone speakers roll off below ~400 Hz, so
sub-bass is bytes nobody hears. The pulse carries in the mids instead.
"""

import json
import os
import wave

import numpy as np
from scipy import signal

SR    = 48000
BPM   = 160                    # derived in SOUND.md, not a taste decision
BEAT  = 60.0 / BPM             # 0.375 s -- the tap cycle the combo window wants
BAR   = 4 * BEAT               # 1.5 s
BARS  = 4
LOOP  = BARS * BAR             # 6.0 s, an exact number of samples at 48 kHz
PULSE_BARS = 2                 # the drum loop needs less length than the melody
GUARD = 0.05                   # silence between cues on the sprite sheet

OUT = os.path.join(os.path.dirname(__file__), os.pardir, "audio", "wav")

# D major pentatonic -- one key across every cue so layers stack freely
NOTE = {n: 440.0 * 2 ** ((m - 69) / 12.0) for n, m in {
    "D2": 38, "A2": 45, "D3": 50, "E3": 52, "F#3": 54, "G3": 55, "A3": 57, "B3": 59,
    "D4": 62, "E4": 64, "F#4": 66, "G4": 67, "A4": 69, "B4": 71,
    "D5": 74, "E5": 76, "F#5": 78, "A5": 81, "B5": 83, "D6": 86,
}.items()}


# ----------------------------------------------------------------- primitives

def n(dur):
    return int(round(dur * SR))


def t(dur):
    return np.arange(n(dur)) / SR


def noise(dur, seed=None):
    rng = np.random.default_rng(seed)
    return rng.uniform(-1, 1, n(dur))


def decay(dur, tau, attack=0.002):
    """Percussive envelope: near-instant attack, exponential tail."""
    x = t(dur)
    env = np.exp(-x / tau)
    a = max(1, n(attack))
    env[:a] *= np.linspace(0, 1, a)
    return env


def ar(dur, attack, release, hold=None):
    """Sustained envelope for pitched, blown or struck-and-held voices."""
    total = n(dur)
    a, r = max(1, n(attack)), max(1, n(release))
    a, r = min(a, total), min(r, total - 1)
    env = np.ones(total)
    env[:a] = np.linspace(0, 1, a) ** 0.7
    env[total - r:] = np.linspace(1, 0, r) ** 1.5
    if hold is not None and hold < 1:
        env[a:total - r] *= hold
    return env


def _sos(kind, cut, order=2):
    if kind == "bp":
        wn = [max(20.0, cut[0]) / (SR / 2), min(cut[1], SR / 2 - 100) / (SR / 2)]
    else:
        wn = min(max(20.0, cut), SR / 2 - 100) / (SR / 2)
    return signal.butter(order, wn, btype={"bp": "bandpass", "lp": "low", "hp": "high"}[kind],
                         output="sos")


def bp(x, lo, hi, order=2):
    return signal.sosfilt(_sos("bp", (lo, hi), order), x)


def lp(x, cut, order=2):
    return signal.sosfilt(_sos("lp", cut, order), x)


def hp(x, cut, order=2):
    return signal.sosfilt(_sos("hp", cut, order), x)


def sweep(f0, f1, dur, shape=1.0):
    """Sine whose frequency glides f0 -> f1; phase is integrated so it stays smooth."""
    x = t(dur)
    k = (x / max(x[-1], 1e-9)) ** shape
    f = f0 + (f1 - f0) * k
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def harm(f, dur, partials, vib=0.0, vib_hz=5.0):
    """Additive tone. `partials` is a list of (multiple, amplitude)."""
    x = t(dur)
    out = np.zeros_like(x)
    detune = 1.0 + vib * np.sin(2 * np.pi * vib_hz * x) if vib else 1.0
    for mult, amp in partials:
        out += amp * np.sin(2 * np.pi * f * mult * np.cumsum(np.full_like(x, 1.0) * detune) / SR)
    return out / max(sum(a for _, a in partials), 1e-9)


def sat(x, drive=2.0):
    return np.tanh(x * drive) / np.tanh(drive)


def place(buf, x, at, gain=1.0):
    """Mix x into buf at `at` seconds, wrapping past the end so loops stay seamless."""
    i = int(round(at * SR)) % len(buf)
    m = len(x)
    if m > len(buf):
        x, m = x[:len(buf)], len(buf)
    end = i + m
    if end <= len(buf):
        buf[i:end] += x * gain
    else:
        cut = len(buf) - i
        buf[i:] += x[:cut] * gain
        buf[:m - cut] += x[cut:] * gain          # wrap, so a tail crossing the loop
    return buf                                    # point lands at the top instead


def db(x):
    return 10 ** (x / 20.0)


def norm_peak(x, target_db):
    p = np.max(np.abs(x))
    return x * (db(target_db) / p) if p > 1e-9 else x


def norm_rms(x, target_db):
    r = np.sqrt(np.mean(x ** 2))
    return x * (db(target_db) / r) if r > 1e-9 else x


def seamless(gen, xf=0.06):
    """Render xf seconds long, then fold the overhang back over the head.

    Noise is not periodic, so a bed rendered to exactly LOOP leaves a step at the
    wrap -- a tick every six seconds. Folding makes the head and tail the same
    material while keeping the length exactly LOOP, which the beat grid needs."""
    x = gen(LOOP + xf)
    m = n(xf)
    f = np.linspace(0, 1, m)
    x[:m] = x[:m] * f + x[n(LOOP):n(LOOP) + m] * (1 - f)
    return x[:n(LOOP)]


def prepare(name, x, peak=None, rms=None, fade=0.004):
    """Filter first, then normalise -- doing it the other way round means the
    high-pass silently walks every level away from its target."""
    x = np.asarray(x, dtype=np.float64)
    x = hp(x, 120, order=2)
    # Fade before normalising, and only the tail. Fading in would attenuate any cue
    # whose transient sits at sample 0 -- the ribbon snap in `tape` lost 4 dB that
    # way -- and every envelope here already ramps up from zero, so it buys nothing.
    if fade:
        f = max(1, n(fade))
        x[-f:] *= np.linspace(1, 0, f)
    if rms is not None:
        x = norm_rms(x, rms)
    elif peak is not None:
        x = norm_peak(x, peak)
    over = np.max(np.abs(x))
    if over > db(-1.0):
        print(f"  ! {name}: peak {20*np.log10(over):+.1f} dBFS, trimming to -1.0")
        x = x * (db(-1.0) / over)
    return np.clip(x, -1.0, 1.0)


def write_wav(name, x):
    path = os.path.join(OUT, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.asarray(x) * 32767).astype("<i2").tobytes())
    print(f"  {name+'.wav':<20} {len(x)/SR:5.2f}s  {os.path.getsize(path)/1024:6.1f} KB")


# ---------------------------------------------------------------- instruments

def kendang(f0=190, dur=0.20, slap=0.7, seed=0):
    """Indonesian hand drum: pitched membrane plus a mid-heavy slap.

    Chosen over a kick precisely because its energy sits in the 200 Hz-2 kHz band
    a phone speaker can actually reproduce."""
    body = sweep(f0, f0 * 0.55, dur, 0.5) * decay(dur, dur * 0.20)
    hit  = bp(noise(dur, seed), 600, 4200) * decay(dur, 0.012, 0.0004)
    ring = np.sin(2 * np.pi * f0 * 2.7 * t(dur)) * decay(dur, 0.03) * 0.25
    return sat(body + hit * slap + ring, 1.8)


def snare(dur=0.16, seed=1):
    tone = (np.sin(2 * np.pi * 195 * t(dur)) + np.sin(2 * np.pi * 278 * t(dur))) * 0.5
    wire = bp(noise(dur, seed), 900, 7500)
    return sat(tone * decay(dur, 0.035) * 0.6 + wire * decay(dur, 0.055, 0.001), 1.5)


def kentongan(dur=0.09, f=1150, seed=2):
    """Split-bamboo slit drum -- the offbeat tick that gives the pulse its swing."""
    woody = np.sin(2 * np.pi * f * t(dur)) * decay(dur, 0.014)
    click = bp(noise(dur, seed), 1800, 6000) * decay(dur, 0.006, 0.0003)
    return woody * 0.7 + click * 0.5


def brass(note, dur, air=0.10, voices=2):
    """Tanjidor horn. Two slightly detuned voices read as a section, not a synth."""
    f = NOTE[note]
    out = np.zeros(n(dur))
    for v in range(voices):
        cents = (v - (voices - 1) / 2) * 7.0
        fv = f * 2 ** (cents / 1200.0)
        out += harm(fv, dur, [(1, 1.0), (2, .62), (3, .44), (4, .27), (5, .16), (6, .09), (7, .05)],
                    vib=0.0035, vib_hz=5.2)
    out /= voices
    out = lp(out, 3400, order=2)
    breath = bp(noise(dur, int(f)), 1500, 5000) * air
    return sat(out + breath, 1.5) * ar(dur, 0.022, min(0.09, dur * 0.5))


def tuba(note, dur):
    f = NOTE[note]
    out = harm(f, dur, [(1, .5), (2, 1.0), (3, .7), (4, .42), (5, .2), (6, .1)])
    return lp(out, 1800) * ar(dur, 0.03, min(0.1, dur * 0.45))


def angklung(note, dur=0.9):
    """Shaken bamboo: inharmonic partials and a woody knock on the attack."""
    f = NOTE[note]
    body = (np.sin(2 * np.pi * f * t(dur)) * decay(dur, dur * 0.34)
            + np.sin(2 * np.pi * f * 2.02 * t(dur)) * decay(dur, dur * 0.20) * .5
            + np.sin(2 * np.pi * f * 2.76 * t(dur)) * decay(dur, dur * 0.10) * .3)
    knock = bp(noise(dur, int(f)), 700, 3500) * decay(dur, 0.008, 0.0004) * 0.4
    shake = bp(noise(dur, int(f) + 7), 2500, 7000) * decay(dur, 0.05) * 0.10
    return body + knock + shake


def suling(note, dur=0.6):
    """Bamboo flute -- mostly fundamental, and mostly breath."""
    f = NOTE[note]
    x = t(dur)
    vib = 1 + 0.008 * np.sin(2 * np.pi * 5.4 * x) * np.linspace(0, 1, len(x))
    tone = np.sin(2 * np.pi * f * np.cumsum(vib) / SR) + 0.18 * np.sin(2 * np.pi * f * 2 * x)
    breath = bp(noise(dur, int(f)), int(f * 1.6), int(f * 4.5)) * 0.22
    return (tone + breath) * ar(dur, 0.05, dur * 0.3)


def crowd(dur, density=170, seed=5, babble=True):
    """A wash plus scattered voice-shaped bursts. The bursts are what stop it
    sounding like plain noise."""
    rng = np.random.default_rng(seed)
    out = bp(noise(dur, seed), 300, 2600) * 0.35
    out *= 1 + 0.25 * np.sin(2 * np.pi * 0.23 * t(dur))       # slow crowd breathing
    if babble:
        for _ in range(int(density * dur)):
            d = rng.uniform(0.06, 0.28)
            v = bp(noise(d, int(rng.integers(1e6))), rng.uniform(350, 900),
                   rng.uniform(1600, 3600)) * ar(d, 0.02, d * 0.5)
            place(out, v, rng.uniform(0, dur), rng.uniform(0.05, 0.22))
    return out


def applause(dur, rate=26, seed=6):
    rng = np.random.default_rng(seed)
    out = np.zeros(n(dur))
    for _ in range(int(rate * dur * 12)):
        d = 0.012
        c = bp(noise(d, int(rng.integers(1e6))), 1400, 7000) * decay(d, 0.003, 0.0002)
        place(out, c, rng.uniform(0, dur - d), rng.uniform(0.2, 1.0))
    return out


# ------------------------------------------------------------------- the cues

def sfx_hop():
    """Cloth push-off plus a low body thump. Short: it fires up to 3x a second."""
    dur = 0.13
    cloth = bp(noise(dur, 11), 500, 3800) * decay(dur, 0.030, 0.001)
    body  = sweep(240, 150, dur, 1.2) * decay(dur, 0.045) * 0.8
    return cloth * 0.8 + body


def sfx_perfect():
    """One asset, twelve pitches: the engine sets playbackRate off the combo
    table in SOUND.md, so the ladder costs a single file."""
    dur = 0.15
    f = NOTE["D5"]
    bell = (np.sin(2 * np.pi * f * t(dur)) * decay(dur, 0.055)
            + np.sin(2 * np.pi * f * 2 * t(dur)) * decay(dur, 0.030) * 0.5
            + np.sin(2 * np.pi * f * 3 * t(dur)) * decay(dur, 0.018) * 0.22)
    spark = bp(noise(dur, 12), 3000, 9000) * decay(dur, 0.008, 0.0003) * 0.3
    return sat(bell, 1.3) + spark


def sfx_land():
    dur = 0.16
    thud = sweep(170, 95, dur, 1.4) * decay(dur, 0.038) * 0.9
    dust = bp(noise(dur, 13), 800, 5200) * decay(dur, 0.045, 0.001) * 0.55
    grit = bp(noise(dur, 14), 2500, 8000) * decay(dur, 0.020, 0.001) * 0.25
    return thud + dust + grit


def sfx_trip():
    """The punishment, and until now completely silent. Downward, dull, and
    mixed hotter than the hop so it cuts through a busy race mix."""
    dur = 0.34
    drag = bp(noise(dur, 15), 260, 2400) * decay(dur, 0.13, 0.004)
    drag *= np.linspace(1.0, 0.35, len(drag))              # scuffing to a stop
    fall = sweep(300, 120, dur * 0.7, 1.6) * decay(dur * 0.7, 0.10) * 0.55
    sour = (np.sin(2 * np.pi * 233 * t(dur)) + np.sin(2 * np.pi * 233 * 1.46 * t(dur))) \
        * decay(dur, 0.09) * 0.30                          # detuned fifth: "wrong"
    out = np.zeros(n(dur))
    place(out, drag, 0); place(out, fall, 0.005); place(out, sour, 0.01)
    return out


def sfx_dud():
    """Tapped during r.lock. Heard you, not yet -- and no reward for mashing."""
    dur = 0.05
    return bp(noise(dur, 16), 400, 1600) * decay(dur, 0.010, 0.0005)


def sfx_tick():
    dur = 0.12
    return kentongan(dur, 900) + np.sin(2 * np.pi * 440 * t(dur)) * decay(dur, 0.05) * .5


def sfx_roll():
    """Kendang roll under the last second of the countdown, accelerating into
    the 160 BPM pulse so the first hop lands on the downbeat."""
    dur = 1.0
    out = np.zeros(n(dur))
    at, gap = 0.0, 0.115
    while at < dur - 0.05:
        place(out, kendang(200, 0.10, 0.55, seed=int(at * 1000)), at, 0.55 + at * 0.45)
        gap *= 0.90                                        # tighten toward the whistle
        at += max(gap, BEAT / 4)
    return out


def sfx_whistle():
    """Pea whistle: two close tones, warbled by the pea at ~26 Hz."""
    dur = 0.42
    x = t(dur)
    warble = 1 + 0.02 * np.sin(2 * np.pi * 26 * x)
    a = np.sin(2 * np.pi * 3180 * np.cumsum(warble) / SR)
    b = np.sin(2 * np.pi * 3960 * np.cumsum(warble) / SR) * 0.5
    air = bp(noise(dur, 17), 2200, 9000) * 0.25
    env = ar(dur, 0.012, 0.06)
    env *= 1 - 0.12 * np.linspace(0, 1, len(env))
    return sat((a + b + air) * env, 1.4)


def sfx_tape():
    dur = 0.9
    snap = bp(noise(0.06, 18), 1200, 9000) * decay(0.06, 0.010, 0.0003)
    flut = bp(noise(0.35, 19), 600, 4000) * decay(0.35, 0.09, 0.003) * 0.35
    out = np.zeros(n(dur))
    place(out, snap, 0); place(out, flut, 0.02)
    place(out, crowd(0.85, 200, 20) * ar(0.85, 0.05, 0.45), 0.04, 0.55)
    place(out, applause(0.85, 30, 21) * ar(0.85, 0.06, 0.4), 0.05, 0.5)
    return out


def sfx_lead():
    """Taking first place. A short crowd lift, deliberately mixed low: it is a
    reaction happening behind the race, not an event in front of it, and it must
    never fight the kendang for the tap grid."""
    dur = 0.85
    out = crowd(dur, 190, 41) * 0.8 + applause(dur, 26, 42) * 0.5
    swell = np.concatenate([np.linspace(0.15, 1.0, n(0.22)) ** 0.6,
                            np.linspace(1.0, 0.10, n(dur) - n(0.22)) ** 1.4])
    return out * swell


def sfx_roar():
    """The win, from the stands. Swells, peaks, settles into chatter."""
    dur = 2.6
    out = crowd(dur, 260, 22) * 0.9
    out += applause(dur, 34, 23) * 0.8
    swell = np.concatenate([np.linspace(0.25, 1.0, n(0.5)) ** 0.7,
                            np.linspace(1.0, 0.55, n(dur) - n(0.5))])
    return out * swell


def sfx_win():
    """Tanjidor fanfare over the roar -- D A D F# A, straight up the pentatonic."""
    dur = 2.4
    out = np.zeros(n(dur))
    for at, note, d, g in [(0.00, "D4", .20, 1.0), (0.16, "A4", .20, 1.0),
                           (0.32, "D5", .30, 1.0), (0.60, "F#5", .22, .95),
                           (0.80, "A5", 1.30, 1.0)]:
        place(out, brass(note, d), at, g * 0.55)
        place(out, tuba("D3" if at < 0.6 else "A2", d), at, 0.30)
    place(out, snare(0.5), 0.80, 0.35)
    for i in range(6):
        place(out, kendang(200, .18), 0.80 + i * BEAT / 2, 0.30)
    place(out, suling("D6", 1.0), 1.05, 0.16)
    place(out, sfx_roar()[:n(dur)] * 0.8, 0.0, 0.5)
    return out


def sfx_lose():
    """Deflating, not punishing -- everyone who finishes still keeps the prize."""
    dur = 1.6
    out = np.zeros(n(dur))
    for at, note, d in [(0.0, "A4", .26), (0.22, "G4", .26), (0.44, "E4", .70)]:
        place(out, brass(note, d, air=.14), at, 0.45)
        place(out, tuba("D3", d), at, 0.22)
    place(out, suling("D4", .8) * np.linspace(1, .2, n(.8)), 0.45, 0.14)
    place(out, crowd(1.2, 90, 24) * ar(1.2, .1, .6), 0.1, 0.22)
    return out


def sfx_prize():
    """Gold shimmer for the reveal: a rising pentatonic sparkle."""
    dur = 1.3
    out = np.zeros(n(dur))
    for i, note in enumerate(["D5", "F#5", "A5", "B5", "D6"]):
        f = NOTE[note]
        d = 0.7
        bell = (np.sin(2 * np.pi * f * t(d)) * decay(d, 0.22)
                + np.sin(2 * np.pi * f * 2.01 * t(d)) * decay(d, 0.11) * .4)
        place(out, bell, i * 0.075, 0.5 - i * 0.05)
    place(out, bp(noise(dur, 25), 4000, 12000) * decay(dur, 0.30, 0.02), 0.0, 0.10)
    return out


def ui(freq, dur=0.08, kind="select"):
    x = t(dur)
    sq = signal.square(2 * np.pi * freq * x, duty=0.5) * 0.5
    sq = lp(sq, 5200)
    env = decay(dur, dur * 0.35, 0.003)
    out = sq * env
    if kind == "confirm":
        out = out * 0.7 + np.sin(2 * np.pi * freq * 1.5 * x) * decay(dur, dur * 0.5) * 0.3
    return out


# ------------------------------------------------------------ the music stems

def stem_pulse():
    """Layer B. The kendang on every quarter IS the tap metronome -- it is the
    loudest thing in the mix on purpose, and nothing else is allowed on the
    quarter grid to compete with it.

    Two bars rather than four: it is a drum pattern whose only variation was the
    fill, and at 160 BPM a race lasting 10-20 s hears it 3-7 times either way.
    Halving it is the cheapest 20 KB on the manifest."""
    out = np.zeros(n(PULSE_BARS * BAR))
    for bar in range(PULSE_BARS):
        for beat in range(4):
            at = bar * BAR + beat * BEAT
            strong = beat in (0, 2)
            place(out, kendang(186 if strong else 205, 0.20, seed=bar * 4 + beat),
                  at, 1.0 if strong else 0.72)
            # offbeat tick, well under the quarter so the grid stays unambiguous
            place(out, kentongan(0.08, 1150 if beat % 2 else 1320), at + BEAT / 2, 0.20)
        place(out, snare(0.16), bar * BAR + BEAT, 0.34)
        place(out, snare(0.16), bar * BAR + 3 * BEAT, 0.34)
    for i in range(3):                                     # fill marking the seam
        place(out, snare(0.13), (PULSE_BARS - 1) * BAR + 3 * BEAT + i * BEAT / 3,
              0.22 + i * 0.06)
    return out


def stem_hook():
    """Layer C. Enters at combo >= 4 -- the music thickens when you are doing
    it right, which is better feedback than any number on screen."""
    E = BEAT / 2
    riff = [                                               # eighths, 8 per bar
        ["D4", None, "F#4", None, "A4", None, "F#4", None],
        ["E4", None, None, "D4", None, "E4", None, None],
        ["F#4", None, "A4", None, "B4", None, "A4", None],
        ["F#4", None, "E4", None, "D4", None, None, None],
    ]
    bass = ["D3", "G3", "A3", "D3"]
    out = np.zeros(n(LOOP))
    for bar, line in enumerate(riff):
        for i, note in enumerate(line):
            if note is None:
                continue
            nxt = next((j for j in range(i + 1, 8) if line[j] is not None), 8)
            place(out, brass(note, min((nxt - i) * E, E * 3.2)), bar * BAR + i * E, 0.5)
        for beat in (0, 2):
            place(out, tuba(bass[bar], BEAT * 0.8), bar * BAR + beat * BEAT, 0.38)
    return out


# The menu tune: an 8-bar march phrase, eighth-note slots, None = hold or rest.
#
# This is an ORIGINAL melody in the 17 Agustus march idiom -- the rising-fourth
# opening, the dotted march tread, the climb to the fifth and the walk back down.
# It is deliberately not "Hari Merdeka": that song is H. Mutahar, 1946, and the
# author died in 2004, so under UU 28/2014 it is in copyright until roughly 2074.
# A paid-traffic campaign using it commercially needs a WAMI/LMKN licence.
#
# If that licence is cleared, swapping the real tune in is this table and the bass
# line under it -- nothing else in the file has to change.
BED_RIFF = [
    ["A4",  None, "A4",  None, "D5",  None, None, None],
    ["D5",  None, "E5",  None, "F#5", None, "E5", None],
    ["D5",  None, None,  None, "A4",  None, "B4", None],
    ["A4",  None, None,  None, None,  None, None, None],
    ["B4",  None, "B4",  None, "D5",  None, "B4", None],
    ["A4",  None, "G4",  None, "F#4", None, None, None],
    ["E4",  None, "F#4", None, "G4",  None, "E4", None],
    ["D4",  None, None,  None, None,  None, None, None],
]
BED_BASS = ["D3", "D3", "A3", "A3", "G3", "D3", "A3", "D3"]
BED_BARS = len(BED_RIFF)
BED_LOOP = BED_BARS * BAR          # 12.0 s -- and 12 divides both 6 and 3


def stem_bed():
    """Layer A, title through picker: the tune, and the only music on the menus.

    Eight bars rather than four because this is a melody the player will hear for
    twenty-odd seconds while they read and type, and a four-bar phrase on a loop
    that short starts to nag. Nothing else plays underneath it now, so its length
    is unconstrained -- though 12 s still divides 6 and 3, which keeps the option
    of layering it open.

    Scored for suling and angklung with the brass well back, and with NO kendang on
    the quarters. That last part is deliberate: the race's kendang is the tap cue,
    and putting a competing pulse on the menus would teach a rhythm to a player who
    has nothing to tap yet."""
    out = np.zeros(n(BED_LOOP))
    E = BEAT / 2
    for bar, line in enumerate(BED_RIFF):
        for i, note in enumerate(line):
            if note is None:
                continue
            nxt = next((j for j in range(i + 1, 8) if line[j] is not None), 8)
            dur = min((nxt - i) * E, E * 4.5)
            at = bar * BAR + i * E
            place(out, suling(note, dur * 1.05), at, 0.50)
            place(out, angklung(note, min(dur * 1.6, BEAT * 2)), at, 0.22)
            # no brass here: at the 0.10 gain it wanted it was inaudible under the
            # suling, but its harmonics still cost the VBR encoder real bytes
        # tuba on 1 and 3 gives the march tread without a tappable pulse
        for beat in (0, 2):
            place(out, tuba(BED_BASS[bar], BEAT * 0.75), bar * BAR + beat * BEAT, 0.26)
        place(out, kentongan(0.08, 1150), bar * BAR, 0.10)    # one soft tick a bar
    return out


def stem_payoff():
    """Layer D. One-shot for the results card, not a loop."""
    dur = 4.0
    out = np.zeros(n(dur))
    for at, note, d in [(0.0, "D4", .34), (0.0, "F#4", .34), (0.0, "A4", .34),
                        (0.375, "A4", .34), (0.375, "D5", .34),
                        (0.75, "B4", .30), (1.125, "A4", .30),
                        (1.5, "F#4", 2.2), (1.5, "D5", 2.2), (1.5, "A5", 2.2)]:
        place(out, brass(note, d), at, 0.34)
    for i in range(10):
        place(out, tuba("D3" if i % 4 < 2 else "A2", BEAT * .7), i * BEAT, 0.26)
        place(out, kendang(186 if i % 2 == 0 else 205, .18), i * BEAT, 0.55)
        place(out, snare(.15), i * BEAT + BEAT / 2, 0.22)
    place(out, suling("D6", 1.6), 1.7, 0.18)
    place(out, crowd(dur, 240, 31), 0, 0.5)
    place(out, applause(dur, 32, 32), 0, 0.45)
    return out


def stem_crowd():
    """Ambience bed for the race. The obvious first thing to replace with a real
    Higgsfield recording -- see SOUND.md."""
    return seamless(lambda d: crowd(d, 150, 40))


# ------------------------------------------------------------------------ main

# One sprite sheet, in this order. 14 files became 1: a short AAC one-shot is
# mostly container overhead, and 14 requests on a paid-traffic page is 14 chances
# to not have arrived yet. The engine plays slices via start(when, offset, dur).
#
# `roar` and `win` are deliberately NOT here. sfx_win() already mixes sfx_roar()
# into itself, and stem_payoff() is the results-card music, so shipping all three
# meant paying for the same crowd three times. Both remain as building blocks.
CUES = {
    "hop": sfx_hop, "perfect": sfx_perfect, "land": sfx_land, "trip": sfx_trip,
    "dud": sfx_dud, "tick": sfx_tick, "roll": sfx_roll, "whistle": sfx_whistle,
    "tape": sfx_tape, "lead": sfx_lead, "lose": sfx_lose, "prize": sfx_prize,
    "ui-select":  lambda: ui(NOTE["F#5"], .07, "select"),
    "ui-confirm": lambda: ui(NOTE["D5"], .10, "confirm"),
    "ui-open":    lambda: ui(NOTE["A4"], .08, "select"),
}

# loops must not be edge-faded: the fade is the click. seamless() handles the wrap.
LOOPS = {"pulse": stem_pulse, "hook": stem_hook, "bed": stem_bed, "crowd": stem_crowd}
ONESHOT_STEMS = {"payoff": stem_payoff}

# The mix, in one place. Beds are matched by RMS because that is what "sits under
# the game" means; one-shots by peak because what matters is whether they cut.
# Mirrors the level table in SOUND.md -- keep the two in step.
LEVELS = {
    "pulse":  ("rms", -20), "hook":   ("rms", -21), "bed":  ("rms", -24),
    "crowd":  ("rms", -26), "payoff": ("rms", -18),
    "hop":    ("peak", -14), "perfect": ("peak", -12), "land": ("peak", -15),
    "trip":   ("peak", -10),          # the punishment has to cut through
    "dud":    ("peak", -26),          # heard you, not yet
    "tick":   ("peak", -12), "roll": ("peak", -12),
    "whistle": ("peak", -8),          # -6 measured piercing on a phone speaker
    "tape":   ("peak", -6), "roar": ("peak", -8), "win": ("peak", -6),
    "lead":   ("peak", -16),          # a reaction behind the race, not in front of it
    "lose":   ("peak", -10), "prize": ("peak", -10),
    "ui-select": ("peak", -16), "ui-confirm": ("peak", -14), "ui-open": ("peak", -16),
}


def emit(name, x, fade=0.004):
    kind, level = LEVELS[name]
    return prepare(name, x, fade=fade, **{kind: level})


def main():
    os.makedirs(OUT, exist_ok=True)
    print(f"{BPM} BPM, beat {BEAT*1000:.1f} ms\n"
          f"melody loop {LOOP:.3f}s = {n(LOOP)} samples, "
          f"drum loop {PULSE_BARS*BAR:.3f}s = {n(PULSE_BARS*BAR)} samples\n")

    print("sprite sheet:")
    parts, sheet, at = [], {}, 0.0
    for name, fn in CUES.items():
        x = emit(name, fn())
        sheet[name] = {"at": round(at, 4), "dur": round(len(x) / SR, 4)}
        print(f"    {name:<12} at {at:6.3f}s  for {len(x)/SR:5.3f}s")
        parts += [x, np.zeros(n(GUARD))]
        at += len(x) / SR + GUARD
    write_wav("sfx", np.concatenate(parts))

    # The exact musical length of each loop, which is NOT the decoded length: AAC
    # pads to whole 1024-sample frames and Chrome does not trim the trailing
    # padding, so a stem decodes 7-14 ms long. Setting loopEnd from
    # buffer.duration therefore drifts the tap grid every loop -- ~85 ms over a
    # race. These come from the tempo instead, which is exact by construction.
    loops = {"pulse": PULSE_BARS * BAR, "bed": BED_LOOP, "crowd": LOOP, "hook": LOOP}

    meta = os.path.join(OUT, os.pardir, "sfx.json")
    with open(meta, "w") as f:
        json.dump({"cues": sheet, "loops": loops}, f, indent=2, sort_keys=True)
    print(f"  {'sfx.json':<20}       {os.path.getsize(meta)/1024:6.1f} KB")
    print(f"    loop lengths: " + ", ".join(f"{k} {v:.3f}s" for k, v in loops.items()) + "\n")

    print("stems:")
    for name, fn in ONESHOT_STEMS.items():
        write_wav(name, emit(name, fn()))
    for name, fn in LOOPS.items():                 # no edge fade: loopStart/loopEnd
        write_wav(name, emit(name, fn(), fade=0))


if __name__ == "__main__":
    main()
