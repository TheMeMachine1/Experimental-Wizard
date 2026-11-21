import pygame
import random
import math
import array
import os
import threading

pygame.mixer.pre_init(44100, -16, 2, 512)  # CD-quality stereo (for the music), small buffer so effects play quickly
pygame.init()
pixelsize = 5
xpixframe = 160
ypixframe = 120
bigxpixframe = xpixframe // 10
bigypixframe = ypixframe // 10
bigpixelsize = pixelsize * 10
border = 15
controlsb = 200
xframe = pixelsize * xpixframe + border * 2 + controlsb
yframe = pixelsize * ypixframe + border * 2
# right-side panel layout (drawing and click checks both use these)
panelx = pixelsize * xpixframe + border * 2   # left edge of the panel
paneltop = border + 10                        # y of the first material row
rowgap = 40                                   # distance between material rows
boxsize = 17                                  # material swatch size
slidery = border + pixelsize * ypixframe      # y of the brush slider
sliderend = xframe - 20                       # right end of the brush slider
notch = 7                                     # slider pixels per brush step
brush = 1
flipscreen = 0
window = pygame.display.set_mode((xframe, yframe), pygame.RESIZABLE)
screen = pygame.Surface((xframe, yframe))  # the game draws here at its normal size; present() fits it to the window
viewscale = 1  # how much the picture is scaled in the window
viewx = 0      # where the picture starts in the window (black bars fill the rest)
viewy = 0

def present():
    # scale the game picture to fit the window, keeping its shape
    global viewscale, viewx, viewy
    windoww, windowh = window.get_size()
    viewscale = min(windoww / xframe, windowh / yframe)
    picturew = int(xframe * viewscale)
    pictureh = int(yframe * viewscale)
    viewx = (windoww - picturew) // 2
    viewy = (windowh - pictureh) // 2
    window.fill((0, 0, 0))
    window.blit(pygame.transform.smoothscale(screen, (picturew, pictureh)), (viewx, viewy))
    pygame.display.flip()

def gamemouse(pos):
    # turn a position in the window into a position in the game
    return (int((pos[0] - viewx) / viewscale), int((pos[1] - viewy) / viewscale))
pygame.display.set_caption("Experimental Wizard")
overlay = pygame.Surface((xframe, yframe), pygame.SRCALPHA)  # see-through layer drawn over particles
clock = pygame.time.Clock()
gray = (100,100,100)
yellow = (255,255,0)
white = (255,255,255)
background = (30,30,60)
empty = {"color": (30,30,60), "interaction": "nothing", "background":True}
gravitycircle = {"color": (100, 0, 100), "interaction": "force", "background":True}
windcircle = {"color": (180,200,255), "interaction": "force", "background":True}
blackholew = {"color": (0,0,0), "interaction": "force", "background":True}
steam = {"color": (90, 90, 90), "move": "liquid", "background":False, "lifespam":"none", "interactionamount":0,
           "density": -1}
obsidian = {"color": (10, 10, 10), "move": "solid", "background":False, "lifespam":"none", "interactionamount":0,
           "density": 10}
air = {"color": (30, 30, 60), "move": "nothing", "background":False, "lifespam":"none", "interactionamount":0,
           "density": 0}
fire = {"color": (200, 50, 0), "move": "all", "background":False, "lifespam":300, "dieout":air, "interactionamount":0,
           "density": 0.1}
water = {"color": (0, 0, 255), "move": "liquid", "background":False, "lifespam":"none", "interactionamount":0,
           "density": 1}
lava = {"color": (255, 0, 0), "move": "liquid", "background":False, "lifespam":"none", "interactionamount":1, "interactiontype1":[water,steam,obsidian],
           "density": 3}
redsand = {"color": (255, 140, 90), "move": "powder", "background":False, "lifespam":"none", "interactionamount":0,
           "density": 2}
magicpowder = {"color": (200, 200, 255), "move": "powder", "background":False, "lifespam":"none", "interactionamount":1, "interactiontype1":[lava,redsand,air],
           "density": 2}
magic = {"color": (50, 50, 80), "move": "random", "background":False, "lifespam":"none", "interactionamount":2, "interactiontype1":[lava,fire,lava], "interactiontype2":[fire,fire,fire],
           "density": 0.1}
rock = {"color": (150, 150, 150), "move": "solid", "background":False, "lifespam":"none", "interactionamount":0,
           "density": 10}
ice = {"color": (100, 100, 240), "move": "solid", "background":False, "lifespam":"none", "interactionamount":1, "interactiontype1":[steam,water,water],
           "density": 10}
scrollist = [air,water,lava,magicpowder,rock,fire,magic,empty,gravitycircle,windcircle,blackholew]
scrollnames = ["Eraser","Water","Lava","Magic powder","Rock","Fire","Magic","Erase circle","Gravity","Wind","Black hole"]
font = pygame.font.Font(None, 22)
labels = [font.render(name, True, white) for name in scrollnames]
listsize = 11 #(pixelsize * ypixframe - 80) // 40
interactionlist = ["interactiontype1","interactiontype2","interactiontype3","interactiontype4"]

running = True
interactions = 0  # material reactions this frame (drives the music)
steammade = 0     # reactions this frame that made steam (drives the sizzle sound)
state = "welcome"  # "welcome" = title screen, "playing" = the sandbox
substaince = air
grid = [[air] * ypixframe for _ in range(xpixframe)]
countgrid = [[0] * ypixframe for _ in range(xpixframe)]
changegrid = [[0] * ypixframe for _ in range(xpixframe)]
backgroundgrid = [[empty] * bigypixframe for _ in range(bigxpixframe)]
backgrounddirgrid = [[0] * bigypixframe for _ in range(bigxpixframe)]
forcegrid = [[0] * ypixframe for _ in range(xpixframe)]
moved = set()  # cells that already moved this frame
windcirclegriddiagonal = [[0] * 50 for _ in range(50)]
windcriclegridstrait = [[0] * 50 for _ in range(50)]

def makewindgrid():
    windcirclegriddiagonalsub = [[8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,2,2,2,2,2,2,2,2,2,2,3,3,3,3,4,4,4,4,4,5,5],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,1,1,2,2,2,2,2,2,2,2,3,3,3,3,4,4,4,4,4,5,5,5],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,1,1,1,2,2,2,2,2,2,2,3,3,3,4,4,4,4,4,4,5,5,5,6],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,1,1,1,1,2,2,2,2,2,2,3,3,3,4,4,4,4,4,5,5,5,5,6,6],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,1,1,1,1,1,2,2,2,2,2,3,3,3,4,4,4,4,4,5,5,5,5,6,6,6],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,1,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,4,5,5,5,5,5,6,6,6],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,1,1,1,1,2,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,5,5,6,6,6,6],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,1,1,1,1,2,2,2,2,3,3,3,3,3,4,4,4,4,5,5,5,5,5,5,6,6,6,6,7],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,1,1,1,2,2,2,2,2,3,3,3,3,4,4,4,4,4,5,5,5,5,5,5,6,6,6,6,7,7],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,1,1,1,2,2,2,2,3,3,3,3,3,4,4,4,4,4,5,5,5,5,5,5,5,6,6,6,6,7,7],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,1,2,2,2,2,2,2,3,3,3,3,4,4,4,4,4,4,5,5,5,5,5,5,5,6,6,6,6,7,7,7],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,1,1,2,2,2,2,3,3,3,3,3,4,4,4,4,4,4,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,1,1,1,2,2,2,3,3,3,3,4,4,4,4,4,4,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,1,1,1,2,3,3,3,3,3,3,4,4,4,4,4,4,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,1,1,1,1,2,3,3,3,3,4,4,4,4,4,4,5,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0,0],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,8,1,1,1,1,1,2,3,3,3,4,4,4,4,4,4,5,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0,0,0],
                                [8,8,8,8,8,8,8,8,8,8,8,8,8,1,1,1,1,1,1,3,4,4,4,4,4,4,4,5,5,5,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0,0,0],
                                [8,8,8,8,8,8,8,8,8,8,8,8,1,1,1,1,1,1,0,3,4,4,4,4,4,4,5,5,5,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0,0,0,0],
                                [8,8,8,8,8,8,8,8,8,8,8,1,1,1,1,1,1,0,0,3,4,4,4,4,5,5,5,5,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0,0,0,0,0],
                                [8,8,8,8,8,8,8,8,8,8,1,1,1,1,1,1,0,0,0,4,4,4,4,5,5,5,5,5,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0,0,0,0,0],
                                [8,8,8,8,8,8,8,8,8,1,1,1,1,1,1,0,0,0,7,4,4,5,5,5,5,5,5,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0,1,1,1,1,0],
                                [8,8,8,8,8,8,8,8,1,1,1,1,1,1,0,0,0,7,7,4,5,5,5,5,5,5,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0,1,1,1,1,1,8],
                                [8,8,8,8,8,8,8,1,1,1,1,1,1,0,0,0,7,7,7,4,5,5,5,5,5,5,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0,1,1,1,1,8,8],
                                [8,8,8,8,8,8,1,1,1,1,1,0,0,0,0,7,7,7,6,5,5,5,5,5,5,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0,1,1,1,1,8,8,8],
                                [8,8,8,8,8,1,1,1,0,0,0,7,7,7,6,6,6,6,5,5,5,5,5,5,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0,1,1,1,1,8,8,8,8],
                                [8,8,8,8,1,1,1,1,0,0,0,7,7,7,6,6,6,6,5,5,5,5,5,5,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0,1,1,1,8,8,8,8,8],
                                [8,8,8,1,1,1,1,0,0,0,7,7,7,6,6,6,6,5,5,5,5,5,5,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0,1,1,1,8,8,8,8,8,8],
                                [8,8,1,1,1,1,0,0,0,7,7,7,6,6,6,6,5,5,5,5,5,5,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0,1,1,1,8,8,8,8,8,8,8],
                                [8,1,1,1,1,1,0,0,0,7,7,7,6,6,6,6,5,5,5,5,5,5,5,5,5,5,5,5,5,5,6,6,6,6,7,7,7,0,0,0,1,1,8,8,8,8,8,8,8,8],
                                [0,1,1,1,1,0,0,0,7,7,7,6,6,6,6,5,5,5,5,5,5,5,5,5,5,5,5,5,5,4,3,3,3,2,2,2,1,1,1,1,1,8,8,8,8,8,8,8,8,8],
                                [0,0,0,0,0,0,0,7,7,7,6,6,6,6,5,5,5,5,5,5,5,5,5,5,5,5,5,4,4,3,3,3,2,2,2,1,1,1,1,1,8,8,8,8,8,8,8,8,8,8],
                                [0,0,0,0,0,0,0,7,7,7,6,6,6,6,5,5,5,5,5,5,5,5,5,5,5,5,4,4,4,3,3,2,2,2,1,1,1,1,1,8,8,8,8,8,8,8,8,8,8,8],
                                [0,0,0,0,0,0,7,7,7,6,6,6,6,5,5,5,5,5,5,5,5,5,5,5,4,4,4,4,4,3,2,2,2,1,1,1,1,1,8,8,8,8,8,8,8,8,8,8,8,8],
                                [0,0,0,0,0,7,7,7,6,6,6,6,5,5,5,5,5,5,5,5,5,5,5,4,4,4,4,4,4,2,2,2,1,1,1,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [0,0,0,0,0,7,7,7,6,6,6,6,5,5,5,5,5,5,5,5,5,4,4,4,4,4,4,3,3,2,2,1,1,1,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [0,0,0,0,7,7,7,6,6,6,6,5,5,5,5,5,5,5,5,5,4,4,4,4,4,4,3,3,3,2,1,1,1,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [0,0,0,7,7,7,6,6,6,6,5,5,5,5,5,5,5,5,4,4,4,4,4,4,3,3,3,3,3,2,1,1,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [0,0,7,7,7,6,6,6,6,5,5,5,5,5,5,5,5,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [0,7,7,7,6,6,6,6,5,5,5,5,5,5,5,4,4,4,4,4,4,3,3,3,3,3,2,2,2,1,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [7,7,7,6,6,6,6,5,5,5,5,5,5,5,4,4,4,4,4,4,3,3,3,3,2,2,2,2,2,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [7,7,6,6,6,6,5,5,5,5,5,5,5,4,4,4,4,4,3,3,3,3,3,2,2,2,2,1,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [7,6,6,6,6,6,5,5,5,5,5,5,4,4,4,4,4,3,3,3,3,2,2,2,2,2,1,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [6,6,6,6,6,5,5,5,5,5,5,4,4,4,4,3,3,3,3,3,2,2,2,2,1,1,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [6,6,6,6,5,5,5,5,5,5,4,4,4,4,3,3,3,3,2,2,2,2,2,1,1,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [6,6,6,5,5,5,5,5,4,4,4,4,4,3,3,3,3,2,2,2,2,1,1,1,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [6,6,6,5,5,5,5,4,4,4,4,4,3,3,3,2,2,2,2,2,1,1,1,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [6,6,5,5,5,5,4,4,4,4,4,3,3,3,2,2,2,2,2,2,1,1,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [6,5,5,5,4,4,4,4,4,4,3,3,3,2,2,2,2,2,2,2,1,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [5,5,5,4,4,4,4,4,4,3,3,3,2,2,2,2,2,2,2,2,1,1,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8],
                                [5,5,4,4,4,4,4,4,3,3,3,2,2,2,2,2,2,2,2,2,2,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8]]
    windcriclegridstraitsub = [[8,8,8,8,8,8,8,8,8,1,1,1,1,1,1,1,2,2,3,3,3,3,3,4,4,4,4,5,5,5,5,5,6,6,7,7,7,7,7,7,7,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,1,1,1,1,1,1,2,2,3,3,3,3,3,4,4,4,4,5,5,5,5,5,6,6,7,7,7,7,7,7,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,1,1,1,1,1,2,2,3,3,3,3,3,4,4,4,4,5,5,5,5,5,6,6,7,7,7,7,7,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,1,2,2,3,3,3,3,3,4,4,4,4,5,5,5,5,5,6,6,7,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,1,2,2,3,3,3,3,4,4,4,4,4,4,5,5,5,5,6,6,7,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,1,2,2,3,3,3,3,4,4,4,4,4,4,5,5,5,5,6,6,7,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,1,2,2,3,3,3,3,4,4,4,4,4,4,5,5,5,5,6,6,7,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,1,2,2,3,3,3,3,4,4,4,4,4,4,5,5,5,5,6,6,7,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,1,2,2,3,3,3,3,4,4,4,4,4,4,5,5,5,5,6,6,7,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,2,2,3,3,3,3,4,4,4,4,4,4,4,4,5,5,5,5,6,6,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,2,2,3,3,3,3,4,4,4,4,4,4,4,4,5,5,5,5,6,6,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,2,2,3,3,3,3,4,4,4,4,4,4,4,4,5,5,5,5,6,6,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,2,2,3,3,3,3,4,4,4,4,4,4,4,4,5,5,5,5,6,6,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,2,2,3,3,3,3,4,4,4,4,4,4,4,4,5,5,5,5,6,6,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,2,2,3,3,3,3,4,4,4,4,4,4,4,4,5,5,5,5,6,6,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,2,2,3,3,3,3,4,4,4,4,4,4,4,4,5,5,5,5,6,6,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,2,2,3,3,3,3,4,4,4,4,4,4,4,4,5,5,5,5,6,6,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,2,2,3,3,3,3,4,4,4,4,4,4,4,4,5,5,5,5,6,6,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,2,2,3,3,3,3,4,4,4,4,4,4,4,4,5,5,5,5,6,6,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,1,1,2,3,3,3,4,4,4,4,4,4,4,4,4,4,5,5,5,6,7,7,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,1,0,0,1,3,3,3,4,4,4,4,4,4,4,4,4,4,5,5,5,7,0,0,7,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,1,0,0,0,0,3,3,3,4,4,4,4,4,4,4,4,4,4,5,5,5,0,0,0,0,7,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,0,6,6,6,6,3,3,4,4,4,4,4,4,4,4,4,4,5,5,2,2,2,2,0,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,6,6,6,6,6,6,6,3,4,4,4,4,4,4,4,4,4,4,5,2,2,2,2,2,2,2,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,6,6,6,6,6,6,6,5,4,4,4,4,4,4,4,4,4,4,3,2,2,2,2,2,2,2,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,5,4,6,6,6,6,5,5,4,4,4,4,4,4,4,4,4,4,3,3,2,2,2,2,4,3,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,4,4,4,4,5,5,5,4,4,4,4,4,4,4,4,4,4,3,3,3,4,4,4,4,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,4,4,7,5,5,5,4,4,4,4,4,4,4,4,4,4,3,3,3,1,4,4,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,7,6,5,5,5,4,4,4,4,4,4,4,4,4,4,3,3,3,2,1,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,7,6,6,5,5,5,5,4,4,4,4,4,4,3,3,3,3,2,2,1,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,0,7,7,7,7,6,6,5,5,5,5,5,4,4,4,4,3,3,3,3,3,2,2,1,1,1,1,0,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,0,7,7,7,7,7,6,6,5,5,5,5,5,4,4,4,4,3,3,3,3,3,2,2,1,1,1,1,1,0,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,0,7,7,7,7,7,7,6,6,5,5,5,5,5,4,4,4,4,3,3,3,3,3,2,2,1,1,1,1,1,1,0,8,8,8,8,8,8,8,8,8],
                                [8,8,8,8,8,8,8,8,8,7,7,7,7,7,7,7,6,6,5,5,5,5,5,4,4,4,4,3,3,3,3,3,2,2,1,1,1,1,1,1,1,8,8,8,8,8,8,8,8,8]]
    for xpaint in range(50):
        for ypaint in range(50):
            windcirclegriddiagonal[xpaint][ypaint] = windcirclegriddiagonalsub[xpaint][ypaint]
            windcriclegridstrait[xpaint][ypaint] = windcriclegridstraitsub[xpaint][ypaint]
            if windcirclegriddiagonal[xpaint][ypaint] == 8:
                windcirclegriddiagonal[xpaint][ypaint] = "none"
            if windcriclegridstrait[xpaint][ypaint] == 8:
                windcriclegridstrait[xpaint][ypaint] = "none"

def updatecountgrid():
    for xpaint in range (xpixframe):
        for ypaint in range (ypixframe):
            count = countgrid[xpaint][ypaint]
            if count > 0:
                countgrid[xpaint][ypaint] = count-1

def interactionrun(xpaint,ypaint,xlocation,ylocation):
    pixel= grid[xpaint][ypaint]
    otherpixel=grid[xlocation][ylocation]
    amount = pixel.get("interactionamount")
    if amount > 0:
        for list in range(amount):
            interaction = pixel.get(interactionlist[list])
            if otherpixel == interaction[0]:
                grid[xpaint][ypaint]=interaction[1]
                if interaction[1].get("lifespam") != "none":
                    countgrid[xpaint][ypaint] = interaction[1].get("lifespam")
                grid[xlocation][ylocation]=interaction[2]
                if interaction[2].get("lifespam") != "none":
                    countgrid[xlocation][ylocation] = interaction[2].get("lifespam")
                return True
    amount = otherpixel.get("interactionamount")
    if amount > 0:
        for list in range(amount):
            interaction = otherpixel.get(interactionlist[list])
            if pixel == interaction[0]:
                grid[xpaint][ypaint]=interaction[1]
                if interaction[1].get("lifespam") != "none":
                    countgrid[xpaint][ypaint] = interaction[1].get("lifespam")
                grid[xlocation][ylocation]=interaction[2]
                if interaction[2].get("lifespam") != "none":
                    countgrid[xlocation][ylocation] = interaction[2].get("lifespam")
                return True
    return False

def drawpanel(selected, brush):
    pygame.draw.rect(screen,background,(panelx - 8,0,xframe - panelx + 8,yframe))  # -8 so the old highlight outline gets cleared too
    for listmaker in range(listsize):
        rowy = paneltop + listmaker*rowgap
        if scrollist[listmaker] is selected:
            pygame.draw.rect(screen,yellow,(panelx - 4,rowy - 4,xframe - border - panelx + 8,boxsize + 8),2)
        pygame.draw.rect(screen,white,(panelx,rowy,boxsize,boxsize))
        pygame.draw.rect(screen,scrollist[listmaker].get("color"),(panelx + 1,rowy + 1,boxsize - 2,boxsize - 2))
        screen.blit(labels[listmaker],(panelx + boxsize + 8,rowy + 2))
    drawvolume("music", "Music", musicvolume)
    drawvolume("effects", "Effects", effectsvolume)
    screen.blit(font.render("Brush size: " + str(brush),True,white),(panelx,slidery - 25))
    pygame.draw.line(screen,gray,(panelx,slidery),(sliderend,slidery),3)
    pygame.draw.rect(screen,white,(panelx + notch*brush,slidery - 3,notch,notch))

volumey = {"music": slidery - 110, "effects": slidery - 60}  # y of each volume slider line

def drawvolume(name, label, value):
    y = volumey[name]
    amount = "muted (M)" if muted else str(round(value * 100)) + "%"
    screen.blit(font.render(label + ": " + amount, True, white), (panelx, y - 25))
    pygame.draw.line(screen, gray, (panelx, y), (sliderend, y), 3)
    knobx = panelx + int(value * (sliderend - panelx))
    pygame.draw.rect(screen, white, (knobx - 3, y - 5, 7, 11))

def volumeclick(mx, my):
    # if the click is on a volume slider: (which slider, new volume 0 to 1)
    for name, y in volumey.items():
        if y - 8 <= my <= y + 8 and panelx - 5 <= mx <= sliderend + 5:
            return name, max(0.0, min(1.0, (mx - panelx) / (sliderend - panelx)))
    return None

def picksubtype(mx, my):
    if panelx <= mx <= xframe - border:
        for listmaker in range(listsize):
            rowy = paneltop + listmaker*rowgap
            if rowy <= my <= rowy + boxsize:
                return scrollist[listmaker]
    return False

def brushsize(mx,my):
    if slidery - 3 <= my <= slidery + 3:
        if panelx <= mx <= sliderend:
            return (mx - panelx) // notch
    return None

def outofbounds (xlocation, ylocation):
    if 0 <= xlocation < xpixframe and 0 <= ylocation < ypixframe:
        return True
    else:
        return False

def flip (xpaint, ypaint, xlocation, ylocation):
    object1 = grid[xpaint][ypaint]
    object2 = grid[xlocation][ylocation]
    grid[xpaint][ypaint] = object2
    grid[xlocation][ylocation] = object1
    count1 = countgrid[xpaint][ypaint]
    count2 = countgrid[xlocation][ylocation]
    countgrid[xpaint][ypaint] = count2
    countgrid[xlocation][ylocation] = count1
    moved.add((xlocation, ylocation))

def moveupdate(potmove, den, xpaint, ypaint, priority):
    global interactions, steammade
    direction = forcegrid[xpaint][ypaint]
    if den < 0:
        goother=4
    else:
        goother=0
    if direction == "none":
        if random.choice([0,1,2])==0:
            direction = random.choice([0,1,2,3,4,5,6,7])
        else:
            return False
    for move in range (8):
        if potmove[priority[move]] == 1:
            if priority[move] == (1 + direction+goother) % 8 or priority[move] == (2 + direction+goother) % 8 or priority[move] == (3 + direction+goother) % 8:
                xlocation = xpaint + 1
            if priority[move] == (5 + direction+goother) % 8 or priority[move] == (6 + direction+goother) % 8 or priority[move] == (7 + direction+goother) % 8:
                xlocation = xpaint - 1
            if priority[move] == (0 + direction+goother) % 8 or priority[move] == (4 + direction+goother) % 8:
                xlocation = xpaint
            if priority[move] == (0 + direction+goother) % 8 or priority[move] == (1 + direction+goother) % 8 or priority[move] == (7 + direction+goother) % 8:
                ylocation = ypaint + 1
            if priority[move] == (3 + direction+goother) % 8 or priority[move] == (4 + direction+goother) % 8 or priority[move] == (5 + direction+goother) % 8:
                ylocation = ypaint -1
            if priority[move] == (2 + direction+goother) % 8 or priority[move] == (6 + direction+goother) % 8:
                ylocation = ypaint
            if outofbounds(xlocation, ylocation):
                otherelement = grid[xlocation][ylocation]
                otherden = otherelement.get("density")
                ran = interactionrun(xpaint,ypaint,xlocation,ylocation)
                if ran == True:
                    interactions += 1
                    if grid[xpaint][ypaint] is steam or grid[xlocation][ylocation] is steam:
                        steammade += 1  # lava hit water: the sizzle sound is for this
                    return True
                else:
                    if goother == 4:
                        if otherden > den:
                            if otherelement.get("move") != "solid":
                                flip (xpaint, ypaint, xlocation, ylocation)
                                return True
                    else:
                        if den > otherden:
                            flip (xpaint, ypaint, xlocation, ylocation)
                            return True           
    return False          

def updategrid(flipscreen):
    moved.clear()
    for xpixnum in range (xpixframe):
        for ypixnum in range (ypixframe):
            if flipscreen == 0:
                xpaint=xpixnum
                ypaint=ypixframe-1-ypixnum
            else:
                xpaint=xpixframe-1-xpixnum
                ypaint=ypixframe-1-ypixnum
            if (xpaint, ypaint) in moved:
                continue
            pixel = grid[xpaint][ypaint]
            change =0
            if pixel.get("lifespam") != "none":
                if countgrid[xpaint][ypaint] == 0:
                    pixel = pixel.get("dieout")
                    grid[xpaint][ypaint]=pixel
                    if pixel.get("lifespam") != "none":
                        countgrid[xpaint][ypaint] = pixel.get("lifespam")
                    mxp = xpaint
                    myp = ypaint
                    size = 1
                    replacetype = 1
                    replacecount = 0
                    transfernone = 0
                    allgrid = changegrid
                    paint(mxp,myp,replacetype,size,allgrid,replacecount,transfernone)
            if changegrid[xpaint][ypaint] == 1 or change ==1:
                element = pixel.get("move")
                den = pixel.get("density")
                if element == "liquid":
                    side = random.choice([1,7])
                    if side == 1:
                        otherside =7
                    else:
                        otherside =1
                    side2 = random.choice([2,6])
                    if side2 == 2:
                        otherside2= 6
                    else:
                        otherside2= 2
                    potmove = [1,1,1,0,0,0,1,1]
                    priority = [0,side,otherside,side2,otherside2,3,4,5]
                elif element == "powder":
                    side = random.choice([1,7])
                    if side == 1:
                        otherside =7
                    else:
                        otherside =1
                    potmove = [1,1,0,0,0,0,0,1]
                    priority = [0,side,otherside,2,3,4,5,6]
                elif element == "random":
                    randomlist =[0,2,4,6]
                    side = random.choice(randomlist)
                    otherside = random.choice([(2+side)%8,(4+side)%8,(6+side)%8])
                    pickran2 = random.choice([0,1])
                    for counter in range(4):
                        if side != randomlist[counter]:
                            if otherside != randomlist[counter]:
                                if pickran2 == 0:
                                    side2 = randomlist[counter]
                                    pickran2 = 1
                                else:
                                    otherside2 = randomlist[counter]
                                    pickran2 = 0
                    potmove = [1,0,1,0,1,0,1,0]
                    priority = [side,otherside,side2,otherside2,1,3,5,7]
                elif element == "all":
                    potmove = [1,1,1,1,1,1,1,1]
                    side = random.choice([1,7])
                    if side == 1:
                        otherside =7
                    else:
                        otherside =1
                    side2 = random.choice([2,6])
                    if side2 == 2:
                        otherside2= 6
                    else:
                        otherside2= 2
                    side3 = random.choice([3,5])
                    if side3 == 3:
                        otherside3 = 5
                    else:
                        otherside3 = 3
                    priority = [0,side,otherside,side2,otherside2,side3,otherside3,4]
                elif element == "powder":
                    side = random.choice([1,7])
                    if side == 1:
                        otherside =7
                    else:
                        otherside =1
                else:
                    potmove = [0,0,0,0,0,0,0,0]
                    priority = [0,0,0,0,0,0,0,0]
                mxp = xpaint
                myp = ypaint
                allgrid = changegrid
                if moveupdate(potmove, den, xpaint, ypaint, priority):
                    replacecount = 0
                    replacetype = 1
                    size = 1
                    transfernone = 0
                    paint(mxp,myp,replacetype,size,allgrid,replacecount,transfernone)
                else:
                    changegrid[xpaint][ypaint] = 0

def showbackground():
    bigcenter = bigpixelsize//2+border
    for xpaint in range(bigxpixframe):
        for ypaint in range(bigypixframe):
            pixel = backgroundgrid[xpaint][ypaint]
            xfirst =xpaint*bigpixelsize+border
            yfirst =ypaint*bigpixelsize+border
            if pixel != empty:
                xbigcenter=xpaint*bigpixelsize+bigcenter
                ybigcenter=ypaint*bigpixelsize+bigcenter
                if pixel == blackholew:
                    pygame.draw.circle(overlay,pixel.get('color') + (120,),(xbigcenter,ybigcenter),10)
                else:
                    target = overlay
                    color = pixel.get('color') + (120,)
                    hole = (0,0,0,0)
                    pygame.draw.circle(target, color, (xbigcenter,ybigcenter),bigpixelsize//2 -5)
                    direction = backgrounddirgrid[xpaint][ypaint]
                    if 1 <= direction <= 3:
                        xchange = 2
                    elif 5<=direction<=7:
                        xchange = 48
                    else:
                        xchange = 25
                    if 3<=direction<=5:
                        ychange = 2
                    elif direction == 2 or direction == 6:
                        ychange = 25
                    else:
                        ychange = 48
                    xend = xfirst+xchange
                    yend = yfirst+ychange
                    pygame.draw.circle(target, hole, (xbigcenter,ybigcenter), 17)
                    pygame.draw.line(target,color,(xbigcenter,ybigcenter),(xend,yend),2)

def showparticle():
    for xpaint in range (xpixframe):
        for ypaint in range (ypixframe):
            pixel = grid[xpaint][ypaint]
            if pixel != air:
                pygame.draw.rect(screen, pixel.get('color'), (xpaint*pixelsize+border,ypaint*pixelsize+border,pixelsize,pixelsize) )

def show():
    pygame.draw.rect(screen,background,(border,border,xpixframe*pixelsize,ypixframe*pixelsize))
    overlay.fill((0,0,0,0))
    showbackground()
    showparticle()
    screen.blit(overlay,(0,0))

def backgroundpaint(mx,my,replacetype,allgrid):
    mxb = ((mx - border) //bigpixelsize)
    myb = ((my - border) //bigpixelsize)
    if 0 <= mxb < bigxpixframe and 0 <= myb < bigypixframe:
        changedtype = allgrid[mxb][myb]
        allgrid[mxb][myb] = replacetype
        mxbextra = ((mx - border) % bigpixelsize) //17
        mybextra = ((my - border) % bigpixelsize) //17
        if mxbextra == 0:
            direction = 3 - mybextra 
            backgrounddirgrid[mxb][myb] = direction
        elif mxbextra == 2:
            direction = 5 + mybextra
        else:
            if mybextra == 0:
                direction = 4
            else:
                direction = 0
        backgrounddirgrid[mxb][myb] = direction
        if replacetype.get('interaction') == "force" or changedtype.get('interaction') == "force":
            forcechange(mxb,myb)

def forcechange(mxb,myb):
    for xpaint in range(5):
        for ypaint in range(5):
            bigxchange = mxb -2 +xpaint
            bigychange = myb -2 +ypaint
            if 0 <= bigxchange < bigxpixframe and 0 <= bigychange < bigypixframe:
                for smallxpaint in range(10):
                    for smallypaint in range(10):
                        xforce=0
                        yforce=0
                        for xpaint2 in range(5):
                            for ypaint2 in range(5):
                                bigxchange2 = bigxchange -2 +xpaint2
                                bigychange2 = bigychange -2 +ypaint2
                                if 0 <= bigxchange2 < bigxpixframe and 0 <= bigychange2 < bigypixframe:
                                    circletype = backgroundgrid[bigxchange2][bigychange2]
                                    if circletype.get('interaction') == 'force':
                                        if circletype == gravitycircle:
                                            direction = backgrounddirgrid[bigxchange2][bigychange2]
                                        elif circletype == windcircle:
                                            circledirection = backgrounddirgrid[bigxchange2][bigychange2]
                                            if circledirection == 0:
                                                podirection = windcriclegridstrait[ypaint2*10+smallypaint][xpaint2*10+smallxpaint]
                                                if podirection != "none":
                                                    direction =(podirection+4)%8
                                                else:
                                                    direction = "none"
                                            elif circledirection ==2:
                                                podirection = windcriclegridstrait[xpaint2*10+smallxpaint][ypaint2*10+smallypaint]
                                                if podirection != "none":
                                                    direction =(podirection+6)%8
                                                else:
                                                    direction = "none"
                                            elif circledirection ==4:
                                                direction = windcriclegridstrait[ypaint2*10+smallypaint][xpaint2*10+smallxpaint]
                                            elif circledirection ==6:
                                                podirection = windcriclegridstrait[xpaint2*10+smallxpaint][ypaint2*10+smallypaint]
                                                if podirection != "none":
                                                    direction =(podirection+2)%8
                                                else:
                                                    direction = "none"
                                            elif circledirection ==1:
                                                podirection = windcirclegriddiagonal[ypaint2*10+smallypaint][xpaint2*10+smallxpaint]
                                                if podirection != "none":
                                                    direction = (podirection+4)%8
                                                else:
                                                    direction = "none"
                                            elif circledirection ==3:
                                                podirection = windcirclegriddiagonal[(4-xpaint2)*10+(9-smallxpaint)][ypaint2*10+smallypaint]
                                                if podirection != "none":
                                                    direction = (podirection+6)%8
                                                else:
                                                    direction = "none"
                                            elif circledirection ==7:
                                                podirection = windcirclegriddiagonal[(4-xpaint2)*10+(9-smallxpaint)][ypaint2*10+smallypaint]
                                                if podirection != "none":
                                                    direction = (podirection+2)%8
                                                else:
                                                    direction = "none"
                                            else:
                                                direction = windcirclegriddiagonal[ypaint2*10+smallypaint][xpaint2*10+smallxpaint]
                                        elif circletype == blackholew:
                                            xofb = (bigxchange - bigxchange2)*10-5+smallxpaint
                                            yofb = (bigychange - bigychange2)*10-5+smallypaint
                                            if xofb < 0:
                                                posxofb = -xofb
                                                xdirectionofb = "negative"
                                            else:
                                                posxofb = xofb+1
                                                xdirectionofb = "positive"
                                            if yofb < 0:
                                                posyofb = -yofb
                                                ydirectionofb = "negative"
                                            else:
                                                posyofb = yofb+1
                                                ydirectionofb = "positive"
                                            if posxofb < posyofb/2:
                                                podirection=4
                                            elif posyofb < posxofb/2:
                                                podirection=2
                                            else:
                                                podirection=3
                                            if xdirectionofb == "negative":
                                                if ydirectionofb == "negative":
                                                    turn=4
                                                else:
                                                    if podirection ==2:
                                                        turn=4
                                                    elif podirection ==4:
                                                        turn=0
                                                    else:
                                                        turn=2
                                            elif ydirectionofb == "negative":
                                                if podirection ==2:
                                                    turn=0
                                                elif podirection ==4:
                                                    turn=4
                                                else:
                                                    turn=6
                                            else:
                                                turn=0
                                            direction= (podirection + turn)%8
                                        if direction != "none":
                                            if 1 <= direction <=3:
                                                xforce = xforce -1
                                            elif 5 <= direction <= 7:
                                                xforce = xforce +1
                                            if 3 <= direction <= 5:
                                                yforce = yforce -1
                                            elif direction <= 1 or direction == 7:
                                                yforce = yforce +1
                        xpixel = bigxchange*10+smallxpaint
                        ypixel = bigychange*10+smallypaint
                        if xforce < 0:
                            posxforce = -xforce
                            xdirection = "negative"
                        else:
                            posxforce = xforce
                            xdirection = "positive"
                        if yforce < 0:
                            posyforce = -yforce
                            ydirection = "negative"
                        else:
                            posyforce = yforce
                            ydirection = "positive"
                        if posxforce < posyforce/3:
                            if ydirection == "negative":
                                forcegrid[xpixel][ypixel]=4
                            else:
                                forcegrid[xpixel][ypixel]=0
                        elif posyforce < posxforce/3:
                            if xdirection == "negative":
                                forcegrid[xpixel][ypixel]=2
                            else:
                                forcegrid[xpixel][ypixel]=6
                        elif xdirection == "negative":
                            if ydirection == "negative":
                                forcegrid[xpixel][ypixel]=3
                            else:
                                forcegrid[xpixel][ypixel]=1
                        elif ydirection == "negative":
                            forcegrid[xpixel][ypixel]=5
                        else:
                            forcegrid[xpixel][ypixel]=7
                        if xforce == 0 and yforce == 0:
                            forcegrid[xpixel][ypixel]= 0
                        changegrid[xpixel][ypixel]=1

def paint(mxp, myp, replacetype, size, allgrid,replacecount,transfernone):
    xlocation = mxp
    ylocation = myp
    if outofbounds (xlocation, ylocation,):
        if mxp-size < 0:
            lowx = 0
        else:
            lowx = mxp - size
        if mxp+size +1 > xpixframe:
            highx = xpixframe
        else:
            highx = mxp + size +1
        if myp-size < 0:
            lowy = 0
        else:
            lowy = myp - size 
        if myp+size +1 > ypixframe:
            highy = ypixframe
        else:
            highy = myp + size +1
        if transfernone != 0:
            for xpaint in range(lowx, highx):
                for ypaint in range(lowy, highy):
                    allgrid[xpaint][ypaint] = replacetype
                    countgrid[xpaint][ypaint] = replacecount
        else:
            for xpaint in range(lowx, highx):
                for ypaint in range(lowy, highy):
                    allgrid[xpaint][ypaint] = replacetype
    if allgrid == grid:
        replacetype = 1
        size = size + 1
        allgrid = changegrid
        transfernone = 1
        paint (mxp,myp,replacetype,size,allgrid,replacecount,transfernone)

# ---------- sound effects ----------
# All sounds are generated from code at startup, so there are no sound files.
sounds = {}

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

# ---------- adaptive music ----------
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

def loadmusic():
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

soundvolume = {}  # base volume of each effect (recorded files are normalized, so they're turned down here)

def addsound(name, volume, generate):
    # Use the recording in sounds/<name>.ogg if there is one (made by tools/prepare_sounds.py),
    # otherwise generate a stand-in sound from code.
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds", name + ".ogg")
    if os.path.exists(path):
        sounds[name] = pygame.mixer.Sound(path)
        soundvolume[name] = volume
    else:
        sounds[name] = generate()
        soundvolume[name] = 1.0  # generated sounds have their volume built in
    sounds[name].set_volume(soundvolume[name])

if pygame.mixer.get_init() and pygame.mixer.get_init()[1] == -16:
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
    loadmusic()

musicvolume = 0.6     # music volume, 0 to 1 (Music slider)
effectsvolume = 1.0   # sound effects volume, 0 to 1 (Effects slider)
muted = False         # M key turns all sound off/on
musicchannels = []  # one mixer channel per layer
musicsection = "menu"
queuedsection = None     # section waiting to play after the current one
queuedstyle = None       # ...and which style it's from
stylestart = 0           # when the current style started (milliseconds)
nextmusicstyle = None    # style being loaded / waiting to take over
layerlevels = {layer: 0.0 for layer in musiclayers}

def startmusic(section):
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

def updatemusic(mood):
    global musicsection, queuedsection, queuedstyle
    global musicstyle, musictracks, stylestart, nextmusicstyle
    if not musicchannels:
        return
    now = pygame.time.get_ticks()
    # time for a new style: start loading one in the background
    if nextmusicstyle is None and len(availablestyles) > 1 and now - stylestart > styleseconds * 1000:
        nextmusicstyle = random.choice([style for style in availablestyles if style != musicstyle])
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
        startmusic(pickmusicsection(mood))
    queuenext(mood)
    # fade each layer toward its target (about a second to get there)
    targets = layertargets(mood)
    for channel, layer in zip(musicchannels, musiclayers):
        layerlevels[layer] += (targets[layer] - layerlevels[layer]) * 0.03
        channel.set_volume(0 if muted else layerlevels[layer] * musicvolume)

reactheat = 0.0  # reactions per frame, smoothed so one sizzle doesn't flip the mood
hotcount = 0     # fire + lava cells (counted every few frames)
moodframe = 0

def measuremood():
    global reactheat, hotcount, moodframe
    reactheat += (interactions - reactheat) * 0.05
    moodframe += 1
    if moodframe % 10 == 0:
        hotcount = sum(column.count(fire) + column.count(lava) for column in grid)
    return {
        "menu": False,
        "reactions": reactheat,
        "moving": len(moved),  # cells that actually moved this frame
        "hot": hotcount,
        "circles": sum(1 for column in backgroundgrid for cell in column if cell is not empty),
    }

menumood = {"menu": True}

def effectlevel(name):
    # how loud an effect should play: its own level x the Effects slider (0 when muted)
    return 0 if muted else soundvolume[name] * effectsvolume

def applyeffectvolume():
    # after the slider or mute changes, update sounds that may already be playing
    for name in sounds:
        sounds[name].set_volume(effectlevel(name))

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
    if material is water: return "water"
    if material is lava: return "lava"
    if material is fire: return "fire"
    if material is magic: return "magic"
    if material is magicpowder or material is rock: return "powder"
    return None  # eraser is silent

sizzlechannel = None

def playsizzle(count):
    # one sizzle at a time, louder when lots of things are reacting
    global sizzlechannel
    if "sizzle" in sounds and (sizzlechannel is None or not sizzlechannel.get_busy()):
        sounds["sizzle"].set_volume(effectlevel("sizzle") * min(1.0, 0.3 + count / 20))
        sizzlechannel = sounds["sizzle"].play()

# ---------- welcome screen ----------
titlefont = pygame.font.Font(None, 96)
buttonfont = pygame.font.Font(None, 48)
welcomedrops = [lava, magicpowder, redsand, fire, magic]  # what rains down behind the menu (no water: water + lava makes solid obsidian that piles up mid-air)
playbutton = pygame.Rect(0, 0, 200, 64)
playbutton.center = (xframe // 2, yframe // 2 + 60)

welcomecircles = []  # screen positions of the force circles placed behind the menu

def welcomecircle():
    # swap the oldest background circle for a new random one
    if len(welcomecircles) >= 4:
        oldx, oldy = welcomecircles.pop(0)
        backgroundpaint(oldx, oldy, empty, backgroundgrid)
    mx = border + random.randrange(bigxpixframe * bigpixelsize)
    my = border + random.randrange(bigypixframe * bigpixelsize)
    backgroundpaint(mx, my, random.choice([windcircle, windcircle, gravitycircle, blackholew]), backgroundgrid)
    welcomecircles.append((mx, my))

def welcomestep(flipscreen):
    if random.random() < 1/180:  # about every 3 seconds
        welcomecircle()
    # now and then drop a random blob of a random material near the top
    if random.random() < 0.5:
        material = random.choice(welcomedrops)
        lifespan = material.get("lifespam")
        x = random.randrange(xpixframe)
        y = random.randrange(15)
        size = random.randint(1, 3)
        if lifespan == "none":
            paint(x, y, material, size, grid, 0, 1)
        else:
            paint(x, y, material, size, grid, lifespan, 0)
    # drain all four edges so nothing piles up; stuff blown off-screen just disappears
    for x in range(xpixframe):
        for y in (0, ypixframe-1):
            grid[x][y] = air
        changegrid[x][1] = 1
        changegrid[x][ypixframe-2] = 1
    for y in range(ypixframe):
        for x in (0, xpixframe-1):
            grid[x][y] = air
        changegrid[1][y] = 1
        changegrid[xpixframe-2][y] = 1
    updategrid(flipscreen)
    updatecountgrid()
    show()

def stretchwelcome():
    # stretch the sandbox over the whole window (cropping a bit of top and bottom)
    # so the menu has no empty strip where the side panel normally goes
    sim = screen.subsurface((border, border, xpixframe*pixelsize, ypixframe*pixelsize))
    stretchedh = xframe * ypixframe // xpixframe
    screen.blit(pygame.transform.scale(sim, (xframe, stretchedh)), (0, (yframe - stretchedh) // 2))

def drawwelcome(mx, my):
    title = "Experimental Wizard"
    shadow = titlefont.render(title, True, (0,0,0))
    text = titlefont.render(title, True, white)
    titlepos = text.get_rect(center=(xframe // 2, yframe // 2 - 60))
    screen.blit(shadow, titlepos.move(4, 4))
    screen.blit(text, titlepos)
    if playbutton.collidepoint(mx, my):
        buttoncolor = (90, 90, 160)
    else:
        buttoncolor = (60, 60, 110)
    pygame.draw.rect(screen, buttoncolor, playbutton, border_radius=12)
    pygame.draw.rect(screen, white, playbutton, 3, border_radius=12)
    label = buttonfont.render("Play", True, white)
    screen.blit(label, label.get_rect(center=playbutton.center))

def cleargrid():
    for x in range(xpixframe):
        for y in range(ypixframe):
            grid[x][y] = air
            countgrid[x][y] = 0
            changegrid[x][y] = 0
    for (mx, my) in welcomecircles:
        backgroundpaint(mx, my, empty, backgroundgrid)
    welcomecircles.clear()

screen.fill(background)
makewindgrid()
for _ in range(4):
    welcomecircle()
wasdown = False  # was the mouse held last frame (so a click only whooshes once)
startmusic("menu")  # music starts on the menu and keeps going into the game
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            muted = not muted
            applyeffectvolume()
        if state == "welcome" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if playbutton.collidepoint(gamemouse(event.pos)):
                playsound("chime")
                startmusic("calm")  # jump straight into the game music (the chime covers the cut)
                cleargrid()
                screen.fill(background)
                state = "playing"
    if state == "welcome":
        flipscreen = 1 - flipscreen
        welcomestep(flipscreen)
        stretchwelcome()
        drawwelcome(*gamemouse(pygame.mouse.get_pos()))
        updatemusic(menumood)
        present()
        clock.tick(60)
        continue
    press = pygame.mouse.get_pressed()
    loopname = None  # which paint sound should be looping this frame
    if press[0]:
        mouse_pos = gamemouse(pygame.mouse.get_pos())
        mx = (mouse_pos[0])
        my = (mouse_pos[1])
        replacetype = substaince
        mightsubstaince = picksubtype(mx,my)
        if mightsubstaince != False:
            if mightsubstaince is not substaince:
                playsound("click")
            substaince = mightsubstaince
        if substaince.get('background') != False:
            allgrid = backgroundgrid
            if not wasdown and mx < panelx:
                playsound("whoosh")
            backgroundpaint(mx,my,replacetype,allgrid)
        else:
            size = brush
            allgrid = grid
            mxp = ((mx - border) //pixelsize)
            myp = ((my - border) //pixelsize)
            replacecount = replacetype.get("lifespam")
            if replacecount == "none":
                replacecount = 0
                transfernone = 1
            else:
                transfernone = 0
            paint(mxp, myp, replacetype, size, allgrid,replacecount,transfernone)
            if outofbounds(mxp, myp):  # (returns True when inside the grid)
                loopname = paintsoundfor(replacetype)
        volume = volumeclick(mx, my)
        if volume:
            if volume[0] == "music":
                musicvolume = volume[1]
            else:
                effectsvolume = volume[1]
                applyeffectvolume()
        checkbrush = brushsize(mx,my)
        if checkbrush != None:
            if checkbrush != brush:
                playsound("click")
            brush = checkbrush
    setpaintloop(loopname)
    wasdown = press[0]
    if flipscreen ==0:
        flipscreen =1
    else:
        flipscreen =0
    interactions = 0
    steammade = 0
    updategrid(flipscreen)
    if steammade > 0:
        playsizzle(steammade)
    updatemusic(measuremood())
    updatecountgrid()
    show()
    drawpanel(substaince, brush)
    present()
    clock.tick(60)
pygame.quit()