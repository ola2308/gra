import pygame
import cv2
import mediapipe as mp
import threading
import time
import random
import sys
import math
from enum import Enum

pygame.init()

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
HOVER_TIME = 0.5
GLOW_DURATION = 1.0
GLOW_PAUSE = 0.3

class GameState(Enum):
    START = 1
    DIFFICULTY = 2
    EASY_GAME = 3
    END_SUCCESS = 4
    END_FAILURE = 5

class ElixirGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Gra Eliksirów")
        
        self.clock = pygame.time.Clock()
        self.state = GameState.START
        
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.cap = cv2.VideoCapture(0)
        
        self.finger_x = None
        self.finger_y = None
        self.finger_lock = threading.Lock()
        
        self.mouse_x = None
        self.mouse_y = None
        
        self.camera_thread = threading.Thread(target=self.camera_loop, daemon=True)
        self.camera_running = True
        self.camera_thread.start()
        
        self.hover_start_time = {}
        
        self.load_assets()
        
        self.recipes_easy = {
            "Eliksir Smoczej Łuski": ["pazur_smoka", "skrzydlo_feniksa", "kropla_eliksiru"],
            "Mikstura Gwiezdnej Iskry": ["swietlisty_krag", "kropla_eliksiru", "skrzydlo_feniksa"],
            "Wywar Feniksa": ["skrzydlo_feniksa", "pazur_smoka", "swietlisty_krag"],
            "Napój Syreniego Głosu": ["luska_syreny", "kropla_eliksiru", "swietlisty_krag"],
            "Esencja Gwiazdozbioru": ["gwiazda_centralna", "swietlisty_krag", "skrzydlo_feniksa"],
            "Eliksir Wiecznego Płomienia": ["pazur_smoka", "kropla_eliksiru", "gwiazda_centralna"],
            "Tonik Magicznego Światła": ["swietlisty_krag", "gwiazda_centralna", "luska_syreny"],
            "Mikstura Smokołuski": ["luska_syreny", "pazur_smoka", "skrzydlo_feniksa"],
            "Wywar Niebiańskiego Piórka": ["skrzydlo_feniksa", "gwiazda_centralna", "kropla_eliksiru"],
            "Eliksir Morskiej Gwiazdy": ["gwiazda_centralna", "luska_syreny", "pazur_smoka"]
        }
        
        self.recipes_hard = {
            "Potężny Eliksir Smoczej Łuski": ["pazur_smoka", "skrzydlo_feniksa", "kropla_eliksiru", "gwiazda_centralna", "luska_syreny", "swietlisty_krag"],
            "Arcymikstura Gwiezdnej Iskry": ["swietlisty_krag", "kropla_eliksiru", "skrzydlo_feniksa", "gwiazda_centralna", "luska_syreny", "pazur_smoka"],
            "Mistyczny Wywar Feniksa": ["skrzydlo_feniksa", "pazur_smoka", "swietlisty_krag", "kropla_eliksiru", "gwiazda_centralna", "luska_syreny"],
            "Pradawny Napój Syreniego Głosu": ["luska_syreny", "kropla_eliksiru", "swietlisty_krag", "pazur_smoka", "skrzydlo_feniksa", "gwiazda_centralna"],
            "Kosmiczna Esencja Gwiazdozbioru": ["gwiazda_centralna", "swietlisty_krag", "skrzydlo_feniksa", "kropla_eliksiru", "pazur_smoka", "luska_syreny"],
            "Wieczny Eliksir Płomienia": ["pazur_smoka", "kropla_eliksiru", "gwiazda_centralna", "skrzydlo_feniksa", "luska_syreny", "swietlisty_krag"],
            "Olśniewający Tonik Światła": ["swietlisty_krag", "gwiazda_centralna", "luska_syreny", "kropla_eliksiru", "skrzydlo_feniksa", "pazur_smoka"],
            "Legendarny Wywar Smokołuski": ["luska_syreny", "pazur_smoka", "skrzydlo_feniksa", "swietlisty_krag", "gwiazda_centralna", "kropla_eliksiru"],
            "Niebiański Nektar Piórka": ["skrzydlo_feniksa", "gwiazda_centralna", "kropla_eliksiru", "luska_syreny", "swietlisty_krag", "pazur_smoka"],
            "Transcendentny Eliksir Morza": ["gwiazda_centralna", "luska_syreny", "pazur_smoka", "swietlisty_krag", "kropla_eliksiru", "skrzydlo_feniksa"]
        }
        
        self.current_recipe = None
        self.current_recipe_name = None
        self.current_difficulty = None
        self.sequence_playing = False
        self.sequence_index = 0
        self.player_sequence = []
        self.glow_start_time = 0
        self.showing_error = False
        self.error_start_time = 0
        
        self.ingredient_positions = {
            "swietlisty_krag": (120, 550, 120, 120),
            "pazur_smoka": (230, 370, 120, 120),
            "skrzydlo_feniksa": (370, 200, 120, 120),
            "kropla_eliksiru": (650, 230, 120, 120),
            "gwiazda_centralna": (790, 320, 120, 120),
            "luska_syreny": (860, 550, 120, 120)
        }
        
        self.button_positions = {
            "start": (400, 500, 200, 80),
            "easy": (300, 400, 150, 60),
            "hard": (500, 400, 150, 60),
            "play_again_success": (362, 650, 300, 80),
            "play_again_failure": (362, 400, 300, 80)
        }

    def load_assets(self):
        try:
            self.backgrounds = {
                "start": pygame.image.load("tla/start.png"),
                "difficulty": pygame.image.load("tla/trudnosc.png"),
                "easy": pygame.image.load("tla/latwy.png"),
                "end": pygame.image.load("tla/koniec.png"),
                "failure": pygame.image.load("tla/zagraj_ponownie.png")
            }
            
            self.ingredients = {
                "swietlisty_krag": pygame.image.load("tla/swietlisty_krag.png"),
                "pazur_smoka": pygame.image.load("tla/pazur_smoka.png"),
                "luska_syreny": pygame.image.load("tla/luska_syreny.png"),
                "kropla_eliksiru": pygame.image.load("tla/kropla_eliksiru.png"),
                "skrzydlo_feniksa": pygame.image.load("tla/skrzydlo_feniksa.png"),
                "gwiazda_centralna": pygame.image.load("tla/gwiazda_centralna.png")
            }
            
            for key in self.ingredients:
                self.ingredients[key] = pygame.transform.scale(self.ingredients[key], (120, 120))
            
            self.play_again_button = pygame.image.load("tla/zagraj_ponownie.png")
            
            for key in self.backgrounds:
                self.backgrounds[key] = pygame.transform.scale(self.backgrounds[key], (SCREEN_WIDTH, SCREEN_HEIGHT))
            
            try:
                self.title_font = pygame.font.Font("arial.ttf", 36)
                self.error_font = pygame.font.Font("arial.ttf", 24)
            except:
                self.title_font = pygame.font.Font(None, 36)
                self.error_font = pygame.font.Font(None, 24)
                
        except Exception as e:
            print(f"Błąd ładowania zasobów: {e}")
            sys.exit(1)

    def camera_loop(self):
        while self.camera_running:
            ret, frame = self.cap.read()
            if not ret:
                continue
                
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            results = self.hands.process(rgb)
            
            with self.finger_lock:
                self.finger_x = None
                self.finger_y = None
                
                if results.multi_hand_landmarks and results.multi_handedness:
                    for landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                        if handedness.classification[0].label == 'Right':
                            point = landmarks.landmark[8]
                            self.finger_x = int(point.x * SCREEN_WIDTH)
                            self.finger_y = int(point.y * SCREEN_HEIGHT)
                            break
            
            time.sleep(1/30)

    def is_hovering(self, rect):
        check_x = None
        check_y = None
        
        with self.finger_lock:
            if self.finger_x is not None and self.finger_y is not None:
                check_x = self.finger_x
                check_y = self.finger_y
        
        if check_x is None and self.mouse_x is not None:
            check_x = self.mouse_x
            check_y = self.mouse_y
        
        if check_x is None or check_y is None:
            return False
            
        x, y, w, h = rect
        return x <= check_x <= x + w and y <= check_y <= y + h

    def get_hover_progress(self, button_id):
        if button_id not in self.hover_start_time:
            return 0.0
        
        current_time = time.time()
        elapsed = current_time - self.hover_start_time[button_id]
        return min(elapsed / HOVER_TIME, 1.0)

    def check_hover_click(self, button_id, rect):
        current_time = time.time()
        is_hover = self.is_hovering(rect)
        
        if is_hover:
            if button_id not in self.hover_start_time:
                self.hover_start_time[button_id] = current_time
            elif current_time - self.hover_start_time[button_id] >= HOVER_TIME:
                self.hover_start_time[button_id] = current_time + 1
                return True
        else:
            if button_id in self.hover_start_time:
                del self.hover_start_time[button_id]
        
        return False

    def draw_loading_circle(self, surface, center, progress, radius=50):
        cx, cy = center
        
        bg_surface = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
        pygame.draw.circle(bg_surface, (0, 0, 0, 120), (radius * 1.5, radius * 1.5), radius)
        surface.blit(bg_surface, (cx - radius * 1.5, cy - radius * 1.5))
        
        pygame.draw.circle(surface, (100, 255, 100), (cx, cy), radius, 3)
        
        if progress > 0:
            angle = int(progress * 360)
            points = [(cx, cy)]
            for i in range(angle + 1):
                rad = math.radians(i - 90)
                x = cx + int((radius - 5) * math.cos(rad))
                y = cy + int((radius - 5) * math.sin(rad))
                points.append((x, y))
            
            if len(points) > 2:
                glow_surface = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
                adjusted_points = [(p[0] - cx + radius * 1.5, p[1] - cy + radius * 1.5) for p in points]
                pygame.draw.polygon(glow_surface, (100, 255, 100, 180), adjusted_points)
                surface.blit(glow_surface, (cx - radius * 1.5, cy - radius * 1.5))
        
        if progress > 0:
            percent_text = f"{int(progress * 100)}%"
            font = pygame.font.Font(None, 32)
            text_surface = font.render(percent_text, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(cx, cy))
            surface.blit(text_surface, text_rect)

    def draw_glow_effect(self, surface, rect, intensity=1.0):
        x, y, w, h = rect
        center_x = x + w // 2
        center_y = y + h // 2
        
        for i in range(5, 0, -1):
            alpha = int(50 * intensity * (i / 5))
            radius = int((w // 2 + 20) * (1 + i * 0.15))
            
            glow_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            color = (255, 255, 150, alpha)
            pygame.draw.circle(glow_surface, color, (radius, radius), radius)
            
            surface.blit(glow_surface, (center_x - radius, center_y - radius))

    def start_new_game(self, difficulty="easy"):
        self.current_difficulty = difficulty
        if difficulty == "easy":
            self.current_recipe_name, self.current_recipe = random.choice(list(self.recipes_easy.items()))
        else:
            self.current_recipe_name, self.current_recipe = random.choice(list(self.recipes_hard.items()))
        
        self.sequence_playing = True
        self.sequence_index = 0
        self.player_sequence = []
        self.glow_start_time = time.time()
        self.showing_error = False

    def update_sequence(self):
        if not self.sequence_playing:
            return
            
        current_time = time.time()
        elapsed = current_time - self.glow_start_time
        
        if elapsed >= GLOW_DURATION + GLOW_PAUSE:
            self.sequence_index += 1
            if self.sequence_index >= len(self.current_recipe):
                self.sequence_playing = False
            else:
                self.glow_start_time = current_time

    def check_ingredient_clicks(self):
        if self.sequence_playing or self.showing_error:
            return
            
        for ingredient, rect in self.ingredient_positions.items():
            if self.check_hover_click(f"ingredient_{ingredient}", rect):
                self.player_sequence.append(ingredient)
                
                expected_index = len(self.player_sequence) - 1
                if expected_index < len(self.current_recipe):
                    if ingredient != self.current_recipe[expected_index]:
                        self.showing_error = True
                        self.error_start_time = time.time()
                        self.player_sequence = []
                        return
                
                if len(self.player_sequence) == len(self.current_recipe):
                    self.state = GameState.END_SUCCESS

    def draw_error_message(self):
        current_time = time.time()
        if current_time - self.error_start_time >= 2.0:
            self.showing_error = False
            self.sequence_playing = True
            self.sequence_index = 0
            self.glow_start_time = current_time
            return
        
        error_text = "Niestety nie udało się, spróbuj ponownie"
        text_surface = self.error_font.render(error_text, True, (255, 0, 0))
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(text_surface, text_rect)

    def draw_start_screen(self):
        self.screen.blit(self.backgrounds["start"], (0, 0))
        
        start_rect = self.button_positions["start"]
        if self.is_hovering(start_rect):
            self.draw_glow_effect(self.screen, start_rect, 0.8)
            
            progress = self.get_hover_progress("start")
            if progress > 0:
                x, y, w, h = start_rect
                center = (x + w // 2, y + h // 2)
                self.draw_loading_circle(self.screen, center, progress)
        
        if self.check_hover_click("start", start_rect):
            self.state = GameState.DIFFICULTY

    def draw_difficulty_screen(self):
        self.screen.blit(self.backgrounds["difficulty"], (0, 0))
        
        easy_rect = self.button_positions["easy"]
        if self.is_hovering(easy_rect):
            self.draw_glow_effect(self.screen, easy_rect, 0.8)
            
            progress = self.get_hover_progress("easy")
            if progress > 0:
                x, y, w, h = easy_rect
                center = (x + w // 2, y + h // 2)
                self.draw_loading_circle(self.screen, center, progress)
        
        hard_rect = self.button_positions["hard"]
        if self.is_hovering(hard_rect):
            self.draw_glow_effect(self.screen, hard_rect, 0.8)
            
            progress = self.get_hover_progress("hard")
            if progress > 0:
                x, y, w, h = hard_rect
                center = (x + w // 2, y + h // 2)
                self.draw_loading_circle(self.screen, center, progress)
        
        if self.check_hover_click("easy", easy_rect):
            self.state = GameState.EASY_GAME
            self.start_new_game("easy")
        
        if self.check_hover_click("hard", hard_rect):
            self.state = GameState.EASY_GAME
            self.start_new_game("hard")

    def draw_easy_game_screen(self):
        self.screen.blit(self.backgrounds["easy"], (0, 0))
        
        title_surface = self.title_font.render(self.current_recipe_name, True, (255, 255, 255))
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(title_surface, title_rect)
        
        for i, (ingredient, rect) in enumerate(self.ingredient_positions.items()):
            self.screen.blit(self.ingredients[ingredient], (rect[0], rect[1]))
            
            if (self.sequence_playing and 
                self.sequence_index < len(self.current_recipe) and
                ingredient == self.current_recipe[self.sequence_index]):
                
                current_time = time.time()
                elapsed = current_time - self.glow_start_time
                if elapsed <= GLOW_DURATION:
                    intensity = 1.0 - (elapsed / GLOW_DURATION * 0.5)
                    self.draw_glow_effect(self.screen, rect, intensity)
            
            elif not self.sequence_playing and not self.showing_error and self.is_hovering(rect):
                self.draw_glow_effect(self.screen, rect, 0.7)
                
                progress = self.get_hover_progress(f"ingredient_{ingredient}")
                if progress > 0:
                    x, y, w, h = rect
                    center = (x + w // 2, y + h // 2)
                    self.draw_loading_circle(self.screen, center, progress, radius=40)
        
        self.update_sequence()
        self.check_ingredient_clicks()
        
        if self.showing_error:
            self.draw_error_message()

    def draw_end_success_screen(self):
        self.screen.blit(self.backgrounds["end"], (0, 0))
        
        play_again_rect = self.button_positions["play_again_success"]
        
        if self.is_hovering(play_again_rect):
            self.draw_glow_effect(self.screen, play_again_rect, 0.8)
            
            progress = self.get_hover_progress("play_again_success")
            if progress > 0:
                x, y, w, h = play_again_rect
                center = (x + w // 2, y + h // 2)
                self.draw_loading_circle(self.screen, center, progress)
        
        try:
            self.screen.blit(self.play_again_button, (play_again_rect[0], play_again_rect[1]))
        except:
            pygame.draw.rect(self.screen, (100, 255, 100), play_again_rect)
            text = self.error_font.render("ZAGRAJ PONOWNIE", True, (255, 255, 255))
            text_rect = text.get_rect(center=(play_again_rect[0] + play_again_rect[2]//2, 
                                             play_again_rect[1] + play_again_rect[3]//2))
            self.screen.blit(text, text_rect)
        
        if self.check_hover_click("play_again_success", play_again_rect):
            self.state = GameState.DIFFICULTY

    def draw_end_failure_screen(self):
        self.screen.blit(self.backgrounds["failure"], (0, 0))
        
        play_again_rect = self.button_positions["play_again_failure"]
        
        if self.is_hovering(play_again_rect):
            self.draw_glow_effect(self.screen, play_again_rect, 0.8)
            
            progress = self.get_hover_progress("play_again_failure")
            if progress > 0:
                x, y, w, h = play_again_rect
                center = (x + w // 2, y + h // 2)
                self.draw_loading_circle(self.screen, center, progress)
        
        if self.check_hover_click("play_again_failure", play_again_rect):
            self.state = GameState.DIFFICULTY

    def draw_finger_cursor(self):
        draw_x = None
        draw_y = None
        
        with self.finger_lock:
            if self.finger_x is not None and self.finger_y is not None:
                draw_x = self.finger_x
                draw_y = self.finger_y
        
        if draw_x is None and self.mouse_x is not None:
            draw_x = self.mouse_x
            draw_y = self.mouse_y
        
        if draw_x is not None and draw_y is not None:
            pygame.draw.circle(self.screen, (255, 50, 50), (draw_x, draw_y), 15)
            pygame.draw.circle(self.screen, (255, 255, 255), (draw_x, draw_y), 8)
            pygame.draw.circle(self.screen, (255, 50, 50), (draw_x, draw_y), 3)
        else:
            pygame.draw.circle(self.screen, (100, 100, 100), (SCREEN_WIDTH - 50, 50), 20)
            pygame.draw.circle(self.screen, (200, 50, 50), (SCREEN_WIDTH - 50, 50), 15)
            pygame.draw.line(self.screen, (255, 255, 255), (SCREEN_WIDTH - 60, 40), (SCREEN_WIDTH - 40, 60), 3)
            pygame.draw.line(self.screen, (255, 255, 255), (SCREEN_WIDTH - 40, 40), (SCREEN_WIDTH - 60, 60), 3)

    def run(self):
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                elif event.type == pygame.MOUSEMOTION:
                    self.mouse_x, self.mouse_y = event.pos
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.mouse_x, self.mouse_y = event.pos
            
            if self.state == GameState.START:
                self.draw_start_screen()
            elif self.state == GameState.DIFFICULTY:
                self.draw_difficulty_screen()
            elif self.state == GameState.EASY_GAME:
                self.draw_easy_game_screen()
            elif self.state == GameState.END_SUCCESS:
                self.draw_end_success_screen()
            elif self.state == GameState.END_FAILURE:
                self.draw_end_failure_screen()
            
            self.draw_finger_cursor()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        self.camera_running = False
        self.cap.release()
        pygame.quit()

if __name__ == "__main__":
    game = ElixirGame()
    game.run()