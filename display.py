"""
The window: scaling the game picture to fit it, turning mouse positions back into game
positions, and growing/shrinking the world when the window (or browser tab) changes shape.

`g` is a link to the game (example.py). Use g.something for the game's variables so you always
get the current one - the window resize below replaces g.grid, g.screen and others.
"""
import pygame

import panel
import welcome

g = None

viewscale = 1  # how much the picture is scaled in the window
viewx = 0      # where the picture starts in the window
viewy = 0
maxxpixframe = 280  # biggest world, in cells (a bigger world means more work every frame)
maxypixframe = 200
windowsize = None   # last window size seen by checkwindow()


def setup(game):
    global g
    g = game


def present():
    # scale the game picture to fit the window, keeping its shape
    global viewscale, viewx, viewy
    windoww, windowh = g.window.get_size()
    viewscale = min(windoww / g.xframe, windowh / g.yframe)
    picturew = int(g.xframe * viewscale)
    pictureh = int(g.yframe * viewscale)
    viewx = (windoww - picturew) // 2
    viewy = (windowh - pictureh) // 2
    g.window.fill((0, 0, 0))
    g.window.blit(pygame.transform.smoothscale(g.screen, (picturew, pictureh)), (viewx, viewy))
    pygame.display.flip()


def gamemouse(pos):
    # turn a position in the window into a position in the game
    return (int((pos[0] - viewx) / viewscale), int((pos[1] - viewy) / viewscale))


# ---------- fitting the window ----------
# When the window changes shape, the world gains or loses rows/columns so the game fills the
# window exactly instead of showing bars. Never smaller than the original size.

def regrid(old, oldw, oldh, neww, newh, fill, shift):
    # copy a grid into a new size; shift moves everything down (keeps piles on the floor)
    new = [[fill] * newh for _ in range(neww)]
    for x in range(min(oldw, neww)):
        for y in range(oldh):
            if 0 <= y + shift < newh:
                new[x][y + shift] = old[x][y]
    return new


def resizeworld(newx, newy, width, height):
    shift = newy - g.ypixframe  # rows are added/removed at the top
    oldx, oldy, oldbx, oldby = g.xpixframe, g.ypixframe, g.bigxpixframe, g.bigypixframe
    g.grid = regrid(g.grid, oldx, oldy, newx, newy, g.air, shift)
    g.countgrid = regrid(g.countgrid, oldx, oldy, newx, newy, 0, shift)
    g.forcegrid = regrid(g.forcegrid, oldx, oldy, newx, newy, 0, shift)
    g.changegrid = [[1] * newy for _ in range(newx)]  # wake everything up so it settles into the new space
    g.backgroundgrid = regrid(g.backgroundgrid, oldbx, oldby, newx // 10, newy // 10, g.empty, shift // 10)
    g.backgrounddirgrid = regrid(g.backgrounddirgrid, oldbx, oldby, newx // 10, newy // 10, 0, shift // 10)
    g.moved.clear()
    g.xpixframe, g.ypixframe, g.bigxpixframe, g.bigypixframe = newx, newy, newx // 10, newy // 10
    g.xframe, g.yframe = width, height
    g.panelx = g.pixelsize * g.xpixframe + g.border * 2
    g.slidery = g.border + g.pixelsize * g.ypixframe
    g.sliderend = g.panelx + 180
    g.screen = pygame.Surface((g.xframe, g.yframe))
    g.screen.fill(g.background)
    g.overlay = pygame.Surface((g.xframe, g.yframe), pygame.SRCALPHA)
    panel.relayout()
    welcome.relayout(shift)


def fitwindow(windoww, windowh):
    # pick a drawing size with the same shape as the window, then size the world to match
    aspect = windoww / max(1, windowh)
    if aspect >= g.basexframe / g.baseyframe:  # wider than the game: add columns
        height = g.baseyframe
        width = round(height * aspect)
    else:                                      # taller than the game: add rows
        width = g.basexframe
        height = round(width / aspect)
    if (width, height) == (g.xframe, g.yframe):
        return
    newx = max(160, min(maxxpixframe, (width - 2 * g.border - g.controlsb) // g.pixelsize // 10 * 10))
    newy = max(120, min(maxypixframe, (height - 2 * g.border) // g.pixelsize // 10 * 10))
    resizeworld(newx, newy, width, height)
    if g.web:
        import platform  # pygbag's link to the web page
        g.window = pygame.display.set_mode((width, height))
        platform.window.window_resize()  # tell the page to re-fit the canvas


def checkwindow():
    # called every frame: notice when the window / browser tab changes size
    global windowsize
    if g.web:
        import platform
        size = (platform.window.innerWidth, platform.window.innerHeight)
    else:
        size = g.window.get_size()
    if size != windowsize:
        windowsize = size
        fitwindow(*size)
