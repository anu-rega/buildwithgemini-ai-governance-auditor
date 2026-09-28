import numpy as np
from scipy.io import wavfile

def generate_lofi_track(filename="lofi_track.wav", duration_sec=40.0, sample_rate=44100):
    bpm = 88
    beat_dur = 60.0 / bpm
    total_samples = int(duration_sec * sample_rate)
    
    audio = np.zeros(total_samples)
    
    # 1. Vinyl Crackle / Soft Tape Hiss
    np.random.seed(42)
    crackle = np.random.normal(0, 0.008, total_samples)
    # Filter crackle to be warm
    from scipy.signal import butter, lfilter
    b, a = butter(2, 3000 / (sample_rate / 2), btype='low')
    crackle = lfilter(b, a, crackle)
    audio += crackle

    # 2. Drum Loop Synthesis
    def make_kick(dur=0.3):
        t = np.linspace(0, dur, int(dur * sample_rate), False)
        freq = 120 * np.exp(-15 * t) + 40
        sine = np.sin(2 * np.pi * freq * t)
        env = np.exp(-8 * t)
        return sine * env * 0.6

    def make_snare(dur=0.25):
        t = np.linspace(0, dur, int(dur * sample_rate), False)
        noise = np.random.normal(0, 1, len(t))
        tone = np.sin(2 * np.pi * 180 * t) * np.exp(-15 * t)
        env = np.exp(-12 * t)
        return (noise * 0.6 + tone * 0.4) * env * 0.35

    def make_hihat(dur=0.08, open_hat=False):
        d = dur * 1.8 if open_hat else dur
        t = np.linspace(0, d, int(d * sample_rate), False)
        noise = np.random.normal(0, 1, len(t))
        b_h, a_h = butter(2, 6000 / (sample_rate / 2), btype='high')
        filtered = lfilter(b_h, a_h, noise)
        decay = 8 if open_hat else 35
        env = np.exp(-decay * t)
        return filtered * env * (0.2 if open_hat else 0.12)

    kick = make_kick()
    snare = make_snare()
    hat_closed = make_hihat(0.08, False)
    hat_open = make_hihat(0.12, True)

    # Sequence drums across 16th notes
    steps_per_beat = 4
    step_dur = beat_dur / steps_per_beat
    total_steps = int(duration_sec / step_dur)

    for step in range(total_steps):
        pos = int(step * step_dur * sample_rate)
        if pos >= total_samples:
            break
        
        step_in_bar = step % 16
        
        # Kick on 0, 6, 10
        if step_in_bar in [0, 6, 10]:
            k_len = min(len(kick), total_samples - pos)
            audio[pos:pos+k_len] += kick[:k_len]
            
        # Snare on 4, 12
        if step_in_bar in [4, 12]:
            s_len = min(len(snare), total_samples - pos)
            audio[pos:pos+s_len] += snare[:s_len]
            
        # Hi-hats on even steps (16th notes with subtle swing)
        if step_in_bar % 2 == 0:
            h = hat_open if step_in_bar == 14 else hat_closed
            h_len = min(len(h), total_samples - pos)
            audio[pos:pos+h_len] += h[:h_len]

    # 3. Rhodes / E-Piano Jazz Chords
    # Fmaj7 - Em7 - Dm7 - Cmaj7
    chords = [
        [349.23, 440.00, 523.25, 659.25], # Fmaj7
        [329.63, 392.00, 493.88, 587.33], # Em7
        [293.66, 349.23, 440.00, 523.25], # Dm7
        [261.63, 329.63, 392.00, 493.88], # Cmaj7
    ]

    def synthesize_chord(freqs, dur=beat_dur*4):
        t = np.linspace(0, dur, int(dur * sample_rate), False)
        signal = np.zeros_like(t)
        for f in freqs:
            # Warm sine + harmonics
            s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t) + 0.1 * np.sin(2 * np.pi * 3 * f * t)
            # Soft attack and slow warm decay
            env = (1 - np.exp(-20 * t)) * np.exp(-1.5 * t)
            signal += s * env
        
        # Soft lowpass for lo-fi chill sound
        b_c, a_c = butter(2, 2200 / (sample_rate / 2), btype='low')
        return lfilter(b_c, a_c, signal) * 0.12

    chord_dur_bars = 1 # 1 bar = 4 beats
    bar_dur = beat_dur * 4
    num_bars = int(duration_sec / bar_dur) + 1

    for bar in range(num_bars):
        chord_idx = bar % len(chords)
        chord_signal = synthesize_chord(chords[chord_idx], bar_dur)
        pos = int(bar * bar_dur * sample_rate)
        c_len = min(len(chord_signal), total_samples - pos)
        if c_len > 0:
            audio[pos:pos+c_len] += chord_signal[:c_len]

    # 4. Bassline
    bass_notes = [174.61, 164.81, 146.83, 130.81] # F2, E2, D2, C2
    for bar in range(num_bars):
        f_bass = bass_notes[bar % len(bass_notes)]
        t_b = np.linspace(0, bar_dur, int(bar_dur * sample_rate), False)
        bass = np.sin(2 * np.pi * f_bass * t_b) + 0.2 * np.sin(2 * np.pi * 2 * f_bass * t_b)
        env_b = (1 - np.exp(-15 * t_b)) * np.exp(-1.2 * t_b)
        b_sig = bass * env_b * 0.22
        
        b_l, a_l = butter(2, 800 / (sample_rate / 2), btype='low')
        b_sig = lfilter(b_l, a_l, b_sig)
        
        pos = int(bar * bar_dur * sample_rate)
        b_len = min(len(b_sig), total_samples - pos)
        if b_len > 0:
            audio[pos:pos+b_len] += b_sig[:b_len]

    # Normalize audio
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.85

    # Save to WAV
    audio_int16 = (audio * 32767).astype(np.int16)
    wavfile.write(filename, sample_rate, audio_int16)
    print(f"Generated upbeat lo-fi track: {filename}")
    return filename

if __name__ == "__main__":
    generate_lofi_track()
