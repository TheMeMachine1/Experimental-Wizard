"""
Sound effects, and the "mood" that steers the music (see music.py).

Effects use recordings from sounds/<name>.ogg when they exist (made by tools/prepare_sounds.py),
otherwise a stand-in sound is generated from code at startup.

`g` is a link to the game (example.py); g.something is always the game's current value.
"""
import array
import math
import os
import random

import pygame

import music

g = None

sounds = {}       # name -> Sound
soundvolume = {}  # base volume of each effect (recorded files are normalized, so they're turned down here)
soundrate = 44100
soundchannels = 2


def setup(game):
    global g
    g = game


# ---------- making sounds from code ----------

def normalize(track):
    peak = max(abs(v) for v in track) or 1
    return [v / peak for v in track]


def tone(freq, length, decay):
    # a sine beep that fades out
    rate = soundrate
    return [math.sin(2*math.pi*freq*i/rate) * math.exp(-decay*i/rate) for i in range(int(length*rate))]


def chirp(startfreq, endfreq, length):
    # a beep that slides in pitch (bubbles, plops)
    out, phase, n = [], 0.0, int(length*soundrate)
    for i in range(n):
        phase += 2*math.pi*(startfreq + (endfreq - startfreq)*i/n)/soundrate
        out.append(math.sin(phase) * (1 - i/n))
    return out


def noise(length, smooth):
    # random noise; small smooth = deep rumble, smooth near 1 = bright hiss
    out, level = [], 0.0
    for i in range(int(length*soundrate)):
        level += smooth * (random.uniform(-1, 1) - level)
        out.append(level)
    return normalize(out)


def scatter(short, times, length):
    # drop copies of a short sound into a silent track at the given times
    out = [0.0] * int(length*soundrate)
    for t in times:
        start = int(t*soundrate)
        for i, v in enumerate(short):
            if start + i < len(out):
                out[start + i] += v
    return out


def mix(*tracks):
    return [sum(t[i] for t in tracks if i < len(t)) for i in range(max(len(t) for t in tracks))]


def makesound(track, volume):
    data = array.array("h")
    for v in track:
        data.extend([int(max(-1.0, min(1.0, v*volume)) * 32767)] * soundchannels)
    return pygame.mixer.Sound(buffer=data.tobytes())


def randomtimes(persecond, length):
    return [random.uniform(0, length) for _ in range(int(persecond*length))]


def bubble(freq, length):
    # one lava "bloop": the pitch jumps up as the bubble pops, and it dies away fast
    out, phase, n = [], 0.0, int(length*soundrate)
    for i in range(n):
        t = i / n
        phase += 2*math.pi*freq*(1 + 1.5*t) / soundrate
        out.append(math.sin(phase) * math.exp(-5*t) * min(1, i / (0.005*soundrate)))
    return out


def makelava():
    # 3-second loop: thick bubbles of random sizes, a low rumble, and a few hot-rock crackles
    length = 3.0
    out = [v * 0.25 for v in noise(length, 0.008)]
    for _ in range(int(10 * length)):
        size = random.uniform(0.06, 0.15)                 # bigger bubbles are lower and last longer
        pop = bubble(random.uniform(90, 260) * 0.1 / size, size)
        start = int(random.uniform(0, length - size) * soundrate)  # never cut off at the loop point
        loudness = random.uniform(0.4, 1.0)
        for i, v in enumerate(pop):
            out[start + i] += v * loudness
    crackle = [v * (1 - i/180) for i, v in enumerate(noise(180/soundrate, 0.9))]
    for _ in range(int(6 * length)):
        start = int(random.uniform(0, length - 0.01) * soundrate)
        for i, v in enumerate(crackle):
            out[start + i] += v * 0.15
    return normalize(out)


def addsound(name, volume, generate):
    # Use the recording in sounds/<name>.ogg if there is one, otherwise generate a stand-in sound.
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds", name + ".ogg")
    if os.path.exists(path):
        sounds[name] = pygame.mixer.Sound(path)
        soundvolume[name] = volume
    else:
        sounds[name] = generate()
        soundvolume[name] = 1.0  # generated sounds have their volume built in
    sounds[name].set_volume(soundvolume[name])


def load():
    # make/load every effect and the music (does nothing if there's no sound device)
    global soundrate, soundchannels
    if not (pygame.mixer.get_init() and pygame.mixer.get_init()[1] == -16):
        return
    soundrate, _, soundchannels = pygame.mixer.get_init()
    addsound("click", 0.4, lambda: makesound(tone(1400, 0.05, 80), 0.3))
    addsound("chime", 0.5, lambda: makesound(mix(tone(660, 0.6, 6), scatter(tone(990, 0.5, 6), [0.12], 0.7)), 0.3))
    whoosh = noise(0.6, 0.15)
    addsound("whoosh", 0.5, lambda: makesound([v * math.sin(math.pi*i/len(whoosh))**2 for i, v in enumerate(whoosh)], 0.35))
    hiss = noise(0.5, 0.9)
    addsound("sizzle", 0.3, lambda: makesound([v * (1 - i/len(hiss))**2 for i, v in enumerate(hiss)], 0.25))
    # looping sounds while painting a material
    addsound("water", 0.5, lambda: makesound(mix(scatter(chirp(300, 900, 0.04), randomtimes(12, 1), 1), [v*0.15 for v in noise(1, 0.05)]), 0.35))
    addsound("lava", 0.55, lambda: makesound(makelava(), 0.45))
    addsound("fire", 0.5, lambda: makesound(mix(scatter([v*(1 - i/150) for i, v in enumerate(noise(150/soundrate, 0.9))], randomtimes(40, 1), 1),
                                                [v*0.3 for v in noise(1, 0.03)]), 0.35))
    addsound("powder", 0.35, lambda: makesound([v * (0.7 + 0.3*math.sin(2*math.pi*7*i/soundrate)) for i, v in enumerate(noise(1, 0.6))], 0.15))
    addsound("magic", 0.4, lambda: makesound(scatter(tone(random.uniform(1800, 3500), 0.15, 30), randomtimes(15, 1), 1), 0.2))
    music.load()


# ---------- playing effects ----------

def effectlevel(name):
    # how loud an effect should play: its own level x the Effects slider (0 when muted)
    return 0 if g.muted else soundvolume[name] * g.effectsvolume


def applyeffectvolume():
    # after the slider or mute changes, update sounds that may already be playing
    for name in sounds:
        sounds[name].set_volume(effectlevel(name))


def togglemute():
    g.muted = not g.muted
    applyeffectvolume()


def playsound(name):
    if name in sounds:
        sounds[name].set_volume(effectlevel(name))
        sounds[name].play()


paintloop = None  # name of the looping paint sound that's playing right now


def setpaintloop(name):
    # start/stop the looping sound for whatever is being painted (None = silence)
    global paintloop
    if name == paintloop:
        return
    if paintloop in sounds:
        sounds[paintloop].fadeout(150)
    if name in sounds:
        sounds[name].set_volume(effectlevel(name))
        sounds[name].play(loops=-1, fade_ms=80)
    paintloop = name


def paintsoundfor(material):
    if material is g.water: return "water"
    if material is g.lava: return "lava"
    if material is g.fire: return "fire"
    if material is g.magic: return "magic"
    if material is g.magicpowder or material is g.rock: return "powder"
    return None  # eraser is silent


sizzlechannel = None


def playsizzle(count):
    # one sizzle at a time, louder when lots of things are reacting
    global sizzlechannel
    if "sizzle" in sounds and (sizzlechannel is None or not sizzlechannel.get_busy()):
        sounds["sizzle"].set_volume(effectlevel("sizzle") * min(1.0, 0.3 + count / 20))
        sizzlechannel = sounds["sizzle"].play()


# ---------- the mood that steers the music ----------

reactheat = 0.0  # reactions per frame, smoothed so one sizzle doesn't flip the mood
hotcount = 0     # fire + lava cells (counted every few frames)
moodframe = 0
menumood = {"menu": True}


def measuremood():
    global reactheat, hotcount, moodframe
    reactheat += (g.interactions - reactheat) * 0.05
    moodframe += 1
    if moodframe % 10 == 0:
        hotcount = sum(column.count(g.fire) + column.count(g.lava) for column in g.grid)
    return {
        "menu": False,
        "reactions": reactheat,
        "moving": len(g.moved),  # cells that actually moved this frame
        "hot": hotcount,
        "circles": sum(1 for column in g.backgroundgrid for cell in column if cell is not g.empty),
    }


def musiclevel():
    # the Music slider, or 0 when muted
    return 0 if g.muted else g.musicvolume
