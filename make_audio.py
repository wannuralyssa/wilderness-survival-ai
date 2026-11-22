"""
Synthesizes every sound and music track for Wilderness Survival (no samples, no downloads).
Writes OGG files into assets/audio/. Requires numpy, scipy and ffmpeg (only to regenerate).
"""
import os
import subprocess
import sys
import numpy as np
from scipy.signal import butter, sosfilt

SR = 22050
OUT = sys.argv[1]
rng = np.random.default_rng(7)


# ------------------------------------------------------------------ building blocks
def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def env(n, a=0.005, d=0.1, s=0.0, r=0.05, sus_time=None):
    """ADSR envelope of length n samples."""
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    e = np.zeros(n)
    i = 0
    seg = min(a_n, n)
    e[:seg] = np.linspace(0, 1, seg, endpoint=False) if seg else 0
    i = seg
    seg = min(d_n, n - i)
    e[i:i + seg] = np.linspace(1, s, seg, endpoint=False)
    i += seg
    rest = n - i - r_n
    if rest > 0:
        e[i:i + rest] = s
        i += rest
    if n - i > 0:
        e[i:] = np.linspace(e[i - 1] if i else s, 0, n - i)
    return e


def exp_decay(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def lp(x, fc, order=2):
    return sosfilt(butter(order, min(fc, SR / 2 - 50) / (SR / 2), "low", output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc / (SR / 2), "high", output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo / (SR / 2), min(hi, SR / 2 - 50) / (SR / 2)], "band", output="sos"), x)


def noise(dur):
    return rng.uniform(-1, 1, int(dur * SR))


def brown(dur):
    w = rng.normal(0, 1, int(dur * SR))
    b = np.cumsum(w)
    b = hp(b, 20)
    return b / (np.max(np.abs(b)) + 1e-9)


def glide(f0, f1, dur, shape="sine", curve=1.0):
    n = int(dur * SR)
    k = np.linspace(0, 1, n) ** curve
    f = f0 + (f1 - f0) * k
    ph = 2 * np.pi * np.cumsum(f) / SR
    if shape == "sine":
        return np.sin(ph)
    if shape == "tri":
        return 2 / np.pi * np.arcsin(np.sin(ph))
    if shape == "square":
        return np.sign(np.sin(ph)) * 0.6
    if shape == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1) - 1
    raise ValueError(shape)


def pluck(freq, dur, decay=0.996, bright=0.5):
    """Karplus-Strong plucked string."""
    n = int(dur * SR)
    period = max(2, int(SR / freq))
    buf = rng.uniform(-1, 1, period)
    buf = lp(buf, 1200 + 5000 * bright)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % period]
        nxt = buf[(i + 1) % period]
        buf[i % period] = decay * 0.5 * (buf[i % period] + nxt)
    return out * exp_decay(n, dur * 0.6)


def bell(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    partials = [(1, 1.0, 1.2), (2.0, 0.45, 0.8), (2.76, 0.3, 0.6), (5.4, 0.15, 0.3), (8.9, 0.06, 0.2)]
    out = sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t / d) for r, a, d in partials)
    attack = np.minimum(1, t / 0.004)
    return out * attack


def flute(freq, dur, vib=5.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = freq * (1 + 0.006 * np.sin(2 * np.pi * vib * t) * np.minimum(1, t / 0.25))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)
    x += 0.03 * lp(noise(dur), 3000)          # breath
    return x * env(n, a=0.06, d=0.15, s=0.75, r=0.18)


def pad(freqs, dur, cutoff=1200):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in freqs:
        for det in (-0.25, 0.0, 0.3):
            ph = 2 * np.pi * (f * (1 + det / 100)) * t + rng.uniform(0, 6.28)
            x += 2 * ((ph / (2 * np.pi)) % 1) - 1
    x = lp(x / (len(freqs) * 3), cutoff, order=2)
    return x * env(n, a=dur * 0.3, d=0.1, s=1.0, r=dur * 0.35)


def reverb(x, mix=0.25, room=0.82):
    """Small Schroeder reverb."""
    out = np.zeros(len(x) + int(1.5 * SR))
    src = np.concatenate([x, np.zeros(int(1.5 * SR))])
    wet = np.zeros_like(out)
    for delay_ms, g in ((29.7, room), (37.1, room - 0.02), (41.1, room - 0.04), (43.7, room - 0.06)):
        d = int(delay_ms / 1000 * SR)
        y = np.zeros_like(src)
        for i in range(0, len(src), d):
            seg = src[i:i + d]
            prev = y[i - d:i - d + len(seg)] if i >= d else np.zeros(len(seg))
            y[i:i + len(seg)] = seg + g * prev
        wet += y
    for delay_ms, g in ((5.0, 0.7), (1.7, 0.7)):
        d = int(delay_ms / 1000 * SR)
        y = np.zeros_like(wet)
        for i in range(len(wet)):
            xd = wet[i - d] if i >= d else 0
            yd = y[i - d] if i >= d else 0
            y[i] = -g * wet[i] + xd + g * yd
        wet = y
    wet = lp(wet, 5000) / 4
    out = src * (1 - mix) + wet * mix
    return out


def place(track, sound, start_s, gain=1.0):
    i = int(start_s * SR)
    j = min(len(track), i + len(sound))
    if j > i:
        track[i:j] += sound[:j - i] * gain


def loopify(x, length_n):
    """Fold the tail past length_n back onto the start, so the loop is seamless."""
    out = x[:length_n].copy()
    tail = x[length_n:]
    k = 0
    while len(tail):
        out[:len(tail[:length_n])] += tail[:length_n]
        tail = tail[length_n:]
        k += 1
    return out


def crossfade_loop(x, fade_s=0.5):
    """Make a noise texture loop seamlessly by crossfading its end into its start."""
    f = int(fade_s * SR)
    body = x[:-f].copy()
    ramp = np.linspace(0, 1, f)
    body[:f] = body[:f] * ramp + x[-f:] * (1 - ramp)
    return body


def normalize(x, peak=0.85):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def save(name, x, peak=0.85, quality=4):
    os.makedirs(os.path.dirname(os.path.join(OUT, name)), exist_ok=True)
    x = normalize(x, peak)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    path = os.path.join(OUT, name + ".ogg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1",
                    "-i", "pipe:0", "-c:a", "libvorbis", "-q:a", str(quality), path], input=pcm, check=True)


# ------------------------------------------------------------------ music
def day_theme():
    bpm = 96
    beat = 60 / bpm
    bars = 16
    total = bars * 4 * beat
    track = np.zeros(int((total + 3) * SR))
    # C - Am - F - G (pentatonic folk)
    chords = [(48, [60, 64, 67]), (45, [57, 60, 64]), (41, [53, 57, 60]), (43, [55, 59, 62])]
    arp = [0, 1, 2, 1, 0, 2, 1, 2]
    melody_bars = [
        [(72, 1), (74, 0.5), (76, 0.5), (79, 1), (76, 1)],
        [(76, 1.5), (74, 0.5), (72, 1), (69, 1)],
        [(69, 1), (72, 1), (74, 1), (72, 0.5), (69, 0.5)],
        [(67, 2), (None, 1), (71, 1)],
        [(72, 0.5), (74, 0.5), (76, 1), (79, 1), (81, 1)],
        [(79, 1), (76, 1), (74, 1), (76, 1)],
        [(77, 1.5), (76, 0.5), (74, 1), (72, 1)],
        [(74, 2), (71, 1), (67, 1)],
    ]
    for bar in range(bars):
        root, tones = chords[bar % 4]
        t0 = bar * 4 * beat
        # bass
        for b in (0, 2):
            place(track, pluck(midi(root - 12), beat * 2.2, 0.997, 0.2), t0 + b * beat, 0.55)
        # guitar arpeggio in eighths
        for k, idx in enumerate(arp):
            note = tones[idx] + (12 if k == 5 else 0)
            place(track, pluck(midi(note), beat * 1.6, 0.994, 0.25), t0 + k * beat / 2, 0.24)
        # shaker on the off-beats
        for k in range(8):
            if k % 2 == 1:
                s = hp(noise(0.06), 6000) * exp_decay(int(0.06 * SR), 0.015)
                place(track, s, t0 + k * beat / 2, 0.05)
        # flute melody from bar 4 on (the first 4 bars introduce the guitar)
        if bar >= 4:
            pos = t0
            for note, length in melody_bars[(bar - 4) % 8]:
                if note:
                    place(track, flute(midi(note), length * beat * 0.95), pos, 0.22)
                pos += length * beat
    track = reverb(track, 0.18)
    return loopify(track, int(total * SR))


def night_theme():
    bpm = 66
    beat = 60 / bpm
    bars = 12
    total = bars * 4 * beat
    track = np.zeros(int((total + 6) * SR))
    # Am - F - Dm - E
    chords = [(45, [57, 60, 64]), (41, [53, 57, 60]), (38, [50, 53, 57]), (40, [52, 56, 59])]
    bell_notes = [[76, None, 72, None], [None, 69, None, 72], [74, None, None, 69], [68, None, 71, None]]
    for bar in range(bars):
        root, tones = chords[bar % 4]
        t0 = bar * 4 * beat
        place(track, pad([midi(n) for n in tones], 4 * beat + 1.2, 900), t0, 0.35)
        place(track, pad([midi(root - 12)], 4 * beat + 1.0, 300), t0, 0.35)
        # slow low pulse, like a heartbeat
        for b in (0, 0.35):
            thump = glide(70, 45, 0.25) * exp_decay(int(0.25 * SR), 0.07)
            place(track, thump, t0 + b * beat, 0.35)
        # sparse bells
        for k, note in enumerate(bell_notes[bar % 4]):
            if note and not (bar < 2 and k > 1):
                place(track, bell(midi(note), 3.0), t0 + k * beat, 0.12)
    track = reverb(track, 0.35, 0.86)
    return loopify(track, int(total * SR))


def menu_theme():
    bpm = 78
    beat = 60 / bpm
    bars = 8
    total = bars * 4 * beat
    track = np.zeros(int((total + 4) * SR))
    # G - Em - C - D
    chords = [(43, [55, 59, 62]), (40, [52, 55, 59]), (36, [48, 52, 55]), (38, [50, 54, 57])]
    melody = [[(74, 2), (71, 1), (74, 1)], [(76, 3), (74, 1)], [(72, 1), (71, 1), (69, 2)], [(66, 2), (69, 2)],
              [(74, 1), (76, 1), (79, 2)], [(78, 2), (76, 2)], [(74, 1.5), (72, 0.5), (71, 2)], [(69, 4)]]
    for bar in range(bars):
        root, tones = chords[bar % 4]
        t0 = bar * 4 * beat
        place(track, pad([midi(n) for n in tones], 4 * beat + 1.0, 1100), t0, 0.22)
        place(track, pluck(midi(root - 12), beat * 3.5, 0.998, 0.2), t0, 0.5)
        for k in range(4):
            place(track, pluck(midi(tones[k % 3] + 12), beat * 2, 0.995, 0.5), t0 + k * beat + beat / 2, 0.16)
        pos = t0
        for note, length in melody[bar]:
            place(track, bell(midi(note), length * beat + 1.0), pos, 0.14)
            place(track, flute(midi(note), length * beat * 0.9), pos, 0.1)
            pos += length * beat
    track = reverb(track, 0.3, 0.84)
    return loopify(track, int(total * SR))


# ------------------------------------------------------------------ sound effects
def step(kind):
    n = int(0.09 * SR)
    if kind == "grass":
        x = bp(noise(0.09), 1500, 6000) * exp_decay(n, 0.02) * 0.6
    elif kind == "dirt":
        x = bp(noise(0.09), 400, 3500) * exp_decay(n, 0.025)
        grit = (rng.random(n) < 0.02) * rng.uniform(-1, 1, n)
        x += hp(grit, 2000) * exp_decay(n, 0.03)
    elif kind == "wood":
        n = int(0.14 * SR)
        x = glide(190, 150, 0.14, "tri") * exp_decay(n, 0.03) + bp(noise(0.14), 300, 1800) * exp_decay(n, 0.012) * 0.5
    else:  # mud
        n = int(0.16 * SR)
        x = lp(noise(0.16), 600) * exp_decay(n, 0.05) * 1.6
        x += glide(160, 90, 0.16) * exp_decay(n, 0.04) * 0.5
    return x


def chop():
    out = np.zeros(int(0.5 * SR))
    for t in (0.0, 0.2):
        n = int(0.25 * SR)
        thunk = glide(220, 90, 0.25, "tri") * exp_decay(n, 0.05)
        crack = bp(noise(0.25), 800, 5000) * exp_decay(n, 0.02)
        place(out, thunk + crack * 0.8, t)
    return out


def mine():
    out = np.zeros(int(0.6 * SR))
    for t, f in ((0.0, 1900), (0.18, 2300)):
        n = int(0.35 * SR)
        tt = np.arange(n) / SR
        clink = sum(np.sin(2 * np.pi * f * r * tt) * a for r, a in ((1, 1), (1.53, 0.6), (2.41, 0.35)))
        clink *= exp_decay(n, 0.06)
        grit = bp(noise(0.35), 1000, 4000) * exp_decay(n, 0.015)
        place(out, clink * 0.5 + grit * 0.7, t)
    return out


def eat():
    out = np.zeros(int(0.5 * SR))
    for t in (0.0, 0.13, 0.26):
        n = int(0.08 * SR)
        place(out, bp(noise(0.08), 1500, 7000) * exp_decay(n, 0.018), t + rng.uniform(0, 0.02))
    return out


def drink():
    out = np.zeros(int(0.6 * SR))
    for t, f in ((0.0, 300), (0.16, 380), (0.32, 340)):
        n = int(0.12 * SR)
        place(out, glide(f, f * 2.2, 0.12, curve=0.6) * env(n, 0.005, 0.05, 0.4, 0.05), t, 0.7)
    out += bp(noise(0.6), 600, 3000) * 0.08 * env(len(out), 0.05, 0.2, 0.5, 0.2)
    return out


def swing():
    n = int(0.22 * SR)
    x = noise(0.22)
    # BAND-PASS SWEEPING UPWARDS = WHOOSH
    chunks = 8
    out = np.zeros(n)
    for k in range(chunks):
        a, b = k * n // chunks, (k + 1) * n // chunks
        lo = 500 + 2500 * k / chunks
        out[a:b] = bp(x, lo, lo * 2.2)[a:b]
    return out * np.sin(np.linspace(0, np.pi, n)) ** 1.5


def hit():
    n = int(0.25 * SR)
    thud = glide(140, 55, 0.25) * exp_decay(n, 0.06)
    smack = bp(noise(0.25), 800, 4000) * exp_decay(n, 0.012)
    return thud + smack * 0.9


def wolf_yelp():
    n = int(0.28 * SR)
    f = glide(700, 1150, 0.12, curve=0.5)
    f2 = glide(1150, 600, 0.16)
    x = np.concatenate([f, f2])[:n]
    x = x + 0.4 * np.sin(2 * np.arcsin(np.clip(x, -1, 1)))
    return bp(x, 400, 4000) * env(n, 0.01, 0.1, 0.6, 0.1)


def wolf_die():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = 900 - 550 * (t / t[-1]) ** 0.8
    f *= 1 + 0.02 * np.sin(2 * np.pi * 7 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)
    return bp(x, 300, 4000) * env(n, 0.02, 0.2, 0.6, 0.5)


def wolf_bite():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    growl = lp(noise(0.45), 500) * (0.6 + 0.4 * np.sin(2 * np.pi * 32 * t)) * env(n, 0.03, 0.1, 0.8, 0.15) * 1.8
    snap = hp(noise(0.05), 1500) * exp_decay(int(0.05 * SR), 0.008)
    out = growl
    place(out, snap * 1.2, 0.18)
    return out


def hurt():
    n = int(0.3 * SR)
    x = glide(330, 170, 0.3, "square")
    return lp(x, 1500) * env(n, 0.005, 0.1, 0.5, 0.12)


def build_fire():
    out = np.zeros(int(1.4 * SR))
    n = int(0.6 * SR)
    whoosh = lp(noise(0.6), 900) * np.sin(np.linspace(0, np.pi, n)) ** 2
    place(out, whoosh * 1.2, 0)
    for _ in range(14):
        t = rng.uniform(0.25, 1.3)
        m = int(0.02 * SR)
        place(out, hp(noise(0.02), 1500) * exp_decay(m, 0.004), t, rng.uniform(0.3, 0.8))
    return out


def build_tent():
    out = np.zeros(int(1.0 * SR))
    for t in (0.0, 0.18):
        n = int(0.2 * SR)
        place(out, bp(noise(0.2), 200, 1500) * np.sin(np.linspace(0, np.pi, n)), t, 0.9)
    for t in (0.5, 0.72):
        n = int(0.15 * SR)
        place(out, glide(260, 200, 0.15, "tri") * exp_decay(n, 0.03), t)
    return out


def relight():
    n = int(0.5 * SR)
    return lp(noise(0.5), 1200) * np.sin(np.linspace(0, np.pi, n)) ** 2 + 0.3 * glide(300, 600, 0.5) * exp_decay(n, 0.2)


def extinguish():
    n = int(1.3 * SR)
    return hp(noise(1.3), 2500) * env(n, 0.01, 0.2, 0.5, 0.9)


def rest():
    out = np.zeros(int(1.4 * SR))
    for k, note in enumerate((72, 76, 79)):
        place(out, bell(midi(note), 1.0), k * 0.14, 0.6)
    return out


def fail():
    out = np.zeros(int(0.3 * SR))
    for k, f in enumerate((330, 247)):
        n = int(0.12 * SR)
        place(out, glide(f, f, 0.12, "tri") * env(n, 0.005, 0.05, 0.6, 0.04), k * 0.12)
    return out


def menu_move():
    n = int(0.05 * SR)
    return glide(1200, 1200, 0.05, "tri") * exp_decay(n, 0.012)


def menu_select():
    out = np.zeros(int(0.4 * SR))
    for k, note in enumerate((76, 83)):
        place(out, bell(midi(note), 0.3), k * 0.08)
    return out


def birds():
    out = np.zeros(int(1.8 * SR))
    for t in (0.0, 0.18, 0.7, 0.85, 1.0, 1.4):
        f0 = rng.uniform(2800, 3800)
        n = int(0.08 * SR)
        place(out, glide(f0, f0 * rng.uniform(1.2, 1.5), 0.08, curve=0.5) * env(n, 0.005, 0.03, 0.5, 0.03), t, 0.5)
    return reverb(out, 0.2)


def howl():
    dur = 2.6
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = np.interp(t, [0, 0.5, 1.6, 2.6], [380, 620, 600, 420])
    f *= 1 + 0.012 * np.sin(2 * np.pi * 5.5 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)
    x = x * env(n, 0.4, 0.3, 0.8, 0.9)
    return reverb(bp(x, 250, 3000), 0.45, 0.88)


def thunder():
    dur = 3.0
    n = int(dur * SR)
    x = lp(brown(dur), 300) * 3
    x *= env(n, 0.05, 0.4, 0.5, 2.0)
    crack = hp(noise(0.3), 800) * exp_decay(int(0.3 * SR), 0.06)
    place(x, crack * 0.5, 0.02)
    return x


def wind_gust():
    dur = 2.5
    n = int(dur * SR)
    x = noise(dur)
    out = np.zeros(n)
    chunks = 20
    for k in range(chunks):
        a, b = k * n // chunks, (k + 1) * n // chunks
        c = 400 + 700 * np.sin(np.pi * k / chunks)
        out[a:b] = bp(x, c * 0.7, c * 1.4)[a:b]
    return out * np.sin(np.linspace(0, np.pi, n)) ** 1.5


def game_over():
    out = np.zeros(int(3.0 * SR))
    for k, note in enumerate((69, 65, 62, 57)):
        place(out, pluck(midi(note), 1.8, 0.997, 0.3), k * 0.32, 0.7)
        place(out, pad([midi(note)], 1.6, 700), k * 0.32, 0.25)
    return reverb(out, 0.35)


# ------------------------------------------------------------------ ambient loops
def loop_rain():
    dur = 6.5
    x = hp(noise(dur), 1200) * 0.35 + lp(noise(dur), 900) * 0.25
    for _ in range(320):
        t = rng.uniform(0, dur - 0.05)
        m = int(0.015 * SR)
        place(x, hp(noise(0.015), 3000) * exp_decay(m, 0.003), t, rng.uniform(0.2, 0.6))
    return crossfade_loop(x, 0.5)


def loop_wind():
    dur = 8.5
    n = int(dur * SR)
    x = noise(dur)
    out = np.zeros(n)
    chunks = 60
    for k in range(chunks):
        a, b = k * n // chunks, (k + 1) * n // chunks
        c = 350 + 250 * np.sin(2 * np.pi * k / chunks) + 120 * np.sin(2 * np.pi * 3 * k / chunks)
        out[a:b] = bp(x, c * 0.7, c * 1.5)[a:b]
    out = lp(out, 2500)
    return crossfade_loop(out, 0.6)


def loop_fire():
    dur = 5.5
    x = lp(brown(dur), 400) * 0.6
    for _ in range(90):
        t = rng.uniform(0, dur - 0.05)
        m = int(0.025 * SR)
        pop = bp(noise(0.025), 1500, 7000) * exp_decay(m, rng.uniform(0.002, 0.008))
        place(x, pop, t, rng.uniform(0.2, 1.0))
    return crossfade_loop(x, 0.4)


if __name__ == "__main__":
    music = {"music_day": day_theme, "music_night": night_theme, "music_menu": menu_theme}
    sfx = {
        "step_grass": lambda: step("grass"), "step_dirt": lambda: step("dirt"),
        "step_wood": lambda: step("wood"), "step_mud": lambda: step("mud"),
        "chop": chop, "mine": mine, "eat": eat, "drink": drink, "swing": swing, "hit": hit,
        "wolf_yelp": wolf_yelp, "wolf_die": wolf_die, "wolf_bite": wolf_bite, "hurt": hurt,
        "build_fire": build_fire, "build_tent": build_tent, "relight": relight, "extinguish": extinguish,
        "rest": rest, "fail": fail, "menu_move": menu_move, "menu_select": menu_select,
        "birds": birds, "howl": howl, "thunder": thunder, "wind_gust": wind_gust, "game_over": game_over,
    }
    loops = {"loop_rain": loop_rain, "loop_wind": loop_wind, "loop_fire": loop_fire}
    for name, fn in sfx.items():
        save(f"sfx/{name}", fn(), 0.85)
        print("sfx", name)
    for name, fn in loops.items():
        save(f"loops/{name}", fn(), 0.7)
        print("loop", name)
    for name, fn in music.items():
        save(f"music/{name}", fn(), 0.8, quality=5)
        print("music", name)
