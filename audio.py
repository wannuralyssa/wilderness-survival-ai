
#MUSIC AND SOUND EFFECTS
#=======================
#EVERY SOUND WAS SYNTHESIZED BY make_audio.py (NO SAMPLES OR DOWNLOADS).
#IF THE COMPUTER HAS NO SOUND DEVICE, EVERYTHING HERE QUIETLY DOES NOTHING.
import glob
import math
import os
import pygame

MASTER_VOLUME = 0.8
MUSIC_VOLUME = 0.45
SFX_VOLUME = 0.7

#HOW LOUD EACH SOUND IS COMPARED WITH THE OTHERS
SOUND_VOLUME = {
    "step_grass": 0.25, "step_dirt": 0.3, "step_wood": 0.35, "step_mud": 0.35,
    "chop": 0.7, "mine": 0.6, "eat": 0.6, "drink": 0.5, "swing": 0.45, "hit": 0.8,
    "wolf_yelp": 0.55, "wolf_die": 0.6, "wolf_bite": 0.8, "hurt": 0.45,
    "build_fire": 0.7, "build_tent": 0.7, "relight": 0.6, "extinguish": 0.6, "rest": 0.5,
    "fail": 0.35, "menu_move": 0.35, "menu_select": 0.5, "birds": 0.45, "howl": 0.55,
    "thunder": 0.8, "wind_gust": 0.5, "game_over": 0.7
}
LOOP_VOLUME = {"loop_rain": 0.55, "loop_wind": 0.5, "loop_fire": 0.6}

MUSIC_FADE = 2000          #MILLISECONDS TO CROSSFADE BETWEEN MUSIC TRACKS
MIN_GAP = 70               #THE SAME SOUND CAN'T PLAY AGAIN WITHIN THIS MANY MILLISECONDS

enabled = False
muted = False
sounds = {}
music_tracks = {}
loop_sounds = {}

_music_channels = []
_current_music = None
_active_music_channel = 0
_loop_channels = {}
_last_played = {}


def init():
    #CALL ONCE, AFTER pygame.init()
    global enabled, _music_channels
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        pygame.mixer.set_num_channels(24)
        #RESERVE CHANNELS: 2 FOR MUSIC (TO CROSSFADE), 3 FOR AMBIENT LOOPS
        pygame.mixer.set_reserved(5)
        _music_channels = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
        for i, name in enumerate(LOOP_VOLUME):
            _loop_channels[name] = pygame.mixer.Channel(2 + i)

        for path in glob.glob("assets/audio/sfx/*.ogg"):
            sounds[os.path.splitext(os.path.basename(path))[0]] = pygame.mixer.Sound(path)
        for path in glob.glob("assets/audio/music/*.ogg"):
            music_tracks[os.path.splitext(os.path.basename(path))[0]] = pygame.mixer.Sound(path)
        for path in glob.glob("assets/audio/loops/*.ogg"):
            loop_sounds[os.path.splitext(os.path.basename(path))[0]] = pygame.mixer.Sound(path)
        enabled = True
    except Exception as error:      #NO SOUND DEVICE, OR AUDIO FILES MISSING
        print("Sound is off:", error)
        enabled = False


def play(name, volume=1.0):
    #PLAY A SOUND EFFECT ONCE
    if not enabled or muted or name not in sounds:
        return
    now = pygame.time.get_ticks()
    if now - _last_played.get(name, -9999) < MIN_GAP:
        return
    _last_played[name] = now
    channel = sounds[name].play()
    if channel is not None:
        channel.set_volume(MASTER_VOLUME * SFX_VOLUME * SOUND_VOLUME.get(name, 0.6) * volume)


def play_music(name):
    #CROSSFADE TO ANOTHER MUSIC TRACK ("music_day", "music_night", "music_menu", OR None FOR SILENCE)
    global _current_music, _active_music_channel
    if not enabled or name == _current_music:
        return
    _current_music = name
    _music_channels[_active_music_channel].fadeout(MUSIC_FADE)
    if name is None or name not in music_tracks:
        return
    _active_music_channel = 1 - _active_music_channel
    channel = _music_channels[_active_music_channel]
    channel.set_volume(0 if muted else MASTER_VOLUME * MUSIC_VOLUME)
    channel.play(music_tracks[name], loops=-1, fade_ms=MUSIC_FADE)


def set_loop(name, level):
    #KEEP AN AMBIENT LOOP (RAIN, WIND, FIRE) PLAYING AT A LEVEL FROM 0 TO 1
    if not enabled or name not in loop_sounds:
        return
    channel = _loop_channels[name]
    level = max(0.0, min(1.0, level))
    if level < 0.02 or muted:
        if channel.get_busy():
            channel.stop()
        return
    if not channel.get_busy():
        channel.play(loop_sounds[name], loops=-1)
    channel.set_volume(MASTER_VOLUME * SFX_VOLUME * LOOP_VOLUME[name] * level)


def stop_loops():
    for name in LOOP_VOLUME:
        set_loop(name, 0)


def toggle_mute():
    global muted
    muted = not muted
    if enabled:
        for channel in _music_channels:
            channel.set_volume(0 if muted else MASTER_VOLUME * MUSIC_VOLUME)
        if muted:
            stop_loops()
    return muted


def update_world(weather, world, player_rect, game_over):
    #CALLED ONCE PER FRAME: MUSIC FOR THE TIME OF DAY, AND AMBIENT LOOPS
    if not enabled:
        return
    if game_over:
        play_music(None)
        stop_loops()
        return
    play_music("music_night" if weather.night_amount > 0.5 else "music_day")
    set_loop("loop_rain", weather.rain_amount)
    set_loop("loop_wind", max(weather.cold_amount, 0.5 * weather.wind_amount))

    #CAMPFIRE CRACKLE GETS LOUDER AS YOU GET CLOSER TO A BURNING FIRE
    closest = min((math.hypot(f.centerx - player_rect.centerx, f.centery - player_rect.centery)
                   for f in world.lit_campfires()), default=9999)
    set_loop("loop_fire", 1 - closest / 320)


#FOOTSTEPS: A STEP EVERY STEP_DISTANCE PIXELS WALKED, SOUNDING DIFFERENT ON EACH GROUND
STEP_DISTANCE = 34
_walked = 0.0


def footstep(distance, terrain):
    global _walked
    _walked += distance
    if _walked < STEP_DISTANCE:
        return
    _walked = 0.0
    if terrain == "bridge":
        play("step_wood")
    elif terrain == "mud":
        play("step_mud")
    elif terrain in ("path", "sand", "stairs"):
        play("step_dirt")
    else:
        play("step_grass")
