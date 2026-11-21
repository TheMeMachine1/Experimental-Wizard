import pygame
import random

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
screen = pygame.display.set_mode((xframe, yframe))
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
    screen.blit(font.render("Brush size: " + str(brush),True,white),(panelx,slidery - 25))
    pygame.draw.line(screen,gray,(panelx,slidery),(sliderend,slidery),3)
    pygame.draw.rect(screen,white,(panelx + notch*brush,slidery - 3,notch,notch))

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

screen.fill(background)
makewindgrid()
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    press = pygame.mouse.get_pressed()
    if press[0]:
        mouse_pos = pygame.mouse.get_pos()
        mx = (mouse_pos[0])
        my = (mouse_pos[1])
        replacetype = substaince
        mightsubstaince = picksubtype(mx,my)
        if mightsubstaince != False:
            substaince = mightsubstaince
        if substaince.get('background') != False:
            allgrid = backgroundgrid
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
        checkbrush = brushsize(mx,my)
        if checkbrush != None:
            brush = checkbrush
    if flipscreen ==0:
        flipscreen =1
    else:
        flipscreen =0
    updategrid(flipscreen)
    updatecountgrid()
    show()
    drawpanel(substaince, brush)
    pygame.display.flip()
    clock.tick(60)
pygame.quit()