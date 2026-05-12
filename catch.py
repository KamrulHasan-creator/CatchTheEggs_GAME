import pygame
import random
import math
import json
import os

pygame.init()

# Constants
WIDTH = 800
HEIGHT = 700
FPS = 60

# Colors
BLACK = (10, 10, 20)
WHITE = (255, 255, 255)
YELLOW = (255, 220, 0)
GOLD = (255, 200, 0)
RED = (255, 50, 50)
GREEN = (100, 255, 100)
BLUE = (100, 180, 255)
PURPLE = (200, 100, 255)
DARK_GRAY = (40, 40, 50)
LIGHT_GRAY = (100, 100, 120)

# Sky colors
SKY_TOP = (10, 15, 60)        # Deep night blue at top
SKY_MID = (20, 40, 100)       # Mid sky
SKY_BOTTOM = (40, 80, 140)    # Horizon glow

# Basket settings
BASKET_Y = 600
BASKET_WIDTH = 120
BASKET_HEIGHT = 25
BASKET_SPEED = 8

# Egg settings
EGG_WIDTH = 35
EGG_HEIGHT = 45
INITIAL_EGG_SPEED = 4

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("🥚 Catch The Eggs - Professional Edition")
pygame.display.set_icon(pygame.Surface((32, 32)))

# Fonts
font_tiny = pygame.font.Font(None, 24)
font_small = pygame.font.Font(None, 36)
font_medium = pygame.font.Font(None, 50)
font_large = pygame.font.Font(None, 80)
font_huge = pygame.font.Font(None, 120)

# Game variables
basket_x = WIDTH // 2 - BASKET_WIDTH // 2
egg_x = random.randint(50, WIDTH - EGG_WIDTH - 50)
egg_y = 0
egg_speed = INITIAL_EGG_SPEED

score = 0
lives = 3
level = 1
combo = 0
max_combo = 0
high_score = 0

clock = pygame.time.Clock()
running = True
game_over = False

# Particle system
particles = []

# ── Sky system ────────────────────────────────────────────────────────────────

class Star:
    def __init__(self):
        self.reset(random.randint(0, HEIGHT))

    def reset(self, y=None):
        self.x = random.uniform(0, WIDTH)
        self.y = y if y is not None else random.uniform(0, HEIGHT)
        self.size = random.uniform(0.5, 2.5)
        self.brightness = random.randint(150, 255)
        self.twinkle_speed = random.uniform(0.02, 0.08)
        self.twinkle_offset = random.uniform(0, math.pi * 2)

    def update(self, t):
        # gentle twinkle
        self.current_brightness = self.brightness + int(
            40 * math.sin(t * self.twinkle_speed + self.twinkle_offset)
        )
        self.current_brightness = max(80, min(255, self.current_brightness))

    def draw(self, surface, t):
        self.update(t)
        b = self.current_brightness
        color = (b, b, min(255, b + 30))
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), max(1, int(self.size)))
        # soft glow for bigger stars
        if self.size > 1.8:
            glow_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
            glow_color = (b, b, min(255, b + 40), 60)
            pygame.draw.circle(glow_surf, glow_color, (5, 5), 5)
            surface.blit(glow_surf, (int(self.x) - 5, int(self.y) - 5))


class Cloud:
    def __init__(self):
        self.reset(random.randint(80, WIDTH + 200))

    def reset(self, x=None):
        self.x = x if x is not None else WIDTH + 200
        self.y = random.randint(80, 300)
        self.speed = random.uniform(0.15, 0.45)
        self.width = random.randint(80, 180)
        self.height = random.randint(25, 50)
        self.alpha = random.randint(18, 45)   # very subtle clouds

    def update(self):
        self.x -= self.speed
        if self.x < -self.width - 50:
            self.reset()

    def draw(self, surface):
        cloud_surf = pygame.Surface((self.width + 40, self.height + 30), pygame.SRCALPHA)
        # draw several overlapping ellipses for fluffy look
        cx, cy = self.width // 2 + 20, self.height // 2 + 15
        col = (180, 200, 240, self.alpha)
        for dx, dy, rw, rh in [
            (0,  0,   self.width,      self.height),
            (-self.width//4, -self.height//3, self.width//2, self.height),
            ( self.width//4, -self.height//3, self.width//2, self.height),
            (-self.width//3,  0,              self.width//2, self.height//2),
            ( self.width//3,  0,              self.width//2, self.height//2),
        ]:
            pygame.draw.ellipse(cloud_surf, col,
                                (cx + dx - rw // 2, cy + dy - rh // 2, rw, rh))
        surface.blit(cloud_surf, (int(self.x) - 20, int(self.y) - 15))


class ShootingStar:
    def __init__(self):
        self.active = False
        self.timer = random.randint(180, 480)   # wait before appearing

    def trigger(self):
        self.active = True
        self.x = random.randint(100, WIDTH - 100)
        self.y = random.randint(80, 250)
        self.length = random.randint(60, 140)
        self.angle = math.radians(random.uniform(20, 45))
        self.speed = random.uniform(6, 12)
        self.alpha = 255
        self.fade = random.randint(8, 15)

    def update(self):
        if not self.active:
            self.timer -= 1
            if self.timer <= 0:
                self.trigger()
            return
        self.x += self.speed * math.cos(self.angle)
        self.y += self.speed * math.sin(self.angle)
        self.alpha -= self.fade
        if self.alpha <= 0 or self.x > WIDTH + 50 or self.y > HEIGHT:
            self.active = False
            self.timer = random.randint(300, 600)

    def draw(self, surface):
        if not self.active:
            return
        tail_x = self.x - self.length * math.cos(self.angle)
        tail_y = self.y - self.length * math.sin(self.angle)
        a = max(0, min(255, self.alpha))
        # draw gradient tail
        steps = 10
        for i in range(steps):
            t = i / steps
            sx = int(tail_x + t * (self.x - tail_x))
            sy = int(tail_y + t * (self.y - tail_y))
            seg_alpha = int(a * t)
            color = (min(255, 200 + seg_alpha // 4), min(255, 220 + seg_alpha // 8), 255)
            pygame.draw.circle(surface, color, (sx, sy), max(1, int(2 * t)))


# Instantiate sky objects
stars = [Star() for _ in range(160)]
clouds = [Cloud() for _ in range(6)]
shooting_stars = [ShootingStar() for _ in range(3)]

sky_gradient = pygame.Surface((WIDTH, HEIGHT))

def build_sky_gradient():
    """Pre-render vertical sky gradient."""
    for y in range(HEIGHT):
        t = y / HEIGHT
        # interpolate SKY_TOP → SKY_MID → SKY_BOTTOM
        if t < 0.5:
            tt = t * 2
            r = int(SKY_TOP[0] + tt * (SKY_MID[0] - SKY_TOP[0]))
            g = int(SKY_TOP[1] + tt * (SKY_MID[1] - SKY_TOP[1]))
            b = int(SKY_TOP[2] + tt * (SKY_MID[2] - SKY_TOP[2]))
        else:
            tt = (t - 0.5) * 2
            r = int(SKY_MID[0] + tt * (SKY_BOTTOM[0] - SKY_MID[0]))
            g = int(SKY_MID[1] + tt * (SKY_BOTTOM[1] - SKY_MID[1]))
            b = int(SKY_MID[2] + tt * (SKY_BOTTOM[2] - SKY_MID[2]))
        pygame.draw.line(sky_gradient, (r, g, b), (0, y), (WIDTH, y))

build_sky_gradient()

tick_counter = 0   # used for twinkle timing

def draw_sky_background():
    """Draw animated sky: gradient + stars + clouds + shooting stars."""
    global tick_counter
    tick_counter += 1
    t = tick_counter

    # 1. gradient base
    screen.blit(sky_gradient, (0, 0))

    # 2. stars (only above HUD line, i.e. y > 60)
    for star in stars:
        star.draw(screen, t)

    # 3. shooting stars
    for ss in shooting_stars:
        ss.update()
        ss.draw(screen)

    # 4. clouds
    for cloud in clouds:
        cloud.update()
        cloud.draw(screen)

    # subtle horizon glow
    glow_surf = pygame.Surface((WIDTH, 80), pygame.SRCALPHA)
    for i in range(80):
        alpha = int((1 - i / 80) * 30)
        pygame.draw.line(glow_surf, (80, 140, 220, alpha), (0, i), (WIDTH, i))
    screen.blit(glow_surf, (0, HEIGHT - 80))

# ── (end sky system) ──────────────────────────────────────────────────────────

class Particle:
    def __init__(self, x, y, vx, vy, color, lifetime=30):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2  # gravity
        self.lifetime -= 1
        
    def draw(self, surface):
        alpha = int((self.lifetime / self.max_lifetime) * 255)
        size = max(2, int((self.lifetime / self.max_lifetime) * 8))
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), size)

def create_particles(x, y, color, count=15):
    """Create particle burst effect"""
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 8)
        vx = speed * math.cos(angle)
        vy = speed * math.sin(angle)
        particles.append(Particle(x, y, vx, vy, color, lifetime=40))

def load_high_score():
    """Load high score from file"""
    global high_score
    try:
        if os.path.exists("highscore.json"):
            with open("highscore.json", "r") as f:
                data = json.load(f)
                high_score = data.get("score", 0)
    except:
        high_score = 0

def save_high_score():
    """Save high score to file"""
    try:
        with open("highscore.json", "w") as f:
            json.dump({"score": high_score}, f)
    except:
        pass

def reset_egg():
    """Reset egg to top with random x position"""
    global egg_x, egg_y, egg_speed
    egg_x = random.randint(50, WIDTH - EGG_WIDTH - 50)
    egg_y = 0
    egg_speed = INITIAL_EGG_SPEED + (level - 1) * 1.2

def draw_game_over_screen(final_score, final_level, final_combo):
    """Draw the game over screen"""
    draw_sky_background()

    # dark overlay
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))
    
    # Game Over Text
    game_over_text = font_huge.render("GAME OVER", True, RED)
    game_over_rect = game_over_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150))
    screen.blit(game_over_text, game_over_rect)
    
    # Score display
    final_score_text = font_medium.render(f"Score: {final_score}", True, GOLD)
    final_score_rect = final_score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20))
    screen.blit(final_score_text, final_score_rect)
    
    # Level display
    final_level_text = font_medium.render(f"Level: {final_level}", True, GREEN)
    final_level_rect = final_level_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
    screen.blit(final_level_text, final_level_rect)
    
    # Combo display
    final_combo_text = font_medium.render(f"Max Combo: {final_combo}x", True, PURPLE)
    final_combo_rect = final_combo_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 120))
    screen.blit(final_combo_text, final_combo_rect)
    
    # High score display
    if final_score >= high_score:
        new_record_text = font_small.render("NEW RECORD!", True, GOLD)
        new_record_rect = new_record_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 180))
        screen.blit(new_record_text, new_record_rect)
    
    high_score_text = font_small.render(f"High Score: {high_score}", True, WHITE)
    high_score_rect = high_score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 240))
    screen.blit(high_score_text, high_score_rect)
    
    # Restart instructions
    restart_text = font_small.render("Press SPACE to restart or Q to quit", True, GREEN)
    restart_rect = restart_text.get_rect(center=(WIDTH // 2, HEIGHT - 80))
    screen.blit(restart_text, restart_rect)
    
    pygame.display.flip()

def draw_menu_screen():
    """Draw the start menu screen"""
    draw_sky_background()

    # semi-transparent panel
    panel = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    panel.fill((0, 0, 20, 120))
    screen.blit(panel, (0, 0))
    
    # Title
    title_text = font_huge.render("CATCH THE EGGS", True, GOLD)
    title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 200))
    screen.blit(title_text, title_rect)
    
    # Instructions
    inst1 = font_medium.render("Use LEFT / RIGHT Arrow Keys to move", True, WHITE)
    inst1_rect = inst1.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20))
    screen.blit(inst1, inst1_rect)
    
    inst2 = font_medium.render("Catch eggs before they hit the ground!", True, WHITE)
    inst2_rect = inst2.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
    screen.blit(inst2, inst2_rect)
    
    # High Score
    hs_text = font_small.render(f"High Score: {high_score}", True, GOLD)
    hs_rect = hs_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 150))
    screen.blit(hs_text, hs_rect)
    
    # Start button
    start_text = font_large.render("Press SPACE to START", True, GREEN)
    start_rect = start_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 280))
    pygame.draw.rect(screen, GREEN, start_rect.inflate(40, 40), 3)
    screen.blit(start_text, start_rect)
    
    pygame.display.flip()

def reset_game():
    """Reset all game variables"""
    global basket_x, egg_x, egg_y, score, lives, level, game_over, egg_speed, combo, particles
    basket_x = WIDTH // 2 - BASKET_WIDTH // 2
    egg_x = random.randint(50, WIDTH - EGG_WIDTH - 50)
    egg_y = 0
    score = 0
    lives = 3
    level = 1
    combo = 0
    game_over = False
    egg_speed = INITIAL_EGG_SPEED
    particles = []

def draw_basket(x, y):
    """Draw stylish basket"""
    pygame.draw.rect(screen, WHITE, (x, y, BASKET_WIDTH, BASKET_HEIGHT), 3)
    pygame.draw.rect(screen, BLUE, (x + 5, y + 5, BASKET_WIDTH - 10, BASKET_HEIGHT - 10))
    for i in range(0, BASKET_WIDTH, 15):
        pygame.draw.line(screen, YELLOW, (x + i, y), (x + i, y + BASKET_HEIGHT), 2)

def draw_egg(x, y, size_factor=1):
    """Draw stylish egg"""
    size_w = int(EGG_WIDTH * size_factor)
    size_h = int(EGG_HEIGHT * size_factor)
    pygame.draw.ellipse(screen, YELLOW, (x, y, size_w, size_h))
    pygame.draw.ellipse(screen, GOLD, (x, y, size_w, size_h), 3)
    pygame.draw.ellipse(screen, WHITE, (x + size_w // 4, y + size_h // 4, size_w // 3, size_h // 3))

def draw_hud():
    """Draw heads-up display"""
    pygame.draw.rect(screen, DARK_GRAY, (0, 0, WIDTH, 60), 1)
    pygame.draw.line(screen, LIGHT_GRAY, (0, 60), (WIDTH, 60), 1)
    
    score_text = font_small.render(f"Score: {score}", True, GOLD)
    screen.blit(score_text, (20, 15))
    
    if combo <= 0:
        level_text = font_small.render(f"Level: {level}", True, GREEN)
        screen.blit(level_text, (WIDTH // 2 - 50, 15))
    
    lives_text = font_small.render(f"Lives: {lives}", True, RED)
    screen.blit(lives_text, (WIDTH - 200, 15))
    
    if combo > 0:
        combo_text = font_small.render(f"Combo: {combo}x", True, PURPLE)
        screen.blit(combo_text, (WIDTH // 2 - 80, 15))

# Load high score
load_high_score()

# Game states
game_state = "menu"

# Main game loop
while running:
    clock.tick(FPS)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if game_state == "menu":
                    reset_game()
                    game_state = "playing"
                elif game_state == "game_over":
                    reset_game()
                    game_state = "playing"
            elif event.key == pygame.K_q and game_state == "game_over":
                running = False
    
    if game_state == "menu":
        draw_menu_screen()
    
    elif game_state == "playing":
        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_LEFT]:
            basket_x -= BASKET_SPEED
        if keys[pygame.K_RIGHT]:
            basket_x += BASKET_SPEED
        
        if basket_x < 0:
            basket_x = 0
        if basket_x > WIDTH - BASKET_WIDTH:
            basket_x = WIDTH - BASKET_WIDTH
        
        egg_y += egg_speed
        
        basket_rect = pygame.Rect(basket_x, BASKET_Y, BASKET_WIDTH, BASKET_HEIGHT)
        egg_rect = pygame.Rect(egg_x, egg_y, EGG_WIDTH, EGG_HEIGHT)
        
        if egg_rect.colliderect(basket_rect):
            score += 10 + (combo * 5)
            combo += 1
            max_combo = max(max_combo, combo)
            
            if score % 50 == 0 and score > 0:
                level += 1
            
            create_particles(egg_x + EGG_WIDTH // 2, egg_y + EGG_HEIGHT // 2, GOLD, 20)
            
            if score > high_score:
                high_score = score
                save_high_score()
            
            reset_egg()
        
        if egg_y > HEIGHT:
            lives -= 1
            combo = 0
            create_particles(egg_x + EGG_WIDTH // 2, HEIGHT, RED, 15)
            
            if lives <= 0:
                game_state = "game_over"
            else:
                reset_egg()
        
        for particle in particles[:]:
            particle.update()
            if particle.lifetime <= 0:
                particles.remove(particle)
        
        # ── Draw ──
        draw_sky_background()   # <-- sky replaces solid black fill

        # Draw HUD
        draw_hud()
        
        # Draw basket
        draw_basket(basket_x, BASKET_Y)
        
        # Draw egg
        draw_egg(egg_x, egg_y)
        
        # Draw particles
        for particle in particles:
            particle.draw(screen)
        
        if combo > 1:
            combo_display = font_medium.render(f"{combo}x COMBO!", True, PURPLE)
            combo_display_rect = combo_display.get_rect(center=(WIDTH // 2, 150))
            screen.blit(combo_display, combo_display_rect)
        
        pygame.display.flip()
    
    elif game_state == "game_over":
        draw_game_over_screen(score, level, max_combo)
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            max_combo = 0
            game_state = "menu"

pygame.quit()