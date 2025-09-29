import pygame
import cv2
import mediapipe as mp
import threading
import time
import random
import sys
import math
from enum import Enum

# Inicjalizacja Pygame
pygame.init()

# Stałe
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
HOVER_TIME = 0.5  # Czas najechania do "kliknięcia"
GLOW_DURATION = 1.0  # Czas podświetlania składnika w sekwencji
GLOW_PAUSE = 0.3  # Pauza między podświetleniami

class GameState(Enum):
    START = 1
    DIFFICULTY = 2
    EASY_GAME = 3
    END = 4

class ElixirGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Gra Eliksirów")
        
        self.clock = pygame.time.Clock()
        self.state = GameState.START
        
        # Detekcja dłoni
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.cap = cv2.VideoCapture(0)
        
        # Pozycja palca
        self.finger_x = None
        self.finger_y = None
        self.finger_lock = threading.Lock()
        
        # Start wątku kamery
        self.camera_thread = threading.Thread(target=self.camera_loop, daemon=True)
        self.camera_running = True
        self.camera_thread.start()
        
        # Hover tracking
        self.hover_start_time = {}
        
        # Ładowanie zasobów
        self.load_assets()
        
        # Przepisy
        self.recipes = {
            "Eliksir Smoczej Łuski": ["pazur_smoka", "skrzydlo_feniksa", "kropla_eliksiru", "gwiazda_centralna", "luska_syreny"],
            "Mikstura Gwiezdnej Iskry": ["swietlisty_krag", "kropla_eliksiru", "skrzydlo_feniksa", "gwiazda_centralna", "luska_syreny"],
            "Wywar Feniksa": ["skrzydlo_feniksa", "pazur_smoka", "swietlisty_krag", "kropla_eliksiru", "gwiazda_centralna"]
        }
        
        # Stan gry
        self.current_recipe = None
        self.current_recipe_name = None
        self.sequence_playing = False
        self.sequence_index = 0
        self.player_sequence = []
        self.glow_start_time = 0
        self.showing_error = False
        self.error_start_time = 0
        
        # Pozycje składników - POWIĘKSZONE I PRZESUNIĘTE W LEWO
        # Format: (x, y, szerokość, wysokość)
        # Rozmiar: 120x120 pikseli, wszystko przesunięte w lewo
        
        self.ingredient_positions = {
            # Lewo dół - Świetlisty Krąg
            "swietlisty_krag": (100, 550, 120, 120),
            
            # Lewo środek - Pazur Smoka
            "pazur_smoka": (220, 370, 120, 120),
            
            # Góra lewo - Skrzydło Feniksa
            "skrzydlo_feniksa": (400, 200, 120, 120),
            
            # Góra środek - Kropla Eliksiru
            "kropla_eliksiru": (680, 230, 120, 120),
            
            # Prawo góra - Gwiazda Centralna
            "gwiazda_centralna": (860, 320, 120, 120),
            
            # Prawo dół - Łuska Syreny
            "luska_syreny": (940, 550, 120, 120)
        }
        
        # Pozycje przycisków (dostosuj do swoich obrazów)
        self.button_positions = {
            "start": (400, 500, 200, 80),
            "easy": (300, 400, 150, 60),
            "hard": (500, 400, 150, 60),
            "play_again": (400, 500, 200, 80)
        }

    def load_assets(self):
        """Ładowanie wszystkich zasobów graficznych"""
        try:
            # Tła
            self.backgrounds = {
                "start": pygame.image.load("tla/start.png"),
                "difficulty": pygame.image.load("tla/trudnosc.png"),
                "easy": pygame.image.load("tla/latwy.png"),
                "end": pygame.image.load("tla/koniec.png")
            }
            
            # Składniki
            self.ingredients = {
                "swietlisty_krag": pygame.image.load("tla/swietlisty_krag.png"),
                "pazur_smoka": pygame.image.load("tla/pazur_smoka.png"),
                "luska_syreny": pygame.image.load("tla/luska_syreny.png"),
                "kropla_eliksiru": pygame.image.load("tla/kropla_eliksiru.png"),
                "skrzydlo_feniksa": pygame.image.load("tla/skrzydlo_feniksa.png"),
                "gwiazda_centralna": pygame.image.load("tla/gwiazda_centralna.png")
            }
            
            # Przeskaluj składniki do większego rozmiaru (120x120 pikseli)
            for key in self.ingredients:
                self.ingredients[key] = pygame.transform.scale(
                    self.ingredients[key], (120, 120)
                )
            
            # Przycisk zagraj ponownie
            self.play_again_button = pygame.image.load("tla/zagraj_ponownie.png")
            
            # Skalowanie tła do rozmiaru ekranu
            for key in self.backgrounds:
                self.backgrounds[key] = pygame.transform.scale(
                    self.backgrounds[key], (SCREEN_WIDTH, SCREEN_HEIGHT)
                )
            
            # Font do tekstu
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
        """Wątek kamery do detekcji dłoni"""
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
                            # Punkt wskazujący (landmark 8)
                            point = landmarks.landmark[8]
                            # Przekształcenie na współrzędne ekranu
                            self.finger_x = int((1 - point.x) * SCREEN_WIDTH)  # Odbicie lustrzane
                            self.finger_y = int(point.y * SCREEN_HEIGHT)
                            break
            
            time.sleep(1/30)  # 30 FPS dla kamery

    def is_hovering(self, rect):
        """Sprawdza czy palec jest nad danym prostokątem"""
        with self.finger_lock:
            if self.finger_x is None or self.finger_y is None:
                return False
            x, y, w, h = rect
            return x <= self.finger_x <= x + w and y <= self.finger_y <= y + h

    def get_hover_progress(self, button_id):
        """Zwraca postęp hovera (0.0 do 1.0) dla danego przycisku"""
        if button_id not in self.hover_start_time:
            return 0.0
        
        current_time = time.time()
        elapsed = current_time - self.hover_start_time[button_id]
        return min(elapsed / HOVER_TIME, 1.0)

    def check_hover_click(self, button_id, rect):
        """Sprawdza czy nastąpiło 'kliknięcie' przez najechanie"""
        current_time = time.time()
        
        if self.is_hovering(rect):
            if button_id not in self.hover_start_time:
                self.hover_start_time[button_id] = current_time
            elif current_time - self.hover_start_time[button_id] >= HOVER_TIME:
                # Reset hover time
                self.hover_start_time[button_id] = current_time + 1  # Zapobiega wielokrotnym kliknięciom
                return True
        else:
            if button_id in self.hover_start_time:
                del self.hover_start_time[button_id]
        
        return False

    def draw_loading_circle(self, surface, center, progress, radius=50):
        """Rysuje ładujące się kółko pokazujące postęp najechania
        progress: 0.0 do 1.0"""
        cx, cy = center
        
        # Tło kółka - ciemne z przezroczystością
        bg_surface = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
        pygame.draw.circle(bg_surface, (0, 0, 0, 120), (radius * 1.5, radius * 1.5), radius)
        surface.blit(bg_surface, (cx - radius * 1.5, cy - radius * 1.5))
        
        # Obwódka zewnętrzna
        pygame.draw.circle(surface, (100, 255, 100), (cx, cy), radius, 3)
        
        # Wypełnienie postępu - rysuj łuk
        if progress > 0:
            # Konwertuj postęp na kąt (0-360 stopni)
            angle = int(progress * 360)
            
            # Rysuj łuk postępu
            points = [(cx, cy)]
            for i in range(angle + 1):
                rad = math.radians(i - 90)  # -90 żeby zaczynać od góry
                x = cx + int((radius - 5) * math.cos(rad))
                y = cy + int((radius - 5) * math.sin(rad))
                points.append((x, y))
            
            if len(points) > 2:
                # Rysuj wypełniony sektor
                glow_surface = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
                adjusted_points = [(p[0] - cx + radius * 1.5, p[1] - cy + radius * 1.5) for p in points]
                pygame.draw.polygon(glow_surface, (100, 255, 100, 180), adjusted_points)
                surface.blit(glow_surface, (cx - radius * 1.5, cy - radius * 1.5))
        
        # Tekst procentowy w środku
        if progress > 0:
            percent_text = f"{int(progress * 100)}%"
            font = pygame.font.Font(None, 32)
            text_surface = font.render(percent_text, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(cx, cy))
            surface.blit(text_surface, text_rect)

    def draw_glow_effect(self, surface, rect, intensity=1.0):
        """Rysuje efekt podświetlenia wokół składnika"""
        x, y, w, h = rect
        
        # Oblicz środek składnika
        center_x = x + w // 2
        center_y = y + h // 2
        
        # Rysuj kilka koncentrycznych okręgów dla efektu glow
        for i in range(5, 0, -1):
            alpha = int(50 * intensity * (i / 5))
            radius = int((w // 2 + 20) * (1 + i * 0.15))
            
            glow_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            color = (255, 255, 150, alpha)
            pygame.draw.circle(glow_surface, color, (radius, radius), radius)
            
            surface.blit(glow_surface, (center_x - radius, center_y - radius))

    def start_new_game(self):
        """Rozpoczyna nową grę"""
        self.current_recipe_name, self.current_recipe = random.choice(list(self.recipes.items()))
        self.sequence_playing = True
        self.sequence_index = 0
        self.player_sequence = []
        self.glow_start_time = time.time()
        self.showing_error = False

    def update_sequence(self):
        """Aktualizuje animację sekwencji"""
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
        """Sprawdza kliknięcia składników"""
        if self.sequence_playing or self.showing_error:
            return
            
        for ingredient, rect in self.ingredient_positions.items():
            if self.check_hover_click(f"ingredient_{ingredient}", rect):
                self.player_sequence.append(ingredient)
                
                # Sprawdź czy gracz się pomylił
                expected_index = len(self.player_sequence) - 1
                if expected_index < len(self.current_recipe):
                    if ingredient != self.current_recipe[expected_index]:
                        # Błąd - pokaż sekwencję ponownie
                        self.showing_error = True
                        self.error_start_time = time.time()
                        self.player_sequence = []
                        return
                
                # Sprawdź czy ukończono przepis
                if len(self.player_sequence) == len(self.current_recipe):
                    self.state = GameState.END

    def draw_error_message(self):
        """Rysuje komunikat o błędzie"""
        current_time = time.time()
        if current_time - self.error_start_time >= 2.0:  # Pokaż błąd przez 2 sekundy
            # Pokaż sekwencję ponownie
            self.showing_error = False
            self.sequence_playing = True
            self.sequence_index = 0
            self.glow_start_time = current_time
            return
        
        # Rysuj komunikat
        error_text = "Niestety nie udało się, spróbuj ponownie"
        text_surface = self.error_font.render(error_text, True, (255, 0, 0))
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(text_surface, text_rect)

    def draw_start_screen(self):
        """Rysuje ekran startowy"""
        self.screen.blit(self.backgrounds["start"], (0, 0))
        
        # Podświetl przycisk START jeśli jest hover
        start_rect = self.button_positions["start"]
        if self.is_hovering(start_rect):
            self.draw_glow_effect(self.screen, start_rect, 0.8)
            
            # Rysuj loading circle
            progress = self.get_hover_progress("start")
            if progress > 0:
                x, y, w, h = start_rect
                center = (x + w // 2, y + h // 2)
                self.draw_loading_circle(self.screen, center, progress)
        
        # Sprawdź kliknięcie START
        if self.check_hover_click("start", start_rect):
            self.state = GameState.DIFFICULTY

    def draw_difficulty_screen(self):
        """Rysuje ekran wyboru trudności"""
        self.screen.blit(self.backgrounds["difficulty"], (0, 0))
        
        # Podświetl przycisk Łatwy jeśli jest hover
        easy_rect = self.button_positions["easy"]
        if self.is_hovering(easy_rect):
            self.draw_glow_effect(self.screen, easy_rect, 0.8)
            
            # Rysuj loading circle
            progress = self.get_hover_progress("easy")
            if progress > 0:
                x, y, w, h = easy_rect
                center = (x + w // 2, y + h // 2)
                self.draw_loading_circle(self.screen, center, progress)
        
        # Podświetl przycisk Trudny jeśli jest hover
        hard_rect = self.button_positions["hard"]
        if self.is_hovering(hard_rect):
            self.draw_glow_effect(self.screen, hard_rect, 0.8)
            
            # Rysuj loading circle
            progress = self.get_hover_progress("hard")
            if progress > 0:
                x, y, w, h = hard_rect
                center = (x + w // 2, y + h // 2)
                self.draw_loading_circle(self.screen, center, progress)
        
        # Sprawdź kliknięcie Łatwy
        if self.check_hover_click("easy", easy_rect):
            self.state = GameState.EASY_GAME
            self.start_new_game()

    def draw_easy_game_screen(self):
        """Rysuje ekran gry łatwej"""
        self.screen.blit(self.backgrounds["easy"], (0, 0))
        
        # Tytuł przepisu
        title_surface = self.title_font.render(self.current_recipe_name, True, (255, 255, 255))
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(title_surface, title_rect)
        
        # Rysuj składniki
        for i, (ingredient, rect) in enumerate(self.ingredient_positions.items()):
            self.screen.blit(self.ingredients[ingredient], (rect[0], rect[1]))
            
            # Podświetl składnik podczas sekwencji
            if (self.sequence_playing and 
                self.sequence_index < len(self.current_recipe) and
                ingredient == self.current_recipe[self.sequence_index]):
                
                current_time = time.time()
                elapsed = current_time - self.glow_start_time
                if elapsed <= GLOW_DURATION:
                    intensity = 1.0 - (elapsed / GLOW_DURATION * 0.5)  # Fade out
                    self.draw_glow_effect(self.screen, rect, intensity)
            
            # Podświetl składnik przy hover (gdy nie ma sekwencji)
            elif not self.sequence_playing and not self.showing_error and self.is_hovering(rect):
                self.draw_glow_effect(self.screen, rect, 0.7)
                
                # Rysuj loading circle dla składników
                progress = self.get_hover_progress(f"ingredient_{ingredient}")
                if progress > 0:
                    x, y, w, h = rect
                    center = (x + w // 2, y + h // 2)
                    self.draw_loading_circle(self.screen, center, progress, radius=40)
        
        # Aktualizuj sekwencję
        self.update_sequence()
        
        # Sprawdź kliknięcia składników
        self.check_ingredient_clicks()
        
        # Pokaż komunikat o błędzie
        if self.showing_error:
            self.draw_error_message()

    def draw_end_screen(self):
        """Rysuje ekran końcowy"""
        self.screen.blit(self.backgrounds["end"], (0, 0))
        
        # Przycisk zagraj ponownie
        play_again_rect = self.button_positions["play_again"]
        
        # Podświetl przycisk jeśli jest hover
        if self.is_hovering(play_again_rect):
            self.draw_glow_effect(self.screen, play_again_rect, 0.8)
            
            # Rysuj loading circle
            progress = self.get_hover_progress("play_again")
            if progress > 0:
                x, y, w, h = play_again_rect
                center = (x + w // 2, y + h // 2)
                self.draw_loading_circle(self.screen, center, progress)
        
        # Rysuj przycisk (jeśli masz osobny obraz)
        try:
            self.screen.blit(self.play_again_button, (play_again_rect[0], play_again_rect[1]))
        except:
            # Fallback - prostokąt z tekstem
            pygame.draw.rect(self.screen, (100, 100, 100), play_again_rect)
            text = self.error_font.render("ZAGRAJ PONOWNIE", True, (255, 255, 255))
            text_rect = text.get_rect(center=(play_again_rect[0] + play_again_rect[2]//2, 
                                             play_again_rect[1] + play_again_rect[3]//2))
            self.screen.blit(text, text_rect)
        
        # Sprawdź kliknięcie
        if self.check_hover_click("play_again", play_again_rect):
            self.state = GameState.DIFFICULTY

    def draw_finger_cursor(self):
        """Rysuje kursor palca na ekranie"""
        with self.finger_lock:
            if self.finger_x is not None and self.finger_y is not None:
                # Główny kursor - czerwone kółko
                pygame.draw.circle(self.screen, (255, 50, 50), 
                                 (self.finger_x, self.finger_y), 15)
                # Wewnętrzne białe kółko
                pygame.draw.circle(self.screen, (255, 255, 255), 
                                 (self.finger_x, self.finger_y), 8)
                # Środkowa kropka
                pygame.draw.circle(self.screen, (255, 50, 50), 
                                 (self.finger_x, self.finger_y), 3)
            else:
                # Wskaźnik braku detekcji w prawym górnym rogu
                pygame.draw.circle(self.screen, (100, 100, 100), 
                                 (SCREEN_WIDTH - 50, 50), 20)
                pygame.draw.circle(self.screen, (200, 50, 50), 
                                 (SCREEN_WIDTH - 50, 50), 15)
                # Znak X
                pygame.draw.line(self.screen, (255, 255, 255), 
                               (SCREEN_WIDTH - 60, 40), (SCREEN_WIDTH - 40, 60), 3)
                pygame.draw.line(self.screen, (255, 255, 255), 
                               (SCREEN_WIDTH - 40, 40), (SCREEN_WIDTH - 60, 60), 3)

    def run(self):
        """Główna pętla gry"""
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
            
            # Rysowanie zależnie od stanu
            if self.state == GameState.START:
                self.draw_start_screen()
            elif self.state == GameState.DIFFICULTY:
                self.draw_difficulty_screen()
            elif self.state == GameState.EASY_GAME:
                self.draw_easy_game_screen()
            elif self.state == GameState.END:
                self.draw_end_screen()
            
            # Rysuj wskaźnik detekcji dłoni
            self.draw_finger_cursor()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        # Cleanup
        self.camera_running = False
        self.cap.release()
        pygame.quit()

if __name__ == "__main__":
    game = ElixirGame()
    game.run()