
import pygame
import game_clock

#MESSAGE SETTINGS
message_text = ""
message_start_time = 0
MESSAGE_DURATION = 1000
message_duration = MESSAGE_DURATION


def show_message(text, duration=MESSAGE_DURATION):
    #duration = HOW LONG THE MESSAGE STAYS ON SCREEN (MILLISECONDS)
    global message_text, message_start_time, message_duration

    message_text = text
    message_start_time = game_clock.now()
    message_duration = duration


def draw_message(screen, font):
    current_time = game_clock.now()

    if message_text and current_time - message_start_time < message_duration:
        text = font.render(message_text, True, (255, 255, 255))

        message_box = pygame.Rect(150, 520, 500, 45)

        pygame.draw.rect(screen, (40, 40, 40), message_box)

        screen.blit(
            text,
            (message_box.x + 15, message_box.y + 12)
        )
