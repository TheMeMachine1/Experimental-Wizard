"""
The side panel: material tabs, the material list, the volume sliders and the brush slider.

Each palette item goes under a tab worked out from what it is (see categoryof), so a new
material added to `materials` in example.py shows up in the right tab by itself.

`g` is a link to the game (example.py); g.something is always the game's current value.
"""
import pygame

import audio
import display

g = None

categories = ["Liquids", "Powders", "Solids", "Energy", "Forces"]
tabcolors = {"Liquids": (70, 130, 255), "Powders": (220, 180, 110), "Solids": (160, 160, 175),
             "Energy": (255, 120, 50), "Forces": (170, 110, 255)}
currenttab = "Liquids"
panelw = 185          # usable width of the side panel
tabh, tabgap = 22, 5  # tab button height and the space between tabs
rowh = 30             # height of one material row
volumey = {}          # y of each volume slider line (set by relayout)
# panel colours
cardcolor = (38, 38, 72)
cardedge = (62, 62, 104)
rowhover = (52, 52, 96)
dimtext = (150, 150, 185)
trackcolor = (70, 70, 110)
fillcolor = (120, 140, 255)
headerfont = None  # fonts are made in setup(), after pygame has started
tabfont = None


def setup(game):
    global g, headerfont, tabfont
    g = game
    headerfont = pygame.font.Font(None, 17)
    tabfont = pygame.font.Font(None, 18)
    relayout()


def relayout():
    # called at startup and whenever the window resize moves the bottom of the panel
    volumey.update(music=g.slidery - 110, effects=g.slidery - 60)


def mixcolor(a, b, amount):
    # blend colour a toward colour b (amount 0 to 1)
    return tuple(int(a[i] + (b[i] - a[i]) * amount) for i in range(3))


def categoryof(material):
    if material.get("background"):
        return "Forces"
    return {"liquid": "Liquids", "powder": "Powders", "solid": "Solids"}.get(material.get("move"), "Energy")


def tabrect(k):
    # 3 tabs on the top row, 2 wider ones below, together filling the panel width
    top = g.paneltop + 12
    if k < 3:
        w = (panelw - 2 * tabgap) / 3
        return pygame.Rect(round(g.panelx + k * (w + tabgap)), top, round(w), tabh)
    w = (panelw - tabgap) / 2
    return pygame.Rect(round(g.panelx + (k - 3) * (w + tabgap)), top + tabh + tabgap, round(w), tabh)


def visiblerows():
    # (index into scrollist, y) for every row shown right now. Drawing AND clicking both use this,
    # so what you see is always what you click.
    rows = []
    y = g.paneltop + 12 + 2 * (tabh + tabgap) + 12
    if g.air in g.scrollist:
        rows.append((g.scrollist.index(g.air), y))  # the Eraser, always there
        y += rowh + 10                              # room for the divider under it
    lastrow = volumey["music"] - 70                 # stop before the SOUND section
    for i, material in enumerate(g.scrollist):
        if material is not g.air and categoryof(material) == currenttab and y + rowh <= lastrow:
            rows.append((i, y))
            y += rowh
    return rows


def rowrect(y):
    return pygame.Rect(g.panelx - 4, y, panelw + 8, rowh - 4)


# ---------- clicks ----------

def picktab(mx, my):
    # if a tab was clicked, switch to it (returns True)
    global currenttab
    for k, name in enumerate(categories):
        if tabrect(k).collidepoint(mx, my) and name != currenttab:
            currenttab = name
            return True
    return False


def picksubtype(mx, my):
    for i, y in visiblerows():
        if rowrect(y).collidepoint(mx, my):
            return g.scrollist[i]
    return False


def volumeclick(mx, my):
    # if the click is on a volume slider: (which slider, new volume 0 to 1)
    for name, y in volumey.items():
        if y - 8 <= my <= y + 8 and g.panelx - 5 <= mx <= g.sliderend + 5:
            return name, max(0.0, min(1.0, (mx - g.panelx) / (g.sliderend - g.panelx)))
    return None


def brushsize(mx, my):
    if g.slidery - 8 <= my <= g.slidery + 8:
        if g.panelx - 5 <= mx <= g.sliderend + 5:
            return max(0, min((g.sliderend - g.panelx) // g.notch, (mx - g.panelx) // g.notch))
    return None


def click(mx, my, firstclick):
    # the mouse is held at (mx, my): handle tabs, materials, volume sliders and the brush slider
    if firstclick and picktab(mx, my):
        audio.playsound("click")
    picked = picksubtype(mx, my)
    if picked != False:
        if picked is not g.substaince:
            audio.playsound("click")
        g.substaince = picked
    volume = volumeclick(mx, my)
    if volume:
        if volume[0] == "music":
            g.musicvolume = volume[1]
        else:
            g.effectsvolume = volume[1]
            audio.applyeffectvolume()
    newbrush = brushsize(mx, my)
    if newbrush is not None:
        if newbrush != g.brush:
            audio.playsound("click")
        g.brush = newbrush


# ---------- drawing ----------

def drawslider(y, amount, label):
    # label above, a rounded track, the filled part in colour, and a round knob
    screen = g.screen
    screen.blit(g.font.render(label, True, g.white), (g.panelx, y - 25))
    knobx = g.panelx + int(amount * (g.sliderend - g.panelx))
    pygame.draw.line(screen, trackcolor, (g.panelx, y), (g.sliderend, y), 4)
    pygame.draw.line(screen, fillcolor, (g.panelx, y), (knobx, y), 4)
    pygame.draw.circle(screen, g.white, (knobx, y), 6)


def drawvolume(name, label, value):
    amount = "muted (M)" if g.muted else str(round(value * 100)) + "%"
    drawslider(volumey[name], value, label + ": " + amount)


def draw(selected, brush):
    screen, panelx, air = g.screen, g.panelx, g.air
    mx, my = display.gamemouse(pygame.mouse.get_pos())
    pygame.draw.rect(screen, g.background, (panelx - 14, 0, g.xframe - panelx + 14, g.yframe))
    card = pygame.Rect(panelx - 10, 8, panelw + 20, g.yframe - 12)
    pygame.draw.rect(screen, cardcolor, card, border_radius=10)
    pygame.draw.rect(screen, cardedge, card, 1, border_radius=10)
    # MATERIALS header and tabs
    screen.blit(headerfont.render("MATERIALS", True, dimtext), (panelx, g.paneltop - 4))
    selectedtab = None if selected is air else categoryof(selected)
    for k, name in enumerate(categories):
        rect = tabrect(k)
        color = tabcolors[name]
        if name == currenttab:
            pygame.draw.rect(screen, mixcolor(cardcolor, color, 0.45), rect, border_radius=6)
            pygame.draw.rect(screen, color, rect, 1, border_radius=6)
            text = g.white
        else:
            hover = rect.collidepoint(mx, my)
            pygame.draw.rect(screen, rowhover if hover else (46, 46, 86), rect, border_radius=6)
            text = dimtext
        label = tabfont.render(name, True, text)
        screen.blit(label, label.get_rect(center=rect.center))
        if name == selectedtab:  # small dot: your selected material is in this tab
            pygame.draw.circle(screen, color, (rect.right - 6, rect.top + 6), 3)
    # material rows
    accent = tabcolors.get(selectedtab, (200, 200, 220))
    for n, (i, y) in enumerate(visiblerows()):
        material = g.scrollist[i]
        row = rowrect(y)
        if material is selected:
            pygame.draw.rect(screen, mixcolor(cardcolor, accent, 0.3), row, border_radius=6)
            pygame.draw.rect(screen, accent, (row.x, row.y + 3, 3, row.height - 6), border_radius=2)
        elif row.collidepoint(mx, my):
            pygame.draw.rect(screen, rowhover, row, border_radius=6)
        swatch = pygame.Rect(panelx + 6, row.centery - 8, 16, 16)
        pygame.draw.rect(screen, material.get("color"), swatch, border_radius=4)
        pygame.draw.rect(screen, (200, 200, 225), swatch, 1, border_radius=4)
        if material is air:  # Eraser: a little x
            pygame.draw.line(screen, (230, 90, 90), (swatch.x + 4, swatch.y + 4), (swatch.right - 5, swatch.bottom - 5), 2)
            pygame.draw.line(screen, (230, 90, 90), (swatch.right - 5, swatch.y + 4), (swatch.x + 4, swatch.bottom - 5), 2)
        label = g.labels[i]
        screen.blit(label, (swatch.right + 10, row.centery - label.get_height() // 2))
        if n == 0 and material is air:  # divider under the Eraser
            pygame.draw.line(screen, cardedge, (panelx, row.bottom + 7), (panelx + panelw, row.bottom + 7), 1)
    # SOUND and brush
    screen.blit(headerfont.render("SOUND", True, dimtext), (panelx, volumey["music"] - 48))
    drawvolume("music", "Music", g.musicvolume)
    drawvolume("effects", "Effects", g.effectsvolume)
    maxbrush = (g.sliderend - panelx) // g.notch
    drawslider(g.slidery, brush / maxbrush, "Brush size: " + str(brush))
