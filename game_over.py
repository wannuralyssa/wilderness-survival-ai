import pygame

def gameover(screen, font, days_survived):
    #GAME OVER TITLE
    title_font = pygame.font.SysFont("Arial", 50, bold=True)
    over_text = title_font.render("GAME OVER", True, (220, 20, 60))
    screen.blit(over_text, (250, 180))

    #DAYS SURVIVED
    days_text = font.render(
        f"You survived {days_survived} days!",
        True,
        (255, 255, 255)
    )
    screen.blit(days_text, (290, 260))

    #RESTART INSTRUCTION
    restart_text = font.render("Press R to Restart", True, (255, 255, 255))
    screen.blit(restart_text, (310, 340))

    #QUIT INSTRUCTION
    quit_text = font.render("Press Q to Quit", True, (255, 255, 255))
    screen.blit(quit_text, (320, 380))