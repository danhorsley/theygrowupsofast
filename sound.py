# sound.py — procedural audio for Dissip8
# All sounds generated from code — works in pygbag (no numpy required).
# Pentatonic major scale so nothing sounds discordant.
# Uses numpy if available, falls back to pure Python array module.

import math
import array as pyarray

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
import pygame

# C major pentatonic: C D E G A (+ octave C)
PENTATONIC = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25]
SAMPLE_RATE = 44100


def _init_mixer():
    """Ensure mixer is initialized. Large buffer for browser compatibility."""
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=4096)
        except Exception:
            try:
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=8192)
            except Exception:
                pass


def _pure_tone(freq, duration, volume, wave, fade_out):
    """Generate tone using pure Python (no numpy). Slower but works everywhere."""
    n = int(SAMPLE_RATE * duration)
    TWO_PI = 2.0 * math.pi
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        if wave == 'sine':
            v = math.sin(TWO_PI * freq * t)
        elif wave == 'square':
            v = 1.0 if math.sin(TWO_PI * freq * t) >= 0 else -1.0
            v *= 0.6
        elif wave == 'triangle':
            phase = t * freq - math.floor(t * freq + 0.5)
            v = 2.0 * abs(2.0 * phase) - 1.0
        elif wave == 'soft':
            v = (math.sin(TWO_PI * freq * t) * 0.8 +
                 math.sin(TWO_PI * 2 * freq * t) * 0.15 +
                 math.sin(TWO_PI * 3 * freq * t) * 0.05)
        else:
            v = math.sin(TWO_PI * freq * t)
        samples.append(v)
    # fade out
    fade_n = int(SAMPLE_RATE * fade_out)
    if fade_n > 0 and fade_n < n:
        for i in range(fade_n):
            samples[n - fade_n + i] *= 1.0 - i / fade_n
    # fade in
    fade_in = min(int(SAMPLE_RATE * 0.005), n)
    for i in range(fade_in):
        samples[i] *= i / fade_in
    # convert to 16-bit mono
    buf = pyarray.array('h')
    for s in samples:
        val = int(s * volume * 32767)
        val = max(-32767, min(32767, val))
        buf.append(val)
    return pygame.mixer.Sound(buffer=buf.tobytes())


def create_tone(freq, duration=0.1, volume=0.3, wave='sine', fade_out=0.02):
    """Generate a single tone as a pygame Sound. Works with or without numpy."""
    if not HAS_NUMPY:
        return _pure_tone(freq, duration, volume, wave, fade_out)
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False)

    if wave == 'sine':
        w = np.sin(2 * np.pi * freq * t)
    elif wave == 'square':
        w = np.sign(np.sin(2 * np.pi * freq * t)) * 0.6
    elif wave == 'triangle':
        w = 2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1
    elif wave == 'soft':
        w = np.sin(2 * np.pi * freq * t) * 0.8 + np.sin(4 * np.pi * freq * t) * 0.15 + np.sin(6 * np.pi * freq * t) * 0.05
    else:
        w = np.sin(2 * np.pi * freq * t)

    fade_samples = int(SAMPLE_RATE * fade_out)
    if fade_samples > 0 and fade_samples < n:
        w[-fade_samples:] *= np.linspace(1, 0, fade_samples)

    fade_in = min(int(SAMPLE_RATE * 0.005), n)
    if fade_in > 0:
        w[:fade_in] *= np.linspace(0, 1, fade_in)

    audio = (w * volume * 32767).astype(np.int16)
    stereo = np.column_stack((audio, audio))
    return pygame.mixer.Sound(buffer=stereo.tobytes())


def create_chord(freqs, duration=0.15, volume=0.2, wave='soft'):
    """Generate a chord (multiple frequencies)."""
    if not HAS_NUMPY:
        # pure python fallback
        n = int(SAMPLE_RATE * duration)
        TWO_PI = 2.0 * math.pi
        buf = pyarray.array('h')
        nf = len(freqs)
        fade_n = int(SAMPLE_RATE * 0.03)
        for i in range(n):
            t = i / SAMPLE_RATE
            v = sum(math.sin(TWO_PI * f * t) for f in freqs) / nf
            if fade_n > 0 and i >= n - fade_n:
                v *= 1.0 - (i - (n - fade_n)) / fade_n
            val = int(v * volume * 32767)
            val = max(-32767, min(32767, val))
            buf.append(val)  # mono
        return pygame.mixer.Sound(buffer=buf.tobytes())
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False)
    w = np.zeros(n)
    for freq in freqs:
        w += np.sin(2 * np.pi * freq * t)
    w /= len(freqs)
    fade_samples = int(SAMPLE_RATE * 0.03)
    if fade_samples > 0 and fade_samples < n:
        w[-fade_samples:] *= np.linspace(1, 0, fade_samples)
    fade_in = min(int(SAMPLE_RATE * 0.005), n)
    if fade_in > 0:
        w[:fade_in] *= np.linspace(0, 1, fade_in)
    audio = (w * volume * 32767).astype(np.int16)
    stereo = np.column_stack((audio, audio))
    return pygame.mixer.Sound(buffer=stereo.tobytes())


def create_sweep(freq_start, freq_end, duration=0.15, volume=0.25, wave='sine'):
    """Frequency sweep (ascending or descending)."""
    if not HAS_NUMPY:
        n = int(SAMPLE_RATE * duration)
        TWO_PI = 2.0 * math.pi
        buf = pyarray.array('h')
        fade_n = int(SAMPLE_RATE * 0.02)
        for i in range(n):
            t = i / SAMPLE_RATE
            freq = freq_start + (freq_end - freq_start) * i / n
            v = math.sin(TWO_PI * freq * t)
            if fade_n > 0 and i >= n - fade_n:
                v *= 1.0 - (i - (n - fade_n)) / fade_n
            val = int(v * volume * 32767)
            val = max(-32767, min(32767, val))
            buf.append(val)  # mono
        return pygame.mixer.Sound(buffer=buf.tobytes())
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False)
    freqs = np.linspace(freq_start, freq_end, n)
    w = np.sin(2 * np.pi * freqs * t)
    fade_samples = int(SAMPLE_RATE * 0.02)
    if fade_samples > 0 and fade_samples < n:
        w[-fade_samples:] *= np.linspace(1, 0, fade_samples)
    audio = (w * volume * 32767).astype(np.int16)
    stereo = np.column_stack((audio, audio))
    return pygame.mixer.Sound(buffer=stereo.tobytes())


def _build_arpeggio(notes, note_dur=0.12, volume=0.25, chord_freqs=None, chord_dur=0.3):
    """Build an arpeggio from a list of frequencies. Pure Python compatible."""
    TWO_PI = 2.0 * math.pi
    buf = pyarray.array('h')
    for freq in notes:
        if freq <= 0:
            continue
        n = int(SAMPLE_RATE * note_dur)
        fade = int(SAMPLE_RATE * 0.02)
        for i in range(n):
            t = i / SAMPLE_RATE
            v = math.sin(TWO_PI * freq * t) * volume
            if fade > 0 and i >= n - fade:
                v *= 1.0 - (i - (n - fade)) / fade
            val = int(v * 32767)
            val = max(-32767, min(32767, val))
            buf.append(val)  # mono
    # optional sustain chord at end
    if chord_freqs:
        cn = int(SAMPLE_RATE * chord_dur)
        nf = len(chord_freqs)
        fade_c = int(SAMPLE_RATE * 0.08)
        for i in range(cn):
            t = i / SAMPLE_RATE
            v = sum(math.sin(TWO_PI * f * t) for f in chord_freqs) / nf * volume * 0.8
            if fade_c > 0 and i >= cn - fade_c:
                v *= 1.0 - (i - (cn - fade_c)) / fade_c
            val = int(v * 32767)
            val = max(-32767, min(32767, val))
            buf.append(val)  # mono
    return pygame.mixer.Sound(buffer=buf.tobytes())


class GameSounds:
    """Pre-generated sound pool for all game events.
    Lazy init: sounds are built on first play() call, not on construction.
    This ensures browser audio context is created after user interaction."""

    def __init__(self):
        self.enabled = True
        self.available = True
        self._initialized = False
        self._last_play_tick = 0
        self._min_gap_ms = 180  # throttle: max ~5 sounds per second

    def _ensure_init(self):
        if not self._initialized:
            self._initialized = True
            try:
                _init_mixer()
                # limit channels to prevent overlap distortion
                pygame.mixer.set_num_channels(4)
                self._build_sounds()
            except Exception:
                self.available = False
                self.enabled = False

    def _can_play(self):
        """Throttle sound playback to prevent browser audio clipping."""
        now = pygame.time.get_ticks()
        if now - self._last_play_tick < self._min_gap_ms:
            return False
        self._last_play_tick = now
        return True

    def _build_sounds(self):
        # consume: pentatonic notes — long enough to hear the pitch
        self.consume = [create_tone(f, 0.1, 0.08, 'soft') for f in PENTATONIC]
        self.consume_idx = 0

        # dissolve: gentle descending tone (this one sounded good, keep similar)
        self.dissolve = create_sweep(440, 220, 0.12, 0.08)

        # replicate: bright chord
        self.replicate = create_chord([329.63, 392.00, 523.25], 0.12, 0.06, 'soft')

        # turn: short but audible blip
        self.turn = create_tone(600, 0.06, 0.06, 'soft')

        # reverse: descending blip
        self.reverse = create_sweep(500, 300, 0.08, 0.08)

        # teleport: ethereal sweep up
        self.teleport = create_sweep(300, 800, 0.12, 0.08, 'sine')

        # level complete: ascending arpeggio
        self.level_complete = _build_arpeggio([261.63, 329.63, 392.00, 523.25], 0.15, 0.12)

        # perfect: arpeggio + sustained chord
        self.perfect = _build_arpeggio([261.63, 329.63, 392.00, 523.25, 0], 0.15, 0.12,
                                        chord_freqs=[261.63, 329.63, 523.25], chord_dur=0.3)

        # fail: sad descending pair
        self.fail = _build_arpeggio([293.66, 220.0], 0.2, 0.12)

        # button click: tiny blip
        self.click = create_tone(800, 0.04, 0.05, 'soft')

        # start sim: gentle rising tone
        self.start = create_sweep(300, 500, 0.1, 0.08)

    def play_consume(self):
        if not self.enabled:
            return
        self._ensure_init()
        if not self.available or not self._can_play():
            return
        self.consume[self.consume_idx % len(self.consume)].play()
        self.consume_idx += 1

    def play_dissolve(self):
        if not self.enabled:
            return
        self._ensure_init()
        if self.available and self._can_play():
            self.dissolve.play()

    def play_replicate(self):
        if not self.enabled:
            return
        self._ensure_init()
        if self.available and self._can_play():
            self.replicate.play()

    def play_turn(self):
        if not self.enabled:
            return
        self._ensure_init()
        if self.available and self._can_play():
            self.turn.play()

    def play_reverse(self):
        if not self.enabled:
            return
        self._ensure_init()
        if self.available and self._can_play():
            self.reverse.play()

    def play_teleport(self):
        if not self.enabled:
            return
        self._ensure_init()
        if self.available:
            self.teleport.play()

    def play_level_complete(self):
        if not self.enabled:
            return
        self._ensure_init()
        if self.available:
            self.level_complete.play()

    def play_perfect(self):
        if not self.enabled:
            return
        self._ensure_init()
        if self.available:
            self.perfect.play()

    def play_fail(self):
        if not self.enabled:
            return
        self._ensure_init()
        if self.available:
            self.fail.play()

    def play_click(self):
        if not self.enabled:
            return
        self._ensure_init()
        if self.available:
            self.click.play()

    def play_start(self):
        if not self.enabled:
            return
        self._ensure_init()
        if self.available:
            self.start.play()
