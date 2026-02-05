import pygame
import sys

# 1. Инициализация
pygame.init()

# 2. Настройки на екрана
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Литературно приключение")

# Цветове (RGB)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 128)

# Шрифт за кирилица (използва системен шрифт или файл)
font = pygame.font.SysFont('arial', 24)

def draw_text(text, font, color, surface, x, y):
    textobj = font.render(text, True, color)
    textrect = textobj.get_rect()
    textrect.topleft = (x, y)
    surface.blit(textobj, textrect)

# 3. Основен цикъл на играта
running = True
while running:
    # Проверка за събития (натискане на X за затваряне)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Изчистване на екрана
    screen.fill(WHITE)

    # Логика на играта: Показване на сюжет
    # Тук може да слагате картинки (сцени от произведенията)
    draw_text("Произведение: 'Под игото'", font, BLACK, screen, 50, 50)
    draw_text("Глава: Гост", font, BLUE, screen, 50, 100)
    draw_text("Бойчо Огнянов влиза в воденицата...", font, BLACK, screen, 50, 150)

    # Обновяване на екрана
    pygame.display.flip()

pygame.quit()
sys.exit()