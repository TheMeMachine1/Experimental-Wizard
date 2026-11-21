"""
The welcome screen: the sandbox runs behind the title with random drops and moving force
circles, and a Play button starts the game.

`g` is a link to the game (example.py); g.something is always the game's current value.
"""
import random

import pygame

import audio
import display
import music

g = None

titlefont = None   # fonts are made in setup(), after pygame has started
buttonfont = None
playbutton = pygame.Rect(0, 0, 200, 64)
welcomedrops = []  # what rains down behind the menu
circles = []       # screen positions of the force circles placed behind the menu


def setup(game):
    global g, titlefont, buttonfont, welcomedrops
    g = game
    titlefont = pygame.font.Font(None, 96)
    buttonfont = pygame.font.Font(None, 48)
    # no water: water + lava makes solid obsidian that piles up mid-air
    welcomedrops = [g.lava, g.magicpowder, g.redsand, g.fire, g.magic]
    relayout(0)


def relayout(shift):
    # called at startup and when the window resize adds/removes `shift` rows at the top
    playbutton.center = (g.xframe // 2, g.yframe // 2 + 60)
    top, bottom = g.border, g.border + g.ypixframe * g.pixelsize
    circles[:] = [(mx, my + shift * g.pixelsize) for mx, my in circles
                  if top <= my + shift * g.pixelsize < bottom and mx < g.border + g.xpixframe * g.pixelsize]


def start():
    for _ in range(4):
        addcircle()


def addcircle():
    # swap the oldest background circle for a new random one
    if len(circles) >= 4:
        oldx, oldy = circles.pop(0)
        g.backgroundpaint(oldx, oldy, g.empty, g.backgroundgrid)
    mx = g.border + random.randrange(g.bigxpixframe * g.bigpixelsize)
    my = g.border + random.randrange(g.bigypixframe * g.bigpixelsize)
    g.backgroundpaint(mx, my, random.choice([g.windcircle, g.windcircle, g.gravitycircle, g.blackholew]), g.backgroundgrid)
    circles.append((mx, my))


def step():
    # one frame of the sandbox behind the menu
    g.flipscreen = 1 - g.flipscreen
    if random.random() < 1/180:  # about every 3 seconds
        addcircle()
    # now and then drop a random blob of a random material near the top
    if random.random() < 0.5:
        material = random.choice(welcomedrops)
        lifespan = material.get("lifespam")
        x = random.randrange(g.xpixframe)
        y = random.randrange(15)
        size = random.randint(1, 3)
        if lifespan == "none":
            g.paint(x, y, material, size, g.grid, 0, 1)
        else:
            g.paint(x, y, material, size, g.grid, lifespan, 0)
    # drain all four edges so nothing piles up; stuff blown off-screen just disappears
    grid, changegrid, air = g.grid, g.changegrid, g.air
    for x in range(g.xpixframe):
        for y in (0, g.ypixframe - 1):
            grid[x][y] = air
        changegrid[x][1] = 1
        changegrid[x][g.ypixframe - 2] = 1
    for y in range(g.ypixframe):
        for x in (0, g.xpixframe - 1):
            grid[x][y] = air
        changegrid[1][y] = 1
        changegrid[g.xpixframe - 2][y] = 1
    g.updategrid(g.flipscreen)
    g.updatecountgrid()
    g.show()


def stretch():
    # stretch the sandbox over the whole window (cropping a bit of top and bottom)
    # so the menu has no empty strip where the side panel normally goes
    sim = g.screen.subsurface((g.border, g.border, g.xpixframe * g.pixelsize, g.ypixframe * g.pixelsize))
    stretchedh = g.xframe * g.ypixframe // g.xpixframe
    g.screen.blit(pygame.transform.scale(sim, (g.xframe, stretchedh)), (0, (g.yframe - stretchedh) // 2))


def draw(mx, my):
    screen = g.screen
    title = "Experimental Wizard"
    shadow = titlefont.render(title, True, (0, 0, 0))
    text = titlefont.render(title, True, g.white)
    titlepos = text.get_rect(center=(g.xframe // 2, g.yframe // 2 - 60))
    screen.blit(shadow, titlepos.move(4, 4))
    screen.blit(text, titlepos)
    buttoncolor = (90, 90, 160) if playbutton.collidepoint(mx, my) else (60, 60, 110)
    pygame.draw.rect(screen, buttoncolor, playbutton, border_radius=12)
    pygame.draw.rect(screen, g.white, playbutton, 3, border_radius=12)
    label = buttonfont.render("Play", True, g.white)
    screen.blit(label, label.get_rect(center=playbutton.center))


def frame():
    # everything the welcome screen does in one frame
    step()
    stretch()
    draw(*display.gamemouse(pygame.mouse.get_pos()))
    music.update(audio.menumood, audio.musiclevel())


def cleargrid():
    for x in range(g.xpixframe):
        for y in range(g.ypixframe):
            g.grid[x][y] = g.air
            g.countgrid[x][y] = 0
            g.changegrid[x][y] = 0
    for mx, my in circles:
        g.backgroundpaint(mx, my, g.empty, g.backgroundgrid)
    circles.clear()


def playclicked(event):
    # True if this event is a click on Play (and gets the game ready to start)
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if playbutton.collidepoint(display.gamemouse(event.pos)):
            audio.playsound("chime")
            music.start("calm")  # jump straight into the game music (the chime covers the cut)
            cleargrid()
            g.screen.fill(g.background)
            return True
    return False
