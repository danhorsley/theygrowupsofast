# sound.py — procedural audio for Replic8
# All sounds generated from code using numpy + pygame.mixer.
# Pentatonic major scale so nothing sounds discordant.
# No external audio files needed — works in pygbag.

import numpy as np
import pygame

# C major pentatonic: C D E G A (+ octave C)
PENTATONIC = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25]
SAMPLE_RATE = 44100


def _init_mixer():
    """Ensure mixer is initialized."""
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)


def create_tone(freq, duration=0.1, volume=0.3, wave='sine', fade_out=0.02):
    """Generate a single tone as a pygame Sound."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False)

    if wave == 'sine':
        w = np.sin(2 * np.pi * freq * t)
    elif wave == 'square':
        w = np.sign(np.sin(2 * np.pi * freq * t)) * 0.6
    elif wave == 'triangle':
        w = 2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1
    elif wave == 'soft':
        # sine with slight harmonics for warmth
        w = np.sin(2 * np.pi * freq * t) * 0.8 + np.sin(4 * np.pi * freq * t) * 0.15 + np.sin(6 * np.pi * freq * t) * 0.05
    else:
        w = np.sin(2 * np.pi * freq * t)

    # fade out to avoid clicks
    fade_samples = int(SAMPLE_RATE * fade_out)
    if fade_samples > 0 and fade_samples < n:
        w[-fade_samples:] *= np.linspace(1, 0, fade_samples)

    # fade in (tiny, just to avoid click)
    fade_in = min(int(SAMPLE_RATE * 0.005), n)
    if fade_in > 0:
        w[:fade_in] *= np.linspace(0, 1, fade_in)

    audio = (w * volume * 32767).astype(np.int16)
    stereo = np.column_stack((audio, audio))
    return pygame.mixer.Sound(buffer=stereo.tobytes())


def create_chord(freqs, duration=0.15, volume=0.2, wave='soft'):
    """Generate a chord (multiple frequencies)."""
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


class GameSounds:
    """Pre-generated sound pool for all game events."""

    def __init__(self):
        _init_mixer()
        self.enabled = True
        self._build_sounds()

    def _build_sounds(self):
        # consume: short ascending pentatonic notes (cycle through scale)
        self.consume = [create_tone(f, 0.06, 0.2, 'soft') for f in PENTATONIC]
        self.consume_idx = 0

        # dissolve: gentle descending tone
        self.dissolve = create_sweep(440, 220, 0.12, 0.2)

        # replicate: bright chord (root + fifth)
        self.replicate = create_chord([329.63, 392.00, 523.25], 0.1, 0.18, 'soft')

        # turn: short click/blip
        self.turn = create_tone(600, 0.04, 0.12, 'triangle')

        # reverse: descending blip
        self.reverse = create_sweep(500, 300, 0.06, 0.15)

        # teleport: ethereal sweep up
        self.teleport = create_sweep(300, 800, 0.12, 0.15, 'sine')

        # level complete: ascending arpeggio
        notes = [261.63, 329.63, 392.00, 523.25]
        parts = []
        for i, f in enumerate(notes):
            n = int(SAMPLE_RATE * 0.12)
            t = np.linspace(0, 0.12, n, False)
            w = np.sin(2 * np.pi * f * t) * 0.25
            fade = int(SAMPLE_RATE * 0.02)
            w[-fade:] *= np.linspace(1, 0, fade)
            parts.append(w)
        combined = np.concatenate(parts)
        audio = (combined * 32767).astype(np.int16)
        stereo = np.column_stack((audio, audio))
        self.level_complete = pygame.mixer.Sound(buffer=stereo.tobytes())

        # perfect: same arpeggio but with a final sustained chord
        chord_n = int(SAMPLE_RATE * 0.3)
        chord_t = np.linspace(0, 0.3, chord_n, False)
        chord_w = (np.sin(2 * np.pi * 261.63 * chord_t) +
                    np.sin(2 * np.pi * 329.63 * chord_t) +
                    np.sin(2 * np.pi * 523.25 * chord_t)) / 3 * 0.2
        chord_w[-int(SAMPLE_RATE*0.08):] *= np.linspace(1, 0, int(SAMPLE_RATE*0.08))
        perfect_combined = np.concatenate([combined, chord_w])
        p_audio = (perfect_combined * 32767).astype(np.int16)
        p_stereo = np.column_stack((p_audio, p_audio))
        self.perfect = pygame.mixer.Sound(buffer=p_stereo.tobytes())

        # fail: sad descending pair
        n1 = int(SAMPLE_RATE * 0.15)
        t1 = np.linspace(0, 0.15, n1, False)
        w1 = np.sin(2 * np.pi * 293.66 * t1) * 0.2
        w1[-int(SAMPLE_RATE*0.03):] *= np.linspace(1, 0, int(SAMPLE_RATE*0.03))
        n2 = int(SAMPLE_RATE * 0.25)
        t2 = np.linspace(0, 0.25, n2, False)
        w2 = np.sin(2 * np.pi * 220 * t2) * 0.2
        w2[-int(SAMPLE_RATE*0.05):] *= np.linspace(1, 0, int(SAMPLE_RATE*0.05))
        fail_combined = np.concatenate([w1, w2])
        f_audio = (fail_combined * 32767).astype(np.int16)
        f_stereo = np.column_stack((f_audio, f_audio))
        self.fail = pygame.mixer.Sound(buffer=f_stereo.tobytes())

        # button click: tiny blip
        self.click = create_tone(800, 0.025, 0.1, 'triangle')

        # start sim: gentle rising tone
        self.start = create_sweep(300, 500, 0.1, 0.15)

    def play_consume(self):
        if not self.enabled:
            return
        self.consume[self.consume_idx % len(self.consume)].play()
        self.consume_idx += 1

    def play_dissolve(self):
        if self.enabled:
            self.dissolve.play()

    def play_replicate(self):
        if self.enabled:
            self.replicate.play()

    def play_turn(self):
        if self.enabled:
            self.turn.play()

    def play_reverse(self):
        if self.enabled:
            self.reverse.play()

    def play_teleport(self):
        if self.enabled:
            self.teleport.play()

    def play_level_complete(self):
        if self.enabled:
            self.level_complete.play()

    def play_perfect(self):
        if self.enabled:
            self.perfect.play()

    def play_fail(self):
        if self.enabled:
            self.fail.play()

    def play_click(self):
        if self.enabled:
            self.click.play()

    def play_start(self):
        if self.enabled:
            self.start.play()
