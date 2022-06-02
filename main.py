from random import choice
from threading import Timer

import librosa
import pygame
import serial
from playsound import playsound
from pygame import mixer
from pygame.locals import *

# the number of milliseconds either side of an event occuring in which a valid
# button press may be counted
ACTIVE_WINDOW = 220

# according to the internet, 30 - 60 frames per second is acceptable for a rhythm game
FPS = 30
HEIGHT = 600
WIDTH = 600
FALL_TIME = 1000
song = "Rain+-+AShamaluevMusic.mp3"


RED = (255, 0, 0)
WHITE = (255, 255, 255)
GREY = (120, 120, 120)

pixels_per_frame = round(HEIGHT / (FPS * FALL_TIME / 1000))

# let's take in a song for analysis
y, sr = librosa.load(song)

# detected note times are called onsets
onset_envelope = librosa.onset.onset_strength(y, sr)
onsets = librosa.onset.onset_detect(onset_envelope=onset_envelope)

# turn onsets into times
onsets = [
    int(round(o * 1000)) + FALL_TIME for o in librosa.frames_to_time(onsets).tolist()
]

# reverse order for game_loop, since popping last is O(1) compared to popping
# intermediate which is O(n)
onsets.reverse()

# for each onset, assign a button
events_buttons_list = [(o, choice([1, 2, 4])) for o in onsets]

# for each event, create a rect
rects = [
    Rect(
        round((int.bit_length(o[1]) - 1) * WIDTH / 3),
        round(-pixels_per_frame * (FPS * (o[0] - FALL_TIME + ACTIVE_WINDOW) / 1000)),
        200,
        round(pixels_per_frame * FPS * (ACTIVE_WINDOW / 1000)),
    )
    for o in events_buttons_list
]

pygame.init()

# the dimensions of the window produced by pygame
screen = pygame.display.set_mode((WIDTH, HEIGHT))

# time to start the game!
# let's initialise the serial port
serialPort = serial.Serial("/dev/ttyACM0", baudrate=115200, timeout=0)


def start_music():
    playsound(song)


def game_loop():
    """
    1. checks the game's state
    2. accepts input
    3. applies game logic
    4. updates the game state
    5. renders
    """

    # prepare text for rendering
    font = pygame.font.SysFont(None, 48)

    # get start time
    latest_time = 0
    key_pressed = False
    score = 0
    print("entering loop")

    # get first note
    next_time, next_key = events_buttons_list[-1]

    # start the music
    music_timer = Timer(FALL_TIME / 1000, start_music)
    music_timer.start()

    # the clock will tick forward a regular amount on each cycle of the game loop
    # this means that the window for interaction in each cycle of the game loop is
    # is a consistent duration
    # consistency is important here because the player won't be able to anticipate
    # the beats if they slow down or speed up without warning
    clock = pygame.time.Clock()

    # check if there are any events left
    while len(events_buttons_list) > 0:
        # accumulate clock tick durations
        latest_time += clock.get_time()
        # increment falling rectangles and then draw them
        screen.fill(WHITE)
        score_text = font.render(f"Score: {score}", True, GREY)
        screen.blit(score_text, (5, 10))
        for rect in rects:
            rect.move_ip([0, pixels_per_frame])
            pygame.draw.rect(screen, RED, rect)
        # check if ready for next note
        if events_buttons_list[-1][0] > next_time:
            next_time, next_key = events_buttons_list[-1]
        # read serial
        ser_bytes = serialPort.read(1)
        decoded_bytes = ser_bytes.decode("utf-8")
        if decoded_bytes == "":
            decoded_bytes = 0
        else:
            decoded_bytes = int(decoded_bytes)
        # TODO: recognise wrong notes
        if decoded_bytes == next_key:
            # check if key pressed in window
            if next_time - ACTIVE_WINDOW < latest_time < next_time + ACTIVE_WINDOW:
                print("hit!")
                key_pressed = True
                score += 1
            # check if key pressed before window
            elif latest_time < next_time - ACTIVE_WINDOW:
                print("too early")
                key_pressed = True

        # after window condition
        if latest_time > next_time + ACTIVE_WINDOW:
            events_buttons_list.pop()
            if not key_pressed:
                print("miss")
            key_pressed = False

        # cycles no faster than the FPS
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    game_loop()
    print("exiting loop")
