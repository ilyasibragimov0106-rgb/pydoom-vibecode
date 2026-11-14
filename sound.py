"""Procedural 8-bit style sounds and a looping metal riff - all numpy, no files.

Everything is synthesized at startup: noise bursts with exponential envelopes
for gunfire/footsteps, swept saw waves for monster growls, sine blips for
pickups, plus a chugging bass riff played in a loop (M toggles it).
"""
import numpy as np
import pygame

RATE = 22050


def _t(dur):
    return np.arange(int(RATE * dur), dtype=np.float32) / RATE


def _env(n, attack=0.005, decay=6.0):
    x = np.linspace(0, 1, max(n, 1), dtype=np.float32)
    e = np.minimum(x / max(attack, 1e-4), 1.0) * np.exp(-decay * x)
    return e.astype(np.float32)


def _saw(f, dur, sweep=1.0):
    tt = _t(dur)
    freq = f * (sweep ** tt)
    ph = (tt * freq) % 1.0
    return (2 * ph - 1).astype(np.float32)


def _sine(f, dur, sweep_to=None):
    tt = _t(dur)
    if sweep_to:
        freq = np.linspace(f, sweep_to, tt.size, dtype=np.float32)
        ph = np.cumsum(freq) / RATE
    else:
        ph = tt * f
    return np.sin(2 * np.pi * ph).astype(np.float32)


def _noise(dur, seed=7):
    rng = np.random.default_rng(seed)
    return rng.uniform(-1, 1, int(RATE * dur)).astype(np.float32)


def _lp(a, k=4):
    if k <= 1:
        return a
    ker = np.ones(k, np.float32) / k
    return np.convolve(a, ker, 'same').astype(np.float32)


def _mix(*parts):
    """parts: (samples, offset_seconds) - overlay them onto one track."""
    n = max(len(arr) + int(off * RATE) for arr, off in parts)
    out = np.zeros(n, np.float32)
    for arr, off in parts:
        i = int(off * RATE)
        out[i:i + len(arr)] += arr
    return out


def _snd(mix, gain=0.9):
    a = np.asarray(mix, np.float32)
    m = float(np.max(np.abs(a))) or 1.0
    a = a / m * gain
    data = (a * 32000).astype(np.int16)
    try:
        ch = pygame.mixer.get_init()[2]
    except Exception:
        ch = 1
    if ch == 2:
        data = np.column_stack([data, data])
    return pygame.sndarray.make_sound(np.ascontiguousarray(data))


def _build_sounds():
    s = {}

    # --- weapons ---------------------------------------------------------
    crack = _lp(_noise(0.05, 11), 2) * _env(int(RATE * 0.05), 0.001, 30)
    body = _lp(_noise(0.16, 12), 6) * _env(int(RATE * 0.16), 0.001, 22)
    thump = _sine(110, 0.12, sweep_to=55) * _env(int(RATE * 0.12), 0.001, 26)
    s['pistol'] = _snd(_mix((crack, 0), (body, 0.005), (thump, 0)), 0.85)

    boom = _lp(_noise(0.30, 21), 9) * _env(int(RATE * 0.30), 0.001, 14)
    thump2 = _sine(90, 0.22, sweep_to=45) * _env(int(RATE * 0.22), 0.001, 16)
    pump1 = _lp(_noise(0.03, 22), 3) * _env(int(RATE * 0.03), 0.001, 60)
    s['shotgun'] = _snd(_mix((boom, 0), (thump2, 0), (pump1, 0.32), (pump1 * 0.8, 0.42)), 0.95)

    s['empty'] = _snd(_lp(_noise(0.03, 31), 3) * _env(int(RATE * 0.03), 0.001, 50), 0.5)
    click = _lp(_noise(0.025, 32), 3) * _env(int(RATE * 0.025), 0.001, 55)
    s['switch_w'] = _snd(_mix((click, 0), (click * 0.8, 0.09)), 0.6)

    # --- player ------------------------------------------------------------
    st = _lp(_noise(0.07, 41), 8) * _env(int(RATE * 0.07), 0.002, 30)
    s['step1'] = _snd(st, 0.35)
    s['step2'] = _snd(_lp(_noise(0.07, 42), 6) * _env(int(RATE * 0.07), 0.002, 26), 0.32)

    b1 = _sine(660, 0.06) * _env(int(RATE * 0.06), 0.004, 18)
    b2 = _sine(990, 0.08) * _env(int(RATE * 0.08), 0.004, 14)
    s['pickup'] = _snd(_mix((b1, 0), (b2, 0.06)), 0.6)

    pp = (_sine(150, 0.20, sweep_to=80) * _env(int(RATE * 0.20), 0.004, 14)
          + _lp(_noise(0.20, 51), 10) * _env(int(RATE * 0.20), 0.002, 18) * 0.4)
    s['player_pain'] = _snd(pp, 0.7)
    pd = (_sine(180, 0.70, sweep_to=45) * _env(int(RATE * 0.70), 0.005, 6)
          + _lp(_noise(0.70, 52), 8) * _env(int(RATE * 0.70), 0.002, 7) * 0.5)
    s['player_die'] = _snd(pd, 0.8)

    # --- monsters ------------------------------------------------------------
    n45 = int(RATE * 0.45)
    s['imp_sight'] = _snd(_saw(120, 0.45, sweep=0.55) * _env(n45, 0.01, 7)
                          + _lp(_noise(0.45, 61), 6) * _env(n45, 0.01, 8) * 0.3, 0.7)
    s['imp_pain'] = _snd(_saw(160, 0.18, sweep=0.7)
                         * _env(int(RATE * 0.18), 0.008, 12), 0.6)
    n75 = int(RATE * 0.75)
    s['imp_die'] = _snd(_saw(150, 0.75, sweep=0.25) * _env(n75, 0.01, 5)
                        + _lp(_noise(0.75, 62), 6) * _env(n75, 0.01, 6) * 0.35, 0.8)
    s['sold_sight'] = _snd(_saw(190, 0.22, sweep=0.6)
                           * _env(int(RATE * 0.22), 0.01, 12), 0.65)
    s['sold_pain'] = _snd(_saw(210, 0.15, sweep=0.7)
                          * _env(int(RATE * 0.15), 0.008, 14), 0.6)
    n60 = int(RATE * 0.6)
    s['sold_die'] = _snd(_saw(170, 0.60, sweep=0.3) * _env(n60, 0.01, 6)
                         + _lp(_noise(0.60, 71), 6) * _env(n60, 0.01, 7) * 0.3, 0.75)

    ecrack = _lp(_noise(0.05, 81), 3) * _env(int(RATE * 0.05), 0.001, 28)
    ebody = _lp(_noise(0.14, 82), 8) * _env(int(RATE * 0.14), 0.001, 20)
    s['enemy_shot'] = _snd(_mix((ecrack, 0), (ebody, 0.004)), 0.5)

    # --- projectiles / misc ---------------------------------------------------
    whoosh = _lp(_noise(0.35, 91), 4) * np.linspace(0.1, 1, int(RATE * 0.35), dtype=np.float32) ** 2
    s['fireball'] = _snd(whoosh, 0.55)
    n45e = int(RATE * 0.45)
    s['explosion'] = _snd(_mix((_lp(_noise(0.45, 92), 7) * _env(n45e, 0.001, 10), 0),
                               (_sine(70, 0.40, sweep_to=35) * _env(int(RATE * 0.40), 0.001, 9), 0)), 0.9)
    s['scratch'] = _snd(_lp(_noise(0.12, 93), 3) * _env(int(RATE * 0.12), 0.002, 20), 0.6)

    env12 = _env(int(RATE * 0.12), 0.004, 12)
    env20 = _env(int(RATE * 0.20), 0.004, 9)
    s['exit'] = _snd(_mix((_sine(523, 0.12) * env12, 0),
                          (_sine(659, 0.12) * env12, 0.12),
                          (_sine(784, 0.20) * env20, 0.24)), 0.6)
    s['menu_blip'] = _snd(_sine(440, 0.05) * _env(int(RATE * 0.05), 0.004, 25), 0.5)
    env8 = _env(int(RATE * 0.08), 0.004, 14)
    s['cheat'] = _snd(_mix((_sine(660, 0.08) * env8, 0),
                           (_sine(880, 0.08) * env8, 0.08),
                           (_sine(1100, 0.14) * _env(int(RATE * 0.14), 0.004, 10), 0.16)), 0.6)

    # --- chainsaw / plasma / cyberdemon ---------------------------------------
    n12 = int(RATE * 0.12)
    motor = (_lp(_saw(72, 0.12), 5) * _env(n12, 0.01, 3)
             + _lp(_noise(0.12, 96), 6) * _env(n12, 0.01, 4) * 0.3)
    s['saw'] = _snd(motor, 0.4)
    hit_sq = _lp(_noise(0.10, 97), 3) * _env(int(RATE * 0.10), 0.002, 22)
    s['saw_hit'] = _snd(_mix((motor, 0), (hit_sq, 0.02),
                             (_sine(90, 0.10, sweep_to=50)
                              * _env(int(RATE * 0.10), 0.002, 18) * 0.6, 0)), 0.65)

    zap = _sine(1150, 0.16, sweep_to=190) * _env(int(RATE * 0.16), 0.002, 16)
    hum = _saw(620, 0.14, sweep=0.35) * _env(int(RATE * 0.14), 0.002, 20) * 0.35
    s['plasma'] = _snd(_mix((zap, 0), (hum, 0.01)), 0.6)
    pzap = _sine(700, 0.10, sweep_to=140) * _env(int(RATE * 0.10), 0.002, 22)
    s['plasma_hit'] = _snd(_mix((pzap, 0),
                                (_lp(_noise(0.08, 95), 4)
                                 * _env(int(RATE * 0.08), 0.002, 26) * 0.5, 0)), 0.5)

    n90 = int(RATE * 0.9)
    s['cyber_sight'] = _snd(_mix((_saw(64, 0.9, sweep=0.55) * _env(n90, 0.02, 5), 0),
                                 (_lp(_noise(0.9, 98), 5) * _env(n90, 0.02, 6) * 0.4, 0)), 0.9)
    s['cyber_pain'] = _snd(_saw(92, 0.28, sweep=0.65)
                           * _env(int(RATE * 0.28), 0.01, 10), 0.75)
    n11 = int(RATE * 1.1)
    s['cyber_die'] = _snd(_mix((_saw(78, 1.1, sweep=0.2) * _env(n11, 0.02, 4), 0),
                               (_lp(_noise(1.1, 99), 6) * _env(n11, 0.02, 4) * 0.5, 0),
                               (_sine(50, 1.0, sweep_to=28)
                                * _env(int(RATE * 1.0), 0.01, 5) * 0.8, 0)), 0.95)
    rk = _lp(_noise(0.4, 105), 5) * np.linspace(0.15, 1, int(RATE * 0.4),
                                                dtype=np.float32) ** 2
    s['rocket'] = _snd(_mix((rk, 0),
                            (_sine(60, 0.3, sweep_to=32)
                             * _env(int(RATE * 0.3), 0.01, 8) * 0.7, 0)), 0.7)
    return s


def _build_music():
    """Chugging saw-bass riff in the spirit of classic doom metal, looped."""
    bpm = 140
    step = 60 / bpm / 4                      # 16th note length
    phrase = [0, 0, 12, 0, 0, 10, 0, 0, 8, 0, 0, 6, 0, 6, 7, 8]
    bars = phrase * 4
    step_s = int(step * RATE)
    n_total = len(bars) * step_s + RATE // 2
    out = np.zeros(n_total, np.float32)
    base = 82.41                             # E2
    for i, semi in enumerate(bars):
        f = base * (2 ** (semi / 12))
        dur = step * 0.92
        nn = int(dur * RATE)
        note = _saw(f, dur) * _env(nn, 0.004, 9)
        acc = 1.0 if i % 4 == 0 else 0.72
        j = i * step_s
        out[j:j + nn] += note * acc * 0.5
        if i % 4 == 0:                        # kick on the beat
            kn = _sine(120, 0.10, sweep_to=45) * _env(int(0.10 * RATE), 0.001, 16)
            out[j:j + len(kn)] += kn * 0.9
        if i % 2 == 1:                        # hat ticks
            hn = _lp(_noise(0.03, i), 2) * _env(int(0.03 * RATE), 0.001, 40)
            out[j:j + len(hn)] += hn * 0.25
    return _snd(out, 0.8)


class SoundManager:
    """Plays the generated sounds; degrades to a silent stub without audio."""

    def __init__(self):
        self.ok = False
        self.sounds = {}
        self.music = None
        self.music_chan = None
        self.music_on = True
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(RATE, -16, 1, 512)
            self.ok = True
        except Exception as exc:              # no audio device - stay silent
            print("audio disabled:", exc)
            return
        self.sounds = _build_sounds()
        try:
            self.music = _build_music()
        except Exception as exc:
            print("music disabled:", exc)
            self.music = None

    def play(self, name, vol=1.0):
        if not self.ok:
            return
        snd = self.sounds.get(name)
        if snd is not None:
            snd.set_volume(max(0.0, min(1.0, vol)))
            snd.play()

    def start_music(self):
        if self.ok and self.music_on and self.music is not None:
            if self.music_chan is None or not self.music_chan.get_busy():
                self.music_chan = self.music.play(loops=-1)
                if self.music_chan is not None:
                    self.music_chan.set_volume(0.3)

    def stop_music(self):
        if self.music_chan is not None:
            self.music_chan.stop()
            self.music_chan = None

    def toggle_music(self):
        self.music_on = not self.music_on
        if self.music_on:
            self.start_music()
        else:
            self.stop_music()
