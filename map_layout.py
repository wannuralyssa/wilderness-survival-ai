
#MAP DESIGN: EDIT THESE TO RESHAPE THE WORLD
#ALL COORDINATES ARE WORLD PIXELS (THE WORLD IS 1600 x 1200)

#WHERE THE PLAYER STARTS
PLAYER_START = (600, 640)

#PLATEAUS (RAISED GROUND)
# polygon = OUTLINE OF THE FLAT TOP (USE MULTIPLES OF 20 FOR CLEAN CLIFF EDGES)
# level   = HEIGHT (A LEVEL 2 PLATEAU MUST SIT INSIDE A LEVEL 1 PLATEAU)
# stairs  = (x, y) OF EACH STAIRWAY: x = LEFT SIDE, y = THE PLATEAU'S SOUTH EDGE.
#           STAIRS ARE 80 PX WIDE, SO THE EDGE MUST BE FLAT THERE. USE MULTIPLES OF 40.
PLATEAUS = [
    {   #NORTH-WEST HILLS
        "level": 1,
        "polygon": [(100, 100), (420, 100), (480, 140), (700, 140), (760, 200),
                    (760, 340), (700, 400), (700, 440), (300, 440), (260, 400),
                    (140, 400), (100, 360)],
        "stairs": [(440, 440), (160, 400)]
    },
    {   #LOOKOUT ON TOP OF THE NORTH-WEST HILLS
        "level": 2,
        "polygon": [(480, 180), (660, 180), (700, 220), (700, 320), (480, 320)],
        "stairs": [(560, 320)]
    },
    {   #EASTERN CLIFFS
        "level": 1,
        "polygon": [(1220, 160), (1440, 140), (1500, 200), (1500, 440), (1440, 480),
                    (1240, 480), (1180, 420), (1180, 240)],
        "stairs": [(1320, 480)]
    },
    {   #SOUTH-WEST RIDGE
        "level": 1,
        "polygon": [(140, 800), (400, 780), (480, 840), (480, 1000), (420, 1040),
                    (200, 1040), (140, 980)],
        "stairs": [(280, 1040)]
    },
    {   #SOUTH-EAST MESA
        "level": 1,
        "polygon": [(1220, 760), (1440, 740), (1480, 800), (1480, 960),
                    (1260, 960), (1200, 900)],
        "stairs": [(1320, 960)]
    }
]

#RIVER: POINTS ALONG THE MIDDLE OF THE RIVER, FROM THE TOP OF THE MAP TO THE BOTTOM
RIVER_POINTS = [(1010, -60), (990, 120), (1060, 260), (1040, 400), (930, 520),
                (880, 660), (950, 800), (1040, 920), (1010, 1060), (960, 1260)]
RIVER_WIDTH = 72

#BRIDGES: THE Y POSITION OF EACH BRIDGE (PICK PLACES WHERE THE RIVER RUNS NORTH-SOUTH)
BRIDGES_Y = [320, 640, 1000]

#DIRT PATHS: EACH PATH IS A LIST OF POINTS
PATH_WIDTH = 36
PATHS = [
    [(600, 700), (570, 600), (500, 530), (480, 490)],           #START -> HILL STAIRS
    [(570, 600), (440, 580), (320, 560), (220, 500), (200, 450)],   #-> WEST STAIRS
    [(320, 560), (295, 600)],                                   #-> POND
    [(600, 700), (720, 660), (840, 640)],                       #-> MIDDLE BRIDGE
    [(960, 640), (1080, 620), (1220, 580), (1360, 530)],        #MIDDLE BRIDGE -> EASTERN CLIFFS
    [(720, 660), (800, 520), (880, 400), (1000, 320)],           #-> NORTH BRIDGE
    [(1120, 330), (1150, 420), (1250, 530), (1360, 530)],                    #NORTH BRIDGE -> EAST
    [(600, 700), (580, 880), (440, 1060), (320, 1090)],         #-> SOUTH-WEST RIDGE
    [(580, 880), (760, 960), (960, 1000)],                      #-> SOUTH BRIDGE
    [(1080, 1000), (1200, 1010), (1360, 1000)]                  #SOUTH BRIDGE -> MESA
]

#PONDS (x, y, width, height OF THE WATER)
PONDS = [(240, 600, 100, 70), (1340, 600, 100, 70)]

#MUD AND TALL GRASS (x, y, width, height; DRAWN AS ROUNDED BLOBS)
MUD = [(640, 500, 110, 60), (760, 780, 140, 80), (1180, 660, 120, 70), (560, 1060, 120, 60)]
TALL_GRASS = [(80, 480, 120, 110), (360, 660, 140, 90), (1080, 460, 100, 120),
              (1100, 1080, 160, 70)]

#WHERE WOLVES START (AND RESPAWN)
WOLF_SPAWNS = [(820, 200), (1460, 700), (700, 1080), (1100, 840)]
