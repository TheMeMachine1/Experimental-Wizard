"""
Adaptive music for Experimental Wizard.

The music lives in music/<style>/<section>_<layer>.ogg (made by tools/make_music.py).
A section is 8 bars and has five layers that loop in sync. All five layers always play;
their volumes follow what's on screen, and the next section is picked when the current one
ends, so changes land on the beat. Every couple of minutes the whole style changes.

The game uses three things:
    music.load()                 once, after the mixer is set up
    music.start(section)         jump straight to a section ("menu", "calm", ...)
    music.update(mood, volume)   every frame; mood describes the screen (see measuremood in example.py)
"""
import os
import random
import sys
import threading

import pygame

# The music lives in music/<style>/<section>_<layer>.ogg (made by tools/make_music.py).
# A section is 8 bars and has five layers that loop in sync. All five layers always play;
# their volumes follow what's on screen (see updatemusic), and the next section is picked when
# the current one ends, so changes land on the beat. Every couple of minutes the whole style changes.
musicstyles = ["orchestral", "lofi", "retro", "arcane", "alchemy"]
musicsections = ["menu", "calm", "busy", "intense"]
musiclayers = ["pad", "arp", "drums", "sparkle", "melody"]
styleseconds = 120     # how long one style plays before switching to another
availablestyles = []   # styles whose files exist
musiclibrary = {}      # style -> its tracks (only the current style, plus the next one while it loads)
musictracks = {}       # tracks of the current style: (section, layer) -> Sound
musicstyle = None

def musicfolder(style):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "music", style)

def loadstyle(style):
    # returns {(section, layer): Sound}, or None if the files are missing
    tracks = {}
    for section in musicsections:
        padpath = os.path.join(musicfolder(style), section + "_pad.ogg")
        if not os.path.exists(padpath):
            return None
        pad = pygame.mixer.Sound(padpath)
        for layer in musiclayers:
            path = os.path.join(musicfolder(style), section + "_" + layer + ".ogg")
            if os.path.exists(path):
                tracks[(section, layer)] = pygame.mixer.Sound(path)
            else:  # e.g. no drums on the menu: silence of the same length keeps the layers in sync
                tracks[(section, layer)] = pygame.mixer.Sound(buffer=bytes(len(pad.get_raw())))
    return tracks

def preloadstyle(style):
    # runs in a background thread so loading the next style doesn't freeze the game
    musiclibrary[style] = loadstyle(style)

def load():
    # pick a random style to start with and load it
    global musictracks, musicstyle
    for style in musicstyles:
        if os.path.isdir(musicfolder(style)):
            availablestyles.append(style)
    random.shuffle(availablestyles)
    for style in list(availablestyles):
        tracks = loadstyle(style)
        if tracks:
            musicstyle = style
            musictracks = tracks
            musiclibrary[style] = tracks
            return
        availablestyles.remove(style)

musicchannels = []  # one mixer channel per layer
musicsection = "menu"
queuedsection = None     # section waiting to play after the current one
queuedstyle = None       # ...and which style it's from
stylestart = 0           # when the current style started (milliseconds)
nextmusicstyle = None    # style being loaded / waiting to take over
layerlevels = {layer: 0.0 for layer in musiclayers}

def start(section):
    # (re)start all layers together at the beginning of a section
    global musicchannels, musicsection, queuedsection, queuedstyle
    if not musictracks:
        return
    if not musicchannels:
        pygame.mixer.set_num_channels(16)
        pygame.mixer.set_reserved(len(musiclayers))  # keep these channels for music only
        musicchannels = [pygame.mixer.Channel(i) for i in range(len(musiclayers))]
    for channel, layer in zip(musicchannels, musiclayers):
        channel.play(musictracks[(section, layer)])
    musicsection = section
    queuedsection = None  # updatemusic queues the next one
    queuedstyle = None

def pickmusicsection(mood):
    if mood["menu"]:
        return "menu"
    if mood["reactions"] > 0.8 or mood["hot"] > 1500:
        return "intense"
    if mood["moving"] > 400 or mood["hot"] > 300:
        return "busy"
    return "calm"

def layertargets(mood):
    # how loud each layer should be right now (0 to 1)
    if mood["menu"]:
        return {"pad": 1, "arp": 0.6, "drums": 0, "sparkle": 0.7, "melody": 0.8}
    return {
        "pad": 1,
        "melody": 0.85,
        "arp": 0.3 + min(0.7, mood["moving"] / 800),
        "drums": min(1, mood["reactions"] / 3 + mood["hot"] / 4000 + mood["moving"] / 2000),
        "sparkle": min(1, 0.15 + mood["circles"] / 2),
    }

def queuenext(mood):
    # Keep the next section queued on every layer. The mixer starts it the instant the current
    # one ends, so there's no gap and no guessing about timing. If the mood changes, the queued
    # section is swapped for a better fit.
    global queuedsection, queuedstyle
    section = pickmusicsection(mood)
    style = musicstyle
    if nextmusicstyle is not None and musiclibrary.get(nextmusicstyle):
        style = nextmusicstyle  # the next style has finished loading: switch at this boundary
    if (section, style) != (queuedsection, queuedstyle):
        for channel, layer in zip(musicchannels, musiclayers):
            channel.queue(musiclibrary[style][(section, layer)])
        queuedsection = section
        queuedstyle = style

def update(mood, volume):
    # call every frame: mood says what's on screen, volume is 0 to 1 (0 when sound is off)
    global musicsection, queuedsection, queuedstyle
    global musicstyle, musictracks, stylestart, nextmusicstyle
    if not musicchannels:
        return
    now = pygame.time.get_ticks()
    # time for a new style: start loading one in the background
    if nextmusicstyle is None and len(availablestyles) > 1 and now - stylestart > styleseconds * 1000:
        nextmusicstyle = random.choice([style for style in availablestyles if style != musicstyle])
        if sys.platform == "emscripten":
            preloadstyle(nextmusicstyle)  # no threads in a web browser: load it right away
        else:
            threading.Thread(target=preloadstyle, args=(nextmusicstyle,), daemon=True).start()
    if nextmusicstyle is not None and nextmusicstyle in musiclibrary and musiclibrary[nextmusicstyle] is None:
        availablestyles.remove(nextmusicstyle)  # its files were missing; forget it
        del musiclibrary[nextmusicstyle]
        nextmusicstyle = None
        stylestart = now
    # the queued section has started playing (the queue slot is empty again)
    if queuedsection is not None and musicchannels[0].get_queue() is None:
        musicsection = queuedsection
        if queuedstyle != musicstyle:
            del musiclibrary[musicstyle]  # free the old style's memory
            musicstyle = queuedstyle
            musictracks = musiclibrary[musicstyle]
            nextmusicstyle = None
            stylestart = now
        queuedsection = None
        queuedstyle = None
    # if the music really ran out (nothing playing AND nothing queued), start again.
    # (Not busy but still queued just means the mixer is about to start the queued section.)
    if not musicchannels[0].get_busy() and musicchannels[0].get_queue() is None:
        start(pickmusicsection(mood))
    queuenext(mood)
    # fade each layer toward its target (about a second to get there)
    targets = layertargets(mood)
    for channel, layer in zip(musicchannels, musiclayers):
        layerlevels[layer] += (targets[layer] - layerlevels[layer]) * 0.03
        channel.set_volume(layerlevels[layer] * volume)
