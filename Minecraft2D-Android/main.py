import array
import json
import math
import os
import random
import time
import pygame
import sys

pygame.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass

# Fenster
BREITE = 900
HOEHE = 600
screen = pygame.display.set_mode((BREITE, HOEHE), pygame.FULLSCREEN | pygame.SCALED)
pygame.display.set_caption("catchaft")

# Farben
HIMMEL_TOP = (65, 120, 210)
HIMMEL_MID = (128, 198, 255)
HIMMEL_BOTTOM = (190, 227, 255)
Sonne = (255, 220, 120)
Wolke = (245, 248, 255)
GRAS = (80, 200, 70)
ERDE = (130, 80, 40)
HOLZ = (145, 90, 45)
BLAETTER = (45, 155, 55)
SPIELER_FARBE = (255, 200, 50)
KATZE_FARBE = (220, 220, 220)
WEISS = (255, 255, 255)
HIMMEL = HIMMEL_MID

# Blockgröße
BLOCK = 40
WORLD_WIDTH = 80
WORLD_HEIGHT = 25

# Lebens- und Hungerwerte
MAX_HEALTH = 10
health = MAX_HEALTH
MAX_HUNGER = 10
hunger = MAX_HUNGER
HUNGER_VERLUST_MS = 40000
hunger_timer = 0

# Text und Symbole
font = pygame.font.SysFont(None, 20)
title_font = pygame.font.SysFont(None, 76)
subtitle_font = pygame.font.SysFont(None, 32)
fullscreen_enabled = True
sound_enabled = True
particles = []
language = "de"
LANGUAGE_NAMES = {"de": "Deutsch", "en": "English"}

# Android / Touch-Steuerung
ANDROID_MODE = sys.platform.startswith("android") or "ANDROID_ARGUMENT" in os.environ
touch_left = False
touch_right = False
touch_jump_pressed = False
touch_mode = "break"

def mobile_button_rects():
    size = 78
    gap = 12
    y = HOEHE - 178
    return {
        "left": pygame.Rect(18, y, size, size),
        "right": pygame.Rect(18 + size + gap, y, size, size),
        "jump": pygame.Rect(BREITE - 18 - size, y, size, size),
        "mode": pygame.Rect(BREITE - 18 - size * 2 - gap, HOEHE - 90, size, 60),
        "inventory": pygame.Rect(BREITE - 105, 18, 87, 52),
        "pause": pygame.Rect(BREITE - 205, 18, 87, 52),
    }

def mobile_touch_pos(event):
    return (int(event.x * BREITE), int(event.y * HOEHE))

def draw_mobile_controls(surface):
    if not ANDROID_MODE:
        return
    rects = mobile_button_rects()
    labels = {
        "left": "◀",
        "right": "▶",
        "jump": "↑",
        "mode": "ABBAU" if touch_mode == "break" else "SETZEN",
        "inventory": "INV",
        "pause": "PAUSE",
    }
    for name, rect in rects.items():
        pygame.draw.rect(surface, (20, 25, 32), rect, border_radius=14)
        pygame.draw.rect(surface, (220, 220, 220), rect, 2, border_radius=14)
        txt = subtitle_font.render(labels[name], True, WEISS)
        surface.blit(txt, txt.get_rect(center=rect.center))


def toggle_language():
    """Switch the current interface language between German and English."""
    global language
    language = "en" if language == "de" else "de"


def lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def spawn_particles(x, y, count=8, color=(255, 255, 255), speed=2.4):
    global particles
    for _ in range(count):
        particles.append({
            "x": x + random.uniform(-8, 8),
            "y": y + random.uniform(-8, 8),
            "vx": random.uniform(-speed, speed),
            "vy": random.uniform(-speed, 0.6),
            "life": random.randint(16, 34),
            "max_life": random.randint(16, 34),
            "size": random.randint(2, 5),
            "color": color,
        })


def update_particles(dt):
    global particles
    for particle in particles[:]:
        particle["life"] -= dt / 16.67
        particle["x"] += particle["vx"] * (dt / 16.67)
        particle["y"] += particle["vy"] * (dt / 16.67)
        particle["vy"] += 0.08 * (dt / 16.67)
        if particle["life"] <= 0:
            particles.remove(particle)


def draw_particles(surface, camera_x=0, camera_y=0):
    for particle in particles:
        alpha = max(0, min(255, int((particle["life"] / particle["max_life"]) * 255)))
        pos = (int(particle["x"] - camera_x), int(particle["y"] - camera_y))
        glow = pygame.Surface((particle["size"] * 4, particle["size"] * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*particle["color"], alpha), (particle["size"] * 2, particle["size"] * 2), particle["size"])
        surface.blit(glow, (pos[0] - particle["size"] * 2, pos[1] - particle["size"] * 2))


def draw_toggle_button(surface, rect, label, enabled):
    """Draw a simple on/off toggle button."""
    button_color = (40, 140, 80) if enabled else (110, 110, 110)
    shadow_color = (15, 60, 35) if enabled else (60, 60, 60)
    pygame.draw.rect(surface, shadow_color, rect.move(0, 4), border_radius=8)
    pygame.draw.rect(surface, button_color, rect, border_radius=8)
    pygame.draw.rect(surface, (230, 230, 230), rect, 2, border_radius=8)
    state_text = font.render(f"{label}: {'AN' if enabled else 'AUS'}", True, WEISS)
    surface.blit(state_text, state_text.get_rect(center=rect.center))


def set_sound_enabled(enabled):
    """Toggle all game sound effects and ambient noise."""
    global sound_enabled
    sound_enabled = enabled
    for sound in all_game_sounds:
        if sound:
            sound.set_volume(1.0 if enabled else 0.0)


def apply_fullscreen_mode(enabled):
    """Switch between fullscreen and windowed mode."""
    global screen, fullscreen_enabled
    fullscreen_enabled = enabled
    if enabled:
        screen = pygame.display.set_mode((BREITE, HOEHE), pygame.FULLSCREEN | pygame.SCALED)
    else:
        screen = pygame.display.set_mode((BREITE, HOEHE))


def show_loading_screen(message="Welt wird generiert..."):
    """Display a short loading animation before creating a new world."""
    loading_clock = pygame.time.Clock()
    start_time = time.monotonic()
    loading_title = "Lädt Welt..." if language == "de" else "Loading world..."

    while time.monotonic() - start_time < 1.4:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

        screen.fill((8, 18, 28))
        pygame.draw.rect(screen, (38, 54, 72), (0, HOEHE // 2 + 80, BREITE, HOEHE // 2))
        pygame.draw.rect(screen, (26, 35, 52), (0, HOEHE // 2 + 120, BREITE, HOEHE // 2))

        title = subtitle_font.render(loading_title, True, WEISS)
        title_rect = title.get_rect(center=(BREITE // 2, HOEHE // 2 - 40))
        screen.blit(title, title_rect)

        bar_x = BREITE // 2 - 180
        bar_y = HOEHE // 2 + 14
        bar_width = 360
        bar_height = 22
        progress = min(1.0, (time.monotonic() - start_time) / 1.4)
        pygame.draw.rect(screen, (50, 50, 58), (bar_x, bar_y, bar_width, bar_height), border_radius=10)
        pygame.draw.rect(screen, (102, 192, 94), (bar_x, bar_y, int(bar_width * progress), bar_height), border_radius=10)
        pygame.draw.rect(screen, (220, 220, 220), (bar_x, bar_y, bar_width, bar_height), 2, border_radius=10)

        message_text = font.render(message, True, WEISS)
        screen.blit(message_text, message_text.get_rect(center=(BREITE // 2, HOEHE // 2 + 60)))

        dots = "." * (1 + int((time.monotonic() * 5) % 4))
        dots_text = font.render(dots, True, WEISS)
        screen.blit(dots_text, dots_text.get_rect(center=(BREITE // 2 + 150, HOEHE // 2 + 60)))

        block_x = BREITE // 2 - 110 + int((time.monotonic() * 60) % 200)
        pygame.draw.rect(screen, (255, 192, 72), (block_x, HOEHE // 2 - 110, 40, 40), border_radius=6)
        pygame.draw.rect(screen, (120, 90, 45), (block_x + 6, HOEHE // 2 - 74, 28, 28), border_radius=4)

        pygame.display.flip()
        loading_clock.tick(60)


def show_title_screen():
    """Wait for the player to start the game from the fullscreen title screen."""
    title_clock = pygame.time.Clock()
    has_save = os.path.exists(SAVE_FILE)

    start_button_rect = pygame.Rect(BREITE // 2 - 130, HOEHE // 2 + 30, 260, 64)
    continue_button_rect = pygame.Rect(BREITE // 2 - 130, HOEHE // 2 + 110, 260, 64) if has_save else None
    settings_button_rect = pygame.Rect(BREITE // 2 - 130, HOEHE // 2 + 190, 260, 52)
    settings_open = False
    language_button_rect = pygame.Rect(BREITE // 2 - 150, HOEHE // 2 + 18, 300, 48)

    while True:
        is_german = language == "de"
        start_label = "NEUE WELT" if is_german else "NEW WORLD"
        continue_label = "WEITER SPIELEN" if is_german else "CONTINUE"
        settings_label = "EINSTELLUNGEN" if is_german else "SETTINGS"
        subtitle_label = "Dein kleines Abenteuer beginnt" if is_german else "Your little adventure begins"
        panel_title = "Einstellungen" if is_german else "Settings"
        back_label = "ZURÜCK" if is_german else "BACK"
        fullscreen_label = "Vollbild" if is_german else "Fullscreen"
        sound_label = "Ton" if is_german else "Sound"
        language_label = "Sprache" if is_german else "Language"
        hint_label = "Enter oder Klick    |    Esc zum Beenden" if is_german else "Enter or click    |    Esc to quit"
        loading_message = "Neue Welt wird geladen..." if is_german else "Loading new world..."

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE) and not settings_open:
                    if has_save:
                        load_game_state()
                        return
                    show_loading_screen(loading_message)
                    start_new_world()
                    return
                if event.key == pygame.K_ESCAPE:
                    if settings_open:
                        settings_open = False
                    else:
                        pygame.quit()
                        sys.exit()
                if event.key == pygame.K_s and not settings_open:
                    settings_open = True
            if event.type == pygame.FINGERDOWN:
                event = pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    pos=mobile_touch_pos(event),
                    button=1
                )

            if event.type == pygame.MOUSEBUTTONDOWN:
                if not settings_open:
                    if start_button_rect.collidepoint(event.pos):
                        show_loading_screen(loading_message)
                        start_new_world()
                        return
                    if continue_button_rect and continue_button_rect.collidepoint(event.pos):
                        if load_game_state():
                            return
                    if settings_button_rect.collidepoint(event.pos):
                        settings_open = True
                else:
                    fullscreen_rect = pygame.Rect(BREITE // 2 - 150, HOEHE // 2 - 20, 300, 48)
                    sound_rect = pygame.Rect(BREITE // 2 - 150, HOEHE // 2 + 48, 300, 48)
                    language_rect = pygame.Rect(BREITE // 2 - 150, HOEHE // 2 + 116, 300, 48)
                    back_rect = pygame.Rect(BREITE // 2 - 115, HOEHE // 2 + 184, 230, 44)
                    if fullscreen_rect.collidepoint(event.pos):
                        apply_fullscreen_mode(not fullscreen_enabled)
                    elif sound_rect.collidepoint(event.pos):
                        set_sound_enabled(not sound_enabled)
                    elif language_rect.collidepoint(event.pos):
                        toggle_language()
                    elif back_rect.collidepoint(event.pos):
                        settings_open = False

        screen.fill((92, 172, 235))
        pygame.draw.rect(screen, (121, 204, 91), (0, HOEHE // 2 + 105, BREITE, HOEHE // 2))
        pygame.draw.rect(screen, (105, 67, 38), (0, HOEHE // 2 + 145, BREITE, HOEHE // 2))

        title = title_font.render("CATCHAFT", True, WEISS)
        title_shadow = title_font.render("CATCHAFT", True, (45, 92, 44))
        title_position = title.get_rect(center=(BREITE // 2, HOEHE // 2 - 115))
        screen.blit(title_shadow, title_position.move(5, 7))
        screen.blit(title, title_position)

        subtitle = subtitle_font.render(subtitle_label, True, WEISS)
        screen.blit(subtitle, subtitle.get_rect(center=(BREITE // 2, HOEHE // 2 - 35)))

        pygame.draw.rect(screen, (55, 115, 58), start_button_rect, border_radius=8)
        pygame.draw.rect(screen, (190, 235, 145), start_button_rect, 3, border_radius=8)
        start_text = subtitle_font.render(start_label, True, WEISS)
        screen.blit(start_text, start_text.get_rect(center=start_button_rect.center))

        if continue_button_rect:
            pygame.draw.rect(screen, (25, 92, 92), continue_button_rect, border_radius=8)
            pygame.draw.rect(screen, (154, 210, 210), continue_button_rect, 3, border_radius=8)
            continue_text = subtitle_font.render(continue_label, True, WEISS)
            screen.blit(continue_text, continue_text.get_rect(center=continue_button_rect.center))

        pygame.draw.rect(screen, (55, 115, 58), settings_button_rect, border_radius=8)
        pygame.draw.rect(screen, (190, 235, 145), settings_button_rect, 3, border_radius=8)
        settings_text = font.render(settings_label, True, WEISS)
        screen.blit(settings_text, settings_text.get_rect(center=settings_button_rect.center))

        if settings_open:
            panel = pygame.Rect(BREITE // 2 - 180, HOEHE // 2 - 120, 360, 320)
            pygame.draw.rect(screen, (30, 30, 30), panel, border_radius=12)
            pygame.draw.rect(screen, (210, 210, 210), panel, 3, border_radius=12)
            panel_title_render = subtitle_font.render(panel_title, True, WEISS)
            screen.blit(panel_title_render, panel_title_render.get_rect(center=(panel.centerx, panel.y + 26)))
            draw_toggle_button(screen, pygame.Rect(BREITE // 2 - 150, HOEHE // 2 - 20, 300, 48), fullscreen_label, fullscreen_enabled)
            draw_toggle_button(screen, pygame.Rect(BREITE // 2 - 150, HOEHE // 2 + 48, 300, 48), sound_label, sound_enabled)
            pygame.draw.rect(screen, (40, 140, 80), pygame.Rect(BREITE // 2 - 150, HOEHE // 2 + 116, 300, 48), border_radius=8)
            pygame.draw.rect(screen, (230, 230, 230), pygame.Rect(BREITE // 2 - 150, HOEHE // 2 + 116, 300, 48), 2, border_radius=8)
            language_text = font.render(f"{language_label}: {LANGUAGE_NAMES[language]}", True, WEISS)
            screen.blit(language_text, language_text.get_rect(center=(BREITE // 2, HOEHE // 2 + 140)))
            back_button = pygame.Rect(BREITE // 2 - 115, HOEHE // 2 + 184, 230, 44)
            pygame.draw.rect(screen, (100, 100, 100), back_button, border_radius=8)
            pygame.draw.rect(screen, (230, 230, 230), back_button, 2, border_radius=8)
            back_text = font.render(back_label, True, WEISS)
            screen.blit(back_text, back_text.get_rect(center=back_button.center))

        hint = font.render(hint_label, True, WEISS)
        screen.blit(hint, hint.get_rect(center=(BREITE // 2, HOEHE - 28)))
        pygame.display.flip()
        title_clock.tick(60)

def draw_cloud(surface, x, y, scale=1.0):
    puff = pygame.Surface((120, 50), pygame.SRCALPHA)
    cloud_color = (245, 248, 255, 210)
    pygame.draw.ellipse(puff, cloud_color, (0, 14, 55, 22))
    pygame.draw.ellipse(puff, cloud_color, (18, 0, 52, 28))
    pygame.draw.ellipse(puff, cloud_color, (45, 12, 52, 24))
    pygame.draw.ellipse(puff, cloud_color, (72, 10, 36, 20))
    puff = pygame.transform.smoothscale(puff, (int(120 * scale), int(50 * scale)))
    surface.blit(puff, (x, y))


def draw_background(surface):
    cycle = (math.sin(time.monotonic() * 0.12) + 1.0) / 2.0
    sky_top = lerp_color((15, 22, 40), (70, 128, 220), cycle)
    sky_mid = lerp_color((72, 109, 169), (145, 215, 255), cycle)
    sky_bottom = lerp_color((165, 215, 255), (255, 235, 188), cycle)

    sky = pygame.Surface((BREITE, HOEHE), pygame.SRCALPHA)
    for i in range(HOEHE):
        t = i / max(1, HOEHE)
        if t < 0.5:
            r, g, b = lerp_color(sky_top, sky_mid, t * 2)
        else:
            r, g, b = lerp_color(sky_mid, sky_bottom, (t - 0.5) * 2)
        pygame.draw.line(sky, (r, g, b), (0, i), (BREITE, i))
    surface.blit(sky, (0, 0))

    sun_x = BREITE - 120 + int(math.sin(time.monotonic() * 0.5) * 26)
    sun_y = 110 + int(math.cos(time.monotonic() * 0.3) * 22)
    sun_r = 48
    pygame.draw.circle(surface, (255, 220, 120), (sun_x, sun_y), sun_r)
    pygame.draw.circle(surface, (255, 236, 170, 120), (sun_x, sun_y), sun_r + 18)

    draw_cloud(surface, 70 + int(math.sin(time.monotonic() * 0.15) * 12), 60, 1.3)
    draw_cloud(surface, 310, 88, 1.0)
    draw_cloud(surface, 540 + int(math.cos(time.monotonic() * 0.18) * 18), 70, 1.2)

    mountain_color = (92, 116, 150)
    mountain_dark = (54, 74, 98)
    for x in range(-40, BREITE + 60, 120):
        points = [(x, HOEHE // 2 + 10), (x + 60, HOEHE // 2 - 80), (x + 120, HOEHE // 2 + 10)]
        pygame.draw.polygon(surface, mountain_color, points)
        pygame.draw.polygon(surface, mountain_dark, [(x + 32, HOEHE // 2 + 10), (x + 60, HOEHE // 2 - 40), (x + 92, HOEHE // 2 + 10)])

    hill_color = (101, 163, 94)
    hill_dark = (72, 131, 68)
    pygame.draw.ellipse(surface, hill_color, (-30, HOEHE // 2 + 30, BREITE + 80, 200))
    pygame.draw.ellipse(surface, hill_dark, (200, HOEHE // 2 + 60, BREITE // 2, 120))

    sparkle_color = (255, 255, 255)
    for i in range(8):
        px = ((i * 117) + int(time.monotonic() * 24)) % BREITE
        py = 80 + (i % 3) * 26 + (i % 2) * 14
        pygame.draw.circle(surface, sparkle_color, (px, py), 1 + (i % 2))


def draw_heart(surface, x, y, size, color):
    radius = size // 4
    pygame.draw.circle(surface, color, (x + radius, y + radius), radius)
    pygame.draw.circle(surface, color, (x + 3 * radius, y + radius), radius)
    points = [
        (x, y + radius),
        (x + size, y + radius),
        (x + size // 2, y + size)
    ]
    pygame.draw.polygon(surface, color, points)


def draw_chicken(surface, x, y, size, color):
    # Hähnchen-Symbol zeichnen
    # Körper
    pygame.draw.ellipse(surface, color, (x + size // 4, y + size // 3, size // 2, size // 2))
    
    # Kopf
    pygame.draw.circle(surface, color, (x + size * 3 // 4, y + size // 4), size // 6)
    
    # Schnabel
    points = [(x + size * 3 // 4 + size // 6, y + size // 4 - size // 12),
              (x + size * 3 // 4 + size // 6, y + size // 4 + size // 12),
              (x + size * 3 // 4 + size // 4, y + size // 4)]
    pygame.draw.polygon(surface, (255, 150, 0), points)
    
    # Flügel (dunklere Variante der Körperfarbe)
    wing_color = (max(0, color[0] - 30), max(0, color[1] - 30), max(0, color[2] - 30))
    pygame.draw.polygon(surface, wing_color, 
                       [(x + size // 3, y + size // 2), (x + size // 3 - size // 8, y + size // 3),
                        (x + size // 2, y + size // 3)])
    
    # Beine
    pygame.draw.line(surface, (255, 150, 0), (x + size // 2 - size // 8, y + size * 5 // 6),
                     (x + size // 2 - size // 8, y + size), 2)
    pygame.draw.line(surface, (255, 150, 0), (x + size // 2 + size // 8, y + size * 5 // 6),
                     (x + size // 2 + size // 8, y + size), 2)


def draw_hud(surface):
    health_panel = pygame.Rect(12, 12, 232, 44)
    hunger_panel = pygame.Rect(12, 58, 232, 44)
    pygame.draw.rect(surface, (18, 24, 34, 160), health_panel, border_radius=12)
    pygame.draw.rect(surface, (18, 24, 34, 160), hunger_panel, border_radius=12)
    pygame.draw.rect(surface, (255, 255, 255, 80), health_panel, 1, border_radius=12)
    pygame.draw.rect(surface, (255, 255, 255, 80), hunger_panel, 1, border_radius=12)

    for i in range(MAX_HEALTH):
        color = (255, 60, 60) if i < health else (80, 35, 35)
        draw_heart(surface, 24 + i * 24, 22, 18, color)

    for i in range(MAX_HUNGER):
        color = (245, 170, 60) if i < hunger else (110, 82, 38)
        draw_chicken(surface, 24 + i * 22, 68, 16, color)

    hotbar_y = HOEHE - 82
    hotbar_bg = pygame.Rect(18, hotbar_y - 12, HOTBAR_SIZE * 70 + 18, 70)
    pygame.draw.rect(surface, (18, 23, 30, 200), hotbar_bg, border_radius=14)
    pygame.draw.rect(surface, (120, 145, 180, 180), hotbar_bg, 2, border_radius=14)

    for i in range(HOTBAR_SIZE):
        slot_x = 26 + i * 70
        slot_rect = pygame.Rect(slot_x, hotbar_y, 60, 40)
        slot_color = (255, 196, 84) if i == selected_slot else (120, 120, 120)
        shadow_color = (167, 111, 20) if i == selected_slot else (80, 80, 80)
        pygame.draw.rect(surface, shadow_color, slot_rect.move(0, 4), border_radius=8)
        pygame.draw.rect(surface, slot_color, slot_rect, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), slot_rect, 2, border_radius=8)

        item = hotbar_items[i]
        count = hotbar_counts[i]

        if item in textures:
            item_texture = pygame.transform.scale(textures[item], (24, 24))
            surface.blit(item_texture, (slot_x + 18, hotbar_y + 8))

        if count > 1:
            text = font.render(str(count), True, WEISS)
            surface.blit(text, (slot_x + 42, hotbar_y + 18))


def draw_player(surface, rect):
    # Schatten
    shadow_rect = pygame.Rect(rect.x + 5, rect.bottom - 5, rect.width - 10, 8)
    pygame.draw.ellipse(surface, (40, 40, 40), shadow_rect)

    lucy_equipped = "armor_items" in globals() and armor_items[0] != "leer"
    fur = (145, 132, 116)
    light_fur = (190, 177, 157)
    dark_fur = (62, 56, 52)
    ear_pink = (174, 112, 112)

    # Körper
    body_rect = pygame.Rect(rect.x, rect.y + rect.height // 4, rect.width, rect.height * 3 // 4)
    body_color = fur if lucy_equipped else (240, 180, 70)
    pygame.draw.rect(surface, dark_fur if lucy_equipped else (240, 180, 70), body_rect, border_radius=8)
    pygame.draw.rect(surface, body_color if lucy_equipped else SPIELER_FARBE,
                     body_rect.inflate(-6, -6), border_radius=6)
    if lucy_equipped:
        pygame.draw.polygon(surface, light_fur, ((rect.x + 7, body_rect.y + 5),
                                                  (rect.centerx, body_rect.bottom - 7),
                                                  (rect.right - 7, body_rect.y + 5)))
        pygame.draw.line(surface, dark_fur, (rect.centerx - 5, body_rect.y + 4),
                         (rect.centerx - 7, body_rect.y + 17), 2)
        pygame.draw.line(surface, dark_fur, (rect.centerx, body_rect.y + 3),
                         (rect.centerx, body_rect.y + 17), 2)
        pygame.draw.line(surface, dark_fur, (rect.centerx + 5, body_rect.y + 4),
                         (rect.centerx + 7, body_rect.y + 17), 2)

    # Kopf
    head_rect = pygame.Rect(rect.x, rect.y, rect.width, rect.height // 2)
    pygame.draw.rect(surface, dark_fur if lucy_equipped else (255, 220, 120), head_rect, border_radius=8)
    pygame.draw.rect(surface, light_fur if lucy_equipped else (240, 200, 90),
                     head_rect.inflate(-6, -6), border_radius=6)

    if lucy_equipped:
        pygame.draw.polygon(surface, dark_fur, ((rect.x + 2, rect.y + 8),
                                                (rect.x + 7, rect.y - 8),
                                                (rect.centerx - 2, rect.y + 3)))
        pygame.draw.polygon(surface, dark_fur, ((rect.right - 2, rect.y + 8),
                                                (rect.right - 7, rect.y - 8),
                                                (rect.centerx + 2, rect.y + 3)))
        pygame.draw.polygon(surface, ear_pink, ((rect.x + 5, rect.y + 3),
                                                (rect.x + 7, rect.y - 4),
                                                (rect.centerx - 3, rect.y + 3)))
        pygame.draw.polygon(surface, ear_pink, ((rect.right - 5, rect.y + 3),
                                                (rect.right - 7, rect.y - 4),
                                                (rect.centerx + 3, rect.y + 3)))
        pygame.draw.line(surface, dark_fur, (rect.x + 8, rect.y + 3),
                         (rect.x + 11, rect.y + 10), 2)
        pygame.draw.line(surface, dark_fur, (rect.right - 8, rect.y + 3),
                         (rect.right - 11, rect.y + 10), 2)
        paw_y = rect.bottom - 7
        pygame.draw.ellipse(surface, dark_fur, (rect.x + 2, paw_y - 3, rect.width // 2 - 2, 10))
        pygame.draw.ellipse(surface, dark_fur, (rect.centerx, paw_y - 3, rect.width // 2 - 2, 10))
        pygame.draw.circle(surface, light_fur, (rect.x + rect.width // 4, paw_y + 2), 2)
        pygame.draw.circle(surface, light_fur, (rect.x + rect.width * 3 // 4, paw_y + 2), 2)

    # Augen
    eye_y = rect.y + rect.height // 8 + 5
    eye_color = (92, 68, 38) if lucy_equipped else (0, 0, 0)
    pygame.draw.circle(surface, eye_color, (rect.x + rect.width // 4, eye_y), 3)
    pygame.draw.circle(surface, eye_color, (rect.x + rect.width * 3 // 4, eye_y), 3)

    # Mund
    pygame.draw.arc(
        surface,
        (0, 0, 0),
        (rect.x + rect.width // 4, rect.y + rect.height // 4, rect.width // 2, rect.height // 6),
        3.3,
        6.0,
        2
    )


def draw_cat(surface, rect, schnurren=False, purr_timer=0):
    # Körper
    body = pygame.Rect(rect.x, rect.y + rect.height // 4, rect.width, rect.height * 3 // 4)
    pygame.draw.ellipse(surface, KATZE_FARBE, body)
    pygame.draw.ellipse(surface, (180, 180, 180), body.inflate(-8, -12))

    # Kopf
    head = pygame.Rect(rect.x + 4, rect.y, rect.width - 8, rect.height // 2)
    pygame.draw.ellipse(surface, KATZE_FARBE, head)
    pygame.draw.polygon(surface, KATZE_FARBE, [(rect.x + 6, rect.y + 4), (rect.x + 14, rect.y - 6), (rect.x + 22, rect.y + 4)])
    pygame.draw.polygon(surface, KATZE_FARBE, [(rect.x + rect.width - 6, rect.y + 4), (rect.x + rect.width - 14, rect.y - 6), (rect.x + rect.width - 22, rect.y + 4)])

    # Gesicht
    eye_y = rect.y + rect.height // 8 + 4
    pygame.draw.circle(surface, (30, 30, 30), (rect.x + rect.width // 4, eye_y), 3)
    pygame.draw.circle(surface, (30, 30, 30), (rect.x + rect.width * 3 // 4, eye_y), 3)
    pygame.draw.line(surface, (30, 30, 30), (rect.x + rect.width // 2 - 4, rect.y + rect.height // 4 + 4), (rect.x + rect.width // 2 + 4, rect.y + rect.height // 4 + 4), 2)

    # Schwanz
    tail = pygame.Rect(rect.right - 5, rect.y + rect.height // 2, 10, 6)
    pygame.draw.rect(surface, KATZE_FARBE, tail, border_radius=4)

    if schnurren:
        offset = 4 if purr_timer < 250 else -4
        pygame.draw.circle(surface, WEISS, (rect.centerx - 12, rect.y - 6 + offset), 4)
        pygame.draw.circle(surface, WEISS, (rect.centerx + 12, rect.y - 10 - offset), 4)
        purr_text = font.render("Schnurr", True, WEISS)
        surface.blit(purr_text, (rect.centerx - purr_text.get_width() // 2, rect.y - 24))


def draw_inventory(surface, show_workbench=False):
    """Draw the inventory window over the game."""
    overlay = pygame.Surface((BREITE, HOEHE), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    surface.blit(overlay, (0, 0))

    panel = pygame.Rect(BREITE // 2 - 310, HOEHE // 2 - 250, 620, 500)
    pygame.draw.rect(surface, (45, 45, 45), panel, border_radius=10)
    pygame.draw.rect(surface, (190, 190, 190), panel, 3, border_radius=10)

    title = font.render("Handwerk" if show_workbench else "Inventar", True, WEISS)
    surface.blit(title, (panel.x + 20, panel.y + 18))

    if not show_workbench:
        for index in range(4):
            armor_rect = pygame.Rect(panel.x + 20, panel.y + 58 + index * 54, 42, 42)
            pygame.draw.rect(surface, (115, 115, 115), armor_rect)
            pygame.draw.rect(surface, (235, 235, 235), armor_rect, 2)
            armor_item = armor_items[index]
            if armor_item in textures:
                armor_texture = pygame.transform.scale(textures[armor_item], (34, 34))
                surface.blit(armor_texture, (armor_rect.x + 4, armor_rect.y + 4))
        player_rect = pygame.Rect(panel.x + 82, panel.y + 58, 120, 170)
        pygame.draw.rect(surface, (15, 15, 15), player_rect)
        draw_player(surface, pygame.Rect(player_rect.x + 42, player_rect.y + 35, 36, 90))

        small_grid_x = panel.x + 350
        small_grid_y = panel.y + 65
        for index in range(4):
            slot_rect = pygame.Rect(small_grid_x + (index % 2) * 54,
                                    small_grid_y + (index // 2) * 54, 50, 50)
            pygame.draw.rect(surface, (115, 115, 115), slot_rect)
            pygame.draw.rect(surface, (235, 235, 235), slot_rect, 2)
        pygame.draw.line(surface, (155, 155, 155), (panel.x + 470, panel.y + 115),
                         (panel.x + 510, panel.y + 115), 7)
        pygame.draw.polygon(surface, (155, 155, 155), ((panel.x + 510, panel.y + 101),
                                                         (panel.x + 530, panel.y + 115),
                                                         (panel.x + 510, panel.y + 129)))
        result_rect = pygame.Rect(panel.x + 545, panel.y + 88, 55, 55)
        pygame.draw.rect(surface, (115, 115, 115), result_rect)
        pygame.draw.rect(surface, (235, 235, 235), result_rect, 2)

        for row in range(3):
            for column in range(9):
                slot_rect = pygame.Rect(panel.x + 20 + column * 66,
                                        panel.y + 255 + row * 54, 60, 50)
                pygame.draw.rect(surface, (115, 115, 115), slot_rect)
                pygame.draw.rect(surface, (235, 235, 235), slot_rect, 2)

    if show_workbench:
        grid_x = panel.x + 28
        grid_y = panel.y + 60
        for index in range(9):
            slot_x = grid_x + (index % 3) * 54
            slot_y = grid_y + (index // 3) * 54
            pygame.draw.rect(surface, (115, 115, 115), (slot_x, slot_y, 50, 50), border_radius=4)
            pygame.draw.rect(surface, (235, 235, 235), (slot_x, slot_y, 50, 50), 2)
            item = craft_grid[index]
            if item in textures:
                surface.blit(pygame.transform.scale(textures[item], (34, 34)), (slot_x + 8, slot_y + 8))

        arrow_y = grid_y + 76
        pygame.draw.line(surface, (155, 155, 155), (panel.x + 220, arrow_y), (panel.x + 270, arrow_y), 7)
        pygame.draw.polygon(surface, (155, 155, 155), ((panel.x + 270, arrow_y - 14),
                                                         (panel.x + 290, arrow_y),
                                                         (panel.x + 270, arrow_y + 14)))
        result_slot = pygame.Rect(panel.x + 315, panel.y + 84, 58, 58)
        pygame.draw.rect(surface, (115, 115, 115), result_slot)
        pygame.draw.rect(surface, (235, 235, 235), result_slot, 2)
        result = "4 Stoecke" if craft_grid[4] == "bretter" and craft_grid[7] == "bretter" and sum(item != "leer" for item in craft_grid) == 2 else ""
        if result:
            surface.blit(pygame.transform.scale(textures["stoecke"], (34, 34)), (result_slot.x + 8, result_slot.y + 8))
        result_text = font.render(result, True, WEISS)
        surface.blit(result_text, (result_slot.x + 5, result_slot.bottom + 4))

    for index, (item, count) in enumerate(zip(hotbar_items, hotbar_counts)):
        slot_x = panel.x + 25 + index * 96
        slot_y = panel.y + (420 if not show_workbench else 255)
        slot_color = (180, 180, 180) if index == selected_slot else (115, 115, 115)
        pygame.draw.rect(surface, slot_color, (slot_x, slot_y, 80, 80), border_radius=6)
        pygame.draw.rect(surface, (220, 220, 220), (slot_x, slot_y, 80, 80), 2, border_radius=6)

        if item in textures:
            item_texture = pygame.transform.scale(textures[item], (40, 40))
            surface.blit(item_texture, (slot_x + 20, slot_y + 18))

        count_text = font.render(str(count), True, WEISS)
        surface.blit(count_text, (slot_x + 58, slot_y + 58))

    if show_workbench:
        craft_title = font.render("Crafting", True, WEISS)
        surface.blit(craft_title, (panel.x + 25, panel.y + 225))
        recipe = font.render(
            f"1 Holz -> 4 Bretter | 4 Bretter -> Werkbank | 2 Bretter -> 4 Stoecke",
            True,
            WEISS,
        )
        surface.blit(recipe, (panel.x + 25, panel.y + 348))

    hint_text = "Linksklick: Nehmen    Rechtsklick: Platzieren    C: Herstellen    E: Schließen" if show_workbench else "Linksklick: Auswählen    E: Schließen"
    hint = font.render(hint_text, True, WEISS)
    surface.blit(hint, hint.get_rect(center=(panel.centerx, panel.bottom - 35)))


def add_item_to_inventory(item, amount=1):
    """Add an item to an existing stack or the first empty slot."""
    for index, current_item in enumerate(hotbar_items):
        if current_item == item:
            hotbar_counts[index] += amount
            return

    for index, current_item in enumerate(hotbar_items):
        if current_item == "leer":
            hotbar_items[index] = item
            hotbar_counts[index] = amount
            return


def can_craft_sticks():
    return (werkbank_open and craft_grid[4] == "bretter"
            and craft_grid[7] == "bretter"
            and sum(item != "leer" for item in craft_grid) == 2)


def take_crafted_sticks():
    if can_craft_sticks():
        craft_grid[4] = "leer"
        craft_grid[7] = "leer"
        add_item_to_inventory("stoecke", 4)
        return True
    return False


def get_block_at_pixel(px, py):
    tx = px // BLOCK
    ty = py // BLOCK
    if 0 <= ty < len(welt) and 0 <= tx < len(welt[0]):
        return welt[ty][tx]
    return "luft"


def get_ground_y_for_rect(rect):
    candidates = []
    for px in (rect.left + 2, rect.centerx, rect.right - 2):
        tx = px // BLOCK
        if 0 <= tx < len(welt[0]):
            for ty in range(len(welt)):
                if welt[ty][tx] != "luft":
                    candidates.append(ty * BLOCK)
                    break
    if not candidates:
        return len(welt) * BLOCK
    return min(candidates)


def _clamp(v, a=0, b=255):
    return max(a, min(b, int(v)))


def shade_color(col, factor):
    return (_clamp(col[0] * factor), _clamp(col[1] * factor), _clamp(col[2] * factor))


def draw_block(surface, bx, by, block_type, offset_x=0, offset_y=0):
    # bx,by are tile coords
    x = bx * BLOCK - offset_x
    y = by * BLOCK - offset_y
    base = pygame.Rect(x, y, BLOCK, BLOCK)

    # If texture available, blit scaled texture
    tex = textures.get(block_type)
    if block_type == "gras" and by > 0 and welt[by - 1][bx] == "gras":
        tex = textures.get("erde", tex)
    if tex:
        if tex.get_width() != BLOCK or tex.get_height() != BLOCK:
            tex_s = pygame.transform.smoothscale(tex, (BLOCK, BLOCK))
        else:
            tex_s = tex
        surface.blit(tex_s, (x, y))
        pygame.draw.rect(surface, (40, 40, 40), base, 1)
        return

    if block_type == "gras":
        base_col = GRAS
        pygame.draw.rect(surface, shade_color(base_col, 0.88), base)
        top_h = max(6, BLOCK // 6)
        pygame.draw.rect(surface, shade_color(base_col, 1.12), (x, y, BLOCK, top_h))
        pygame.draw.line(surface, (160, 232, 120), (x, y + 2), (x + BLOCK, y + 2), 2)
        for i in range(4):
            rx = x + (i * 9 + bx * 3) % (BLOCK - 4)
            ry = y + (i * 7 + by * 5) % (BLOCK - 6)
            pygame.draw.rect(surface, shade_color(base_col, 0.75), (rx, ry, 3, 3))
        pygame.draw.line(surface, shade_color(base_col, 0.6), (x, y + top_h), (x + BLOCK, y + top_h))

    elif block_type == "erde":
        base_col = ERDE
        pygame.draw.rect(surface, shade_color(base_col, 0.95), base)
        band_h = max(6, BLOCK // 6)
        pygame.draw.rect(surface, shade_color(base_col, 0.78), (x, y + BLOCK - band_h, BLOCK, band_h))
        for i in range(6):
            rx = x + (i * 5 + bx * 11) % (BLOCK - 3)
            ry = y + (i * 3 + by * 13) % (BLOCK - 3)
            pygame.draw.rect(surface, shade_color(base_col, 0.6), (rx, ry, 2, 2))

    elif block_type == "holz":
        base_col = HOLZ
        pygame.draw.rect(surface, base_col, base)
        for grain_x in (7, 18, 29, 40):
            pygame.draw.line(surface, shade_color(base_col, 0.68), (x + grain_x, y), (x + grain_x, y + BLOCK), 2)
        for ring_y in range(0, BLOCK + 1, 8):
            pygame.draw.line(surface, shade_color(base_col, 1.18), (x + 2, y + ring_y), (x + BLOCK - 2, y + ring_y), 1)

    elif block_type == "blaetter":
        base_col = BLAETTER
        pygame.draw.rect(surface, base_col, base)
        for i in range(5):
            rx = x + (i * 11 + bx * 3) % (BLOCK - 5)
            ry = y + (i * 7 + by * 5) % (BLOCK - 5)
            pygame.draw.rect(surface, shade_color(base_col, 0.7), (rx, ry, 4, 4))
        pygame.draw.circle(surface, shade_color(base_col, 1.2), (x + BLOCK // 2, y + BLOCK // 2), 7)

    else:
        return

    # thin border for contrast
    pygame.draw.rect(surface, (40, 40, 40), base, 1)


AUDIO_EXTENSIONS = ['wav', 'ogg', 'mp3', 'aac', 'm4a', 'flac']


def load_sound_for_keywords(keywords, label):
    base_dir = os.path.dirname(__file__) or os.getcwd()
    candidates = []

    for keyword in keywords:
        for ext in AUDIO_EXTENSIONS:
            candidates.append(os.path.join(base_dir, f'{keyword}.{ext}'))

    for root, _, files in os.walk(base_dir):
        for name in files:
            lower = name.lower()
            if any(keyword in lower for keyword in keywords) and any(lower.endswith(f'.{ext}') for ext in AUDIO_EXTENSIONS):
                candidates.append(os.path.join(root, name))

    seen = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if os.path.exists(path):
            try:
                sound = pygame.mixer.Sound(path)
                print(f'Loaded {label} sound: {path}')
                return sound
            except pygame.error:
                print(f'Failed to load {label} sound: {path}')
                continue

    print(f'No valid {label} sound found in project directory.')
    return None


def load_purr_sound():
    return load_sound_for_keywords(['schnurren', 'schnurr', 'purr'], 'purr')


def load_run_sound():
    return load_sound_for_keywords(['grass1', 'grass', 'step', 'steps', 'lauf', 'walk', 'foot', 'footstep'], 'run')


def load_damage_sound():
    return load_sound_for_keywords(['damage', 'hurt', 'hit', 'schaden', 'verletz', 'minecraft damage'], 'damage')


def load_jump_sound():
    return load_sound_for_keywords(['jump', 'sprung', 'bounce', 'hop'], 'jump')


def load_break_sound():
    return load_sound_for_keywords(['break', 'mine', 'dig', 'abbau', 'block', 'stone', 'grass'], 'break')


def load_place_sound():
    return load_sound_for_keywords(['place', 'build', 'set', 'platz', 'bauen'], 'place')


def load_craft_sound():
    return load_sound_for_keywords(['craft', 'crafting', 'recipe', 'herstell', 'workbench'], 'craft')


def load_death_sound():
    return load_sound_for_keywords(['death', 'die', 'tot', 'gameover', 'minecraft death'], 'death')


purr_sound = load_purr_sound()
run_sound = load_run_sound()
damage_sound = load_damage_sound()
jump_sound = load_jump_sound()
break_sound = load_break_sound()
place_sound = load_place_sound()
craft_sound = load_craft_sound()
death_sound = load_death_sound()
all_game_sounds = [run_sound, purr_sound, damage_sound, jump_sound, break_sound, place_sound, craft_sound, death_sound]
run_sound_playing = False
damage_sound_cooldown = 0
death_sound_played = False

# Textures dict (fills with loaded or generated textures)
textures = {}


def create_grass_texture(size):
    surf = pygame.Surface((size, size)).convert_alpha()
    soil = (119, 75, 42)
    soil_light = (151, 99, 52)
    soil_dark = (78, 48, 31)
    grass_light = (133, 211, 67)
    grass_mid = (83, 177, 54)
    grass_dark = (47, 119, 47)
    surf.fill(soil)

    for y in range(size // 3, size, 4):
        shade = soil_light if (y // 4) % 2 == 0 else soil_dark
        pygame.draw.line(surf, shade, (0, y), (size - 1, y), 1)
    for i in range(16):
        x = (i * 17 + 3) % size
        y = size // 3 + (i * 11 + 2) % max(1, size - size // 3 - 2)
        color = soil_dark if i % 3 == 0 else soil_light
        pygame.draw.rect(surf, color, (x, y, 2 + i % 2, 2))

    top_h = max(9, size // 4)
    pygame.draw.rect(surf, grass_dark, (0, 0, size, top_h + 3))
    pygame.draw.rect(surf, grass_mid, (0, 0, size, top_h))
    pygame.draw.rect(surf, grass_light, (0, 0, size, max(3, size // 10)))
    pygame.draw.line(surf, (191, 232, 103), (0, 1), (size - 1, 1), 1)
    pygame.draw.line(surf, (54, 137, 49), (0, top_h - 1), (size - 1, top_h - 1), 2)
    for x, drop_h in ((4, 5), (11, 3), (19, 7), (29, 4), (36, 6)):
        if x < size:
            pygame.draw.rect(surf, grass_mid, (x, top_h, 3, min(drop_h, size - top_h)))
            pygame.draw.rect(surf, grass_dark, (x + 2, top_h + 2, 1, max(1, drop_h - 2)))
    for i in range(12):
        x = (i * 13 + 3) % size
        y = (i * 7 + 4) % max(1, top_h - 2)
        pygame.draw.rect(surf, grass_light if i % 3 else (183, 218, 83), (x, y, 2, 2))
    for x, y in ((7, 25), (18, 32), (33, 22), (25, 37)):
        if x + 2 < size and y + 2 < size:
            pygame.draw.rect(surf, soil_dark, (x, y, 2, 2))
    return surf


def create_dirt_texture(size):
    surf = pygame.Surface((size, size)).convert_alpha()
    soil_mid = (139, 88, 48)
    soil_light = (174, 119, 66)
    soil_dark = (91, 56, 37)
    soil_deep = (67, 46, 35)
    surf.fill(soil_mid)
    for y in range(3, size, 8):
        pygame.draw.line(surf, soil_dark if (y // 8) % 2 else soil_light,
                         (0, y), (size - 1, y), 1)
    for i in range(24):
        x = (i * 17 + 3) % max(1, size - 3)
        y = (i * 11 + 5) % max(1, size - 3)
        color = (soil_light, soil_dark, soil_deep)[i % 3]
        pebble_w = 2 + i % 3
        pygame.draw.rect(surf, color, (x, y, min(pebble_w, size - x), 1 + i % 2))
        if i % 4 == 0 and y + 3 < size:
            pygame.draw.rect(surf, soil_deep, (x + 1, y + 2, 2, 1))
    for x, y in ((5, 7), (28, 14), (13, 28), (34, 34)):
        if x + 3 < size and y + 3 < size:
            pygame.draw.rect(surf, (112, 112, 103), (x, y, 3, 2))
            pygame.draw.rect(surf, (78, 81, 77), (x + 1, y + 2, 2, 1))
    pygame.draw.line(surf, (194, 139, 79), (1, 1), (size - 2, 1), 1)
    pygame.draw.line(surf, soil_deep, (0, size - 1), (size - 1, size - 1), 1)
    return surf


def create_wood_texture(size):
    surf = pygame.Surface((size, size)).convert_alpha()
    bark_base = (126, 76, 41)
    bark_light = (177, 116, 60)
    bark_highlight = (205, 145, 74)
    bark_dark = (79, 48, 32)
    surf.fill(bark_base)
    for x, width, color in ((3, 4, bark_dark), (7, 3, bark_light), (13, 5, bark_base),
                            (20, 3, bark_dark), (24, 5, bark_light), (32, 4, bark_dark),
                            (37, 2, bark_highlight)):
        if x < size:
            pygame.draw.rect(surf, color, (x, 0, min(width, size - x), size))
    for y in (6, 17, 29, 37):
        if y < size:
            pygame.draw.line(surf, bark_dark, (0, y), (size - 1, min(size - 1, y + 1)), 1)
            pygame.draw.line(surf, bark_highlight, (1, y + 2), (size - 3, min(size - 1, y + 2)), 1)
    if size >= 24:
        pygame.draw.ellipse(surf, bark_dark, (size // 2 - 5, size // 2 - 7, 10, 15))
        pygame.draw.ellipse(surf, bark_light, (size // 2 - 2, size // 2 - 5, 3, 10))
        pygame.draw.rect(surf, bark_highlight, (2, 2, size - 4, 1))
    pygame.draw.rect(surf, bark_dark, (0, 0, size, size), 1)
    return surf


def create_plank_texture(size):
    surf = pygame.Surface((size, size)).convert_alpha()
    board_base = (151, 99, 49)
    board_light = (197, 145, 79)
    board_mid = (173, 119, 58)
    board_dark = (91, 57, 33)
    surf.fill(board_dark)
    board_h = max(7, size // 4)
    for row, y in enumerate(range(1, size, board_h)):
        left = 2 if row % 2 == 0 else size // 3
        right = size - 2 if row % 2 == 0 else size - size // 3
        rect = pygame.Rect(1, y, size - 2, min(board_h - 1, size - y - 1))
        pygame.draw.rect(surf, board_base if row % 2 else board_mid, rect)
        seam_x = left if row % 2 == 0 else right
        pygame.draw.line(surf, board_dark, (1, y), (size - 2, y), 1)
        pygame.draw.line(surf, board_dark, (seam_x, y + 1), (seam_x, min(size - 2, y + board_h - 1)), 1)
        pygame.draw.line(surf, board_light, (3, y + 2), (size - 4, y + 2), 1)
        for mark in range(3):
            gx = 5 + (row * 11 + mark * 13) % max(1, size - 10)
            gy = y + 4 + (mark * 3) % max(1, board_h - 4)
            if gx + 3 < size and gy < size:
                pygame.draw.line(surf, board_dark, (gx, gy), (gx + 3, gy), 1)
        for nail_x in (4, size - 5):
            if y + board_h // 2 < size:
                pygame.draw.rect(surf, (225, 188, 120), (nail_x, y + board_h // 2, 2, 2))
    pygame.draw.rect(surf, (73, 46, 30), (0, 0, size, size), 1)
    pygame.draw.line(surf, (222, 177, 103), (1, 1), (size - 2, 1), 1)
    return surf


def create_workbench_texture(size):
    surf = pygame.Surface((size, size)).convert_alpha()
    side_light = (173, 119, 61)
    side_mid = (126, 76, 39)
    side_dark = (68, 43, 30)
    top = (130, 63, 34)
    top_light = (219, 139, 62)
    metal = (190, 190, 176)
    top_h = max(12, size // 3)
    surf.fill(side_mid)

    pygame.draw.rect(surf, side_dark, (0, top_h, size, size - top_h))
    for y in range(top_h + 2, size, max(6, size // 5)):
        pygame.draw.rect(surf, side_light, (1, y, size - 2, max(2, size // 8)))
        pygame.draw.line(surf, side_dark, (1, y + max(2, size // 8)), (size - 2, y + max(2, size // 8)), 1)
    for x in (size // 4, size // 2, size * 3 // 4):
        pygame.draw.line(surf, side_mid, (x, top_h + 1), (x, size - 2), 2)
    for x, y in ((4, size // 2), (size - 8, size * 3 // 4)):
        if x >= 0 and y < size - 3:
            pygame.draw.rect(surf, metal, (x, y, 4, 3))
            pygame.draw.rect(surf, (105, 111, 112), (x + 1, y + 1, 2, 1))

    pygame.draw.rect(surf, side_dark, (0, 0, size, top_h))
    pygame.draw.rect(surf, top, (2, 2, size - 4, top_h - 3))
    tile = max(6, size // 5)
    for row in range(2):
        for column in range(3):
            cell = pygame.Rect(4 + column * tile, 4 + row * max(5, (top_h - 7) // 2),
                               max(2, tile - 2), max(2, (top_h - 8) // 2))
            if cell.right < size - 1 and cell.bottom < top_h:
                color = top_light if (row + column) % 2 == 0 else (164, 87, 45)
                pygame.draw.rect(surf, color, cell)
                pygame.draw.rect(surf, (94, 47, 33), cell, 1)
    pygame.draw.line(surf, (241, 176, 89), (2, 1), (size - 3, 1), 1)
    pygame.draw.line(surf, (53, 37, 29), (0, top_h), (size - 1, top_h), 2)
    return surf


def create_sticks_texture(size):
    surf = pygame.Surface((size, size)).convert_alpha()
    surf.fill((128, 83, 39))
    for start, end in (((7, size - 7), (size - 5, 7)), ((15, size - 4), (size - 2, 17))):
        pygame.draw.line(surf, (220, 169, 86), start, end, 3)
        pygame.draw.line(surf, (82, 48, 23), (start[0] + 2, start[1]), (end[0] + 2, end[1]), 1)
    return surf


def create_lucy_armor_texture(size, armor_type):
    """Create a small icon for one piece of Lucy's armor."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    fur = (145, 132, 116)
    light_fur = (190, 177, 157)
    dark_fur = (62, 56, 52)
    ear_pink = (174, 112, 112)
    if armor_type == "helm":
        pygame.draw.polygon(surf, dark_fur, ((4, 12), (7, 2), (14, 8), (18, 8), (25, 2), (28, 12), (26, 25), (6, 25)))
        pygame.draw.polygon(surf, fur, ((7, 11), (9, 5), (14, 11)))
        pygame.draw.polygon(surf, fur, ((18, 11), (23, 5), (25, 11)))
        pygame.draw.polygon(surf, ear_pink, ((9, 7), (10, 5), (13, 10)))
        pygame.draw.polygon(surf, ear_pink, ((19, 10), (22, 5), (23, 8)))
        pygame.draw.ellipse(surf, light_fur, (7, 10, 20, 16))
        pygame.draw.circle(surf, dark_fur, (12, 17), 2)
        pygame.draw.circle(surf, dark_fur, (21, 17), 2)
        pygame.draw.polygon(surf, ear_pink, ((14, 21), (16, 19), (18, 21), (16, 23)))
    elif armor_type == "ruestung":
        pygame.draw.polygon(surf, dark_fur, ((6, 6), (13, 4), (19, 4), (26, 6), (29, 28), (3, 28)))
        pygame.draw.rect(surf, fur, (7, 8, 18, 18), border_radius=4)
        pygame.draw.polygon(surf, light_fur, ((8, 10), (16, 7), (24, 10), (22, 22), (10, 22)))
        for stripe_x in (11, 16, 21):
            pygame.draw.line(surf, dark_fur, (stripe_x, 8), (stripe_x - 2, 14), 2)
        pygame.draw.circle(surf, dark_fur, (12, 19), 2)
        pygame.draw.circle(surf, dark_fur, (20, 19), 2)
    elif armor_type == "hose":
        pygame.draw.polygon(surf, dark_fur, ((7, 5), (25, 5), (23, 28), (17, 28), (16, 16), (14, 28), (8, 28)))
        pygame.draw.polygon(surf, fur, ((10, 7), (22, 7), (20, 25), (17, 25), (16, 13), (13, 25), (11, 25)))
        pygame.draw.line(surf, dark_fur, (11, 11), (21, 11), 2)
        pygame.draw.line(surf, dark_fur, (10, 16), (20, 16), 2)
    else:
        pygame.draw.rect(surf, dark_fur, (5, 13, 11, 15), border_radius=4)
        pygame.draw.rect(surf, dark_fur, (18, 13, 11, 15), border_radius=4)
        pygame.draw.rect(surf, fur, (7, 14, 7, 10), border_radius=3)
        pygame.draw.rect(surf, fur, (20, 14, 7, 10), border_radius=3)
        pygame.draw.circle(surf, light_fur, (10, 22), 2)
        pygame.draw.circle(surf, light_fur, (24, 22), 2)
    return surf


def create_death_fist_texture(size):
    """Create the icon for the one-hit Death Fist weapon."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    dark = (35, 20, 30)
    red = (190, 35, 45)
    bright = (255, 110, 70)
    pygame.draw.circle(surf, dark, (size // 2, size // 2), size // 3)
    pygame.draw.polygon(surf, red, ((8, 25), (10, 10), (15, 7), (17, 18),
                                    (21, 7), (25, 10), (24, 25)))
    pygame.draw.rect(surf, red, (10, 19, 15, 10), border_radius=4)
    pygame.draw.line(surf, bright, (12, 21), (23, 21), 2)
    pygame.draw.circle(surf, bright, (16, 14), 2)
    pygame.draw.circle(surf, bright, (21, 14), 2)
    return surf


def create_leaves_texture(size):
    surf = pygame.Surface((size, size)).convert_alpha()
    leaf_dark = (28, 91, 48)
    leaf_mid = (43, 139, 58)
    leaf_light = (92, 188, 69)
    leaf_glint = (151, 216, 83)
    surf.fill(leaf_dark)
    for y in range(2, size, 6):
        for x in range((y // 6 % 2) * 3, size, 7):
            pygame.draw.rect(surf, leaf_mid, (x, y, 5, 4))
            pygame.draw.rect(surf, leaf_light, (x + 1, y, 2, 2))
            if (x + y) % 3 == 0:
                pygame.draw.rect(surf, leaf_dark, (x + 4, y + 3, 2, 2))
    for i in range(14):
        x = (i * 13 + 5) % max(1, size - 3)
        y = (i * 9 + 3) % max(1, size - 3)
        pygame.draw.rect(surf, leaf_glint if i % 4 == 0 else leaf_light, (x, y, 2, 2))
    pygame.draw.rect(surf, (22, 75, 42), (0, 0, size, size), 1)
    return surf


def load_textures():
    base_dir = os.path.join(os.path.dirname(__file__), 'textures')
    if os.path.isdir(base_dir):
        for name in ['gras', 'erde']:
            for ext in ('png', 'jpg'):
                path = os.path.join(base_dir, f"{name}.{ext}")
                if os.path.exists(path):
                    try:
                        img = pygame.image.load(path).convert_alpha()
                        textures[name] = img
                        print(f'Loaded texture: {path}')
                        break
                    except Exception:
                        continue
    # Generate defaults if not loaded.
    if 'gras' not in textures:
        textures['gras'] = create_grass_texture(BLOCK)
    if 'erde' not in textures:
        textures['erde'] = create_dirt_texture(BLOCK)
    if 'holz' not in textures:
        textures['holz'] = create_wood_texture(BLOCK)
    if 'bretter' not in textures:
        textures['bretter'] = create_plank_texture(BLOCK)
    if 'werkbank' not in textures:
        textures['werkbank'] = create_workbench_texture(BLOCK)
    if 'stoecke' not in textures:
        textures['stoecke'] = create_sticks_texture(BLOCK)
    if 'blaetter' not in textures:
        textures['blaetter'] = create_leaves_texture(BLOCK)
    textures['lucy_helm'] = create_lucy_armor_texture(BLOCK, "helm")
    textures['lucy_ruestung'] = create_lucy_armor_texture(BLOCK, "ruestung")
    textures['lucy_hose'] = create_lucy_armor_texture(BLOCK, "hose")
    textures['lucy_stiefel'] = create_lucy_armor_texture(BLOCK, "stiefel")
    textures['faust_des_todes'] = create_death_fist_texture(BLOCK)


load_textures()


def respawn():
    global health, hunger, hunger_timer, velocity_y, on_ground, game_over, damage_sound_cooldown, death_sound_played
    health = MAX_HEALTH
    hunger = MAX_HUNGER
    hunger_timer = 0
    velocity_y = 0
    on_ground = False
    game_over = False
    damage_sound_cooldown = 0
    death_sound_played = False
    spieler.topleft = (200, 250)


def play_sound_effect(sound_obj):
    if not sound_enabled or not sound_obj:
        return
    try:
        sound_obj.play()
    except pygame.error:
        pass


def play_damage_sound():
    global damage_sound_cooldown
    if not sound_enabled or not damage_sound or damage_sound_cooldown > 0:
        return
    play_sound_effect(damage_sound)
    damage_sound_cooldown = 500


def play_death_sound_once():
    global death_sound_played
    if death_sound_played:
        return
    if sound_enabled and death_sound:
        death_sound_played = True
        play_sound_effect(death_sound)

# Hotbar / Inventar
HOTBAR_SIZE = 9
hotbar_items = ["leer"] * HOTBAR_SIZE
hotbar_counts = [0] * HOTBAR_SIZE
armor_items = ["leer", "leer", "leer", "leer"]
lucy_armor_equipped = False
creative_mode = False
craft_materials = {"holz": 0, "bretter": 0}
craft_grid = ["leer"] * 9
selected_slot = 0


def fill_creative_inventory():
    """Give the player an endless free-build inventory while Lucy armor is equipped."""
    global creative_mode, hotbar_items, hotbar_counts, selected_slot
    creative_mode = True
    hotbar_items = ["gras", "erde", "holz", "bretter", "werkbank", "blaetter", "stoecke", "faust_des_todes", "leer"]
    hotbar_counts = [99, 99, 99, 99, 99, 99, 99, 1, 0]
    selected_slot = 0


def equip_lucy_armor():
    """Equip Lucy's complete armor set once."""
    global lucy_armor_equipped
    if not lucy_armor_equipped:
        armor_items[:] = ["lucy_helm", "lucy_ruestung", "lucy_hose", "lucy_stiefel"]
        lucy_armor_equipped = True
        fill_creative_inventory()


def has_lucy_armor():
    """Return True when the Lucy armor set is equipped."""
    return "armor_items" in globals() and any(item.startswith("lucy_") for item in armor_items if item != "leer")


def give_death_fist():
    """Put the one-hit Death Fist in the player's inventory once."""
    global selected_slot
    if "faust_des_todes" not in hotbar_items:
        add_item_to_inventory("faust_des_todes")
    if "faust_des_todes" in hotbar_items:
        selected_slot = hotbar_items.index("faust_des_todes")

game_over = False
inventory_open = False
werkbank_open = False
pause_menu_open = False
status_message = ""
status_timer = 0
if ANDROID_MODE:
    SAVE_DIR = os.environ.get("ANDROID_PRIVATE") or os.path.expanduser("~")
else:
    SAVE_DIR = os.path.dirname(__file__)
SAVE_FILE = os.path.join(SAVE_DIR, "savegame.json")


def show_status(message, duration_ms=1200):
    global status_message, status_timer
    status_message = message
    status_timer = duration_ms


def draw_animal(surface, animal, offset_x=0, offset_y=0):
    animal_x = int(animal["x"] * BLOCK) - offset_x
    animal_y = int(animal["y"] * BLOCK) - offset_y
    animal_type = animal["type"]
    if animal_type == "huhn":
        pygame.draw.ellipse(surface, (255, 220, 130), (animal_x, animal_y, 18, 12))
        pygame.draw.circle(surface, (255, 220, 130), (animal_x + 14, animal_y - 4), 6)
        pygame.draw.polygon(surface, (255, 150, 0), [(animal_x + 18, animal_y - 3), (animal_x + 28, animal_y + 1), (animal_x + 18, animal_y + 5)])
        pygame.draw.line(surface, (255, 150, 0), (animal_x + 6, animal_y + 12), (animal_x + 6, animal_y + 18), 2)
        pygame.draw.line(surface, (255, 150, 0), (animal_x + 12, animal_y + 12), (animal_x + 12, animal_y + 18), 2)
    elif animal_type == "schaf":
        pygame.draw.ellipse(surface, (245, 245, 245), (animal_x, animal_y, 22, 16))
        pygame.draw.circle(surface, (245, 245, 245), (animal_x + 4, animal_y - 5), 6)
        pygame.draw.circle(surface, (30, 30, 30), (animal_x + 3, animal_y - 6), 2)
        pygame.draw.circle(surface, (30, 30, 30), (animal_x + 8, animal_y - 6), 2)
    elif animal_type == "kuh":
        pygame.draw.ellipse(surface, (240, 240, 240), (animal_x, animal_y, 28, 18))
        pygame.draw.ellipse(surface, (240, 240, 240), (animal_x + 16, animal_y - 5, 12, 12))
        pygame.draw.circle(surface, (30, 30, 30), (animal_x + 8, animal_y - 2), 2)
        pygame.draw.circle(surface, (30, 30, 30), (animal_x + 20, animal_y - 2), 2)
        pygame.draw.line(surface, (30, 30, 30), (animal_x + 8, animal_y + 18), (animal_x + 8, animal_y + 24), 2)
        pygame.draw.line(surface, (30, 30, 30), (animal_x + 18, animal_y + 18), (animal_x + 18, animal_y + 24), 2)


def spawn_nature_patch(center_x, center_y):
    kind = random.choice(["wald", "wiese", "dorf"])
    radius = random.randint(2, 4)
    if kind == "wald":
        for y in range(center_y - radius, center_y + radius + 1):
            for x in range(center_x - radius, center_x + radius + 1):
                if abs(x - center_x) + abs(y - center_y) <= radius + 1:
                    if 0 <= y < len(welt) and 0 <= x < len(welt[0]) and welt[y][x] == "luft":
                        welt[y][x] = "gras"
        for _ in range(6):
            tree_x = random.randint(center_x - radius, center_x + radius)
            tree_y = random.randint(center_y - radius, center_y + radius)
            if 0 <= tree_y < len(welt) and 0 <= tree_x < len(welt[0]):
                for trunk_y in range(tree_y - 3, tree_y):
                    if 0 <= trunk_y < len(welt):
                        welt[trunk_y][tree_x] = "holz"
                for leaf_y in (tree_y - 4, tree_y - 5):
                    for leaf_x in range(tree_x - 1, tree_x + 2):
                        if 0 <= leaf_y < len(welt) and 0 <= leaf_x < len(welt[0]) and welt[leaf_y][leaf_x] == "luft":
                            welt[leaf_y][leaf_x] = "blaetter"
                if 0 <= tree_y - 6 < len(welt):
                    welt[tree_y - 6][tree_x] = "blaetter"
        for _ in range(3):
            animal_x = random.randint(center_x - radius, center_x + radius)
            animal_y = random.randint(center_y - radius, center_y + radius)
            if 0 <= animal_y < len(welt) and 0 <= animal_x < len(welt[0]):
                animals.append({"type": random.choice(["huhn", "schaf"]), "x": animal_x + 0.5, "y": animal_y - 0.5})
        show_status("Wald entstanden")

    elif kind == "wiese":
        for y in range(center_y - radius, center_y + radius + 1):
            for x in range(center_x - radius, center_x + radius + 1):
                if abs(x - center_x) + abs(y - center_y) <= radius + 2:
                    if 0 <= y < len(welt) and 0 <= x < len(welt[0]) and welt[y][x] == "luft":
                        welt[y][x] = "gras"
        for _ in range(5):
            animal_x = random.randint(center_x - radius, center_x + radius)
            animal_y = random.randint(center_y - radius, center_y + radius)
            if 0 <= animal_y < len(welt) and 0 <= animal_x < len(welt[0]):
                animals.append({"type": random.choice(["huhn", "kuh", "schaf"]), "x": animal_x + 0.5, "y": animal_y - 0.5})
        show_status("Wiese mit Tieren")

    else:
        for y in range(center_y - radius, center_y + radius + 1):
            for x in range(center_x - radius, center_x + radius + 1):
                if abs(x - center_x) + abs(y - center_y) <= radius + 1:
                    if 0 <= y < len(welt) and 0 <= x < len(welt[0]) and welt[y][x] == "luft":
                        welt[y][x] = "gras"
        for house_x in range(center_x - 2, center_x + 3):
            for house_y in (center_y - 1, center_y):
                if 0 <= house_x < len(welt[0]) and 0 <= house_y < len(welt):
                    is_corner_post = house_x in (center_x - 2, center_x + 2)
                    welt[house_y][house_x] = "holz" if is_corner_post else "bretter"
        if 0 <= center_y - 2 < len(welt):
            welt[center_y - 2][center_x] = "werkbank"
        for _ in range(2):
            animal_x = random.randint(center_x - radius, center_x + radius)
            animal_y = random.randint(center_y - radius, center_y + radius)
            if 0 <= animal_y < len(welt) and 0 <= animal_x < len(welt[0]):
                animals.append({"type": random.choice(["huhn", "schaf"]), "x": animal_x + 0.5, "y": animal_y - 0.5})
        show_status("Dorf entstanden")

    return kind


def save_game_state():
    global welt, hotbar_items, hotbar_counts, armor_items, lucy_armor_equipped, craft_materials, craft_grid, selected_slot, health, hunger, spieler, game_over, animals
    data = {
        "welt": welt,
        "animals": animals,
        "player": {
            "x": int(spieler.x),
            "y": int(spieler.y),
            "health": health,
            "hunger": hunger,
            "selected_slot": selected_slot,
        },
        "hotbar_items": hotbar_items,
        "hotbar_counts": hotbar_counts,
        "armor_items": armor_items,
        "lucy_armor_equipped": lucy_armor_equipped,
        "creative_mode": creative_mode,
        "craft_materials": craft_materials,
        "craft_grid": craft_grid,
        "game_over": game_over,
        "inventory_open": inventory_open,
        "werkbank_open": werkbank_open,
    }
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as save_file:
            json.dump(data, save_file)
        show_status("Spiel gespeichert")
        return True
    except (OSError, TypeError, ValueError):
        show_status("Speichern fehlgeschlagen")
        return False


def load_game_state():
    global welt, hotbar_items, hotbar_counts, armor_items, lucy_armor_equipped, craft_materials, craft_grid, selected_slot, health, hunger, spieler, game_over, inventory_open, werkbank_open, animals, creative_mode
    if not os.path.exists(SAVE_FILE):
        show_status("Kein Speicherstand gefunden")
        return False
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as save_file:
            data = json.load(save_file)
    except (OSError, ValueError, json.JSONDecodeError):
        show_status("Laden fehlgeschlagen")
        return False

    if not isinstance(data, dict):
        show_status("Speicherstand ungültig")
        return False

    world_data = data.get("welt")
    if isinstance(world_data, list) and world_data:
        welt = [list(row) for row in world_data]

    animals_data = data.get("animals", [])
    if isinstance(animals_data, list):
        animals = list(animals_data)

    player_data = data.get("player", {})
    if isinstance(player_data, dict):
        spieler.x = float(player_data.get("x", spieler.x))
        spieler.y = float(player_data.get("y", spieler.y))
        health = int(player_data.get("health", health))
        hunger = int(player_data.get("hunger", hunger))
        selected_slot = int(player_data.get("selected_slot", selected_slot))

    hotbar_items = list(data.get("hotbar_items", hotbar_items))
    hotbar_counts = list(data.get("hotbar_counts", hotbar_counts))
    armor_items = list(data.get("armor_items", armor_items))
    lucy_armor_equipped = bool(data.get("lucy_armor_equipped", lucy_armor_equipped))
    creative_mode = bool(data.get("creative_mode", creative_mode))
    if lucy_armor_equipped and creative_mode:
        fill_creative_inventory()
    craft_materials = dict(data.get("craft_materials", craft_materials))
    craft_grid = list(data.get("craft_grid", craft_grid))
    inventory_open = bool(data.get("inventory_open", inventory_open))
    werkbank_open = bool(data.get("werkbank_open", werkbank_open))
    game_over = bool(data.get("game_over", game_over))

    health = max(0, min(MAX_HEALTH, health))
    hunger = max(0, min(MAX_HUNGER, hunger))
    selected_slot = max(0, min(HOTBAR_SIZE - 1, selected_slot))
    show_status("Spiel geladen")
    return True

def generate_chunk(start_x, width):
    chunk = []
    for y in range(WORLD_HEIGHT):
        zeile = []
        for x in range(width):
            world_x = start_x + x
            if y == 8:
                zeile.append("gras")
            elif y > 8:
                zeile.append("erde")
            else:
                zeile.append("luft")
        chunk.append(zeile)

    def add_tree(tree_x, ground_y):
        tree_x = max(0, min(tree_x, width - 1))
        for trunk_y in range(ground_y - 4, ground_y):
            if 0 <= trunk_y < WORLD_HEIGHT:
                chunk[trunk_y][tree_x] = "holz"
        for leaf_y in (ground_y - 5, ground_y - 6):
            for leaf_x in range(tree_x - 1, tree_x + 2):
                if 0 <= leaf_y < WORLD_HEIGHT and 0 <= leaf_x < width and chunk[leaf_y][leaf_x] == "luft":
                    chunk[leaf_y][leaf_x] = "blaetter"
        if 0 <= ground_y - 7 < WORLD_HEIGHT:
            chunk[ground_y - 7][tree_x] = "blaetter"

    for tree_x in (4, 12, 18, 24):
        add_tree(tree_x, 8)

    return chunk


def auto_spawn_village(world_data, center_x, center_y=8, radius=6):
    """Build a small village with a few houses, a path and animal spawns."""
    if not world_data or not world_data[0]:
        return

    for y in range(max(0, center_y - radius), min(len(world_data), center_y + radius + 1)):
        for x in range(max(0, center_x - radius), min(len(world_data[0]), center_x + radius + 1)):
            dx = abs(x - center_x)
            dy = abs(y - center_y)
            if dx + dy <= radius + 1 and world_data[y][x] == "luft":
                world_data[y][x] = "gras"

    def place_house(hx, hy):
        width = 4
        height = 4
        for y in range(hy - 1, hy + height - 1):
            for x in range(hx - 1, hx + width + 1):
                if 0 <= y < len(world_data) and 0 <= x < len(world_data[0]):
                    if y == hy - 1 or y == hy + height - 2 or x == hx - 1 or x == hx + width:
                        world_data[y][x] = "holz"
                    elif world_data[y][x] == "luft":
                        world_data[y][x] = "gras"

        for x in range(hx, hx + width):
            if 0 <= x < len(world_data[0]):
                world_data[hy + height - 2][x] = "holz"

        if 0 <= hy - 2 < len(world_data) and 0 <= hx + 1 < len(world_data[0]):
            world_data[hy - 2][hx + 1] = "werkbank"

        door_x = hx + 1
        if 0 <= hy + 1 < len(world_data) and 0 <= door_x < len(world_data[0]):
            world_data[hy + 1][door_x] = "luft"

    path_xs = list(range(center_x - radius, center_x + radius + 1, 2))
    for px in path_xs:
        if 0 <= px < len(world_data[0]):
            for y in range(center_y - 1, center_y + 2):
                if 0 <= y < len(world_data):
                    world_data[y][px] = "gras"

    for hx in (center_x - 5, center_x - 1, center_x + 4):
        if 0 <= hx < len(world_data[0]):
            place_house(hx, center_y - 1)

    if 0 <= center_x + 1 < len(world_data[0]):
        world_data[center_y + 1][center_x + 1] = "werkbank"

    if 0 <= center_y + 3 < len(world_data):
        for x in range(center_x - 2, center_x + 3):
            if 0 <= x < len(world_data[0]):
                world_data[center_y + 3][x] = "gras"
        world_data[center_y + 3][center_x] = "werkbank"

    for _ in range(4):
        animal_x = random.randint(center_x - radius, center_x + radius)
        animal_y = random.randint(center_y - radius, center_y + radius)
        if 0 <= animal_y < len(world_data) and 0 <= animal_x < len(world_data[0]):
            if world_data[animal_y][animal_x] == "gras":
                animals.append({"type": random.choice(["huhn", "schaf", "kuh"]), "x": animal_x + 0.5, "y": animal_y - 0.5})

    show_status("Dorf entstanden")


def spawn_animals_on_grass(world_data, start_x, width):
    global animals
    if not isinstance(animals, list):
        animals = []

    count = random.randint(2, 5)
    for _ in range(count):
        attempts = 0
        while attempts < 30:
            x = random.randint(start_x, start_x + width - 1)
            y = random.randint(7, 9)
            if 0 <= y < len(world_data) and 0 <= x < len(world_data[0]) and world_data[y][x] == "gras":
                animals.append({"type": random.choice(["huhn", "schaf", "kuh"]), "x": x + 0.5, "y": y - 0.5})
                break
            attempts += 1


def generate_world():
    global animals, welt
    world = []
    chunk = generate_chunk(0, WORLD_WIDTH)
    for row in chunk:
        world.append(row[:])
    animals = []

    for _ in range(random.randint(1, 3)):
        auto_spawn_village(world, random.randint(14, WORLD_WIDTH - 18), 8, radius=random.randint(5, 7))

    spawn_animals_on_grass(world, 0, WORLD_WIDTH)
    welt = world
    return world


def append_world_chunk():
    global welt
    if not welt:
        welt = generate_world()
        return

    start_x = len(welt[0])
    chunk = generate_chunk(start_x, 25)
    for row_index in range(len(chunk)):
        welt[row_index].extend(chunk[row_index])

    if random.random() < 0.35:
        auto_spawn_village(welt, start_x + random.randint(6, 18), 8, radius=random.randint(4, 6))

    spawn_animals_on_grass(welt, start_x, 25)


def start_new_world():
    global welt
    welt = generate_world()
    for _ in range(24):
        spawn_particles(random.randint(120, BREITE - 120), random.randint(80, HOEHE - 120), 2, (255, 230, 150), 1.2)
    respawn()
    return welt


welt = generate_world()
animals = []

# Spieler
spieler = pygame.Rect(200, 250, 30, 40)
geschwindigkeit = 5
velocity_y = 0
GRAVITY = 0.5
MAX_FALL_SPEED = 10
FALL_DAMAGE_THRESHOLD = 9
on_ground = False

katze = pygame.Rect(320, 250, 30, 30)
katze_direction = 1
katze_speed = 2
katze_schnurren = False
katze_purr_timer = 0
katze_purr_playing = False

# Disable cat (set to True to enable)
SHOW_CAT = False

uhr = pygame.time.Clock()

dt = 0
camera_x = 0
camera_y = 0

show_title_screen()

# Hauptschleife
while True:
    dt = uhr.tick(60)

    respawn_rect = pygame.Rect(BREITE // 2 - 140, HOEHE // 2 + 40, 120, 40)
    quit_rect = pygame.Rect(BREITE // 2 + 20, HOEHE // 2 + 40, 120, 40)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if ANDROID_MODE and event.type == pygame.FINGERDOWN:
            pos = mobile_touch_pos(event)
            rects = mobile_button_rects()
            if rects["left"].collidepoint(pos):
                touch_left = True
                continue
            if rects["right"].collidepoint(pos):
                touch_right = True
                continue
            if rects["jump"].collidepoint(pos):
                touch_jump_pressed = True
                continue
            if rects["mode"].collidepoint(pos):
                touch_mode = "place" if touch_mode == "break" else "break"
                continue
            if rects["inventory"].collidepoint(pos):
                if not game_over and not pause_menu_open:
                    inventory_open = not inventory_open
                    werkbank_open = False
                continue
            if rects["pause"].collidepoint(pos):
                if not game_over:
                    pause_menu_open = not pause_menu_open
                continue
            event = pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                pos=pos,
                button=1 if touch_mode == "break" else 3
            )

        elif ANDROID_MODE and event.type == pygame.FINGERUP:
            pos = mobile_touch_pos(event)
            rects = mobile_button_rects()
            if rects["left"].collidepoint(pos):
                touch_left = False
            if rects["right"].collidepoint(pos):
                touch_right = False
            continue

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if not game_over:
                pause_menu_open = not pause_menu_open
                if pause_menu_open:
                    show_status("Pause")
            continue

        if pause_menu_open:
            if event.type == pygame.MOUSEBUTTONDOWN:
                save_rect = pygame.Rect(BREITE // 2 - 130, HOEHE // 2 - 40, 260, 52)
                quit_rect = pygame.Rect(BREITE // 2 - 130, HOEHE // 2 + 30, 260, 52)
                if save_rect.collidepoint(event.pos):
                    save_game_state()
                    pause_menu_open = False
                elif quit_rect.collidepoint(event.pos):
                    save_game_state()
                    pygame.quit()
                    sys.exit()
            continue

        if game_over:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if respawn_rect.collidepoint(event.pos):
                    respawn()
                elif quit_rect.collidepoint(event.pos):
                    pygame.quit()
                    sys.exit()
            continue

        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            equip_lucy_armor()
            give_death_fist()
            inventory_open = True
            werkbank_open = False
            continue

        if event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
            save_game_state()
            continue

        if event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
            load_game_state()
            continue

        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            inventory_open = not inventory_open
            werkbank_open = False
            continue

        if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            if can_craft_sticks():
                take_crafted_sticks()
                play_sound_effect(craft_sound)
            elif craft_materials["bretter"] >= 4:
                craft_materials["bretter"] -= 4
                add_item_to_inventory("werkbank")
                for index, item in enumerate(hotbar_items):
                    if item == "bretter" and hotbar_counts[index] >= 4:
                        hotbar_counts[index] -= 4
                        if hotbar_counts[index] == 0:
                            hotbar_items[index] = "leer"
                        break
                play_sound_effect(craft_sound)
            elif craft_materials["holz"] >= 1:
                craft_materials["holz"] -= 1
                craft_materials["bretter"] += 4
                add_item_to_inventory("bretter", 4)
                for index, item in enumerate(hotbar_items):
                    if item == "holz" and hotbar_counts[index] > 0:
                        hotbar_counts[index] -= 1
                        if hotbar_counts[index] == 0:
                            hotbar_items[index] = "leer"
                        break
                play_sound_effect(craft_sound)

        if inventory_open:
            if not werkbank_open and event.type == pygame.MOUSEBUTTONDOWN:
                panel_x = BREITE // 2 - 310
                panel_y = HOEHE // 2 - 250
                inventory_hotbar_y = panel_y + 420
                for index in range(HOTBAR_SIZE):
                    slot_rect = pygame.Rect(panel_x + 25 + index * 96,
                                            inventory_hotbar_y, 80, 80)
                    if slot_rect.collidepoint(event.pos) and event.button == 1:
                        selected_slot = index
                        break
                continue
            if werkbank_open and event.type == pygame.MOUSEBUTTONDOWN:
                grid_x = BREITE // 2 - 310 + 28
                grid_y = HOEHE // 2 - 210 + 60
                result_rect = pygame.Rect(BREITE // 2 - 310 + 315, HOEHE // 2 - 210 + 84, 58, 58)
                if event.button == 1 and result_rect.collidepoint(event.pos):
                    take_crafted_sticks()
                    continue
                grid_index = None
                for row in range(3):
                    for column in range(3):
                        slot_rect = pygame.Rect(grid_x + column * 54, grid_y + row * 54, 50, 50)
                        if slot_rect.collidepoint(event.pos):
                            grid_index = row * 3 + column
                if grid_index is not None:
                    if event.button == 1 and craft_grid[grid_index] != "leer":
                        item = craft_grid[grid_index]
                        add_item_to_inventory(item)
                        if item in craft_materials:
                            craft_materials[item] += 1
                        craft_grid[grid_index] = "leer"
                    elif event.button == 3 and craft_grid[grid_index] == "leer":
                        item = hotbar_items[selected_slot]
                        if item != "leer" and hotbar_counts[selected_slot] > 0:
                            craft_grid[grid_index] = item
                            hotbar_counts[selected_slot] -= 1
                            if item in craft_materials:
                                craft_materials[item] -= 1
                            if hotbar_counts[selected_slot] == 0:
                                hotbar_items[selected_slot] = "leer"
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
                if can_craft_sticks():
                    take_crafted_sticks()
                elif craft_materials["bretter"] >= 4:
                    craft_materials["bretter"] -= 4
                    add_item_to_inventory("werkbank")
                    for index, item in enumerate(hotbar_items):
                        if item == "bretter" and hotbar_counts[index] >= 4:
                            hotbar_counts[index] -= 4
                            if hotbar_counts[index] == 0:
                                hotbar_items[index] = "leer"
                            break
                elif craft_materials["holz"] >= 1:
                    craft_materials["holz"] -= 1
                    craft_materials["bretter"] += 4
                    add_item_to_inventory("bretter", 4)
                    for index, item in enumerate(hotbar_items):
                        if item == "holz" and hotbar_counts[index] > 0:
                            hotbar_counts[index] -= 1
                            if hotbar_counts[index] == 0:
                                hotbar_items[index] = "leer"
                            break
            continue

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            bx = (mx + camera_x) // BLOCK
            by = (my + camera_y) // BLOCK

            if 0 <= bx < len(welt[0]) and 0 <= by < len(welt):
                if event.button == 1:  # Linke Maustaste: Abbau
                    if welt[by][bx] != "luft":
                        broken_block = welt[by][bx]
                        welt[by][bx] = "luft"
                        if broken_block in ("gras", "erde"):
                            add_item_to_inventory("erde")
                        elif broken_block == "holz":
                            craft_materials["holz"] += 1
                            add_item_to_inventory("holz")
                        play_sound_effect(break_sound)
                elif event.button == 3:  # Rechte Maustaste: Platzieren oder Natur erzeugen
                    if welt[by][bx] == "werkbank":
                        inventory_open = True
                        werkbank_open = True
                    elif welt[by][bx] == "luft":
                        if creative_mode and hotbar_items[selected_slot] != "leer":
                            welt[by][bx] = hotbar_items[selected_slot]
                            play_sound_effect(place_sound)
                        elif hotbar_items[selected_slot] == "leer":
                            spawn_nature_patch(bx, by)
                        elif hotbar_items[selected_slot] != "faust_des_todes" and hotbar_counts[selected_slot] > 0:
                            welt[by][bx] = hotbar_items[selected_slot]
                            hotbar_counts[selected_slot] -= 1
                            if hotbar_counts[selected_slot] == 0:
                                hotbar_items[selected_slot] = "leer"
                            play_sound_effect(place_sound)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                selected_slot = 0
            elif event.key == pygame.K_2:
                selected_slot = 1
            elif event.key == pygame.K_3:
                selected_slot = 2
            elif event.key == pygame.K_4:
                selected_slot = 3
            elif event.key == pygame.K_5:
                selected_slot = 4
            elif event.key == pygame.K_6:
                selected_slot = 5
            elif event.key == pygame.K_7:
                selected_slot = 6
            elif event.key == pygame.K_8:
                selected_slot = 7
            elif event.key == pygame.K_9:
                selected_slot = 8

    # Bewegung
    tasten = pygame.key.get_pressed()
    lucy_active = has_lucy_armor()

    moving_x = False
    if tasten[pygame.K_a] or touch_left:
        spieler.x -= geschwindigkeit
        moving_x = True

    if tasten[pygame.K_d] or touch_right:
        spieler.x += geschwindigkeit
        moving_x = True

    while spieler.right > len(welt[0]) * BLOCK - 260:
        append_world_chunk()

    if lucy_active:
        wall_left = get_block_at_pixel(spieler.left - 2, spieler.centery) != "luft"
        wall_right = get_block_at_pixel(spieler.right + 2, spieler.centery) != "luft"
        climbing = (tasten[pygame.K_w] or tasten[pygame.K_UP]
                    or (tasten[pygame.K_LSHIFT] or tasten[pygame.K_RSHIFT])
                    and tasten[pygame.K_SPACE])
        if climbing and (wall_left or wall_right):
            spieler.y -= 4
            velocity_y = 0
            on_ground = False

    if run_sound:
        current_tile = get_block_at_pixel(spieler.centerx, spieler.bottom + 2)
        on_grass = current_tile == "gras"
        if moving_x and on_ground and on_grass and not run_sound_playing:
            try:
                run_sound.play(-1)
                run_sound_playing = True
            except pygame.error:
                run_sound_playing = False
        elif (not moving_x or not on_ground or not on_grass) and run_sound_playing:
            run_sound.stop()
            run_sound_playing = False

    if (tasten[pygame.K_SPACE] or touch_jump_pressed) and on_ground:
        jump_strength = -20 if lucy_active else -10
        velocity_y = jump_strength
        on_ground = False
        spawn_particles(spieler.centerx, spieler.bottom, 12, (255, 212, 110), 2.6)
        play_sound_effect(jump_sound)
    touch_jump_pressed = False

    # Schwerkraft
    velocity_y += GRAVITY
    if velocity_y > MAX_FALL_SPEED:
        velocity_y = MAX_FALL_SPEED

    spieler.y += int(velocity_y)

    # Kollision mit Gras und Erde
    check_y = spieler.bottom
    tile_y = check_y // BLOCK
    left_x = spieler.left
    right_x = spieler.right - 1

    if tile_y >= len(welt):
        if not lucy_active and not on_ground and velocity_y > FALL_DAMAGE_THRESHOLD:
            fall_speed = max(0, velocity_y)
            damage = max(0, int((fall_speed - FALL_DAMAGE_THRESHOLD) ** 1.35 / 2.5))
            if damage > 0:
                old_health = health
                health -= damage
                if health < 0:
                    health = 0
                if health < old_health:
                    play_damage_sound()

        spieler.bottom = len(welt) * BLOCK
        velocity_y = 0
        on_ground = True
    elif get_block_at_pixel(left_x, check_y) != "luft" or get_block_at_pixel(right_x, check_y) != "luft":
        if not lucy_active and not on_ground and velocity_y > FALL_DAMAGE_THRESHOLD:
            fall_speed = max(0, velocity_y)
            damage = max(0, int((fall_speed - FALL_DAMAGE_THRESHOLD) ** 1.35 / 2.5))
            if damage > 0:
                old_health = health
                health -= damage
                if health < 0:
                    health = 0
                if health < old_health:
                    play_damage_sound()

        spieler.bottom = tile_y * BLOCK
        velocity_y = 0
        on_ground = True
    else:
        on_ground = False

    # Katze (deaktiviert wenn SHOW_CAT == False)
    if SHOW_CAT:
        katze.x += katze_direction * katze_speed
        if katze.left < 100 or katze.right > BREITE - 100:
            katze_direction *= -1
            katze.x += katze_direction * katze_speed

        ground_y = get_ground_y_for_rect(katze)
        katze.bottom = ground_y
        katze_schnurren = True
        katze_purr_timer = (katze_purr_timer + dt) % 500

        if purr_sound:
            if katze_schnurren and not katze_purr_playing:
                try:
                    purr_sound.play(-1)
                    katze_purr_playing = True
                except pygame.error:
                    katze_purr_playing = False
            elif not katze_schnurren and katze_purr_playing:
                purr_sound.stop()
                katze_purr_playing = False

    if not game_over:
        damage_sound_cooldown = max(0, damage_sound_cooldown - dt)

        # Hunger aktualisieren
        hunger_timer += dt
        if hunger_timer >= HUNGER_VERLUST_MS:
            hunger_timer = 0
            hunger -= 1
            if hunger < 0:
                hunger = 0

        if hunger == 0:
            old_health = health
            health -= 1
            hunger = MAX_HUNGER
            if health < 0:
                health = 0
            if health < old_health:
                play_damage_sound()

        if health <= 0:
            health = 0
            game_over = True
            play_death_sound_once()

    camera_x = int(max(0, min(spieler.centerx - BREITE // 2, max(0, len(welt[0]) * BLOCK - BREITE))))
    camera_y = int(max(0, min(spieler.centery - HOEHE // 2, max(0, len(welt) * BLOCK - HOEHE))))

    update_particles(dt)

    # Hintergrund
    draw_background(screen)

    # Welt zeichnen
    for y in range(len(welt)):
        for x in range(len(welt[y])):
            block = welt[y][x]
            if block != "luft":
                draw_block(screen, x, y, block, offset_x=camera_x, offset_y=camera_y)

    draw_particles(screen, camera_x, camera_y)

    # Katze zeichnen (nur wenn aktiviert)
    if SHOW_CAT:
        cat_screen = pygame.Rect(katze.x - camera_x, katze.y - camera_y, katze.width, katze.height)
        draw_cat(screen, cat_screen, schnurren=katze_schnurren, purr_timer=katze_purr_timer)

    # Tiere zeichnen
    for animal in animals:
        draw_animal(screen, animal, offset_x=camera_x, offset_y=camera_y)

    # Spieler zeichnen
    player_screen = pygame.Rect(spieler.x - camera_x, spieler.y - camera_y, spieler.width, spieler.height)
    draw_player(screen, player_screen)

    draw_hud(screen)

    if inventory_open:
        draw_inventory(screen, show_workbench=werkbank_open)

    if pause_menu_open:
        overlay = pygame.Surface((BREITE, HOEHE))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        panel = pygame.Rect(BREITE // 2 - 170, HOEHE // 2 - 120, 340, 220)
        pygame.draw.rect(screen, (28, 28, 34), panel, border_radius=12)
        pygame.draw.rect(screen, (200, 200, 200), panel, 3, border_radius=12)

        pause_title = subtitle_font.render("PAUSE", True, WEISS)
        screen.blit(pause_title, pause_title.get_rect(center=(BREITE // 2, HOEHE // 2 - 72)))

        save_rect = pygame.Rect(BREITE // 2 - 130, HOEHE // 2 - 30, 260, 52)
        quit_rect = pygame.Rect(BREITE // 2 - 130, HOEHE // 2 + 40, 260, 52)
        pygame.draw.rect(screen, (50, 120, 70), save_rect, border_radius=8)
        pygame.draw.rect(screen, (190, 220, 150), save_rect, 3, border_radius=8)
        pygame.draw.rect(screen, (100, 60, 60), quit_rect, border_radius=8)
        pygame.draw.rect(screen, (220, 160, 160), quit_rect, 3, border_radius=8)

        save_text = subtitle_font.render("SPEICHERN", True, WEISS)
        quit_text = subtitle_font.render("BEENDEN", True, WEISS)
        screen.blit(save_text, save_text.get_rect(center=save_rect.center))
        screen.blit(quit_text, quit_text.get_rect(center=quit_rect.center))

    if status_timer > 0:
        status_timer -= dt
        if status_timer <= 0:
            status_message = ""
        else:
            status_text = font.render(status_message, True, WEISS)
            status_bg = pygame.Rect(BREITE // 2 - 120, 12, 240, 32)
            pygame.draw.rect(screen, (25, 25, 25, 180), status_bg, border_radius=8)
            screen.blit(status_text, status_text.get_rect(center=status_bg.center))

    if game_over:
        overlay = pygame.Surface((BREITE, HOEHE))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        text = font.render("Du bist gestorben", True, WEISS)
        text_rect = text.get_rect(center=(BREITE // 2, HOEHE // 2 - 20))
        screen.blit(text, text_rect)

        pygame.draw.rect(screen, (100, 100, 100), respawn_rect, border_radius=8)
        pygame.draw.rect(screen, (100, 100, 100), quit_rect, border_radius=8)

        respawn_text = font.render("Respawn", True, WEISS)
        quit_text = font.render("Schließen", True, WEISS)
        screen.blit(respawn_text, respawn_text.get_rect(center=respawn_rect.center))
        screen.blit(quit_text, quit_text.get_rect(center=quit_rect.center))

    draw_mobile_controls(screen)

    pygame.display.flip()
    