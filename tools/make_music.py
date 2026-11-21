"""
Makes the game's music: music/<style>/<section>_<layer>.ogg

Styles:   orchestral, lofi, retro, arcane, alchemy   (the game rotates between them every ~2 minutes;
          celtic is defined below but not rendered - add it to RENDER to bring it back)
Sections: menu, calm, busy, intense              (picked by what's happening on screen)
Layers:   pad, arp, drums, sparkle, melody       (all play together; the game fades each one)

For each one this writes the notes as a MIDI file, plays it through FluidSynth with the
FluidR3 General MIDI soundfont, and saves an .ogg the game loads.

Only needed to MAKE the music (the game just loads the .ogg files):
    sudo pacman -S fluidsynth soundfont-fluid      (and ffmpeg)
    Better instruments: GeneralUser GS (https://schristiancollins.com/generaluser.php),
    saved as ~/.local/share/soundfonts/GeneralUser-GS.sf2 - used automatically if it's there.
Run from the project folder:
    python tools/make_music.py
"""
import array
import os
import random
import shutil
import struct
import subprocess
import tempfile
import wave

SOUNDFONTS = [os.path.expanduser("~/.local/share/soundfonts/GeneralUser-GS.sf2"),  # nicer, used if present
              "/usr/share/soundfonts/FluidR3_GM.sf2"]
SOUNDFONT = next((path for path in SOUNDFONTS if os.path.exists(path)), SOUNDFONTS[-1])
OUTFOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "music")
RATE = 44100
TICKS = 480        # MIDI ticks per beat
BARS = 8           # every section is 8 bars (4 chords, played twice)
A = 57             # MIDI note A3; all chords are semitones from A (everything is in A minor)

# ---- General MIDI instruments (program numbers) ----
ELECTRIC_PIANO, CELESTA, GLOCKENSPIEL, MUSIC_BOX, VIBES, MARIMBA, TUBULAR_BELLS = 4, 8, 9, 10, 11, 12, 14
ACCORDION, NYLON_GUITAR, STEEL_GUITAR = 21, 24, 25
ACOUSTIC_BASS, FINGER_BASS, PICK_BASS, SYNTH_BASS = 32, 33, 34, 38
VIOLIN, CONTRABASS, TREMOLO_STRINGS, PIZZICATO, HARP, TIMPANI = 40, 43, 44, 45, 46, 47
STRINGS, SYNTH_STRINGS, CHOIR = 48, 50, 52
MUTED_TRUMPET, FRENCH_HORN, TENOR_SAX, OBOE, FLUTE, PAN_FLUTE = 59, 60, 66, 68, 73, 75
SQUARE_LEAD, SAW_LEAD, VOICE_LEAD, WARM_PAD, POLYSYNTH, CRYSTAL = 80, 81, 85, 89, 90, 98
BAGPIPE, FIDDLE = 109, 110
TRUMPET, XYLOPHONE, DULCIMER, CELLO, TUBA, BRASS_SECTION, BASSOON, CLARINET = 56, 13, 15, 42, 58, 61, 70, 71
CHOIR_PAD, TAIKO = 91, 116

# ---- drum kit (MIDI channel 10) ----
DRUMS = 9
STANDARD_KIT, TR808_KIT, JAZZ_KIT = 0, 25, 32
KICK, SIDESTICK, SNARE, CLAP, CLOSED_HAT, OPEN_HAT, CRASH = 36, 37, 38, 39, 42, 46, 49
LOW_TOM, MID_TOM, HIGH_TOM, TAMBOURINE, HIGH_CONGA, LOW_CONGA, MARACAS = 45, 47, 50, 54, 63, 64, 70
HIGH_WOODBLOCK, LOW_WOODBLOCK, TRIANGLE, CASTANETS = 76, 77, 81, 85
EIGHTHS = [k / 2 for k in range(8)]
SIXTEENTHS = [k / 4 for k in range(16)]
OFFBEATS = [0.5, 1.5, 2.5, 3.5]

# ---- chords (semitones from A) ----
Am, C, Dm, Em, F, G, E = [0, 3, 7], [3, 7, 10], [-7, -4, 0], [-5, -2, 2], [-4, 0, 3], [-2, 2, 5], [-5, -1, 2]
Am7, Dm7, Em7, G7, E7 = [0, 3, 7, 10], [-7, -4, 0, 3], [-5, -2, 2, 5], [-2, 2, 5, 8], [-5, -1, 2, 5]
Cmaj7, Fmaj7 = [3, 7, 10, 14], [-4, 0, 3, 7]
Bb = [1, 5, 8]  # B-flat major: the dark, "magic" chord next to A minor

# ---- melody rhythms: each is one bar of (beat, length) ----
RHYTHMS = {
    "sparse":  [[(0, 3), (3, 1)], [(0, 2), (2, 2)], [(0.5, 1.5), (2, 2)], [(0, 4)]],
    "flowing": [[(0, 1.5), (1.5, 0.5), (2, 1), (3, 1)], [(0, 1), (1, 1), (2, 2)],
                [(0, 0.5), (0.5, 0.5), (1, 1), (2, 1.5), (3.5, 0.5)], [(0, 2), (2, 1), (3, 1)]],
    "busy":    [[(0, 0.5), (0.5, 0.5), (1, 0.5), (1.5, 0.5), (2, 1), (3, 1)],
                [(0, 0.75), (0.75, 0.25), (1, 1), (2, 0.5), (2.5, 0.5), (3, 1)],
                [(0, 1), (1, 0.5), (1.5, 0.5), (2, 0.5), (2.5, 0.5), (3, 1)]],
    "lazy":    [[(0.5, 1), (1.5, 0.5), (2.5, 1.5)], [(0, 0.5), (0.5, 1), (2, 2)],
                [(1, 1), (2, 0.5), (2.5, 1.5)], [(0, 1.5), (2, 0.5), (2.5, 1)]],
    "jig":     [[(0, 0.75), (0.75, 0.25), (1, 0.75), (1.75, 0.25), (2, 1), (3, 0.5), (3.5, 0.5)],
                [(0, 0.5), (0.5, 0.5), (1, 0.5), (1.5, 0.5), (2, 0.75), (2.75, 0.25), (3, 1)],
                [(0, 1), (1, 0.75), (1.75, 0.25), (2, 0.5), (2.5, 0.5), (3, 1)]],
    "chip":    [[(0, 0.25), (0.25, 0.25), (0.5, 0.5), (1, 0.5), (1.5, 0.5), (2, 1), (3, 0.5), (3.5, 0.5)],
                [(0, 0.5), (0.5, 0.25), (0.75, 0.25), (1, 1), (2, 0.5), (2.5, 0.5), (3, 1)],
                [(0, 1.5), (1.5, 0.5), (2, 0.25), (2.25, 0.25), (2.5, 0.5), (3, 1)]],
}

# ---- the four styles ----
# pad:     list of (instrument, how it plays, velocity)  - hold / hold+12 / stabs / pulse / strum / drone
# bass:    (instrument, pattern, velocity)               - whole / half / eighths / octaves / walking / bounce
# arp:     (instrument, notes per beat, velocity, octave shift in semitones)
# drums:   {"kit", "hits": [(drum, beats, velocity)], "crash", "fill", "timpani"}
# sparkle: (instrument, notes per bar)  or (instrument, "downbeats")
# melody:  (instrument, octave, rhythm style, velocity)
STYLES = {
    "orchestral": dict(
        bpm=120, swing=0,
        chords={"menu": [Am, Fmaj7, C, G], "calm": [Am, F, C, G], "busy": [C, G, Am, F], "intense": [Am, Am, F, E]},
        pad={"menu": [(WARM_PAD, "hold", 55), (STRINGS, "hold", 35)],
             "calm": [(STRINGS, "hold", 60)],
             "busy": [(STRINGS, "hold", 65), (CHOIR, "hold+12", 40)],
             "intense": [(TREMOLO_STRINGS, "hold", 75), (CHOIR, "hold+12", 60)]},
        bass={"menu": (CONTRABASS, "whole", 60), "calm": (ACOUSTIC_BASS, "half", 75),
              "busy": (FINGER_BASS, "octaves", 80), "intense": (PICK_BASS, "eighths", 90)},
        arp={"menu": (HARP, 1, 65, 0), "calm": (HARP, 2, 70, 0), "busy": (PIZZICATO, 2, 72, 0), "intense": (STRINGS, 4, 78, 0)},
        drums={"calm": {"hits": [(KICK, [0, 2], 70), (SIDESTICK, [1, 3], 55), (CLOSED_HAT, EIGHTHS, 40)]},
               "busy": {"hits": [(KICK, [0, 2, 2.5], 90), (SNARE, [1, 3], 85), (CLOSED_HAT, EIGHTHS, 55), (OPEN_HAT, [3.5], 55)], "crash": True},
               "intense": {"hits": [(KICK, [0, 0.75, 2, 2.75], 105), (SNARE, [1, 3], 105), (CLOSED_HAT, SIXTEENTHS, 50)],
                           "crash": True, "fill": True, "timpani": True}},
        sparkle={"menu": (CELESTA, 3), "calm": (GLOCKENSPIEL, 3), "busy": (MUSIC_BOX, 3), "intense": (TUBULAR_BELLS, "downbeats")},
        melody={"menu": (FLUTE, 0, "sparse", 62), "calm": (OBOE, 0, "flowing", 72),
                "busy": (VIOLIN, 0, "busy", 80), "intense": (FRENCH_HORN, -1, "flowing", 95)},
    ),
    "lofi": dict(
        bpm=84, swing=0.16,
        chords={"menu": [Am7, Fmaj7, Am7, Fmaj7], "calm": [Am7, Dm7, G7, Cmaj7],
                "busy": [Fmaj7, Em7, Dm7, Cmaj7], "intense": [Fmaj7, E7, Am7, G7]},
        pad={"menu": [(ELECTRIC_PIANO, "hold", 50), (WARM_PAD, "hold", 35)],
             "calm": [(ELECTRIC_PIANO, "stabs", 60)],
             "busy": [(ELECTRIC_PIANO, "stabs", 68)],
             "intense": [(ELECTRIC_PIANO, "stabs", 78), (WARM_PAD, "hold", 40)]},
        bass={"menu": (ACOUSTIC_BASS, "whole", 60), "calm": (ACOUSTIC_BASS, "walking", 70),
              "busy": (ACOUSTIC_BASS, "walking", 78), "intense": (FINGER_BASS, "walking", 85)},
        arp={"menu": (VIBES, 1, 85, 0), "calm": (VIBES, 1, 85, 0), "busy": (VIBES, 2, 88, 0), "intense": (VIBES, 2, 92, 0)},
        drums={"calm": {"kit": JAZZ_KIT, "hits": [(KICK, [0, 2.5], 75), (SIDESTICK, [1, 3], 60), (CLOSED_HAT, EIGHTHS, 35)]},
               "busy": {"kit": JAZZ_KIT, "hits": [(KICK, [0, 1.75, 2.5], 85), (SNARE, [1, 3], 72), (CLOSED_HAT, EIGHTHS, 45)]},
               "intense": {"kit": JAZZ_KIT, "hits": [(KICK, [0, 0.75, 1.75, 2.5], 95), (SNARE, [1, 3], 88),
                                                     (CLOSED_HAT, EIGHTHS, 55), (OPEN_HAT, [3.5], 50)], "crash": True}},
        sparkle={"menu": (MUSIC_BOX, 2), "calm": (CELESTA, 2), "busy": (CELESTA, 2), "intense": (MUSIC_BOX, 3)},
        melody={"menu": (FLUTE, 0, "lazy", 55), "calm": (NYLON_GUITAR, 0, "lazy", 78),
                "busy": (TENOR_SAX, -1, "lazy", 80), "intense": (MUTED_TRUMPET, 0, "busy", 85)},
    ),
    "retro": dict(
        bpm=140, swing=0, gain={"drums": 0.45},  # the 808 kit is much louder than the others
        chords={"menu": [Am, F, C, G], "calm": [Am, Em, F, G], "busy": [F, G, Em, Am], "intense": [Am, F, G, E]},
        pad={"menu": [(POLYSYNTH, "hold", 45)],
             "calm": [(SYNTH_STRINGS, "hold", 55)],
             "busy": [(POLYSYNTH, "pulse", 55)],
             "intense": [(POLYSYNTH, "pulse", 62), (SYNTH_STRINGS, "hold", 50)]},
        bass={"menu": (SYNTH_BASS, "whole", 65), "calm": (SYNTH_BASS, "half", 75),
              "busy": (SYNTH_BASS, "octaves", 85), "intense": (SYNTH_BASS, "octaves", 95)},
        arp={"menu": (SQUARE_LEAD, 2, 40, 12), "calm": (SQUARE_LEAD, 4, 40, 12), "busy": (SQUARE_LEAD, 4, 45, 12), "intense": (SQUARE_LEAD, 4, 50, 12)},
        drums={"calm": {"kit": TR808_KIT, "hits": [(KICK, [0, 2], 85), (CLAP, [1, 3], 65), (CLOSED_HAT, OFFBEATS, 55)]},
               "busy": {"kit": TR808_KIT, "hits": [(KICK, [0, 1, 2, 3], 95), (CLAP, [1, 3], 80), (CLOSED_HAT, OFFBEATS, 65),
                                                   (OPEN_HAT, [3.5], 60)], "crash": True},
               "intense": {"kit": TR808_KIT, "hits": [(KICK, [0, 1, 2, 2.5, 3], 105), (SNARE, [1, 3], 100), (CLAP, [1, 3], 80),
                                                      (CLOSED_HAT, SIXTEENTHS, 55)], "crash": True, "fill": True}},
        sparkle={"menu": (CRYSTAL, 2), "calm": (CRYSTAL, 2), "busy": (CRYSTAL, 3), "intense": (CRYSTAL, 3)},
        melody={"menu": (VOICE_LEAD, 0, "sparse", 60), "calm": (SAW_LEAD, 0, "flowing", 62),
                "busy": (SAW_LEAD, 0, "chip", 66), "intense": (SAW_LEAD, 0, "chip", 72)},
    ),
    # Hand-written melodies: themes[section] = 8 bars, each a list of (beat, length, note),
    # note in semitones from the melody's home A (0 = A, 3 = C, 7 = E, 12 = A an octave up...).
    "arcane": dict(  # mysterious wizard tower: A minor with B-flat and E major (Phrygian / harmonic minor)
        bpm=96, swing=0,
        chords={"menu": [Am, Bb, Am, E], "calm": [Am, F, Dm, E], "busy": [Am, Dm, Bb, E], "intense": [Am, F, Bb, E]},
        pad={"menu": [(CHOIR_PAD, "hold", 50), (WARM_PAD, "hold", 35)],
             "calm": [(STRINGS, "hold", 50), (CHOIR, "hold", 40)],
             "busy": [(STRINGS, "hold", 60), (CHOIR, "hold+12", 45)],
             "intense": [(TREMOLO_STRINGS, "hold", 80), (CHOIR, "hold+12", 65), (BRASS_SECTION, "stabs", 70)]},
        bass={"menu": (CONTRABASS, "whole", 55), "calm": (CELLO, "half", 65),
              "busy": (CELLO, "eighths", 75), "intense": (CONTRABASS, "eighths", 90)},
        arp={"menu": (HARP, 1, 60, 0), "calm": (DULCIMER, 2, 58, 0), "busy": (PIZZICATO, 2, 72, 0), "intense": (STRINGS, 4, 76, 0)},
        drums={"calm": {"hits": [(LOW_CONGA, [0, 2.5], 55), (TRIANGLE, [3], 40)]},
               "busy": {"hits": [(LOW_CONGA, [0, 1.5, 2, 3.5], 75), (HIGH_CONGA, [1, 3], 55), (MARACAS, EIGHTHS, 35)],
                        "taiko": [0, 2]},
               "intense": {"hits": [(KICK, [0, 1.5, 2], 100), (SNARE, [1, 3], 90), (CLOSED_HAT, EIGHTHS, 45)],
                           "crash": True, "fill": True, "timpani": True, "taiko": [0, 0.75, 1.5, 2, 3]}},
        sparkle={"menu": (CRYSTAL, 3), "calm": (CELESTA, 2), "busy": (GLOCKENSPIEL, 3), "intense": (TUBULAR_BELLS, "downbeats")},
        melody={"menu": (FLUTE, 0, None, 58), "calm": (OBOE, 0, None, 70), "busy": (CLARINET, 0, None, 76), "intense": (FRENCH_HORN, -1, None, 98)},
        themes={
            "menu": [[(0, 2, 7), (2, 1, 8), (3, 1, 7)], [(0, 3, 5), (3, 1, 1)], [(0, 2, 0), (2, 1, 3), (3, 1, 5)], [(0, 4, 11)],
                     [(0, 2, 7), (2, 1, 8), (3, 1, 7)], [(0, 1, 5), (1, 1, 8), (2, 2, 13)], [(0, 1.5, 3), (1.5, 0.5, 1), (2, 2, 0)],
                     [(0, 2, 11), (2, 2, 7)]],
            "calm": [[(0, 1, 0), (1, 0.5, 3), (1.5, 0.5, 7), (2, 1.5, 12), (3.5, 0.5, 10)], [(0, 1, 8), (1, 1, 7), (2, 1, 5), (3, 1, 3)],
                     [(0, 1.5, 5), (1.5, 0.5, 8), (2, 1, 12), (3, 1, 10)], [(0, 2, 11), (2, 1, 7), (3, 1, 2)],
                     [(0, 1, 0), (1, 0.5, 3), (1.5, 0.5, 7), (2, 1.5, 12), (3.5, 0.5, 10)], [(0, 1, 8), (1, 0.5, 12), (1.5, 0.5, 10), (2, 2, 8)],
                     [(0, 1, 5), (1, 1, 8), (2, 1, 7), (3, 1, 5)], [(0, 1.5, 2), (1.5, 0.5, 5), (2, 2, 11)]],
            "busy": [[(0, .5, 12), (.5, .5, 7), (1, .5, 3), (1.5, .5, 7), (2, .5, 12), (2.5, .5, 15), (3, 1, 12)],
                     [(0, .5, 8), (.5, .5, 5), (1, .5, 0), (1.5, .5, 5), (2, .5, 8), (2.5, .5, 12), (3, 1, 8)],
                     [(0, .5, 13), (.5, .5, 8), (1, .5, 5), (1.5, .5, 8), (2, 1, 13), (3, .5, 12), (3.5, .5, 10)],
                     [(0, 1, 11), (1, .5, 7), (1.5, .5, 11), (2, 2, 14)],
                     [(0, .5, 12), (.5, .5, 7), (1, .5, 3), (1.5, .5, 7), (2, .5, 12), (2.5, .5, 15), (3, 1, 12)],
                     [(0, .5, 8), (.5, .5, 5), (1, .5, 0), (1.5, .5, 5), (2, .5, 8), (2.5, .5, 12), (3, 1, 8)],
                     [(0, .5, 13), (.5, .5, 12), (1, .5, 10), (1.5, .5, 8), (2, .5, 7), (2.5, .5, 5), (3, .5, 3), (3.5, .5, 1)],
                     [(0, 1, 7), (1, 1, 11), (2, 2, 14)]],
            "intense": [[(0, 1.5, 0), (1.5, .5, 0), (2, 1, 7), (3, 1, 12)], [(0, 2, 12), (2, 1, 10), (3, 1, 8)],
                        [(0, 1.5, 5), (1.5, .5, 8), (2, 2, 13)], [(0, 1, 11), (1, 1, 7), (2, 2, 11)],
                        [(0, 1.5, 0), (1.5, .5, 0), (2, 1, 7), (3, 1, 12)], [(0, 1, 12), (1, 1, 15), (2, 2, 12)],
                        [(0, 1, 13), (1, 1, 12), (2, 1, 10), (3, 1, 8)], [(0, 2, 7), (2, 2, 11)]],
        },
    ),
    "alchemy": dict(  # bubbling cauldron: oom-pah tuba and pizzicato, bassoon and clarinet tunes, a bit spooky
        bpm=132, swing=0,
        chords={"menu": [Am, E7, Am, E7], "calm": [Am, Dm, E, Am], "busy": [Am, Dm, G, C], "intense": [Am, Bb, E7, Am]},
        pad={"menu": [(ACCORDION, "hold", 35), (STRINGS, "hold", 30)],
             "calm": [(PIZZICATO, "oompah", 70)],
             "busy": [(PIZZICATO, "oompah", 78), (ACCORDION, "oompah", 45)],
             "intense": [(BRASS_SECTION, "oompah", 80), (TREMOLO_STRINGS, "hold", 55)]},
        bass={"menu": (CONTRABASS, "whole", 55), "calm": (TUBA, "half", 80),
              "busy": (TUBA, "half", 88), "intense": (TUBA, "half", 98)},
        arp={"menu": (HARP, 1, 55, 0), "calm": (MARIMBA, 2, 55, 0), "busy": (XYLOPHONE, 2, 60, 12), "intense": (XYLOPHONE, 4, 65, 12)},
        drums={"calm": {"hits": [(LOW_WOODBLOCK, [0, 2], 60), (HIGH_WOODBLOCK, [1, 3], 55)]},
               "busy": {"hits": [(LOW_WOODBLOCK, [0, 2], 70), (HIGH_WOODBLOCK, [1, 3], 65), (CASTANETS, OFFBEATS, 50),
                                 (TAMBOURINE, [1, 3], 50)]},
               "intense": {"hits": [(KICK, [0, 2], 95), (SNARE, [1, 3], 90), (CLOSED_HAT, EIGHTHS, 50), (CASTANETS, OFFBEATS, 55)],
                           "crash": True, "fill": True}},
        sparkle={"menu": (CELESTA, 2), "calm": (CELESTA, 3), "busy": (MUSIC_BOX, 3), "intense": (TUBULAR_BELLS, "downbeats")},
        melody={"menu": (CLARINET, 0, None, 60), "calm": (BASSOON, -1, None, 82), "busy": (CLARINET, 0, None, 78), "intense": (TRUMPET, 0, None, 92)},
        themes={
            "menu": [[(0, 1, 12), (1, 1, 11), (2, 2, 12)], [(0, 1, 14), (1, 1, 11), (2, 2, 5)], [(0, 1, 7), (1, 1, 8), (2, 1, 7), (3, 1, 3)],
                     [(0, 4, 11)], [(0, 1, 12), (1, 1, 11), (2, 2, 12)], [(0, 1, 14), (1, 1, 11), (2, 2, 5)],
                     [(0, 1, 3), (1, 1, 7), (2, 1, 12), (3, 1, 15)], [(0, 2, 14), (2, 2, 11)]],
            "calm": [[(0, .5, 0), (.5, .5, 3), (1, 1, 7), (2, .5, 8), (2.5, .5, 7), (3, 1, 3)],
                     [(0, .5, 5), (.5, .5, 8), (1, 1, 12), (2, .5, 10), (2.5, .5, 8), (3, 1, 5)],
                     [(0, .5, 7), (.5, .5, 11), (1, 1, 14), (2, .5, 12), (2.5, .5, 11), (3, 1, 7)],
                     [(0, 1, 12), (1, 1, 7), (2, 2, 0)],
                     [(0, .5, 0), (.5, .5, 3), (1, 1, 7), (2, .5, 8), (2.5, .5, 7), (3, 1, 3)],
                     [(0, .5, 5), (.5, .5, 8), (1, 1, 12), (2, .5, 10), (2.5, .5, 8), (3, 1, 5)],
                     [(0, 1, 11), (1, 1, 8), (2, 1, 7), (3, 1, 5)], [(0, 1, 3), (1, 1, -1), (2, 2, 0)]],
            "busy": [[(0, .5, 7), (.5, .5, 8), (1, .5, 7), (1.5, .5, 5), (2, .5, 3), (2.5, .5, 5), (3, 1, 7)],
                     [(0, .5, 8), (.5, .5, 10), (1, .5, 8), (1.5, .5, 7), (2, .5, 5), (2.5, .5, 7), (3, 1, 8)],
                     [(0, .5, 10), (.5, .5, 12), (1, .5, 10), (1.5, .5, 8), (2, .5, 7), (2.5, .5, 5), (3, 1, 2)],
                     [(0, 1, 3), (1, 1, 7), (2, 2, 15)],
                     [(0, .5, 7), (.5, .5, 8), (1, .5, 7), (1.5, .5, 5), (2, .5, 3), (2.5, .5, 5), (3, 1, 7)],
                     [(0, .5, 8), (.5, .5, 10), (1, .5, 8), (1.5, .5, 7), (2, .5, 5), (2.5, .5, 7), (3, 1, 8)],
                     [(0, 1, 14), (1, 1, 10), (2, 1, 5), (3, 1, 2)], [(0, 1, 3), (1, .5, 5), (1.5, .5, 3), (2, 2, 7)]],
            "intense": [[(0, .5, 12), (.5, .5, 12), (1, .5, 11), (1.5, .5, 12), (2, 1, 15), (3, 1, 12)],
                        [(0, .5, 13), (.5, .5, 13), (1, .5, 12), (1.5, .5, 13), (2, 1, 17), (3, 1, 13)],
                        [(0, 1, 11), (1, 1, 14), (2, 1, 17), (3, 1, 14)], [(0, 2, 12), (2, 1, 7), (3, 1, 3)],
                        [(0, .5, 12), (.5, .5, 12), (1, .5, 11), (1.5, .5, 12), (2, 1, 15), (3, 1, 12)],
                        [(0, .5, 13), (.5, .5, 13), (1, .5, 12), (1.5, .5, 13), (2, 1, 17), (3, 1, 13)],
                        [(0, .5, 11), (.5, .5, 12), (1, .5, 14), (1.5, .5, 15), (2, 1, 17), (3, 1, 14)], [(0, 2, 12), (2, 2, 0)]],
        },
    ),
    "celtic": dict(
        bpm=112, swing=0.1,
        chords={"menu": [Am, Em, F, G], "calm": [Am, G, Am, Em], "busy": [C, G, Am, G], "intense": [Am, G, F, E]},
        pad={"menu": [(STRINGS, "hold", 40), (ACCORDION, "hold", 30)],
             "calm": [(STEEL_GUITAR, "strum", 62)],
             "busy": [(STEEL_GUITAR, "strum", 72), (ACCORDION, "hold", 38)],
             "intense": [(STEEL_GUITAR, "strum", 82), (BAGPIPE, "drone", 40)]},
        bass={"menu": (ACOUSTIC_BASS, "whole", 55), "calm": (ACOUSTIC_BASS, "bounce", 68),
              "busy": (ACOUSTIC_BASS, "bounce", 76), "intense": (ACOUSTIC_BASS, "bounce", 85)},
        arp={"menu": (HARP, 1, 60, 0), "calm": (NYLON_GUITAR, 2, 58, 0), "busy": (NYLON_GUITAR, 2, 62, 0), "intense": (HARP, 4, 70, 0)},
        drums={"calm": {"hits": [(LOW_CONGA, [0, 1.5, 2, 3.5], 75), (TAMBOURINE, [1, 3], 50), (MARACAS, EIGHTHS, 35)]},
               "busy": {"hits": [(LOW_CONGA, [0, 1.5, 2, 3.5], 85), (HIGH_CONGA, [0.75, 2.75], 70), (TAMBOURINE, [1, 3], 65),
                                 (MARACAS, EIGHTHS, 45)]},
               "intense": {"hits": [(LOW_TOM, [0, 1.5, 2, 3.5], 100), (LOW_CONGA, [0.75, 2.75], 85), (TAMBOURINE, EIGHTHS, 55),
                                    (SNARE, [1, 3], 80)], "fill": True}},
        sparkle={"menu": (GLOCKENSPIEL, 2), "calm": (GLOCKENSPIEL, 2), "busy": (CELESTA, 2), "intense": (TUBULAR_BELLS, "downbeats")},
        melody={"menu": (PAN_FLUTE, 0, "sparse", 60), "calm": (FLUTE, 0, "jig", 72),
                "busy": (FIDDLE, 0, "jig", 80), "intense": (BAGPIPE, 0, "jig", 70)},
    ),
}
SECTIONS = ["menu", "calm", "busy", "intense"]
RENDER = ["orchestral", "lofi", "retro", "arcane", "alchemy"]  # styles to make (celtic left out)


class Song:
    """Collects the notes for one layer of one section."""
    def __init__(self, seed, swing):
        self.programs = {}
        self.notes = []  # (start beat, length in beats, channel, pitch, velocity)
        self.rng = random.Random(seed)
        self.swing = swing

    def instrument(self, channel, program):
        self.programs[channel] = program

    def note(self, beat, length, channel, pitch, velocity):
        if self.swing and beat % 1 == 0.5:
            beat += self.swing  # push off-beat eighths late for a laid-back feel
        velocity = max(1, min(127, velocity + self.rng.randint(-4, 4)))  # tiny human feel
        self.notes.append((beat, length, channel, pitch, velocity))


# ---------------- layers ----------------

def pad(style, section, song):
    chords = style["chords"][section] * 2
    channel = 0
    for program, mode, velocity in style["pad"][section]:
        song.instrument(channel, program)
        for bar, chord in enumerate(chords):
            b = bar * 4
            tones = [A + n for n in chord]
            if mode == "hold":
                for p in tones:
                    song.note(b, 4, channel, p, velocity)
            elif mode == "hold+12":
                for p in tones:
                    song.note(b, 4, channel, p + 12, velocity)
            elif mode == "stabs":  # electric piano chords, a bit off the beat
                for beat, length in ((0, 1.5), (2.5, 1.2)):
                    for p in tones:
                        song.note(b + beat, length, channel, p, velocity)
            elif mode == "pulse":  # synth chords on every eighth note
                for k in range(8):
                    for p in tones:
                        song.note(b + k / 2, 0.35, channel, p, velocity if k % 2 == 0 else velocity - 15)
            elif mode == "strum":  # guitar strumming pattern, notes spread slightly like a real strum
                for beat in (0, 1, 1.5, 2.5, 3, 3.5):
                    for j, p in enumerate(tones + [A + chord[0] + 12]):
                        song.note(b + beat + j * 0.02, 0.45, channel, p, velocity - (10 if beat % 1 else 0))
            elif mode == "oompah":  # short chords on the off-beats ("pah"), the bass plays the "oom"
                for beat in (1, 3):
                    for p in tones:
                        song.note(b + beat, 0.4, channel, p, velocity)
            elif mode == "drone":  # bagpipe-style A + E underneath everything
                song.note(b, 4, channel, A - 12, velocity)
                song.note(b, 4, channel, A - 5, velocity)
        channel += 1
    program, pattern, velocity = style["bass"][section]
    song.instrument(channel, program)
    for bar, chord in enumerate(chords):
        b = bar * 4
        root = A + chord[0] - 12
        if root > A - 5:
            root -= 12
        nextroot = A + chords[(bar + 1) % len(chords)][0] - 12
        if nextroot > A - 5:
            nextroot -= 12
        if pattern == "whole":
            song.note(b, 4, channel, root, velocity)
        elif pattern == "half":
            for beat in (0, 2):
                song.note(b + beat, 1.8, channel, root, velocity)
        elif pattern == "eighths":
            for k in range(8):
                song.note(b + k / 2, 0.4, channel, root, velocity if k % 2 == 0 else velocity - 12)
        elif pattern == "octaves":
            for k in range(8):
                song.note(b + k / 2, 0.45, channel, root + (12 if k % 2 else 0), velocity)
        elif pattern == "walking":  # jazz bass: root, third, fifth, then a step into the next chord
            third = root + (chord[1] - chord[0])
            approach = nextroot - 1 if nextroot > root else nextroot + 1
            for k, p in enumerate((root, third, root + 7, approach)):
                song.note(b + k, 0.9, channel, p, velocity)
        elif pattern == "bounce":  # folk bass: root and fifth with a skip
            for beat, length, p in ((0, 1.2, root), (1.5, 0.4, root + 7), (2, 1.2, root), (3.5, 0.4, root + 7)):
                song.note(b + beat, length, channel, p, velocity)


def arp(style, section, song):
    program, perbeat, velocity, shift = style["arp"][section]
    song.instrument(0, program)
    for bar, chord in enumerate(style["chords"][section] * 2):
        tones = [A + n + 12 + shift for n in chord] + [A + chord[0] + 24 + shift]
        updown = tones + tones[-2:0:-1]
        lift = 12 if bar >= 4 and perbeat <= 2 else 0  # slower arps go up an octave in the second half
        for k in range(4 * perbeat):
            accent = 10 if k % perbeat == 0 else 0
            song.note(bar * 4 + k / perbeat, min(1.5 / perbeat, 1.2), 0, updown[k % len(updown)] + lift, velocity + accent)


def drums(style, section, song):
    spec = style["drums"].get(section)
    if not spec:
        return  # no drums (e.g. on the menu)
    chords = style["chords"][section] * 2
    song.instrument(DRUMS, spec.get("kit", STANDARD_KIT))
    for bar in range(BARS):
        b = bar * 4
        fillbar = spec.get("fill") and bar == BARS - 1
        if spec.get("timpani"):
            song.instrument(8, TIMPANI)
            song.note(b, 2, 8, A + chords[bar][0] - 12, 100)
        if spec.get("taiko"):  # big Japanese drum on its own channel
            song.instrument(7, TAIKO)
            for beat in spec["taiko"]:
                if not (fillbar and beat >= 2):
                    song.note(b + beat, 0.5, 7, A - 12, 110 if beat == 0 else 90)
        if spec.get("crash") and bar in (0, 4):
            song.note(b, 1, DRUMS, CRASH, 90)
        for drum, beats, velocity in spec["hits"]:
            for beat in beats:
                if fillbar and beat >= 2:
                    continue  # leave room for the fill
                song.note(b + beat, 0.25, DRUMS, drum, velocity)
        if fillbar:  # tom fill leading into the next loop
            for k, tom in enumerate([HIGH_TOM, HIGH_TOM, MID_TOM, MID_TOM, LOW_TOM, LOW_TOM, LOW_TOM, LOW_TOM]):
                song.note(b + 2 + k / 4, 0.25, DRUMS, tom, 100)


def sparkle(style, section, song):
    program, count = style["sparkle"][section]
    song.instrument(0, program)
    for bar, chord in enumerate(style["chords"][section] * 2):
        if count == "downbeats":  # one big bell per bar
            song.note(bar * 4, 2, 0, A + chord[0] + 12, 80)
            continue
        for spot in song.rng.sample(range(8), count):  # a few twinkles on random eighth notes
            song.note(bar * 4 + spot / 2, 1, 0, A + song.rng.choice(chord) + 24, 60)


def melody(style, section, song):
    """A tune that follows the chords: chord notes on strong beats, small steps in between.
    Bars 5-6 repeat bars 1-2 (so it sounds like a tune, not random notes) and bar 8 lands on the home note."""
    program, octave, rhythmstyle, velocity = style["melody"][section]
    song.instrument(0, program)
    theme = style.get("themes", {}).get(section)
    if theme:  # a hand-written tune: play it as written
        home = A + 12 + 12 * octave
        for bar, notes in enumerate(theme):
            for beat, length, pitch in notes:
                song.note(bar * 4 + beat, length * 0.95, 0, home + pitch, velocity + (8 if beat == 0 else 0))
        return
    rng = song.rng
    chords = style["chords"][section] * 2
    base = A + 12 + 12 * octave
    low, high = base - 5, base + 12
    bank = RHYTHMS[rhythmstyle]
    rhythms = [rng.choice(bank) for _ in range(4)]
    rhythms += [rhythms[0], rhythms[1], rng.choice(bank), [(0, 1), (1, 1), (2, 2)]]
    previous = base
    opening = []  # notes of bars 1-2, repeated in bars 5-6
    for bar in range(BARS):
        chord = chords[bar]
        if bar in (4, 5):
            for beat, length, pitch in opening[bar - 4]:
                song.note(bar * 4 + beat, length, 0, pitch, velocity + (8 if beat == 0 else 0))
            previous = opening[bar - 4][-1][2]
            continue
        chordtones = [n % 12 for n in chord]
        scale = [0, 2, 3, 5, 7, 8, 11] if 11 in chordtones else [0, 2, 3, 5, 7, 8, 10]  # E chord borrows G#
        pitches = [p for p in range(low, high + 1) if (p - A) % 12 in scale]
        notes = []
        for i, (beat, length) in enumerate(rhythms[bar]):
            last = bar == BARS - 1 and i == len(rhythms[bar]) - 1
            if beat in (0, 2) or last:  # strong beat: nearest chord note
                options = [p for p in pitches if (p - A) % 12 in chordtones]
                if last:
                    options = [p for p in options if (p - A) % 12 == chord[0] % 12] or options
                pitch = min(options, key=lambda p: abs(p - previous) + rng.random() * 3)
            else:  # in between: step up or down the scale
                index = min(range(len(pitches)), key=lambda k: abs(pitches[k] - previous))
                index = max(0, min(len(pitches) - 1, index + rng.choice([-2, -1, -1, 1, 1, 2])))
                pitch = pitches[index]
            notes.append((beat, length * 0.95, pitch))
            song.note(bar * 4 + beat, length * 0.95, 0, pitch, velocity + (8 if beat == 0 else 0))
            previous = pitch
        if bar < 2:
            opening.append(notes)


LAYERS = {"pad": pad, "arp": arp, "drums": drums, "sparkle": sparkle, "melody": melody}


# ---------------- MIDI file + rendering ----------------

def varlen(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


def writemidi(path, song, bpm):
    events = []  # (tick, order, bytes); note-offs sort before note-ons on the same tick
    for channel, program in song.programs.items():
        events.append((0, 0, bytes([0xC0 | channel, program])))
        events.append((0, 0, bytes([0xB0 | channel, 91, 60])))  # some reverb
    for beat, length, channel, pitch, velocity in song.notes:
        events.append((int(beat * TICKS), 2, bytes([0x90 | channel, pitch, velocity])))
        events.append((int((beat + length) * TICKS), 1, bytes([0x80 | channel, pitch, 0])))
    events.sort(key=lambda e: (e[0], e[1]))
    track = bytearray(b"\x00\xFF\x51\x03" + (60_000_000 // bpm).to_bytes(3, "big"))  # tempo
    last = 0
    for tick, _, data in events:
        track += varlen(tick - last) + data
        last = tick
    end = BARS * 4 * TICKS + 8 * TICKS  # keep going past the loop so reverb tails get rendered
    track += varlen(max(0, end - last)) + b"\xFF\x2F\x00"
    with open(path, "wb") as f:
        f.write(b"MThd" + struct.pack(">IHHH", 6, 0, 1, TICKS))
        f.write(b"MTrk" + struct.pack(">I", len(track)) + track)


def render(midipath, wavpath, gain):
    subprocess.run(["fluidsynth", "-ni", "-q", "-g", str(gain), "-r", str(RATE), "-F", wavpath, SOUNDFONT, midipath],
                   check=True, stderr=subprocess.DEVNULL)


def makeloop(wavpath, bpm):
    """Cut to exactly 8 bars and fold the ringing tail back onto the start, so it loops smoothly."""
    with wave.open(wavpath) as w:
        channels = w.getnchannels()
        samples = array.array("h", w.readframes(w.getnframes()))
    looplength = round(BARS * 4 * 60 / bpm * RATE) * channels
    loop = samples[:looplength]
    loop.extend([0] * (looplength - len(loop)))
    for i, v in enumerate(samples[looplength:2 * looplength]):
        loop[i] = max(-32768, min(32767, loop[i] + v))
    with wave.open(wavpath, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(loop.tobytes())
    return max(abs(v) for v in loop)


def main():
    for old in os.listdir(OUTFOLDER) if os.path.isdir(OUTFOLDER) else []:
        path = os.path.join(OUTFOLDER, old)
        if old.endswith(".ogg"):
            os.remove(path)  # files from before styles existed
        elif os.path.isdir(path) and old not in RENDER:
            shutil.rmtree(path)  # styles that are no longer made
    with tempfile.TemporaryDirectory() as tmp:
        print("soundfont:", SOUNDFONT)
        for stylename in RENDER:
            style = STYLES[stylename]
            folder = os.path.join(OUTFOLDER, stylename)
            shutil.rmtree(folder, ignore_errors=True)
            os.makedirs(folder)
            for section in SECTIONS:
                for layer, compose in LAYERS.items():
                    song = Song(seed=f"{stylename}-{section}-{layer}", swing=style["swing"])
                    compose(style, section, song)
                    if not song.notes:
                        continue  # the game plays silence for a missing layer
                    midi = os.path.join(tmp, "song.mid")
                    wav = os.path.join(tmp, "song.wav")
                    writemidi(midi, song, style["bpm"])
                    defaultgain = 1.4 if layer == "melody" else 0.9  # the tune should sit on top of the mix
                    render(midi, wav, style.get("gain", {}).get(layer, defaultgain))
                    peak = makeloop(wav, style["bpm"])
                    out = os.path.join(folder, f"{section}_{layer}.ogg")
                    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "4", out], check=True)
                    print(f"{stylename:10} {section:8} {layer:8} peak {peak / 32768:4.0%}")


if __name__ == "__main__":
    main()
