"""
Turns downloaded sound effects into the game's sounds/<name>.ogg files.

1. Put your downloads (any format ffmpeg reads: .wav .mp3 .ogg .flac ...) in a folder,
   named after what they're for, e.g.  water.mp3  lava.wav  click.ogg
2. Run:  python tools/prepare_sounds.py path/to/that/folder

Names the game uses:
  loops (play while you hold the mouse):  water  lava  fire  powder  magic
  one-shots:                              click  chime  whoosh  sizzle

Loops get a few seconds cut out and the end cross-faded into the start so they repeat
without a click or gap. One-shots get silence trimmed off the front and are kept short.
Everything is converted to 44.1 kHz stereo and evened out in loudness.
Any name you don't provide keeps the game's built-in generated sound.

Needs ffmpeg. Remember to note where each sound came from in sounds/CREDITS.txt.
"""
import array
import math
import os
import subprocess
import sys
import tempfile
import wave

RATE = 44100
LOOPS = {"water": 4.0, "lava": 4.0, "fire": 4.0, "powder": 6.0, "magic": 2.0}  # loop length in seconds
# Recordings with stops and starts (e.g. separate pours): layer several busy slices on top of each
# other and even out the volume, so the loop is one continuous sound instead of pour... gap... pour.
SMOOTH = {"powder"}
ONESHOTS = {"click": 0.4, "chime": 2.0, "whoosh": 1.2, "sizzle": 1.5}         # longest allowed, seconds
# extra shaping for particular one-shots (ffmpeg filters)
SHAPES = {
    # steam should go "pssshh": hit fast, then die away; and lose some harsh top end
    "sizzle": "highpass=f=300,lowpass=f=9000,afade=t=in:d=0.02,"
              "volume='exp(-2.5*max(t-0.08,0))':eval=frame,afade=t=out:st=1.3:d=0.2",
}
CROSSFADE = 0.5  # seconds of end blended into the start of a loop
OUTFOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sounds")


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def readwav(path):
    with wave.open(path) as w:
        return array.array("h", w.readframes(w.getnframes()))


def writewav(path, samples):
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(samples.tobytes())


def level(chunk):
    return math.sqrt(sum(v * v for v in chunk) / len(chunk)) if chunk else 0


def layerslices(source, wavpath, seconds):
    """Find up to 4 stretches where the sound never drops out, and mix them together."""
    ffmpeg("-i", source, "-t", "180", "-ar", str(RATE), "-ac", "2", wavpath)
    samples = readwav(wavpath)
    window = RATE // 4 * 2  # a quarter second of stereo samples
    levels = [level(samples[k:k + window]) for k in range(0, len(samples) - window + 1, window)]
    need = int((seconds + CROSSFADE + 0.1) * 4) + 1  # quarter seconds per slice
    floor = max(levels) * 10 ** (-18 / 20)            # "busy" = within 18 dB of the loudest moment
    starts, k = [], 0
    while k + need <= len(levels) and len(starts) < 4:
        if min(levels[k:k + need]) > floor:
            starts.append(k * window)
            k += need  # next slice must not overlap
        else:
            k += 1
    if not starts:
        raise ValueError(f"has no {seconds + CROSSFADE:.1f}-second stretch without gaps")
    length = need * window
    scale = 1 / math.sqrt(len(starts))
    mixed = [sum(samples[st + i] for st in starts) * scale for i in range(length)]
    # even out the volume: measure every 50 ms, turn quiet bits up and loud bits down (smoothed so it doesn't pump)
    step = RATE // 20 * 2
    levels = [level(mixed[k:k + step]) for k in range(0, length, step)]
    target = sorted(levels)[len(levels) // 2]
    gains = [max(0.25, min(8.0, target / (lv or 1))) for lv in levels]
    smooth = [sum(gains[max(0, i - 3):i + 4]) / len(gains[max(0, i - 3):i + 4]) for i in range(len(gains))]
    levelled = array.array("h", (max(-32768, min(32767, int(v * smooth[i // step]))) for i, v in enumerate(mixed)))
    writewav(wavpath, levelled)
    return len(starts)


def makeloop(name, source, wavpath, seconds):
    # skip the first half second (fade-ins are common), even out the loudness, then cross-fade
    if name in SMOOTH:
        layered = wavpath + ".layered.wav"
        layerslices(source, layered, seconds)
        ffmpeg("-i", layered, "-af", "loudnorm=I=-20:TP=-2", "-ar", str(RATE), "-ac", "2", wavpath)
    else:
        ffmpeg("-ss", "0.5", "-i", source, "-t", str(seconds + CROSSFADE + 0.1),
               "-af", "loudnorm=I=-20:TP=-2", "-ar", str(RATE), "-ac", "2", wavpath)
    samples = readwav(wavpath)
    length = int(seconds * RATE) * 2
    fade = int(CROSSFADE * RATE) * 2
    if len(samples) < length + fade:
        raise ValueError(f"needs at least {seconds + CROSSFADE + 0.5:.1f} seconds of sound")
    loop = samples[:length]
    for i in range(fade):  # blend the bit after the loop end into the loop start
        t = (i // 2) / (fade // 2)
        loop[i] = int(samples[length + i] * (1 - t) + samples[i] * t)
    writewav(wavpath, loop)


def makeoneshot(name, source, wavpath, seconds):
    # trim silence at the start, keep it short, fade the end, then bring the peak up to a set level
    shape = SHAPES.get(name, f"afade=t=out:st={max(0.0, seconds - 0.15)}:d=0.15")
    ffmpeg("-i", source, "-af", f"silenceremove=start_periods=1:start_threshold=-45dB,atrim=0:{seconds},{shape}",
           "-ar", str(RATE), "-ac", "2", wavpath)
    samples = readwav(wavpath)
    peak = max((abs(v) for v in samples), default=0)
    if peak == 0:
        raise ValueError("is silent")
    scale = 0.7 * 32767 / peak
    writewav(wavpath, array.array("h", (int(v * scale) for v in samples)))


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    folder = sys.argv[1]
    os.makedirs(OUTFOLDER, exist_ok=True)
    found = {os.path.splitext(f)[0].lower(): os.path.join(folder, f) for f in os.listdir(folder)}
    with tempfile.TemporaryDirectory() as tmp:
        for name in list(LOOPS) + list(ONESHOTS):
            if name not in found:
                print(f"{name:7} - not found, game keeps its generated sound")
                continue
            wav = os.path.join(tmp, name + ".wav")
            try:
                if name in LOOPS:
                    makeloop(name, found[name], wav, LOOPS[name])
                else:
                    makeoneshot(name, found[name], wav, ONESHOTS[name])
            except (ValueError, subprocess.CalledProcessError) as problem:
                print(f"{name:7} - skipped: {os.path.basename(found[name])} {problem}")
                continue
            ffmpeg("-i", wav, "-c:a", "libvorbis", "-q:a", "5", os.path.join(OUTFOLDER, name + ".ogg"))
            print(f"{name:7} - done   ({os.path.basename(found[name])})")


if __name__ == "__main__":
    main()
