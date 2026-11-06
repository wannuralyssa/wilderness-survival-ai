
import pygame

#MESSAGE SETTINGS
message_text = ""
message_start_time = 0
MESSAGE_DURATION = 1000


def show_message(text):
    global message_text, message_start_time

    message_text = text
    message_start_time = pygame.time.get_ticks()


def draw_message(screen, font):
    current_time = pygame.time.get_ticks()

    if current_time - message_start_time < MESSAGE_DURATION:
        text = font.render(message_text, True, (255, 255, 255))

        message_box = pygame.Rect(150, 520, 500, 45)

        pygame.draw.rect(screen, (40, 40, 40), message_box)

        screen.blit(
            text,
            (message_box.x + 15, message_box.y + 12)
        )
