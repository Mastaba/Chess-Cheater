import math
import re
import sys
import threading
import time
from pathlib import Path

import pygame
from pygame.locals import *

from stockfish_engine import StockfishEngine, StockfishError


pygame.init()

APP_NAME = "Chess Cheater"
APP_VERSION = "0.1.0"
APP_TITLE = f"{APP_NAME} v{APP_VERSION}"
PROJECT_ROOT = Path(__file__).resolve().parent
APP_ICON_PATH = PROJECT_ROOT / "assets" / "chess_cheater_rook.ico"
OPENINGS_ROOT = PROJECT_ROOT / "openings"
BOARD_SIZE = 8
BOARD_PIXELS = 640
LABEL_GUTTER = 32
PANEL_HEIGHT = 204
MENU_HEIGHT = 30
TURN_BANNER_HEIGHT = 44
ANALYSIS_WIDTH = 390
NOTATION_WIDTH = 420
GAME_AREA_WIDTH = BOARD_PIXELS + LABEL_GUTTER * 2
GAME_LEFT = NOTATION_WIDTH
ANALYSIS_LEFT = NOTATION_WIDTH + GAME_AREA_WIDTH
WIDTH = NOTATION_WIDTH + GAME_AREA_WIDTH + ANALYSIS_WIDTH
HEIGHT = MENU_HEIGHT + BOARD_PIXELS + LABEL_GUTTER * 2 + PANEL_HEIGHT + TURN_BANNER_HEIGHT
BOARD_LEFT = GAME_LEFT + LABEL_GUTTER
BOARD_TOP = MENU_HEIGHT + TURN_BANNER_HEIGHT + LABEL_GUTTER
SQUARE_SIZE = BOARD_PIXELS // BOARD_SIZE
FPS = 60
PREVIEW_TRAVEL_SECONDS = 0.95
PREVIEW_HOLD_SECONDS = 0.5
PREVIEW_CYCLE_SECONDS = PREVIEW_TRAVEL_SECONDS + PREVIEW_HOLD_SECONDS
PREVIEW_EASE_POWER = 2.8
EXECUTE_TRAVEL_SECONDS = 0.46
EXECUTE_HOLD_SECONDS = 0.16
EXECUTE_CYCLE_SECONDS = EXECUTE_TRAVEL_SECONDS + EXECUTE_HOLD_SECONDS
EXECUTE_EASE_POWER = 2.35
POST_MOVE_ARROW_SECONDS = 2.8
STOCKFISH_MOVE_COUNT = 10

CAPTURED_PIECE_SIZE = 26
SPLASH_SECONDS = 5.2
SPLASH_DROP_SECONDS = 2.15
SPLASH_SETTLE_SECONDS = 0.65
SPLASH_TOTAL_SPIN_RADIANS = math.tau * 6

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARKGRAY = (169, 169, 169)
LIGHTGRAY = (211, 211, 211)
DARK_SQUARE = (118, 150, 86)
LIGHT_SQUARE = (238, 238, 210)
GREEN = (0, 255, 0, 180)
RED = (255, 0, 0, 180)
HIGHLIGHT = (255, 255, 0)
PREVIOUS_MOVE_FROM = (255, 241, 79, 72)
PREVIOUS_MOVE_TO = (255, 241, 79, 42)
UI_BG = (238, 239, 233)
PANEL_BG = (226, 229, 220)
BUTTON_BG = (248, 249, 245)
BUTTON_DISABLED = (199, 203, 195)
BUTTON_BORDER = (74, 80, 70)
TEXT_MAIN = BLACK
TEXT_MUTED = (76, 82, 74)
PREVIEW_BLUE = (52, 121, 211, 150)
STOCKFISH_HINT = (42, 101, 176)
STOCKFISH_HINT_BG = (226, 240, 255)
STOCKFISH_HINT_FILL = (42, 101, 176, 180)
OPENING_HINT = (40, 178, 88)
OPENING_HINT_BG = (222, 248, 230)
OPENING_HINT_FILL = (40, 178, 88, 145)
ANALYSIS_SELECTED = (224, 164, 0)
HOVER_GLOW = (88, 164, 242)
HOVER_GLOW_SOFT = (211, 234, 255)
EXECUTE_BEST_MOVE = "__execute_best_move__"

UI_THEMES = {
    "Light": {
        "ui_bg": (238, 239, 233),
        "panel_bg": (226, 229, 220),
        "button_bg": (248, 249, 245),
        "button_disabled": (199, 203, 195),
        "button_border": (74, 80, 70),
        "text_main": BLACK,
        "text_muted": (76, 82, 74),
        "stockfish_hint_bg": (226, 240, 255),
        "hover_glow_soft": (211, 234, 255),
    },
    "Dark": {
        "ui_bg": (28, 31, 34),
        "panel_bg": (39, 43, 47),
        "button_bg": (57, 63, 68),
        "button_disabled": (73, 77, 80),
        "button_border": (146, 156, 164),
        "text_main": (238, 242, 245),
        "text_muted": (176, 185, 191),
        "stockfish_hint_bg": (36, 64, 94),
        "hover_glow_soft": (41, 80, 118),
    },
}

BOARD_THEMES = {
    "Classic": {"light": (238, 238, 210), "dark": (118, 150, 86)},
    "Blue": {"light": (218, 229, 241), "dark": (82, 122, 168)},
    "Gray": {"light": (226, 228, 230), "dark": (104, 111, 118)},
    "Walnut": {"light": (230, 199, 151), "dark": (125, 83, 50)},
}

PIECE_TO_FEN = {
    'wp': 'P',
    'wr': 'R',
    'wn': 'N',
    'wb': 'B',
    'wq': 'Q',
    'wk': 'K',
    'bp': 'p',
    'br': 'r',
    'bn': 'n',
    'bb': 'b',
    'bq': 'q',
    'bk': 'k',
}

PIECE_NAMES = {
    'p': 'pawn',
    'r': 'rook',
    'n': 'knight',
    'b': 'bishop',
    'q': 'queen',
    'k': 'king',
}


def set_window_icon():
    if not APP_ICON_PATH.exists():
        return
    try:
        pygame.display.set_icon(pygame.image.load(str(APP_ICON_PATH)).convert_alpha())
    except pygame.error:
        pass


screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(APP_TITLE)
set_window_icon()
clock = pygame.time.Clock()


def load_pieces():
    pieces = {}
    for color in ['w', 'b']:
        for piece in ['p', 'r', 'n', 'b', 'q', 'k']:
            key = color + piece
            try:
                img = pygame.image.load(str(PROJECT_ROOT / "images" / f"{key}.png")).convert_alpha()
                pieces[key] = pygame.transform.smoothscale(img, (SQUARE_SIZE, SQUARE_SIZE))
            except pygame.error:
                pieces[key] = create_fallback_piece(color, piece)
    return pieces


def create_fallback_piece(color, piece_type):
    surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
    bg_color = (200, 200, 200) if color == 'w' else (50, 50, 50)
    text_color = BLACK if color == 'w' else WHITE

    pygame.draw.circle(
        surface,
        bg_color,
        (SQUARE_SIZE // 2, SQUARE_SIZE // 2),
        SQUARE_SIZE // 2 - 5,
    )

    font = pygame.font.SysFont('Arial', SQUARE_SIZE // 2)
    text = font.render(piece_type.upper(), True, text_color)
    text_rect = text.get_rect(center=(SQUARE_SIZE // 2, SQUARE_SIZE // 2))
    surface.blit(text, text_rect)
    return surface


def create_arrow(from_pos, to_pos, color, piece_type=None):
    arrow_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    path = create_indicator_path(from_pos, to_pos, piece_type)
    end_pos = path[-1]

    stroke_width = 7
    for index in range(len(path) - 1):
        pygame.draw.line(arrow_surface, color, path[index], path[index + 1], stroke_width)

    for point in path[:-1]:
        pygame.draw.circle(arrow_surface, color, point, stroke_width // 2)

    last_start = path[-2]
    dx, dy = end_pos[0] - last_start[0], end_pos[1] - last_start[1]
    length = (dx**2 + dy**2) ** 0.5
    if length == 0:
        return arrow_surface

    dx, dy = dx / length, dy / length
    arrow_length = round((SQUARE_SIZE // 5) * 4 / 3)
    arrow_width = round((SQUARE_SIZE // 9) * 4 / 3)
    arrow_base = (
        end_pos[0] - arrow_length * dx,
        end_pos[1] - arrow_length * dy,
    )
    p1 = (arrow_base[0] + arrow_width * dy, arrow_base[1] - arrow_width * dx)
    p2 = (arrow_base[0] - arrow_width * dy, arrow_base[1] + arrow_width * dx)

    pygame.draw.polygon(arrow_surface, color, [end_pos, p1, p2])
    return arrow_surface


def create_chevron_line(from_pos, to_pos, color, piece_type=None):
    chevron_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    path = create_chevron_path(from_pos, to_pos, piece_type)

    stroke_width = 5
    chevron_length = 9
    chevron_width = 15
    spacing = 18
    speed = 92
    alpha = color[3] if len(color) == 4 else 180
    shadow_color = tuple(max(0, round(channel * 0.36)) for channel in color[:3]) + (alpha,)
    segments = []
    total_length = 0

    for index in range(len(path) - 1):
        start = path[index]
        end = path[index + 1]
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = (dx**2 + dy**2) ** 0.5
        if length == 0:
            continue

        ux, uy = dx / length, dy / length
        segments.append((start, length, ux, uy, total_length))
        total_length += length

    if not segments:
        return chevron_surface

    def point_at(distance):
        for start, length, ux, uy, segment_start in segments:
            if distance <= segment_start + length:
                local_distance = distance - segment_start
                return (
                    (start[0] + ux * local_distance, start[1] + uy * local_distance),
                    (ux, uy),
                )

        start, length, ux, uy, segment_start = segments[-1]
        return (
            (start[0] + ux * length, start[1] + uy * length),
            (ux, uy),
        )

    margin = max(14, chevron_length * 0.8)
    first_distance = margin + (time.monotonic() * speed) % spacing
    last_distance = max(margin, total_length - margin)
    distance = first_distance

    while distance <= last_distance:
        center, (ux, uy) = point_at(distance)
        px, py = -uy, ux
        tip = (
            center[0] + ux * chevron_length / 2,
            center[1] + uy * chevron_length / 2,
        )
        tail_center = (
            center[0] - ux * chevron_length / 2,
            center[1] - uy * chevron_length / 2,
        )
        left_tail = (
            tail_center[0] + px * chevron_width / 2,
            tail_center[1] + py * chevron_width / 2,
        )
        right_tail = (
            tail_center[0] - px * chevron_width / 2,
            tail_center[1] - py * chevron_width / 2,
        )

        for draw_color, width in ((shadow_color, stroke_width + 2), (color, stroke_width)):
            pygame.draw.line(chevron_surface, draw_color, left_tail, tip, width)
            pygame.draw.line(chevron_surface, draw_color, right_tail, tip, width)

        distance += spacing

    return chevron_surface


def create_chevron_path(from_pos, to_pos, piece_type=None):
    from_x, from_y = from_pos
    to_x, to_y = to_pos

    start_pos = (
        BOARD_LEFT + from_x * SQUARE_SIZE + SQUARE_SIZE // 2,
        BOARD_TOP + from_y * SQUARE_SIZE + SQUARE_SIZE // 2,
    )
    end_pos = (
        BOARD_LEFT + to_x * SQUARE_SIZE + SQUARE_SIZE // 2,
        BOARD_TOP + to_y * SQUARE_SIZE + SQUARE_SIZE // 2,
    )

    dx = to_x - from_x
    dy = to_y - from_y
    if piece_type != 'n' or abs(dx) + abs(dy) != 3:
        return [start_pos, end_pos]

    pixel_dx = end_pos[0] - start_pos[0]
    pixel_dy = end_pos[1] - start_pos[1]
    curve_strength = 0.72
    if abs(dx) > abs(dy):
        control_one = (start_pos[0] + pixel_dx * curve_strength, start_pos[1])
        control_two = (end_pos[0], end_pos[1] - pixel_dy * curve_strength)
    else:
        control_one = (start_pos[0], start_pos[1] + pixel_dy * curve_strength)
        control_two = (end_pos[0] - pixel_dx * curve_strength, end_pos[1])

    samples = 22
    path = []
    for index in range(samples + 1):
        t = index / samples
        inverse = 1 - t
        x = (
            inverse**3 * start_pos[0]
            + 3 * inverse**2 * t * control_one[0]
            + 3 * inverse * t**2 * control_two[0]
            + t**3 * end_pos[0]
        )
        y = (
            inverse**3 * start_pos[1]
            + 3 * inverse**2 * t * control_one[1]
            + 3 * inverse * t**2 * control_two[1]
            + t**3 * end_pos[1]
        )
        path.append((x, y))

    return path


def create_indicator_path(from_pos, to_pos, piece_type=None):
    from_x, from_y = from_pos
    to_x, to_y = to_pos

    start_pos = (
        BOARD_LEFT + from_x * SQUARE_SIZE + SQUARE_SIZE // 2,
        BOARD_TOP + from_y * SQUARE_SIZE + SQUARE_SIZE // 2,
    )
    end_pos = (
        BOARD_LEFT + to_x * SQUARE_SIZE + SQUARE_SIZE // 2,
        BOARD_TOP + to_y * SQUARE_SIZE + SQUARE_SIZE // 2,
    )

    path = [start_pos]
    if piece_type == 'n' and abs(to_x - from_x) + abs(to_y - from_y) == 3:
        if abs(to_x - from_x) > abs(to_y - from_y):
            path.append((end_pos[0], start_pos[1]))
        else:
            path.append((start_pos[0], end_pos[1]))
    path.append(end_pos)
    return path


def draw_text(surface, text, font, color, pos, anchor='topleft'):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    setattr(rect, anchor, pos)
    surface.blit(rendered, rect)
    return rect


def draw_stroked_text(surface, text, font, color, stroke_color, pos, anchor='center', stroke_width=2):
    base_rect = font.render(text, True, color).get_rect()
    setattr(base_rect, anchor, pos)

    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx == 0 and dy == 0:
                continue
            stroke = font.render(text, True, stroke_color)
            surface.blit(stroke, base_rect.move(dx, dy))

    rendered = font.render(text, True, color)
    surface.blit(rendered, base_rect)
    return base_rect


def accelerated_preview_progress(elapsed, cycle_seconds, travel_seconds, ease_power):
    cycle_elapsed = elapsed % cycle_seconds
    if cycle_elapsed >= travel_seconds:
        return 1.0

    t = cycle_elapsed / travel_seconds
    return t ** ease_power


def clamp(value, minimum=0.0, maximum=1.0):
    return max(minimum, min(maximum, value))


def hover_pulse(started_at):
    if not started_at:
        return 0.0
    elapsed = time.monotonic() - started_at
    return 0.5 + 0.5 * math.sin(elapsed * math.tau * 1.85)


def apply_ui_theme(theme_name):
    global UI_BG, PANEL_BG, BUTTON_BG, BUTTON_DISABLED, BUTTON_BORDER
    global TEXT_MAIN, TEXT_MUTED, STOCKFISH_HINT_BG, HOVER_GLOW_SOFT

    theme = UI_THEMES.get(theme_name, UI_THEMES["Light"])
    UI_BG = theme["ui_bg"]
    PANEL_BG = theme["panel_bg"]
    BUTTON_BG = theme["button_bg"]
    BUTTON_DISABLED = theme["button_disabled"]
    BUTTON_BORDER = theme["button_border"]
    TEXT_MAIN = theme["text_main"]
    TEXT_MUTED = theme["text_muted"]
    STOCKFISH_HINT_BG = theme["stockfish_hint_bg"]
    HOVER_GLOW_SOFT = theme["hover_glow_soft"]


def read_clipboard_text():
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        raw = pygame.scrap.get(pygame.SCRAP_TEXT)
    except pygame.error:
        return ""

    if not raw:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="ignore").replace("\x00", "")
    return str(raw)


def wrapped_lines(text, font, max_width):
    lines = []
    for raw_line in text.splitlines() or [""]:
        words = raw_line.split(" ")
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            current = word
        lines.append(current)
    return lines


def resolve_user_path(raw_path):
    path = Path(raw_path.strip().strip('"')).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def choose_import_pgn_path():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as exc:
        return None, f"Open dialog unavailable: {exc}"

    initial_dir = OPENINGS_ROOT
    if not initial_dir.exists():
        initial_dir = PROJECT_ROOT

    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        root.update()
        selected = filedialog.askopenfilename(
            parent=root,
            title="Import PGN File",
            initialdir=str(initial_dir),
            filetypes=[
                ("PGN files", "*.pgn"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )
    except tk.TclError as exc:
        return None, f"Open dialog unavailable: {exc}"
    finally:
        if root is not None:
            root.destroy()

    if not selected:
        return None, None
    return Path(selected), None


class AppMenu:
    def __init__(self):
        self.font = pygame.font.SysFont('Arial', 16)
        self.small_font = pygame.font.SysFont('Arial', 14)
        self.active_menu = None
        self.hovered_action = None
        self.menu_rects = {
            "File": pygame.Rect(8, 0, 58, MENU_HEIGHT),
            "View": pygame.Rect(68, 0, 62, MENU_HEIGHT),
            "Learn": pygame.Rect(132, 0, 68, MENU_HEIGHT),
        }
        self.item_rects = []
        self.items = {
            "File": [
                ("Import PGN file...", "import_path"),
                ("Export PGN file...", "export_path"),
                ("Paste PGN...", "paste_game"),
                ("Exit", "exit"),
            ],
            "View": [
                ("Light mode", "theme:Light"),
                ("Dark mode", "theme:Dark"),
                ("Classic board", "board:Classic"),
                ("Blue board", "board:Blue"),
                ("Gray board", "board:Gray"),
                ("Walnut board", "board:Walnut"),
            ],
            "Learn": [
                ("Opening Mode", "learn_openings"),
            ],
        }

    def draw(self, surface, ui_theme_name, board_theme_name, learn_opening_mode=False):
        pygame.draw.rect(surface, PANEL_BG, pygame.Rect(0, 0, WIDTH, MENU_HEIGHT))
        pygame.draw.line(surface, BUTTON_BORDER, (0, MENU_HEIGHT - 1), (WIDTH, MENU_HEIGHT - 1), 1)

        for name, rect in self.menu_rects.items():
            selected = self.active_menu == name
            if selected:
                pygame.draw.rect(surface, BUTTON_BG, rect, border_radius=4)
                pygame.draw.rect(surface, BUTTON_BORDER, rect, 1, border_radius=4)
            draw_text(surface, name, self.font, TEXT_MAIN, rect.center, 'center')

        self.item_rects = []
        if not self.active_menu:
            return

        menu_rect = self.menu_rects[self.active_menu]
        width = 190 if self.active_menu in ("File", "View") else 160
        x = menu_rect.x
        y = MENU_HEIGHT + 2
        dropdown_rect = pygame.Rect(x, y, width, len(self.items[self.active_menu]) * 30 + 8)
        pygame.draw.rect(surface, BUTTON_BG, dropdown_rect, border_radius=6)
        pygame.draw.rect(surface, BUTTON_BORDER, dropdown_rect, 1, border_radius=6)

        for index, (label, action) in enumerate(self.items[self.active_menu]):
            item_rect = pygame.Rect(x + 4, y + 4 + index * 30, width - 8, 28)
            checked = (
                action == f"theme:{ui_theme_name}"
                or action == f"board:{board_theme_name}"
                or (action == "learn_openings" and learn_opening_mode)
            )
            hovered = self.hovered_action == action
            if hovered:
                pygame.draw.rect(surface, STOCKFISH_HINT_BG, item_rect, border_radius=4)
            marker = "*" if checked else ""
            draw_text(surface, marker, self.small_font, STOCKFISH_HINT, (item_rect.x + 8, item_rect.y + 7))
            draw_text(surface, label, self.small_font, TEXT_MAIN, (item_rect.x + 28, item_rect.y + 7))
            self.item_rects.append((item_rect, action))

    def handle_mouse_motion(self, pos):
        hovered_action = None
        for rect, action in self.item_rects:
            if rect.collidepoint(pos):
                hovered_action = action
                break
        self.hovered_action = hovered_action

    def handle_click(self, pos):
        for name, rect in self.menu_rects.items():
            if rect.collidepoint(pos):
                self.active_menu = None if self.active_menu == name else name
                self.hovered_action = None
                return "menu"

        if self.active_menu:
            for rect, action in self.item_rects:
                if rect.collidepoint(pos):
                    self.active_menu = None
                    self.hovered_action = None
                    return action

            self.active_menu = None
            self.hovered_action = None
            return "menu"

        return None


class TextModal:
    def __init__(self, title, prompt, action, text="", multiline=False):
        self.title = title
        self.prompt = prompt
        self.action = action
        self.text = text
        self.multiline = multiline
        self.message = ""
        self.title_font = pygame.font.SysFont('Arial', 22, bold=True)
        self.font = pygame.font.SysFont('Arial', 17)
        self.small_font = pygame.font.SysFont('Arial', 14)
        self.rect = pygame.Rect(0, 0, 650, 400 if multiline else 210)
        self.rect.center = (WIDTH // 2, HEIGHT // 2)
        self.text_rect = pygame.Rect(self.rect.x + 22, self.rect.y + 86, self.rect.width - 44, self.rect.height - 150)
        self.submit_rect = pygame.Rect(self.rect.right - 188, self.rect.bottom - 48, 78, 30)
        self.cancel_rect = pygame.Rect(self.rect.right - 98, self.rect.bottom - 48, 76, 30)

    def draw(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surface.blit(overlay, (0, 0))

        pygame.draw.rect(surface, PANEL_BG, self.rect, border_radius=8)
        pygame.draw.rect(surface, BUTTON_BORDER, self.rect, 2, border_radius=8)
        draw_text(surface, self.title, self.title_font, TEXT_MAIN, (self.rect.x + 22, self.rect.y + 18))
        draw_text(surface, self.prompt, self.small_font, TEXT_MUTED, (self.rect.x + 22, self.rect.y + 52))

        pygame.draw.rect(surface, BUTTON_BG, self.text_rect, border_radius=6)
        pygame.draw.rect(surface, BUTTON_BORDER, self.text_rect, 1, border_radius=6)

        visible_lines = wrapped_lines(self.text or " ", self.font, self.text_rect.width - 18)
        max_lines = max(1, (self.text_rect.height - 14) // 22)
        for index, line in enumerate(visible_lines[-max_lines:]):
            draw_text(surface, line, self.font, TEXT_MAIN, (self.text_rect.x + 9, self.text_rect.y + 8 + index * 22))

        if self.message:
            draw_text(surface, self.message, self.small_font, TEXT_MUTED, (self.rect.x + 22, self.rect.bottom - 43))

        self.draw_modal_button(surface, self.submit_rect, "OK", True)
        self.draw_modal_button(surface, self.cancel_rect, "Cancel", False)

    def draw_modal_button(self, surface, rect, label, primary):
        bg = STOCKFISH_HINT_BG if primary else BUTTON_BG
        pygame.draw.rect(surface, bg, rect, border_radius=5)
        pygame.draw.rect(surface, STOCKFISH_HINT if primary else BUTTON_BORDER, rect, 1, border_radius=5)
        draw_text(surface, label, self.font, STOCKFISH_HINT if primary else TEXT_MAIN, rect.center, 'center')

    def handle_event(self, event):
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if self.submit_rect.collidepoint(event.pos):
                return self.action, self.text.strip()
            if self.cancel_rect.collidepoint(event.pos):
                return "cancel", None
        if event.type != KEYDOWN:
            return None

        if event.key == K_ESCAPE:
            return "cancel", None
        if event.key == K_RETURN:
            if self.multiline and not (pygame.key.get_mods() & KMOD_CTRL):
                self.text += "\n"
                return None
            return self.action, self.text.strip()
        if event.key == K_BACKSPACE:
            self.text = self.text[:-1]
            return None
        if event.key == K_v and (pygame.key.get_mods() & KMOD_CTRL):
            self.text += read_clipboard_text()
            return None
        if event.key == K_a and (pygame.key.get_mods() & KMOD_CTRL):
            self.text = ""
            return None
        if event.unicode:
            self.text += event.unicode
        return None


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


class SplashScreen:
    def __init__(self):
        self.started_at = time.monotonic()
        self.background = self.load_background()
        self.background_rect = None
        self.title_surface = self.create_pixel_title(APP_NAME)
        self.title_glow_surface = self.create_title_glow(self.title_surface)
        self.prompt_font = pygame.font.SysFont('Times New Roman', 18)
        self.version_font = pygame.font.SysFont('Georgia', 21, bold=True)

    def load_background(self):
        candidates = sorted(PROJECT_ROOT.glob("ChatGPT Image*.png"))
        if not candidates:
            return None

        try:
            image = pygame.image.load(str(candidates[0])).convert()
        except pygame.error:
            return None

        source_width, source_height = image.get_size()
        target_width = int(WIDTH * 0.92)
        target_height = int(HEIGHT * 0.66)
        scale = min(target_width / source_width, target_height / source_height)
        scaled_size = (math.ceil(source_width * scale), math.ceil(source_height * scale))
        return pygame.transform.scale(image, scaled_size)

    def create_pixel_title(self, text):
        font = pygame.font.SysFont('Times New Roman', 46, bold=True)
        sample = font.render(text, True, WHITE)
        depth = 10
        padding = 12
        surface = pygame.Surface(
            (sample.get_width() + padding * 2 + depth, sample.get_height() + padding * 2 + depth),
            pygame.SRCALPHA,
        )

        depth_light = (88, 178, 255)
        depth_dark = (2, 18, 86)
        for offset in range(depth, 0, -1):
            t = offset / depth
            shade = tuple(
                round(depth_light[index] * (1 - t) + depth_dark[index] * t)
                for index in range(3)
            )
            layer = font.render(text, True, shade)
            surface.blit(layer, (padding + offset, padding + offset))

        stroke_top = (2, 18, 86)
        stroke_bottom = (112, 196, 255)
        stroke_radius = 2
        for dx in range(-stroke_radius, stroke_radius + 1):
            for dy in range(-stroke_radius, stroke_radius + 1):
                if dx == 0 and dy == 0:
                    continue
                if dx * dx + dy * dy > stroke_radius * stroke_radius:
                    continue
                t = (dy + stroke_radius) / (stroke_radius * 2)
                stroke_color = tuple(
                    round(stroke_top[index] * (1 - t) + stroke_bottom[index] * t)
                    for index in range(3)
                )
                outline = font.render(text, True, stroke_color)
                surface.blit(outline, (padding + dx, padding + dy))

        face = font.render(text, True, (8, 34, 116))
        surface.blit(face, (padding, padding))

        highlight = font.render(text, True, (255, 244, 158))
        original_clip = surface.get_clip()
        surface.set_clip(pygame.Rect(padding, padding + 4, face.get_width(), face.get_height() // 4))
        surface.blit(highlight, (padding - 1, padding - 1))
        surface.set_clip(pygame.Rect(padding, padding + face.get_height() // 2, face.get_width(), 5))
        surface.blit(highlight, (padding + 2, padding - 1))

        white_highlight = font.render(text, True, WHITE)
        surface.set_clip(pygame.Rect(padding + 4, padding + 7, face.get_width() - 8, 5))
        surface.blit(white_highlight, (padding - 1, padding - 2))
        surface.set_clip(pygame.Rect(padding + 8, padding + face.get_height() // 2 + 2, face.get_width() - 16, 2))
        surface.blit(white_highlight, (padding + 2, padding - 1))
        surface.set_clip(original_clip)

        title_detail = surface.subsurface(
            pygame.Rect(padding, padding, face.get_width(), face.get_height())
        ).copy()
        def make_inner_edge(source, color, thickness=1):
            mask = pygame.mask.from_surface(source)
            edge = pygame.Surface(source.get_size(), pygame.SRCALPHA)
            width, height = source.get_size()
            for y in range(height):
                for x in range(width):
                    if not mask.get_at((x, y)):
                        continue
                    found_edge = False
                    for dy in range(-thickness, thickness + 1):
                        for dx in range(-thickness, thickness + 1):
                            if dx == 0 and dy == 0:
                                continue
                            if dx * dx + dy * dy > thickness * thickness:
                                continue
                            nx, ny = x + dx, y + dy
                            if nx < 0 or nx >= width or ny < 0 or ny >= height or not mask.get_at((nx, ny)):
                                edge.set_at((x, y), color)
                                found_edge = True
                                break
                        if found_edge:
                            break
            return edge

        scaled = pygame.transform.scale(surface, (surface.get_width() * 2, surface.get_height() * 2))
        inner_white = pygame.transform.scale(
            font.render(text, True, WHITE),
            (face.get_width() * 2, face.get_height() * 2),
        )
        scaled_detail = pygame.transform.scale(
            title_detail,
            (face.get_width() * 2, face.get_height() * 2),
        )
        base_pos = (padding * 2, padding * 2)

        scaled.blit(make_inner_edge(scaled, BLACK, 3), (0, 0))
        scaled.blit(scaled_detail, base_pos)
        scaled.blit(make_inner_edge(inner_white, WHITE, 1), base_pos)
        return scaled

    def create_title_glow(self, title_surface):
        glow = pygame.Surface(title_surface.get_size(), pygame.SRCALPHA)
        mask = pygame.mask.from_surface(title_surface)
        mask_surface = mask.to_surface(setcolor=(255, 244, 158, 255), unsetcolor=(0, 0, 0, 0))
        glow.blit(mask_surface, (0, 0))
        return glow

    def draw(self, target):
        elapsed = time.monotonic() - self.started_at
        self.draw_background(target)
        self.draw_title(target, elapsed)
        self.draw_version(target)
        self.draw_prompt(target, elapsed)

    def draw_background(self, target):
        target.fill(BLACK)
        if not self.background:
            return

        scaled_size = self.background.get_size()
        self.background_rect = pygame.Rect(
            (WIDTH - scaled_size[0]) // 2,
            (HEIGHT - scaled_size[1]) // 2,
            scaled_size[0],
            scaled_size[1],
        )
        target.blit(
            self.background,
            self.background_rect,
        )

        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 88))
        target.blit(shade, (0, 0))

    def draw_title(self, target, elapsed):
        motion_progress = clamp(elapsed / (SPLASH_DROP_SECONDS + SPLASH_SETTLE_SECONDS))
        drop_progress = ease_out_cubic(elapsed / SPLASH_DROP_SECONDS)
        target_y = int(HEIGHT * 0.22)
        start_y = -self.title_surface.get_height()
        center_y = start_y + (target_y - start_y) * drop_progress

        remaining_spin = (1 - ease_out_cubic(motion_progress)) ** 1.35
        spin = SPLASH_TOTAL_SPIN_RADIANS * (1 - (1 - motion_progress) ** 3)
        width_scale = 1 - 0.76 * abs(math.sin(spin)) * remaining_spin
        side_offset = round(math.sin(spin) * 22 * remaining_spin)
        current_width = max(12, round(self.title_surface.get_width() * width_scale))
        spun = pygame.transform.scale(self.title_surface, (current_width, self.title_surface.get_height()))
        title_rect = spun.get_rect(center=(WIDTH // 2 + side_offset, round(center_y)))
        self.draw_title_glow(target, title_rect, elapsed)

        shadow = pygame.Surface(spun.get_size(), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 85))
        shadow_rect = shadow.get_rect(center=(WIDTH // 2 + side_offset + 8, round(center_y) + 10))
        target.blit(shadow, shadow_rect)

        target.blit(spun, title_rect)

        if width_scale < 0.32:
            edge = pygame.Rect(0, 0, 8, self.title_surface.get_height())
            edge.center = (WIDTH // 2 + side_offset, round(center_y))
            pygame.draw.rect(target, (255, 244, 158), edge)
            pygame.draw.rect(target, BLACK, edge, 2)

    def draw_version(self, target):
        if self.background_rect:
            center = (self.background_rect.centerx, self.background_rect.bottom - 28)
        else:
            center = (WIDTH // 2, HEIGHT - 82)

        draw_stroked_text(
            target,
            f"v{APP_VERSION}",
            self.version_font,
            (248, 244, 224),
            (4, 18, 58),
            center,
            stroke_width=2,
        )

    def draw_title_glow(self, target, title_rect, elapsed):
        pulse = 0.5 + 0.5 * math.sin(elapsed * 2.4)
        base_alpha = 70 + round(65 * pulse)

        for index, grow in enumerate((18, 34, 54)):
            glow = pygame.transform.smoothscale(
                self.title_glow_surface,
                (max(8, title_rect.width + grow), title_rect.height + grow),
            )
            glow.set_alpha(max(18, base_alpha - index * 30))
            glow_rect = glow.get_rect(center=title_rect.center)
            target.blit(glow, glow_rect)

    def draw_prompt(self, target, elapsed):
        if elapsed < 1.8 or int(elapsed * 2) % 2 == 0:
            return

        prompt = self.prompt_font.render("Press any key or click to skip", True, (245, 238, 220))
        rect = prompt.get_rect(center=(WIDTH // 2, HEIGHT - 44))
        target.blit(prompt, rect)

    @property
    def finished(self):
        return time.monotonic() - self.started_at >= SPLASH_SECONDS


class ChessGame:
    def __init__(self, enable_engine=True):
        self.board = self.initial_board()
        self.pieces = load_pieces()
        self.small_pieces = {
            key: pygame.transform.smoothscale(
                image,
                (CAPTURED_PIECE_SIZE, CAPTURED_PIECE_SIZE),
            )
            for key, image in self.pieces.items()
        }
        self.font = pygame.font.SysFont('Arial', 20)
        self.small_font = pygame.font.SysFont('Arial', 16)
        self.button_font = pygame.font.SysFont('Arial', 24, bold=True)
        self.label_font = pygame.font.SysFont('Arial', 18, bold=True)
        self.turn_banner_font = pygame.font.SysFont('Arial', 24, bold=True)
        self.square_overlay_font = pygame.font.SysFont('Arial', 22, bold=True)

        self.white_to_move = True
        self.move_log = []
        self.current_move_index = 0
        self.state_history = []
        self.selected_piece = None
        self.valid_moves = []
        self.threats = []
        self.danger_threats = []
        self.attack_threats = []
        self.hover_square = None
        self.hover_control = None
        self.hover_control_started_at = 0.0
        self.show_square_overlay = False
        self.show_hover_empty_square_label = True
        self.chevron_options = {
            'danger_white_turn': True,
            'danger_black_turn': True,
            'attacks_white_turn': False,
            'attacks_black_turn': False,
        }
        self.board_flipped = False
        self.board_theme_name = "Classic"
        self.light_square = BOARD_THEMES[self.board_theme_name]["light"]
        self.dark_square = BOARD_THEMES[self.board_theme_name]["dark"]
        self.preview_move = None
        self.post_move_arrow = None
        self.dragging_piece = False
        self.drag_from = None
        self.drag_piece = None
        self.drag_mouse_pos = None
        self.drag_start_pos = None
        self.drag_has_moved = False
        self.drag_was_selected_same = False
        self.white_king_pos = (7, 4)
        self.black_king_pos = (0, 4)
        self.castling_rights = {'wks': True, 'bks': True, 'wqs': True, 'bqs': True}
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.engine = StockfishEngine.discover() if enable_engine else None
        self.engine_status = "Stockfish ready" if self.engine else "Stockfish not found"
        self.checkmate = False
        self.stalemate = False
        self.in_check = False

        self.control_buttons = {
            'start': pygame.Rect(GAME_LEFT + 26, HEIGHT - 54, 52, 36),
            'prev': pygame.Rect(GAME_LEFT + 86, HEIGHT - 54, 52, 36),
            'next': pygame.Rect(GAME_LEFT + 146, HEIGHT - 54, 52, 36),
            'end': pygame.Rect(GAME_LEFT + 206, HEIGHT - 54, 52, 36),
            'flip': pygame.Rect(GAME_LEFT + 274, HEIGHT - 54, 136, 36),
        }
        self.hover_label_toggle_rect = pygame.Rect(GAME_LEFT + 26, HEIGHT - PANEL_HEIGHT + 76, 18, 18)
        self.chevron_toggle_rects = {
            'danger_white_turn': pygame.Rect(GAME_LEFT + 26, HEIGHT - PANEL_HEIGHT + 100, 18, 18),
            'danger_black_turn': pygame.Rect(GAME_LEFT + 236, HEIGHT - PANEL_HEIGHT + 100, 18, 18),
            'attacks_white_turn': pygame.Rect(GAME_LEFT + 26, HEIGHT - PANEL_HEIGHT + 124, 18, 18),
            'attacks_black_turn': pygame.Rect(GAME_LEFT + 236, HEIGHT - PANEL_HEIGHT + 124, 18, 18),
        }
        self.state_history.append(self.snapshot_state())

    def initial_board(self):
        return [
            ['br', 'bn', 'bb', 'bq', 'bk', 'bb', 'bn', 'br'],
            ['bp', 'bp', 'bp', 'bp', 'bp', 'bp', 'bp', 'bp'],
            ['--', '--', '--', '--', '--', '--', '--', '--'],
            ['--', '--', '--', '--', '--', '--', '--', '--'],
            ['--', '--', '--', '--', '--', '--', '--', '--'],
            ['--', '--', '--', '--', '--', '--', '--', '--'],
            ['wp', 'wp', 'wp', 'wp', 'wp', 'wp', 'wp', 'wp'],
            ['wr', 'wn', 'wb', 'wq', 'wk', 'wb', 'wn', 'wr'],
        ]

    def reset_game(self):
        self.board = self.initial_board()
        self.white_to_move = True
        self.move_log = []
        self.current_move_index = 0
        self.state_history = []
        self.selected_piece = None
        self.valid_moves = []
        self.threats = []
        self.danger_threats = []
        self.attack_threats = []
        self.hover_square = None
        self.preview_move = None
        self.post_move_arrow = None
        self.clear_drag()
        self.white_king_pos = (7, 4)
        self.black_king_pos = (0, 4)
        self.castling_rights = {'wks': True, 'bks': True, 'wqs': True, 'bqs': True}
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.checkmate = False
        self.stalemate = False
        self.in_check = False
        self.state_history.append(self.snapshot_state())
        self.update_threats()

    def set_board_theme(self, theme_name):
        theme = BOARD_THEMES.get(theme_name)
        if not theme:
            return
        self.board_theme_name = theme_name
        self.light_square = theme["light"]
        self.dark_square = theme["dark"]

    def import_game_text(self, text):
        tokens = self.pgn_move_tokens(text)
        if not tokens:
            self.engine_status = "No PGN moves found"
            return False, "No moves found."

        self.reset_game()
        imported = 0
        for token in tokens:
            resolved = self.resolve_import_move(token)
            if not resolved:
                message = f"Stopped at '{token}' after {imported} moves."
                self.engine_status = message
                return False, message

            from_pos, to_pos, promotion = resolved
            self.make_move(from_pos, to_pos, promotion)
            imported += 1

        message = f"Imported {imported} moves."
        self.engine_status = message
        return True, message

    def pgn_move_tokens(self, text):
        text = re.sub(r"\[[^\]]*\]", " ", text)
        text = re.sub(r"\{.*?\}", " ", text, flags=re.DOTALL)
        text = re.sub(r";[^\n]*", " ", text)
        while "(" in text and ")" in text:
            text = re.sub(r"\([^()]*\)", " ", text)

        tokens = []
        for raw_token in text.replace("\n", " ").split():
            token = re.sub(r"^\d+\.(?:\.\.)?", "", raw_token.strip())
            token = token.strip()
            if not token or token.startswith("$"):
                continue
            if token in ("1-0", "0-1", "1/2-1/2", "*"):
                continue
            token = token.rstrip("!?")
            if token:
                tokens.append(token)
        return tokens

    def resolve_import_move(self, token):
        token = token.strip()
        normalized = token.replace("0", "O").rstrip("+#!?")
        color = 'w' if self.white_to_move else 'b'
        king_row = 7 if color == 'w' else 0

        if normalized in ("O-O", "O-O-O"):
            to_col = 6 if normalized == "O-O" else 2
            return (king_row, 4), (king_row, to_col), None

        coordinate = re.fullmatch(r"([a-h][1-8])[-x]?([a-h][1-8])([qrbnQRBN])?", normalized)
        if coordinate:
            from_pos = self.square_to_pos(coordinate.group(1))
            to_pos = self.square_to_pos(coordinate.group(2))
            promotion = coordinate.group(3).lower() if coordinate.group(3) else None
            piece = self.board[from_pos[0]][from_pos[1]]
            if piece != '--' and piece[0] == color:
                if to_pos in self.get_valid_moves(*from_pos) or (piece[1] == 'k' and abs(to_pos[1] - from_pos[1]) == 2):
                    return from_pos, to_pos, promotion
            return None

        return self.resolve_san_move(normalized, color)

    def resolve_san_move(self, san, color):
        promotion = None
        promotion_match = re.search(r"=([QRBNqrbn])", san)
        if promotion_match:
            promotion = promotion_match.group(1).lower()
            san = san[:promotion_match.start()] + san[promotion_match.end():]

        san = san.replace("+", "").replace("#", "").replace("e.p.", "")
        target_match = re.search(r"([a-h][1-8])$", san)
        if not target_match:
            return None

        target_square = target_match.group(1)
        to_pos = self.square_to_pos(target_square)
        prefix = san[:target_match.start()]
        piece_type = 'p'
        if prefix and prefix[0] in "KQRBN":
            piece_type = {'K': 'k', 'Q': 'q', 'R': 'r', 'B': 'b', 'N': 'n'}[prefix[0]]
            prefix = prefix[1:]

        disambiguation = prefix.replace("x", "")
        candidates = []
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.board[row][col]
                if piece == '--' or piece[0] != color or piece[1] != piece_type:
                    continue
                if disambiguation:
                    square = self.pos_to_square(row, col)
                    if len(disambiguation) == 2 and square != disambiguation:
                        continue
                    if len(disambiguation) == 1 and disambiguation not in square:
                        continue
                if to_pos in self.get_valid_moves(row, col):
                    candidates.append(((row, col), to_pos, promotion))

        return candidates[0] if candidates else None

    def export_pgn(self):
        moves = self.move_log[:self.current_move_index]
        headers = [
            '[Event "Chess Cheater Game"]',
            '[Site "?"]',
            f'[Date "{time.strftime("%Y.%m.%d")}"]',
            '[Round "-"]',
            '[White "White"]',
            '[Black "Black"]',
            '[Result "*"]',
        ]
        board = self.initial_board()
        move_parts = []
        for index, move in enumerate(moves):
            if index % 2 == 0:
                move_parts.append(f"{index // 2 + 1}.")
            move_parts.append(self.san_for_export_move(board, move))
            self.apply_export_move(board, move)
        move_parts.append("*")
        return "\n".join(headers) + "\n\n" + " ".join(move_parts) + "\n"

    def san_for_export_move(self, board, move):
        piece = move['piece']
        from_row, from_col = move['from']
        to_row, to_col = move['to']
        to_square = self.pos_to_square(to_row, to_col)
        captured = board[to_row][to_col] != '--' or move.get('captured', '--') != '--'

        if piece[1] == 'k' and abs(to_col - from_col) == 2:
            return "O-O" if to_col > from_col else "O-O-O"

        if piece[1] == 'p':
            notation = ""
            if captured:
                notation += self.pos_to_square(from_row, from_col)[0] + "x"
            notation += to_square
        else:
            piece_letter = {'n': 'N', 'b': 'B', 'r': 'R', 'q': 'Q', 'k': 'K'}[piece[1]]
            notation = piece_letter + self.export_disambiguation(board, move)
            if captured:
                notation += "x"
            notation += to_square

        if move.get('promotion'):
            notation += f"={move['promotion'].upper()}"
        return notation

    def export_disambiguation(self, board, move):
        piece = move['piece']
        from_row, from_col = move['from']
        to_pos = move['to']
        alternatives = []

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if (row, col) == (from_row, from_col):
                    continue
                if board[row][col] != piece:
                    continue
                if to_pos in self.piece_moves_on_board(board, row, col):
                    alternatives.append((row, col))

        if not alternatives:
            return ""

        same_file = any(col == from_col for _, col in alternatives)
        same_rank = any(row == from_row for row, _ in alternatives)
        square = self.pos_to_square(from_row, from_col)
        if not same_file:
            return square[0]
        if not same_rank:
            return square[1]
        return square

    def apply_export_move(self, board, move):
        from_row, from_col = move['from']
        to_row, to_col = move['to']
        moving_piece = board[from_row][from_col]
        board[to_row][to_col] = moving_piece
        board[from_row][from_col] = '--'

        if moving_piece[1] == 'k' and abs(to_col - from_col) == 2:
            rook_from_col = 7 if to_col > from_col else 0
            rook_to_col = 5 if to_col > from_col else 3
            board[to_row][rook_to_col] = board[to_row][rook_from_col]
            board[to_row][rook_from_col] = '--'

        if move.get('promotion'):
            board[to_row][to_col] = moving_piece[0] + move['promotion']

    def piece_moves_on_board(self, board, row, col):
        piece = board[row][col]
        if piece == '--':
            return []

        color, piece_type = piece[0], piece[1]
        moves = []
        if piece_type == 'p':
            direction = 1 if color == 'b' else -1
            if 0 <= row + direction < BOARD_SIZE and board[row + direction][col] == '--':
                moves.append((row + direction, col))
                starting_row = 1 if color == 'b' else 6
                if row == starting_row and board[row + 2 * direction][col] == '--':
                    moves.append((row + 2 * direction, col))
            for dc in (-1, 1):
                capture_row, capture_col = row + direction, col + dc
                if 0 <= capture_row < BOARD_SIZE and 0 <= capture_col < BOARD_SIZE:
                    target = board[capture_row][capture_col]
                    if target != '--' and target[0] != color:
                        moves.append((capture_row, capture_col))

        if piece_type in ('r', 'q'):
            moves.extend(self.sliding_moves_on_board(board, row, col, color, [(-1, 0), (0, 1), (1, 0), (0, -1)]))
        if piece_type in ('b', 'q'):
            moves.extend(self.sliding_moves_on_board(board, row, col, color, [(-1, 1), (1, 1), (1, -1), (-1, -1)]))
        if piece_type == 'n':
            for dr, dc in [(-2, -1), (-2, 1), (-1, 2), (1, 2), (2, 1), (2, -1), (1, -2), (-1, -2)]:
                new_row, new_col = row + dr, col + dc
                if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                    target = board[new_row][new_col]
                    if target == '--' or target[0] != color:
                        moves.append((new_row, new_col))
        if piece_type == 'k':
            for dr, dc in [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)]:
                new_row, new_col = row + dr, col + dc
                if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                    target = board[new_row][new_col]
                    if target == '--' or target[0] != color:
                        moves.append((new_row, new_col))
        return moves

    def sliding_moves_on_board(self, board, row, col, color, directions):
        moves = []
        for dr, dc in directions:
            for step in range(1, BOARD_SIZE):
                new_row, new_col = row + step * dr, col + step * dc
                if not (0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE):
                    break
                target = board[new_row][new_col]
                if target == '--':
                    moves.append((new_row, new_col))
                elif target[0] != color:
                    moves.append((new_row, new_col))
                    break
                else:
                    break
        return moves

    def snapshot_state(self):
        return {
            'board': [row[:] for row in self.board],
            'white_to_move': self.white_to_move,
            'white_king_pos': self.white_king_pos,
            'black_king_pos': self.black_king_pos,
            'castling_rights': self.castling_rights.copy(),
            'halfmove_clock': self.halfmove_clock,
            'fullmove_number': self.fullmove_number,
        }

    def restore_state(self, index):
        state = self.state_history[index]
        self.board = [row[:] for row in state['board']]
        self.white_to_move = state['white_to_move']
        self.white_king_pos = state['white_king_pos']
        self.black_king_pos = state['black_king_pos']
        self.castling_rights = state['castling_rights'].copy()
        self.halfmove_clock = state['halfmove_clock']
        self.fullmove_number = state['fullmove_number']
        self.current_move_index = index
        self.selected_piece = None
        self.valid_moves = []
        self.clear_drag()
        self.stop_preview()
        self.post_move_arrow = None
        self.update_threats()
        self.check_game_state()

    def truncate_future_history(self):
        if self.current_move_index >= len(self.move_log):
            return

        del self.move_log[self.current_move_index:]
        del self.state_history[self.current_move_index + 1:]

    def draw_game_state(self, surface, stockfish_moves=None, opening_choices=None):
        self.draw_turn_banner(surface)
        self.draw_labels(surface)
        self.draw_board(surface)
        self.draw_highlights(surface, stockfish_moves or [], opening_choices)
        self.draw_preview(surface)
        self.draw_square_name_overlay(surface)
        self.draw_dragged_piece(surface)
        self.draw_control_panel(surface)

    def draw_turn_banner(self, surface):
        side_to_move = "White" if self.white_to_move else "Black"
        is_white = self.white_to_move
        rect = pygame.Rect(GAME_LEFT, MENU_HEIGHT, GAME_AREA_WIDTH, TURN_BANNER_HEIGHT)
        pygame.draw.rect(surface, WHITE if is_white else BLACK, rect)
        pygame.draw.rect(surface, BUTTON_BORDER, rect, 1)

        label = f"{side_to_move} to move"
        if self.checkmate:
            label += " - Checkmate"
        elif self.stalemate:
            label += " - Stalemate"
        elif self.in_check:
            label += " - Check"

        draw_text(
            surface,
            label,
            self.turn_banner_font,
            BLACK if is_white else WHITE,
            rect.center,
            'center',
        )

    def board_to_display(self, row, col):
        if self.board_flipped:
            return BOARD_SIZE - 1 - row, BOARD_SIZE - 1 - col
        return row, col

    def display_to_board(self, row, col):
        if self.board_flipped:
            return BOARD_SIZE - 1 - row, BOARD_SIZE - 1 - col
        return row, col

    def square_rect(self, row, col):
        display_row, display_col = self.board_to_display(row, col)
        return pygame.Rect(
            BOARD_LEFT + display_col * SQUARE_SIZE,
            BOARD_TOP + display_row * SQUARE_SIZE,
            SQUARE_SIZE,
            SQUARE_SIZE,
        )

    def square_center(self, row, col):
        rect = self.square_rect(row, col)
        return rect.center

    def create_board_arrow(self, from_pos, to_pos, color, piece_type=None):
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        display_from_row, display_from_col = self.board_to_display(from_row, from_col)
        display_to_row, display_to_col = self.board_to_display(to_row, to_col)
        return create_arrow(
            (display_from_col, display_from_row),
            (display_to_col, display_to_row),
            color,
            piece_type,
        )

    def create_board_chevrons(self, from_pos, to_pos, color, piece_type=None):
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        display_from_row, display_from_col = self.board_to_display(from_row, from_col)
        display_to_row, display_to_col = self.board_to_display(to_row, to_col)
        return create_chevron_line(
            (display_from_col, display_from_row),
            (display_to_col, display_to_row),
            color,
            piece_type,
        )

    def draw_labels(self, surface):
        for display_col in range(BOARD_SIZE):
            _, board_col = self.display_to_board(0, display_col)
            file_name = chr(ord('a') + board_col)
            x = BOARD_LEFT + display_col * SQUARE_SIZE + SQUARE_SIZE // 2
            draw_text(surface, file_name, self.label_font, TEXT_MUTED, (x, BOARD_TOP - 22), 'midtop')
            draw_text(
                surface,
                file_name,
                self.label_font,
                TEXT_MUTED,
                (x, BOARD_TOP + BOARD_PIXELS + 8),
                'midtop',
            )

        for display_row in range(BOARD_SIZE):
            board_row, _ = self.display_to_board(display_row, 0)
            rank_name = str(BOARD_SIZE - board_row)
            y = BOARD_TOP + display_row * SQUARE_SIZE + SQUARE_SIZE // 2
            draw_text(surface, rank_name, self.label_font, TEXT_MUTED, (GAME_LEFT + 12, y), 'midleft')
            draw_text(
                surface,
                rank_name,
                self.label_font,
                TEXT_MUTED,
                (BOARD_LEFT + BOARD_PIXELS + 12, y),
                'midleft',
            )

    def draw_board(self, surface):
        preview_from = None
        preview_to = None
        preview_hide_target = False
        if self.preview_move:
            preview_from = self.preview_move['from']
            preview_to = self.preview_move['to']
            preview_hide_target = self.preview_move.get('hide_target', False)

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                color = self.light_square if (row + col) % 2 == 0 else self.dark_square
                rect = self.square_rect(row, col)
                pygame.draw.rect(surface, color, rect)

                piece = self.board[row][col]
                is_dragged_origin = self.dragging_piece and (row, col) == self.drag_from
                is_preview_origin = (row, col) == preview_from
                is_preview_target = preview_hide_target and (row, col) == preview_to
                if piece != '--' and not is_preview_origin and not is_preview_target and not is_dragged_origin:
                    surface.blit(self.pieces[piece], rect)

    def draw_highlights(self, surface, stockfish_moves, opening_choices=None):
        stockfish_hint_targets = {}
        opening_hint_targets = {}
        opening_mode_selected = opening_choices is not None
        opening_choices = opening_choices or []

        self.draw_previous_move_highlight(surface)

        if self.selected_piece:
            row, col = self.selected_piece
            if opening_mode_selected:
                opening_hint_targets = self.opening_move_hint_targets(opening_choices)
            else:
                stockfish_hint_targets = self.stockfish_move_hint_targets(stockfish_moves)
            highlight = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            highlight.fill((255, 255, 0, 100))
            surface.blit(highlight, self.square_rect(row, col))

            if opening_mode_selected:
                self.draw_stockfish_hint_squares(surface, opening_hint_targets, OPENING_HINT_FILL, OPENING_HINT)
            else:
                self.draw_stockfish_hint_squares(surface, stockfish_hint_targets)

        if self.show_danger_chevrons():
            self.draw_chevron_vectors(surface, self.danger_threats, RED)

        if self.show_attack_chevrons():
            self.draw_chevron_vectors(surface, self.attack_threats, GREEN)

        self.draw_post_move_arrow(surface)

        if self.selected_piece:
            row, col = self.selected_piece
            arrow_moves = self.opening_arrow_moves(opening_choices) if opening_mode_selected else self.valid_moves
            for move in arrow_moves:
                end_row, end_col = move
                selected_piece = self.board[row][col]
                arrow = self.create_board_arrow(
                    self.selected_piece,
                    (end_row, end_col),
                    GREEN,
                    selected_piece[1],
                )
                surface.blit(arrow, (0, 0))

            if opening_mode_selected:
                self.draw_stockfish_hint_badges(surface, opening_hint_targets, OPENING_HINT, OPENING_HINT)
            else:
                self.draw_stockfish_hint_badges(surface, stockfish_hint_targets)

        if self.hover_square:
            row, col = self.square_to_pos(self.hover_square)
            rect = self.square_rect(row, col)
            pygame.draw.rect(surface, (255, 255, 255), rect, 2)

        if self.dragging_piece and self.drag_mouse_pos:
            target = self.pixel_to_board(self.drag_mouse_pos)
            if target and target in self.valid_moves:
                row, col = target
                rect = self.square_rect(row, col)
                pygame.draw.rect(surface, (20, 125, 50), rect, 4)

    def draw_previous_move_highlight(self, surface):
        if self.current_move_index <= 0 or self.current_move_index > len(self.move_log):
            return

        previous_move = self.move_log[self.current_move_index - 1]
        highlights = (
            (previous_move.get('from'), PREVIOUS_MOVE_FROM),
            (previous_move.get('to'), PREVIOUS_MOVE_TO),
        )
        for square, color in highlights:
            if not square:
                continue

            overlay = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            overlay.fill(color)
            surface.blit(overlay, self.square_rect(*square))

    def draw_chevron_vectors(self, surface, vectors, color):
        for from_pos, to_pos in vectors:
            threat_piece = self.board[from_pos[0]][from_pos[1]]
            chevrons = self.create_board_chevrons(
                from_pos,
                to_pos,
                color,
                threat_piece[1] if threat_piece != '--' else None,
            )
            surface.blit(chevrons, (0, 0))

    def show_danger_chevrons(self):
        key = 'danger_white_turn' if self.white_to_move else 'danger_black_turn'
        return self.chevron_options.get(key, False)

    def show_attack_chevrons(self):
        key = 'attacks_white_turn' if self.white_to_move else 'attacks_black_turn'
        return self.chevron_options.get(key, False)

    def draw_square_name_overlay(self, surface):
        if self.show_square_overlay:
            for row in range(BOARD_SIZE):
                for col in range(BOARD_SIZE):
                    self.draw_square_overlay_label(surface, row, col)
            return

        if not self.show_hover_empty_square_label or not self.hover_square:
            return

        row, col = self.square_to_pos(self.hover_square)
        if self.board[row][col] != '--':
            return

        self.draw_square_overlay_label(surface, row, col)

    def draw_square_overlay_label(self, surface, row, col):
        square = self.pos_to_square(row, col)
        center = self.square_center(row, col)
        draw_stroked_text(
            surface,
            square,
            self.square_overlay_font,
            BLACK,
            WHITE,
            center,
            stroke_width=2,
        )

    def stockfish_move_hint_targets(self, stockfish_moves):
        matches_by_target = {}
        selected_square = self.selected_square_name()
        if not selected_square:
            return matches_by_target

        for move in stockfish_moves:
            uci_move = move.get('move', '')
            if len(uci_move) < 4 or uci_move[:2] != selected_square:
                continue

            target_square = uci_move[2:4]
            matches_by_target.setdefault(target_square, []).append(str(move.get('rank', '?')))

        return matches_by_target

    def opening_move_hint_targets(self, opening_choices):
        matches_by_target = {}
        for choice in opening_choices:
            matches_by_target.setdefault(choice['to'], []).append(str(choice['rank']))
        return matches_by_target

    def opening_arrow_moves(self, opening_choices):
        moves = []
        seen = set()
        for choice in opening_choices:
            try:
                to_pos = self.square_to_pos(choice['to'])
            except (IndexError, ValueError):
                continue
            if to_pos in seen or to_pos not in self.valid_moves:
                continue
            moves.append(to_pos)
            seen.add(to_pos)
        return moves

    def draw_stockfish_hint_squares(self, surface, matches_by_target, fill_color=STOCKFISH_HINT_FILL, border_color=STOCKFISH_HINT):
        for target_square, ranks in matches_by_target.items():
            row, col = self.square_to_pos(target_square)
            rect = self.square_rect(row, col)
            overlay = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            overlay.fill(fill_color)
            surface.blit(overlay, rect)
            pygame.draw.rect(surface, border_color, rect, 4)

    def draw_stockfish_hint_badges(self, surface, matches_by_target, text_color=STOCKFISH_HINT, border_color=STOCKFISH_HINT):
        for target_square, ranks in matches_by_target.items():
            row, col = self.square_to_pos(target_square)
            center = self.square_center(row, col)
            label = ",".join(ranks)
            badge_radius = 17 if len(label) <= 2 else 21
            pygame.draw.circle(surface, WHITE, center, badge_radius)
            pygame.draw.circle(surface, border_color, center, badge_radius, 3)
            draw_text(surface, label, self.label_font, text_color, center, 'center')

    def draw_preview(self, surface):
        if not self.preview_move:
            return

        move = self.preview_move
        from_row, from_col = move['from']
        to_row, to_col = move['to']

        for row, col in [move['from'], move['to']]:
            overlay = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            overlay.fill(PREVIEW_BLUE)
            surface.blit(overlay, self.square_rect(row, col))

        elapsed = time.monotonic() - move['started_at']
        if move.get('one_shot') and elapsed >= move['loop_seconds']:
            self.show_post_move_arrow(move)
            self.stop_preview()
            return

        progress = accelerated_preview_progress(
            elapsed,
            move['loop_seconds'],
            move['travel_seconds'],
            move['ease_power'],
        )
        start_rect = self.square_rect(from_row, from_col)
        end_rect = self.square_rect(to_row, to_col)
        start_x = start_rect.x
        start_y = start_rect.y
        end_x = end_rect.x
        end_y = end_rect.y
        x = start_x + (end_x - start_x) * progress
        y = start_y + (end_y - start_y) * progress

        surface.blit(self.pieces[move['piece']], (round(x), round(y)))

    def show_post_move_arrow(self, move):
        self.post_move_arrow = {
            'from': move['from'],
            'to': move['to'],
            'piece': move['piece'],
            'expires_at': time.monotonic() + POST_MOVE_ARROW_SECONDS,
        }

    def draw_post_move_arrow(self, surface):
        if not self.post_move_arrow:
            return

        if time.monotonic() >= self.post_move_arrow['expires_at']:
            self.post_move_arrow = None
            return

        arrow = self.create_board_arrow(
            self.post_move_arrow['from'],
            self.post_move_arrow['to'],
            GREEN,
            self.post_move_arrow['piece'][1],
        )
        surface.blit(arrow, (0, 0))

    def draw_dragged_piece(self, surface):
        if not self.dragging_piece or not self.drag_piece or not self.drag_mouse_pos:
            return

        x, y = self.drag_mouse_pos
        surface.blit(
            self.pieces[self.drag_piece],
            (x - SQUARE_SIZE // 2, y - SQUARE_SIZE // 2),
        )

    def draw_control_panel(self, surface):
        panel_rect = pygame.Rect(GAME_LEFT, HEIGHT - PANEL_HEIGHT, GAME_AREA_WIDTH, PANEL_HEIGHT)
        pygame.draw.rect(surface, PANEL_BG, panel_rect)
        pygame.draw.line(surface, BUTTON_BORDER, panel_rect.topleft, panel_rect.topright, 1)

        status_text = "Status: Ready"
        if self.checkmate:
            status_text = "Status: Checkmate"
        elif self.stalemate:
            status_text = "Status: Stalemate"
        elif self.in_check:
            status_text = "Status: Check"

        draw_text(surface, status_text, self.font, TEXT_MAIN, (GAME_LEFT + 26, HEIGHT - PANEL_HEIGHT + 12))
        draw_text(
            surface,
            f"Move {self.current_move_index} / {len(self.move_log)}",
            self.small_font,
            TEXT_MUTED,
            (GAME_LEFT + 26, HEIGHT - PANEL_HEIGHT + 38),
        )

        hover_text = f"Square: {self.hover_square}" if self.hover_square else "Square: -"
        draw_text(surface, hover_text, self.font, TEXT_MAIN, (GAME_LEFT + GAME_AREA_WIDTH - 182, HEIGHT - PANEL_HEIGHT + 12))
        draw_text(surface, self.engine_status, self.small_font, TEXT_MUTED, (GAME_LEFT + GAME_AREA_WIDTH - 182, HEIGHT - PANEL_HEIGHT + 38))

        self.draw_captured_row(surface, "White took", 'w', HEIGHT - PANEL_HEIGHT + 68)
        self.draw_captured_row(surface, "Black took", 'b', HEIGHT - PANEL_HEIGHT + 100)
        self.draw_checkbox(
            surface,
            self.hover_label_toggle_rect,
            self.show_hover_empty_square_label,
            "Hover labels",
        )
        self.draw_chevron_option_checkboxes(surface)

        self.draw_button(
            surface,
            self.control_buttons['start'],
            "<<",
            self.control_button_enabled('start'),
            hovered=self.hover_control == 'start',
        )
        self.draw_button(
            surface,
            self.control_buttons['prev'],
            "<",
            self.control_button_enabled('prev'),
            hovered=self.hover_control == 'prev',
        )
        self.draw_button(
            surface,
            self.control_buttons['next'],
            ">",
            self.control_button_enabled('next'),
            hovered=self.hover_control == 'next',
        )
        self.draw_button(
            surface,
            self.control_buttons['end'],
            ">>",
            self.control_button_enabled('end'),
            hovered=self.hover_control == 'end',
        )
        self.draw_perspective_button(
            surface,
            self.control_buttons['flip'],
            hovered=self.hover_control == 'flip',
        )

    def draw_perspective_button(self, surface, rect, hovered=False):
        if hovered:
            self.draw_button_hover_glow(surface, rect)

        playing_as_white = not self.board_flipped
        label = "Playing as White" if playing_as_white else "Playing as Black"
        bg = WHITE if playing_as_white else BLACK
        text_color = BLACK if playing_as_white else WHITE
        border = BUTTON_BORDER if playing_as_white else WHITE

        pygame.draw.rect(surface, bg, rect, border_radius=5)
        pygame.draw.rect(surface, border, rect, 2 if hovered else 1, border_radius=5)
        if hovered:
            pygame.draw.rect(surface, border, rect.inflate(-4, -4), 1, border_radius=4)
        draw_text(surface, label, self.small_font, text_color, rect.center, 'center')

    def draw_captured_row(self, surface, label, color, y):
        captured = self.captured_by(color)
        draw_text(surface, label, self.small_font, TEXT_MUTED, (GAME_LEFT + 430, y + 5))

        x = GAME_LEFT + 516
        if not captured:
            draw_text(surface, "-", self.small_font, TEXT_MUTED, (x, y + 5))
            return

        for piece in captured:
            surface.blit(self.small_pieces[piece], (x, y))
            x += CAPTURED_PIECE_SIZE + 4

    def draw_chevron_option_checkboxes(self, surface):
        labels = {
            'danger_white_turn': "Danger on white turn",
            'danger_black_turn': "Danger on black turn",
            'attacks_white_turn': "Attacks on white turn",
            'attacks_black_turn': "Attacks on black turn",
        }
        for key, rect in self.chevron_toggle_rects.items():
            self.draw_checkbox(surface, rect, self.chevron_options[key], labels[key])

    def draw_button(self, surface, rect, text, enabled, selected=False, font=None, hovered=False):
        if hovered and enabled:
            self.draw_button_hover_glow(surface, rect)

        bg = STOCKFISH_HINT_BG if selected else BUTTON_BG
        if hovered and enabled:
            if TEXT_MAIN == BLACK:
                bg = (255, 255, 249) if not selected else (236, 248, 255)
            else:
                bg = (68, 80, 90) if not selected else (47, 78, 110)
        if not enabled:
            bg = BUTTON_DISABLED
        pygame.draw.rect(surface, bg, rect, border_radius=5)
        border = STOCKFISH_HINT if selected or (hovered and enabled) else BUTTON_BORDER
        border_width = 2 if selected or (hovered and enabled) else 1
        pygame.draw.rect(surface, border, rect, border_width, border_radius=5)
        color = STOCKFISH_HINT if selected or (hovered and enabled) else TEXT_MAIN
        if not enabled:
            color = TEXT_MUTED
        draw_text(surface, text, font or self.button_font, color, rect.center, 'center')

    def draw_button_hover_glow(self, surface, rect):
        pulse = hover_pulse(self.hover_control_started_at)
        pad = 7 + round(pulse * 4)
        glow_rect = rect.inflate(pad * 2, pad * 2)
        glow_surface = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
        local_rect = pygame.Rect(pad, pad, rect.width, rect.height)
        for index, inflate in enumerate((10, 6, 2)):
            alpha = max(28, int(92 - index * 24 + pulse * 28))
            color = (*HOVER_GLOW, alpha)
            pygame.draw.rect(
                glow_surface,
                color,
                local_rect.inflate(inflate, inflate),
                2,
                border_radius=9,
            )
        pygame.draw.rect(
            glow_surface,
            (*WHITE, int(44 + pulse * 42)),
            local_rect.inflate(2, 2),
            1,
            border_radius=7,
        )
        surface.blit(glow_surface, glow_rect)

    def draw_checkbox(self, surface, rect, checked, label):
        pygame.draw.rect(surface, BUTTON_BG, rect, border_radius=3)
        pygame.draw.rect(surface, BUTTON_BORDER, rect, 1, border_radius=3)
        if checked:
            pygame.draw.line(surface, STOCKFISH_HINT, (rect.x + 4, rect.centery), (rect.x + 8, rect.bottom - 5), 3)
            pygame.draw.line(surface, STOCKFISH_HINT, (rect.x + 8, rect.bottom - 5), (rect.right - 4, rect.y + 4), 3)
        draw_text(surface, label, self.small_font, TEXT_MUTED, (rect.right + 8, rect.y - 1))

    def handle_mouse_down(self, pos):
        if self.handle_control_click(pos):
            self.clear_drag()
            return

        board_pos = self.pixel_to_board(pos)
        if not board_pos:
            self.clear_drag()
            return

        self.update_hover(pos)
        self.stop_preview()
        row, col = board_pos
        current_color = 'w' if self.white_to_move else 'b'

        if self.board[row][col] != '--' and self.board[row][col][0] == current_color:
            self.drag_was_selected_same = self.selected_piece == board_pos
            self.selected_piece = board_pos
            self.valid_moves = self.get_valid_moves(row, col)
            self.dragging_piece = True
            self.drag_from = board_pos
            self.drag_piece = self.board[row][col]
            self.drag_mouse_pos = pos
            self.drag_start_pos = pos
            self.drag_has_moved = False
        elif self.selected_piece and board_pos in self.valid_moves:
            self.make_move(self.selected_piece, board_pos)
            self.selected_piece = None
            self.valid_moves = []
            self.clear_drag()
        else:
            self.clear_drag()

    def handle_mouse_motion(self, pos):
        self.update_hover(pos)
        if not self.dragging_piece:
            return

        self.drag_mouse_pos = pos
        if not self.drag_start_pos:
            return

        dx = pos[0] - self.drag_start_pos[0]
        dy = pos[1] - self.drag_start_pos[1]
        if dx * dx + dy * dy >= 16:
            self.drag_has_moved = True

    def handle_mouse_up(self, pos):
        if not self.dragging_piece:
            return

        self.update_hover(pos)
        release_square = self.pixel_to_board(pos)
        from_square = self.drag_from
        should_toggle_selection = (
            self.drag_was_selected_same
            and not self.drag_has_moved
            and release_square == from_square
        )

        if release_square and release_square in self.valid_moves:
            self.make_move(from_square, release_square)
            self.selected_piece = None
            self.valid_moves = []
        elif should_toggle_selection:
            self.selected_piece = None
            self.valid_moves = []

        self.clear_drag()

    def clear_drag(self):
        self.dragging_piece = False
        self.drag_from = None
        self.drag_piece = None
        self.drag_mouse_pos = None
        self.drag_start_pos = None
        self.drag_has_moved = False
        self.drag_was_selected_same = False

    def handle_click(self, pos):
        if self.handle_control_click(pos):
            return

        board_pos = self.pixel_to_board(pos)
        if not board_pos:
            return

        self.stop_preview()
        row, col = board_pos
        current_color = 'w' if self.white_to_move else 'b'

        if self.selected_piece == (row, col):
            self.selected_piece = None
            self.valid_moves = []
        elif self.board[row][col] != '--' and self.board[row][col][0] == current_color:
            self.selected_piece = (row, col)
            self.valid_moves = self.get_valid_moves(row, col)
        elif self.selected_piece and (row, col) in self.valid_moves:
            self.make_move(self.selected_piece, (row, col))
            self.selected_piece = None
            self.valid_moves = []

    def handle_control_click(self, pos):
        self.update_control_hover(pos)
        if self.hover_label_toggle_rect.collidepoint(pos):
            self.show_hover_empty_square_label = not self.show_hover_empty_square_label
            return True

        for key, rect in self.chevron_toggle_rects.items():
            if rect.collidepoint(pos):
                self.chevron_options[key] = not self.chevron_options[key]
                return True

        for name, rect in self.control_buttons.items():
            if not rect.collidepoint(pos):
                continue
            if not self.control_button_enabled(name):
                return True

            if name == 'start':
                self.go_to_start()
            elif name == 'prev':
                self.go_prev()
            elif name == 'next':
                self.go_next()
            elif name == 'end':
                self.go_to_end()
            elif name == 'flip':
                self.board_flipped = not self.board_flipped
            return True

        return False

    def control_button_enabled(self, name):
        if name in ('start', 'prev'):
            return self.current_move_index > 0
        if name in ('next', 'end'):
            return self.current_move_index < len(self.move_log)
        if name == 'flip':
            return True
        return False

    def update_control_hover(self, pos):
        hovered = None
        for name, rect in self.control_buttons.items():
            if rect.collidepoint(pos) and self.control_button_enabled(name):
                hovered = name
                break

        if hovered != self.hover_control:
            self.hover_control = hovered
            self.hover_control_started_at = time.monotonic() if hovered else 0.0

    def clear_control_hover(self):
        self.hover_control = None
        self.hover_control_started_at = 0.0

    def update_hover(self, pos):
        self.update_control_hover(pos)
        board_pos = self.pixel_to_board(pos)
        self.hover_square = self.pos_to_square(*board_pos) if board_pos else None

    def go_to_start(self):
        self.restore_state(0)

    def go_prev(self):
        if self.current_move_index > 0:
            self.restore_state(self.current_move_index - 1)

    def go_next(self):
        if self.current_move_index < len(self.move_log):
            self.restore_state(self.current_move_index + 1)

    def go_to_end(self):
        self.restore_state(len(self.move_log))

    def select_piece_for_move_to_square(self, target_square):
        try:
            target_pos = self.square_to_pos(target_square)
        except (IndexError, ValueError):
            return False

        current_color = 'w' if self.white_to_move else 'b'
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.board[row][col]
                if piece == '--' or piece[0] != current_color:
                    continue

                valid_moves = self.get_valid_moves(row, col)
                if target_pos not in valid_moves:
                    continue

                self.stop_preview()
                self.clear_drag()
                self.selected_piece = (row, col)
                self.valid_moves = valid_moves
                return True

        return False

    def make_move(self, from_pos, to_pos, promotion_piece=None):
        self.stop_preview()
        self.post_move_arrow = None
        self.truncate_future_history()

        from_row, from_col = from_pos
        to_row, to_col = to_pos
        moving_piece = self.board[from_row][from_col]
        if moving_piece == '--':
            return

        moving_color = moving_piece[0]
        promotion_piece = promotion_piece.lower() if promotion_piece else None
        is_castling = moving_piece[1] == 'k' and abs(to_col - from_col) == 2
        captured = self.board[to_row][to_col]

        self.move_log.append(
            {
                'piece': moving_piece,
                'from': from_pos,
                'to': to_pos,
                'captured': captured,
                'promotion': promotion_piece,
                'uci': self.positions_to_uci(from_pos, to_pos, promotion_piece),
            }
        )

        if moving_piece == 'wk':
            self.white_king_pos = (to_row, to_col)
        elif moving_piece == 'bk':
            self.black_king_pos = (to_row, to_col)

        if moving_piece == 'wk':
            self.castling_rights['wks'] = False
            self.castling_rights['wqs'] = False
        elif moving_piece == 'bk':
            self.castling_rights['bks'] = False
            self.castling_rights['bqs'] = False
        elif moving_piece == 'wr':
            if from_col == 0:
                self.castling_rights['wqs'] = False
            elif from_col == 7:
                self.castling_rights['wks'] = False
        elif moving_piece == 'br':
            if from_col == 0:
                self.castling_rights['bqs'] = False
            elif from_col == 7:
                self.castling_rights['bks'] = False

        if captured == 'wr' and to_row == 7:
            if to_col == 0:
                self.castling_rights['wqs'] = False
            elif to_col == 7:
                self.castling_rights['wks'] = False
        elif captured == 'br' and to_row == 0:
            if to_col == 0:
                self.castling_rights['bqs'] = False
            elif to_col == 7:
                self.castling_rights['bks'] = False

        self.board[to_row][to_col] = moving_piece
        self.board[from_row][from_col] = '--'

        if is_castling:
            rook_from_col = 7 if to_col > from_col else 0
            rook_to_col = 5 if to_col > from_col else 3
            self.board[to_row][rook_to_col] = self.board[to_row][rook_from_col]
            self.board[to_row][rook_from_col] = '--'

        if moving_piece[1] == 'p' and to_row in (0, BOARD_SIZE - 1):
            self.board[to_row][to_col] = moving_color + (promotion_piece or 'q')

        if moving_piece[1] == 'p' or captured != '--':
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        if moving_color == 'b':
            self.fullmove_number += 1

        self.white_to_move = not self.white_to_move
        self.update_threats()
        self.check_game_state()

        self.current_move_index += 1
        self.state_history.append(self.snapshot_state())

    def make_engine_move(self):
        if not self.engine:
            self.engine_status = "Stockfish not found"
            return

        try:
            best_move = self.engine.best_move(self.to_fen())
        except StockfishError as exc:
            self.engine_status = f"Stockfish error: {exc}"
            return

        if not best_move:
            self.engine_status = "Stockfish found no move"
            return

        self.execute_uci_move_with_animation(best_move)
        self.engine_status = f"Stockfish played {best_move}"

    def make_uci_move(self, uci_move):
        if len(uci_move) < 4:
            raise ValueError(f"Invalid UCI move: {uci_move}")

        from_pos = self.square_to_pos(uci_move[:2])
        to_pos = self.square_to_pos(uci_move[2:4])
        promotion_piece = uci_move[4] if len(uci_move) > 4 else None
        self.make_move(from_pos, to_pos, promotion_piece)

    def execute_uci_move_with_animation(self, uci_move):
        if len(uci_move) < 4:
            raise ValueError(f"Invalid UCI move: {uci_move}")

        from_pos = self.square_to_pos(uci_move[:2])
        to_pos = self.square_to_pos(uci_move[2:4])
        piece = self.board[from_pos[0]][from_pos[1]]
        if piece == '--':
            return

        self.selected_piece = None
        self.valid_moves = []
        self.clear_drag()
        self.make_uci_move(uci_move)
        self.start_move_animation(uci_move, from_pos, to_pos, piece, one_shot=True, hide_target=True)

    def preview_uci_move(self, uci_move):
        if len(uci_move) < 4:
            return

        from_pos = self.square_to_pos(uci_move[:2])
        to_pos = self.square_to_pos(uci_move[2:4])
        piece = self.board[from_pos[0]][from_pos[1]]
        if piece == '--':
            return

        self.selected_piece = from_pos
        self.valid_moves = self.get_valid_moves(*from_pos)
        self.start_move_animation(uci_move, from_pos, to_pos, piece, one_shot=False, hide_target=False)

    def start_move_animation(self, uci_move, from_pos, to_pos, piece, one_shot, hide_target):
        self.post_move_arrow = None
        loop_seconds = EXECUTE_CYCLE_SECONDS if one_shot else PREVIEW_CYCLE_SECONDS
        travel_seconds = EXECUTE_TRAVEL_SECONDS if one_shot else PREVIEW_TRAVEL_SECONDS
        ease_power = EXECUTE_EASE_POWER if one_shot else PREVIEW_EASE_POWER
        self.preview_move = {
            'uci': uci_move,
            'from': from_pos,
            'to': to_pos,
            'piece': piece,
            'started_at': time.monotonic(),
            'loop_seconds': loop_seconds,
            'travel_seconds': travel_seconds,
            'ease_power': ease_power,
            'one_shot': one_shot,
            'hide_target': hide_target,
        }

    def stop_preview(self):
        self.preview_move = None

    def captured_by(self, color):
        captured = []
        for move in self.move_log[:self.current_move_index]:
            if move['piece'][0] == color and move['captured'] != '--':
                captured.append(move['captured'])
        return captured

    def to_fen(self):
        ranks = []

        for row in self.board:
            empty = 0
            fen_rank = ""

            for piece in row:
                if piece == '--':
                    empty += 1
                else:
                    if empty:
                        fen_rank += str(empty)
                        empty = 0
                    fen_rank += PIECE_TO_FEN[piece]

            if empty:
                fen_rank += str(empty)

            ranks.append(fen_rank)

        active_color = 'w' if self.white_to_move else 'b'
        return (
            f"{'/'.join(ranks)} {active_color} {self.castling_fen()} - "
            f"{self.halfmove_clock} {self.fullmove_number}"
        )

    def castling_fen(self):
        rights = ""

        if self.castling_rights['wks'] and self.board[7][4] == 'wk' and self.board[7][7] == 'wr':
            rights += "K"
        if self.castling_rights['wqs'] and self.board[7][4] == 'wk' and self.board[7][0] == 'wr':
            rights += "Q"
        if self.castling_rights['bks'] and self.board[0][4] == 'bk' and self.board[0][7] == 'br':
            rights += "k"
        if self.castling_rights['bqs'] and self.board[0][4] == 'bk' and self.board[0][0] == 'br':
            rights += "q"

        return rights or "-"

    def pixel_to_board(self, pos):
        x, y = pos
        if not (BOARD_LEFT <= x < BOARD_LEFT + BOARD_PIXELS):
            return None
        if not (BOARD_TOP <= y < BOARD_TOP + BOARD_PIXELS):
            return None

        display_col = (x - BOARD_LEFT) // SQUARE_SIZE
        display_row = (y - BOARD_TOP) // SQUARE_SIZE
        return self.display_to_board(display_row, display_col)

    def square_to_pos(self, square):
        col = ord(square[0].lower()) - ord('a')
        row = BOARD_SIZE - int(square[1])
        return row, col

    def pos_to_square(self, row, col):
        return f"{chr(ord('a') + col)}{BOARD_SIZE - row}"

    def positions_to_uci(self, from_pos, to_pos, promotion_piece=None):
        uci = self.pos_to_square(*from_pos) + self.pos_to_square(*to_pos)
        return uci + promotion_piece if promotion_piece else uci

    def selected_square_name(self):
        if not self.selected_piece:
            return None
        return self.pos_to_square(*self.selected_piece)

    def update_threats(self):
        current_color = 'w' if self.white_to_move else 'b'
        opponent_color = 'b' if current_color == 'w' else 'w'
        self.danger_threats = self.capture_vectors(opponent_color, current_color)
        self.attack_threats = self.capture_vectors(current_color, opponent_color)
        self.threats = self.danger_threats

    def capture_vectors(self, attacker_color, target_color):
        vectors = []
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.board[row][col]
                if piece == '--' or piece[0] != attacker_color:
                    continue

                attacking_moves = self.get_piece_moves(row, col, capture_only=True)
                for target_row, target_col in attacking_moves:
                    target_piece = self.board[target_row][target_col]
                    if target_piece != '--' and target_piece[0] == target_color:
                        vectors.append(((row, col), (target_row, target_col)))
        return vectors

    def check_game_state(self):
        # The current move generator is still pseudo-legal; Stockfish integration
        # will sit alongside this until full legal chess state is implemented.
        self.checkmate = False
        self.stalemate = False
        self.in_check = False

    def get_valid_moves(self, row, col):
        return self.get_piece_moves(row, col)

    def get_piece_moves(self, row, col, capture_only=False):
        piece = self.board[row][col]

        if piece == '--':
            return []

        color, piece_type = piece[0], piece[1]
        moves = []

        if piece_type == 'p':
            direction = 1 if color == 'b' else -1

            if not capture_only:
                if 0 <= row + direction < BOARD_SIZE and self.board[row + direction][col] == '--':
                    moves.append((row + direction, col))

                    starting_row = 1 if color == 'b' else 6
                    if row == starting_row and self.board[row + 2 * direction][col] == '--':
                        moves.append((row + 2 * direction, col))

            for dc in [-1, 1]:
                capture_row, capture_col = row + direction, col + dc
                if 0 <= capture_row < BOARD_SIZE and 0 <= capture_col < BOARD_SIZE:
                    target = self.board[capture_row][capture_col]
                    if target != '--' and target[0] != color:
                        moves.append((capture_row, capture_col))

        if piece_type in ['r', 'q']:
            directions = [(-1, 0), (0, 1), (1, 0), (0, -1)]
            for dr, dc in directions:
                for i in range(1, BOARD_SIZE):
                    new_row, new_col = row + i * dr, col + i * dc

                    if not (0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE):
                        break

                    target = self.board[new_row][new_col]
                    if target == '--':
                        if not capture_only:
                            moves.append((new_row, new_col))
                    elif target[0] != color:
                        moves.append((new_row, new_col))
                        break
                    else:
                        break

        if piece_type in ['b', 'q']:
            directions = [(-1, 1), (1, 1), (1, -1), (-1, -1)]
            for dr, dc in directions:
                for i in range(1, BOARD_SIZE):
                    new_row, new_col = row + i * dr, col + i * dc

                    if not (0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE):
                        break

                    target = self.board[new_row][new_col]
                    if target == '--':
                        if not capture_only:
                            moves.append((new_row, new_col))
                    elif target[0] != color:
                        moves.append((new_row, new_col))
                        break
                    else:
                        break

        if piece_type == 'n':
            knight_moves = [
                (-2, -1),
                (-2, 1),
                (-1, -2),
                (-1, 2),
                (1, -2),
                (1, 2),
                (2, -1),
                (2, 1),
            ]
            for dr, dc in knight_moves:
                new_row, new_col = row + dr, col + dc

                if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                    target = self.board[new_row][new_col]
                    if target == '--':
                        if not capture_only:
                            moves.append((new_row, new_col))
                    elif target[0] != color:
                        moves.append((new_row, new_col))

        if piece_type == 'k':
            king_moves = [
                (-1, -1),
                (-1, 0),
                (-1, 1),
                (0, -1),
                (0, 1),
                (1, -1),
                (1, 0),
                (1, 1),
            ]
            for dr, dc in king_moves:
                new_row, new_col = row + dr, col + dc

                if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                    target = self.board[new_row][new_col]
                    if target == '--':
                        if not capture_only:
                            moves.append((new_row, new_col))
                    elif target[0] != color:
                        moves.append((new_row, new_col))

        return moves

    def close(self):
        if self.engine:
            self.engine.close()


def format_move_notation(move):
    from_square = move['uci'][:2] if move.get('uci') else "??"
    to_square = move['uci'][2:4] if move.get('uci') and len(move['uci']) >= 4 else "??"
    separator = "x" if move.get('captured') and move['captured'] != '--' else "-"
    notation = f"{from_square}{separator}{to_square}"
    if move.get('promotion'):
        notation += f"={move['promotion'].upper()}"
    return notation


def format_ordinal(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return str(value)

    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class OpeningLibrary:
    def __init__(self, root):
        self.root = Path(root)
        self.lines = []
        self.load_errors = []

    def load(self, parser_game):
        self.lines = []
        self.load_errors = []

        if not self.root.exists():
            self.load_errors.append(f"Opening folder not found: {self.root}")
            return

        for pgn_path in sorted(self.root.rglob("*.pgn")):
            self.load_pgn(parser_game, pgn_path)

        parser_game.reset_game()

    def load_pgn(self, parser_game, pgn_path):
        try:
            text = pgn_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            self.load_errors.append(f"{pgn_path.name}: {exc}")
            return

        tokens = parser_game.pgn_move_tokens(text)
        if not tokens:
            return

        parser_game.reset_game()
        moves = []
        for token in tokens:
            resolved = parser_game.resolve_import_move(token)
            if not resolved:
                self.load_errors.append(f"{pgn_path.name}: stopped at {token!r}")
                return

            from_pos, to_pos, promotion = resolved
            parser_game.make_move(from_pos, to_pos, promotion)
            moves.append(parser_game.move_log[-1]['uci'])

        if moves:
            self.lines.append(
                {
                    'name': self.opening_name(text, pgn_path),
                    'moves': tuple(moves),
                    'path': self.display_path(pgn_path),
                }
            )

    def opening_name(self, text, pgn_path):
        match = re.search(r'\[Opening\s+"([^"]+)"\]', text)
        if match:
            return match.group(1)

        name = pgn_path.stem
        name = re.sub(r"^\d+_", "", name)
        return name.replace("_", " ").title()

    def display_path(self, pgn_path):
        try:
            return str(pgn_path.relative_to(PROJECT_ROOT))
        except ValueError:
            return str(pgn_path)

    def prefix_for_game(self, game):
        return tuple(move.get('uci', '') for move in game.move_log[:game.current_move_index])

    def matching_lines(self, game):
        prefix = self.prefix_for_game(game)
        return [
            line
            for line in self.lines
            if len(line['moves']) > len(prefix) and line['moves'][:len(prefix)] == prefix
        ]

    def choices_for_game(self, game, selected_square=None):
        prefix = self.prefix_for_game(game)
        prefix_len = len(prefix)
        groups = {}
        ordered_moves = []

        for line in self.lines:
            moves = line['moves']
            if len(moves) <= prefix_len or moves[:prefix_len] != prefix:
                continue

            uci_move = moves[prefix_len]
            if selected_square and not uci_move.startswith(selected_square):
                continue

            if selected_square:
                try:
                    target_pos = game.square_to_pos(uci_move[2:4])
                except (IndexError, ValueError):
                    continue
                if target_pos not in game.valid_moves:
                    continue

            if uci_move not in groups:
                groups[uci_move] = {
                    'rank': len(ordered_moves) + 1,
                    'move': uci_move,
                    'from': uci_move[:2],
                    'to': uci_move[2:4],
                    'openings': [],
                }
                ordered_moves.append(uci_move)

            groups[uci_move]['openings'].append(line)

        return [groups[uci_move] for uci_move in ordered_moves]


class StockfishAnalysisWindow:
    def __init__(self):
        self.panel_rect = pygame.Rect(ANALYSIS_LEFT, MENU_HEIGHT, ANALYSIS_WIDTH, HEIGHT - MENU_HEIGHT)
        self.engine = StockfishEngine.discover()
        self.status = "Stockfish not found"
        self.moves = []
        self.click_rects = []
        self.hovered_item = None
        self.hover_started_at = 0.0
        self.execute_button_rect = pygame.Rect(self.panel_rect.x + 16, self.panel_rect.y + 66, ANALYSIS_WIDTH - 32, 34)
        self.execute_move = None
        self.execute_button_pressed_until = 0
        self.lock = threading.Lock()
        self.worker = None
        self.last_requested_fen = None
        self.pending_fen = None
        self.closed = False
        self.title_font = pygame.font.SysFont('Arial', 22, bold=True)
        self.font = pygame.font.SysFont('Arial', 17)
        self.small_font = pygame.font.SysFont('Arial', 14)
        self.rank_font = pygame.font.SysFont('Arial', 18, bold=True)

        if self.engine:
            self.status = "Waiting for position"

    def contains(self, pos):
        return self.panel_rect.collidepoint(pos)

    def update(self, fen):
        if not self.engine:
            return

        if fen == self.last_requested_fen:
            return

        with self.lock:
            if self.worker and self.worker.is_alive():
                self.pending_fen = fen
                return

        self.start_analysis(fen)

    def start_analysis(self, fen):
        self.last_requested_fen = fen
        with self.lock:
            self.moves = []
            self.execute_move = None
            self.status = "Analyzing"
        self.worker = threading.Thread(target=self._analyze, args=(fen,), daemon=True)
        self.worker.start()

    def _analyze(self, fen):
        try:
            moves = self.engine.analyze_top_moves(fen, multipv=STOCKFISH_MOVE_COUNT, movetime_ms=1200)
            status = "Top moves" if moves else "No moves found"
        except StockfishError as exc:
            moves = []
            status = f"Stockfish error: {exc}"

        with self.lock:
            next_fen = self.pending_fen
            self.pending_fen = None

            if next_fen and next_fen != fen:
                self.status = "Analyzing"
            else:
                self.moves = moves
                self.status = status

        if next_fen and next_fen != fen:
            self.start_analysis(next_fen)

    def get_moves(self):
        with self.lock:
            return [move.copy() for move in self.moves]

    def draw(self, surface, game, selected_square=None, selected_move=None):
        panel = self.panel_rect

        with self.lock:
            moves = list(self.moves)
            status = self.status

        pygame.draw.rect(surface, PANEL_BG, panel)
        pygame.draw.line(surface, BUTTON_BORDER, panel.topleft, panel.bottomleft, 1)
        draw_text(surface, "Stockfish Analysis", self.title_font, TEXT_MAIN, (panel.x + 18, panel.y + 16))
        draw_text(surface, status, self.small_font, TEXT_MUTED, (panel.x + 18, panel.y + 44))

        execute_choice = self.get_execute_choice(moves, selected_move)
        self.execute_move = execute_choice.get('move') if execute_choice else None
        self.draw_execute_button(surface, execute_choice, self.engine is not None and bool(self.execute_move))
        self.click_rects = []

        y = panel.y + 112
        if moves:
            for move in moves[:STOCKFISH_MOVE_COUNT]:
                rect = pygame.Rect(panel.x + 16, y, ANALYSIS_WIDTH - 32, 62)
                uci_move = move.get('move', '')
                is_selected_piece_move = (
                    bool(selected_square)
                    and len(uci_move) >= 4
                    and uci_move[:2] == selected_square
                )
                is_selected_row = bool(selected_move) and uci_move == selected_move
                is_hovered_row = self.hovered_item == uci_move
                row_bg = STOCKFISH_HINT_BG if is_selected_piece_move else BUTTON_BG
                if is_hovered_row:
                    row_bg = (241, 249, 255) if TEXT_MAIN == BLACK else (48, 75, 103)
                row_border = STOCKFISH_HINT if is_selected_piece_move or is_hovered_row else BUTTON_BORDER

                if is_hovered_row:
                    self.draw_hover_glow(surface, rect, emphasis=is_selected_row)
                pygame.draw.rect(surface, row_bg, rect, border_radius=6)
                pygame.draw.rect(surface, row_border, rect, 2 if is_hovered_row else 1, border_radius=6)
                if is_hovered_row:
                    pygame.draw.rect(surface, WHITE, rect.inflate(-5, -5), 1, border_radius=5)
                if is_selected_piece_move:
                    inner_rect = rect.inflate(-4, -4)
                    pygame.draw.rect(surface, STOCKFISH_HINT, inner_rect, 1, border_radius=5)
                if is_selected_row:
                    for inset in (0, 3, 6):
                        pygame.draw.rect(surface, ANALYSIS_SELECTED, rect.inflate(-inset, -inset), 2, border_radius=6)

                move_from = uci_move[:2] if len(uci_move) >= 2 else "??"
                move_to = uci_move[2:4] if len(uci_move) >= 4 else "??"
                move_text = f"{move_from}-{move_to}"
                if move.get('score'):
                    move_text += f"  {move['score']}"
                if move.get('depth'):
                    move_text += f"  d{move['depth']}"

                pv = " ".join(move.get('pv', [])[:6])
                text_color = STOCKFISH_HINT if is_selected_piece_move or is_hovered_row else TEXT_MAIN
                text_x = self.draw_move_piece_icons(surface, game, uci_move, rect, move.get('rank', '?'))
                draw_text(surface, move_text, self.font, text_color, (text_x, rect.y + 9))
                draw_text(surface, pv, self.small_font, TEXT_MUTED, (text_x, rect.y + 34))
                self.click_rects.append((rect, move['move']))
                y += 72
        else:
            message = "No analysis yet"
            if not self.engine:
                message = "Stockfish not found"
            draw_text(surface, message, self.font, TEXT_MUTED, (panel.x + 18, y))

    def handle_click(self, pos):
        self.handle_mouse_motion(pos)
        for rect, move in self.click_rects:
            if rect.collidepoint(pos):
                return move

        if self.engine and self.execute_move and self.execute_button_rect.collidepoint(pos):
            self.execute_button_pressed_until = time.monotonic() + 0.18
            return EXECUTE_BEST_MOVE
        return None

    def handle_mouse_motion(self, pos):
        hovered = None
        if self.engine and self.execute_move and self.execute_button_rect.collidepoint(pos):
            hovered = EXECUTE_BEST_MOVE
        else:
            for rect, move in self.click_rects:
                if rect.collidepoint(pos):
                    hovered = move
                    break

        self.set_hovered_item(hovered)

    def set_hovered_item(self, hovered):
        if hovered == self.hovered_item:
            return
        self.hovered_item = hovered
        self.hover_started_at = time.monotonic() if hovered else 0.0

    def clear_hover(self):
        self.set_hovered_item(None)

    def get_execute_move(self):
        return self.execute_move

    def get_execute_choice(self, moves, selected_move):
        if selected_move:
            for move in moves[:STOCKFISH_MOVE_COUNT]:
                if move.get('move') == selected_move:
                    return move
        return moves[0] if moves else None

    def draw_execute_button(self, surface, execute_choice, enabled):
        pressed = time.monotonic() < self.execute_button_pressed_until
        rect = self.execute_button_rect.move(0, 2 if pressed else 0)
        hovered = enabled and self.hovered_item == EXECUTE_BEST_MOVE
        execute_move = execute_choice.get('move') if execute_choice else None
        if execute_move:
            rank = execute_choice.get('rank', 1)
            rank_label = "best" if rank == 1 or str(rank) == "1" else f"{format_ordinal(rank)} best"
            label = f"Execute {rank_label} move: {execute_move}"
        elif self.engine:
            label = "Execute best move: Analyzing..."
        else:
            label = "Execute best move: unavailable"
        if TEXT_MAIN == BLACK:
            bg = (229, 229, 224) if pressed else (242, 242, 236)
        else:
            bg = (46, 52, 57) if pressed else (57, 63, 68)
        if hovered:
            bg = (255, 255, 249) if TEXT_MAIN == BLACK else (52, 82, 111)
        if not enabled:
            bg = BUTTON_DISABLED
        border = STOCKFISH_HINT if hovered else BUTTON_BORDER
        text_color = TEXT_MAIN if enabled else TEXT_MUTED
        if hovered:
            self.draw_hover_glow(surface, rect, emphasis=True)
        pygame.draw.rect(surface, bg, rect, border_radius=6)
        pygame.draw.rect(surface, border, rect, 2 if hovered else 1, border_radius=6)
        if pressed or hovered:
            pygame.draw.rect(surface, border, rect.inflate(-4, -4), 1, border_radius=4)
        draw_text(surface, label, self.font, text_color, rect.center, 'center')

    def draw_move_piece_icons(self, surface, game, uci_move, rect, rank):
        icon_size = CAPTURED_PIECE_SIZE
        rank_text = f"{rank}."
        rank_rect = draw_text(surface, rank_text, self.rank_font, TEXT_MAIN, (rect.x + 12, rect.centery), 'midleft')
        x = rank_rect.right + 9
        y = rect.y + (rect.height - icon_size) // 2

        moving_piece, captured_piece, from_pos, to_pos = self.move_piece_info(game, uci_move)
        if not moving_piece or moving_piece not in game.small_pieces:
            return x

        self.draw_piece_icon_with_square(surface, game, moving_piece, from_pos, x, y)
        x += icon_size + 8

        if captured_piece and captured_piece in game.small_pieces:
            self.draw_capture_arrow(surface, x, rect.centery)
            x += 28
            self.draw_piece_icon_with_square(surface, game, captured_piece, to_pos, x, y)
            x += icon_size + 10

        return x + 2

    def draw_capture_arrow(self, surface, x, center_y):
        start = (x, center_y)
        end = (x + 20, center_y)
        arrow_color = TEXT_MUTED
        pygame.draw.line(surface, arrow_color, start, end, 2)
        pygame.draw.polygon(
            surface,
            arrow_color,
            [
                (end[0], end[1]),
                (end[0] - 6, end[1] - 4),
                (end[0] - 6, end[1] + 4),
            ],
        )

    def draw_piece_icon_with_square(self, surface, game, piece, board_pos, x, y):
        icon_size = CAPTURED_PIECE_SIZE
        bg_rect = pygame.Rect(x - 2, y - 2, icon_size + 4, icon_size + 4)
        row, col = board_pos
        square_color = game.light_square if (row + col) % 2 == 0 else game.dark_square
        pygame.draw.rect(surface, square_color, bg_rect, border_radius=3)
        pygame.draw.rect(surface, BUTTON_BORDER, bg_rect, 1, border_radius=3)
        surface.blit(game.small_pieces[piece], (x, y))

    def move_piece_info(self, game, uci_move):
        if len(uci_move) < 4:
            return None, None, None, None

        try:
            from_pos = game.square_to_pos(uci_move[:2])
            to_pos = game.square_to_pos(uci_move[2:4])
        except (ValueError, IndexError):
            return None, None, None, None

        from_row, from_col = from_pos
        to_row, to_col = to_pos
        if not (0 <= from_row < BOARD_SIZE and 0 <= from_col < BOARD_SIZE):
            return None, None, None, None
        if not (0 <= to_row < BOARD_SIZE and 0 <= to_col < BOARD_SIZE):
            return None, None, None, None

        moving_piece = game.board[from_row][from_col]
        captured_piece = game.board[to_row][to_col]
        if moving_piece == '--':
            moving_piece = None
        if captured_piece == '--':
            captured_piece = None
        return moving_piece, captured_piece, from_pos, to_pos

    def draw_hover_glow(self, surface, rect, emphasis=False):
        pulse = hover_pulse(self.hover_started_at)
        pad = (8 if emphasis else 6) + round(pulse * 4)
        glow_rect = rect.inflate(pad * 2, pad * 2)
        glow_surface = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
        local_rect = pygame.Rect(pad, pad, rect.width, rect.height)
        pygame.draw.rect(glow_surface, (*HOVER_GLOW_SOFT, 92), local_rect.inflate(pad, pad), border_radius=10)
        for index, inflate in enumerate((pad + 4, max(4, pad - 1), 2)):
            alpha = 110 - index * 28 + round(pulse * 30)
            color = WHITE if index == 2 else HOVER_GLOW
            pygame.draw.rect(
                glow_surface,
                (*color, int(clamp(alpha, 40, 180))),
                local_rect.inflate(inflate, inflate),
                2,
                border_radius=8,
            )
        surface.blit(glow_surface, glow_rect)

    def close(self):
        self.closed = True
        if self.engine:
            self.engine.close()


class OpeningGuidePanel:
    def __init__(self):
        self.panel_rect = pygame.Rect(ANALYSIS_LEFT, MENU_HEIGHT, ANALYSIS_WIDTH, HEIGHT - MENU_HEIGHT)
        self.click_rects = []
        self.hovered_move = None
        self.hover_started_at = 0.0
        self.scroll_offset = 0
        self.max_scroll = 0
        self.last_signature = None
        self.title_font = pygame.font.SysFont('Arial', 22, bold=True)
        self.font = pygame.font.SysFont('Arial', 17)
        self.small_font = pygame.font.SysFont('Arial', 14)
        self.rank_font = pygame.font.SysFont('Arial', 18, bold=True)

    def contains(self, pos):
        return self.panel_rect.collidepoint(pos)

    def draw(self, surface, game, choices, selected_square, matching_line_count, selected_move=None):
        panel = self.panel_rect
        viewport = pygame.Rect(panel.x, panel.y + 88, panel.width, panel.height - 100)
        signature = (
            selected_square,
            game.current_move_index,
            tuple((choice['move'], len(choice['openings'])) for choice in choices),
        )
        if signature != self.last_signature:
            self.scroll_offset = 0
            self.last_signature = signature

        content_height = self.content_height(choices)
        self.max_scroll = max(0, content_height - viewport.height)
        self.scroll_offset = int(clamp(self.scroll_offset, 0, self.max_scroll))

        pygame.draw.rect(surface, PANEL_BG, panel)
        pygame.draw.line(surface, BUTTON_BORDER, panel.topleft, panel.bottomleft, 1)
        draw_text(surface, "Learn Openings", self.title_font, TEXT_MAIN, (panel.x + 18, panel.y + 16))

        selected_label = selected_square or "-"
        selected_line_count = sum(len(choice['openings']) for choice in choices)
        move_group_word = "move group" if len(choices) == 1 else "move groups"
        selected_line_word = "line" if selected_line_count == 1 else "lines"
        matching_line_word = "line" if matching_line_count == 1 else "lines"
        status = f"{selected_label}: {len(choices)} {move_group_word}, {selected_line_count} {selected_line_word}"
        draw_text(surface, status, self.small_font, TEXT_MUTED, (panel.x + 18, panel.y + 44))
        draw_text(
            surface,
            f"Position matches {matching_line_count} opening {matching_line_word}",
            self.small_font,
            TEXT_MUTED,
            (panel.x + 18, panel.y + 64),
        )

        self.click_rects = []
        old_clip = surface.get_clip()
        surface.set_clip(viewport)

        y = viewport.y - self.scroll_offset
        if choices:
            for choice in choices:
                height = self.choice_height(choice)
                rect = pygame.Rect(panel.x + 16, y, ANALYSIS_WIDTH - 32, height)
                if self.is_visible(rect, viewport):
                    self.draw_choice(surface, game, choice, rect, selected_move == choice['move'])
                    self.click_rects.append((rect, choice['move']))
                y += height + 10
        else:
            message = "No openings use this piece from here."
            detail = "Try another piece, or rewind into the opening book."
            draw_text(surface, message, self.font, TEXT_MAIN, (panel.x + 18, y + 6))
            draw_text(surface, detail, self.small_font, TEXT_MUTED, (panel.x + 18, y + 34))

        surface.set_clip(old_clip)
        self.draw_scrollbar(surface, viewport)

    def draw_choice(self, surface, game, choice, rect, selected):
        hovered = self.hovered_move == choice['move']
        if hovered:
            self.draw_hover_glow(surface, rect, emphasis=selected)

        row_bg = OPENING_HINT_BG if TEXT_MAIN == BLACK else (34, 65, 47)
        if hovered:
            row_bg = (236, 255, 242) if TEXT_MAIN == BLACK else (45, 86, 62)

        pygame.draw.rect(surface, row_bg, rect, border_radius=6)
        border = ANALYSIS_SELECTED if selected else (OPENING_HINT if hovered else BUTTON_BORDER)
        pygame.draw.rect(surface, border, rect, 2 if hovered or selected else 1, border_radius=6)
        if selected:
            pygame.draw.rect(surface, ANALYSIS_SELECTED, rect.inflate(-5, -5), 1, border_radius=5)

        badge_center = (rect.x + 24, rect.y + 25)
        self.draw_rank_badge(surface, badge_center, str(choice['rank']))

        move_text = f"{choice['from']}-{choice['to']}"
        piece = game.board[game.square_to_pos(choice['from'])[0]][game.square_to_pos(choice['from'])[1]]
        if piece in game.small_pieces:
            icon_x = rect.x + 50
            icon_y = rect.y + 14
            self.draw_piece_icon_with_square(surface, game, piece, game.square_to_pos(choice['from']), icon_x, icon_y)
            text_x = icon_x + CAPTURED_PIECE_SIZE + 9
        else:
            text_x = rect.x + 50

        draw_text(surface, move_text, self.font, TEXT_MAIN, (text_x, rect.y + 12))
        draw_text(
            surface,
            f"{len(choice['openings'])} opening line{'s' if len(choice['openings']) != 1 else ''}",
            self.small_font,
            TEXT_MUTED,
            (text_x, rect.y + 36),
        )

        opening_y = rect.y + 58
        for line in choice['openings']:
            draw_text(surface, line['name'], self.small_font, TEXT_MAIN, (rect.x + 50, opening_y))
            opening_y += 19

    def draw_piece_icon_with_square(self, surface, game, piece, board_pos, x, y):
        icon_size = CAPTURED_PIECE_SIZE
        bg_rect = pygame.Rect(x - 2, y - 2, icon_size + 4, icon_size + 4)
        row, col = board_pos
        square_color = game.light_square if (row + col) % 2 == 0 else game.dark_square
        pygame.draw.rect(surface, square_color, bg_rect, border_radius=3)
        pygame.draw.rect(surface, BUTTON_BORDER, bg_rect, 1, border_radius=3)
        surface.blit(game.small_pieces[piece], (x, y))

    def draw_rank_badge(self, surface, center, label):
        radius = 16 if len(label) <= 2 else 20
        pygame.draw.circle(surface, WHITE, center, radius)
        pygame.draw.circle(surface, OPENING_HINT, center, radius, 3)
        draw_text(surface, label, self.rank_font, OPENING_HINT, center, 'center')

    def choice_height(self, choice):
        return max(76, 62 + len(choice['openings']) * 19)

    def content_height(self, choices):
        if not choices:
            return 54
        return sum(self.choice_height(choice) + 10 for choice in choices) - 10

    def is_visible(self, rect, viewport):
        return rect.bottom >= viewport.y and rect.y <= viewport.bottom

    def handle_click(self, pos):
        self.handle_mouse_motion(pos)
        for rect, move in self.click_rects:
            if rect.collidepoint(pos):
                return move
        return None

    def handle_mouse_motion(self, pos):
        hovered = None
        for rect, move in self.click_rects:
            if rect.collidepoint(pos):
                hovered = move
                break

        if hovered != self.hovered_move:
            self.hovered_move = hovered
            self.hover_started_at = time.monotonic() if hovered else 0.0

    def clear_hover(self):
        self.hovered_move = None
        self.hover_started_at = 0.0

    def handle_scroll(self, amount):
        self.scroll_offset = int(clamp(self.scroll_offset - amount * 52, 0, self.max_scroll))

    def draw_scrollbar(self, surface, viewport):
        if self.max_scroll <= 0:
            return

        track = pygame.Rect(self.panel_rect.right - 10, viewport.y, 4, viewport.height)
        pygame.draw.rect(surface, BUTTON_BORDER, track, border_radius=2)
        thumb_height = max(34, round(viewport.height * viewport.height / (viewport.height + self.max_scroll)))
        thumb_range = viewport.height - thumb_height
        thumb_y = viewport.y + round((self.scroll_offset / self.max_scroll) * thumb_range)
        thumb = pygame.Rect(track.x - 1, thumb_y, 6, thumb_height)
        pygame.draw.rect(surface, OPENING_HINT, thumb, border_radius=3)

    def draw_hover_glow(self, surface, rect, emphasis=False):
        pulse = hover_pulse(self.hover_started_at)
        pad = (8 if emphasis else 6) + round(pulse * 4)
        glow_rect = rect.inflate(pad * 2, pad * 2)
        glow_surface = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
        local_rect = pygame.Rect(pad, pad, rect.width, rect.height)
        pygame.draw.rect(glow_surface, (*OPENING_HINT, int(58 + pulse * 56)), local_rect.inflate(pad, pad), 2, border_radius=9)
        pygame.draw.rect(glow_surface, (*WHITE, int(38 + pulse * 40)), local_rect.inflate(2, 2), 1, border_radius=7)
        surface.blit(glow_surface, glow_rect)


class NotationWindow:
    def __init__(self):
        self.panel_rect = pygame.Rect(0, MENU_HEIGHT, NOTATION_WIDTH, HEIGHT - MENU_HEIGHT)
        self.closed = False
        self.click_rects = []
        self.hover_index = None
        self.hover_started_at = 0.0
        self.scroll_offset = 0
        self.max_scroll = 0
        self.last_current_move_index = None
        self.last_move_count = None
        self.title_font = pygame.font.SysFont('Arial', 22, bold=True)
        self.font = pygame.font.SysFont('Arial', 18)
        self.small_font = pygame.font.SysFont('Arial', 14)

    def contains(self, pos):
        return self.panel_rect.collidepoint(pos)

    def draw(self, surface, moves, current_move_index):
        panel = self.panel_rect
        viewport = pygame.Rect(panel.x, panel.y + 76, panel.width, panel.height - 88)
        content_height = self.content_height(moves)
        self.max_scroll = max(0, content_height - viewport.height)

        if (
            current_move_index != self.last_current_move_index
            or len(moves) != self.last_move_count
        ):
            self.ensure_move_visible(current_move_index, viewport.height)
            self.last_current_move_index = current_move_index
            self.last_move_count = len(moves)

        self.scroll_offset = int(clamp(self.scroll_offset, 0, self.max_scroll))

        pygame.draw.rect(surface, PANEL_BG, panel)
        pygame.draw.line(surface, BUTTON_BORDER, panel.topright, panel.bottomright, 1)
        draw_text(surface, "Game Notation", self.title_font, TEXT_MAIN, (panel.x + 18, panel.y + 16))
        draw_text(
            surface,
            f"Current turn: {current_move_index} / {len(moves)}",
            self.small_font,
            TEXT_MUTED,
            (panel.x + 18, panel.y + 44),
        )

        self.click_rects = []
        old_clip = surface.get_clip()
        surface.set_clip(viewport)

        start_y = viewport.y - self.scroll_offset
        if self.is_visible(start_y, 34, viewport):
            start_rect = self._draw_start_row(surface, start_y, current_move_index == 0)
            self.click_rects.append((start_rect, 0))

        if not moves:
            draw_text(surface, "No moves yet", self.font, TEXT_MUTED, (panel.x + 18, start_y + 44))
            surface.set_clip(old_clip)
            self.draw_scrollbar(surface, viewport)
            return

        for pair_index in range(0, len(moves), 2):
            move_number = pair_index // 2 + 1
            white_move = moves[pair_index]
            black_move = moves[pair_index + 1] if pair_index + 1 < len(moves) else None
            y = viewport.y + self.row_logical_y(pair_index) - self.scroll_offset
            if not self.is_visible(y, 40, viewport):
                continue

            row_rect = pygame.Rect(panel.x + 16, y, NOTATION_WIDTH - 32, 40)
            pygame.draw.rect(surface, BUTTON_BG, row_rect, border_radius=6)

            draw_text(surface, f"{move_number}.", self.font, TEXT_MUTED, (row_rect.x + 10, row_rect.y + 10))
            white_index = pair_index + 1
            white_rect = self._draw_move_cell(
                surface,
                row_rect.x + 58,
                row_rect.y + 5,
                132,
                format_move_notation(white_move),
                current_move_index == white_index,
                self.hover_index == white_index,
            )
            self.click_rects.append((white_rect, white_index))
            if black_move:
                black_index = pair_index + 2
                black_rect = self._draw_move_cell(
                    surface,
                    row_rect.x + 210,
                    row_rect.y + 5,
                    132,
                    format_move_notation(black_move),
                    current_move_index == black_index,
                    self.hover_index == black_index,
                )
                self.click_rects.append((black_rect, black_index))

            pygame.draw.rect(surface, BUTTON_BORDER, row_rect, 1, border_radius=6)

        surface.set_clip(old_clip)
        self.draw_scrollbar(surface, viewport)

    def _draw_start_row(self, surface, y, selected):
        rect = pygame.Rect(self.panel_rect.x + 16, y, NOTATION_WIDTH - 32, 34)
        hovered = self.hover_index == 0
        if hovered:
            self.draw_hover_glow(surface, rect)
        pygame.draw.rect(surface, STOCKFISH_HINT_BG if selected else BUTTON_BG, rect, border_radius=6)
        pygame.draw.rect(surface, ANALYSIS_SELECTED if selected else (STOCKFISH_HINT if hovered else BUTTON_BORDER), rect, 1, border_radius=6)
        if selected:
            pygame.draw.rect(surface, ANALYSIS_SELECTED, rect.inflate(-4, -4), 1, border_radius=4)
        draw_text(surface, "Start position", self.font, TEXT_MAIN, (rect.x + 12, rect.y + 8))
        return rect

    def _draw_move_cell(self, surface, x, y, width, text, selected, hovered):
        rect = pygame.Rect(x, y, width, 30)
        if hovered:
            self.draw_hover_glow(surface, rect)
            pygame.draw.rect(surface, STOCKFISH_HINT_BG, rect, border_radius=5)
        if selected:
            pygame.draw.rect(surface, STOCKFISH_HINT_BG, rect, border_radius=5)
            for inset in (0, 3):
                pygame.draw.rect(surface, ANALYSIS_SELECTED, rect.inflate(-inset, -inset), 1, border_radius=5)
        elif hovered:
            pygame.draw.rect(surface, STOCKFISH_HINT, rect, 1, border_radius=5)
        draw_text(surface, text, self.font, TEXT_MAIN, (rect.x + 8, rect.y + 6))
        return rect

    def content_height(self, moves):
        pair_count = (len(moves) + 1) // 2
        return 40 + pair_count * 46

    def row_logical_y(self, pair_index):
        return 40 + (pair_index // 2) * 46

    def is_visible(self, y, height, viewport):
        return y + height >= viewport.y and y <= viewport.bottom

    def move_logical_span(self, move_index):
        if move_index <= 0:
            return 0, 34
        pair_index = ((move_index - 1) // 2) * 2
        y = self.row_logical_y(pair_index)
        return y, y + 40

    def ensure_move_visible(self, move_index, viewport_height):
        top, bottom = self.move_logical_span(move_index)
        padding = 10
        if top < self.scroll_offset + padding:
            self.scroll_offset = top - padding
        elif bottom > self.scroll_offset + viewport_height - padding:
            self.scroll_offset = bottom - viewport_height + padding
        self.scroll_offset = int(clamp(self.scroll_offset, 0, self.max_scroll))

    def handle_click(self, pos):
        for rect, move_index in self.click_rects:
            if rect.collidepoint(pos):
                return move_index
        return None

    def handle_mouse_motion(self, pos):
        hovered = None
        for rect, move_index in self.click_rects:
            if rect.collidepoint(pos):
                hovered = move_index
                break

        if hovered != self.hover_index:
            self.hover_index = hovered
            self.hover_started_at = time.monotonic() if hovered is not None else 0.0

    def clear_hover(self):
        self.hover_index = None
        self.hover_started_at = 0.0

    def handle_scroll(self, amount):
        self.scroll_offset = int(clamp(self.scroll_offset - amount * 46, 0, self.max_scroll))

    def draw_scrollbar(self, surface, viewport):
        if self.max_scroll <= 0:
            return

        track = pygame.Rect(self.panel_rect.right - 10, viewport.y, 4, viewport.height)
        pygame.draw.rect(surface, BUTTON_BORDER, track, border_radius=2)
        thumb_height = max(34, round(viewport.height * viewport.height / (viewport.height + self.max_scroll)))
        thumb_range = viewport.height - thumb_height
        thumb_y = viewport.y + round((self.scroll_offset / self.max_scroll) * thumb_range)
        thumb = pygame.Rect(track.x - 1, thumb_y, 6, thumb_height)
        pygame.draw.rect(surface, STOCKFISH_HINT, thumb, border_radius=3)

    def draw_hover_glow(self, surface, rect):
        pulse = hover_pulse(self.hover_started_at)
        glow_rect = rect.inflate(10, 10)
        glow_surface = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
        local_rect = pygame.Rect(5, 5, rect.width, rect.height)
        pygame.draw.rect(
            glow_surface,
            (*HOVER_GLOW, int(58 + pulse * 54)),
            local_rect.inflate(4, 4),
            2,
            border_radius=6,
        )
        surface.blit(glow_surface, glow_rect)

    def close(self):
        self.closed = True


def run_splash_screen():
    splash = SplashScreen()

    while not splash.finished:
        for event in pygame.event.get():
            if event.type in (QUIT, WINDOWCLOSE):
                return False
            if event.type in (KEYDOWN, MOUSEBUTTONDOWN):
                return True

        splash.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)

    return True


def main():
    if not run_splash_screen():
        pygame.quit()
        sys.exit()

    apply_ui_theme("Dark")
    game = ChessGame()
    opening_parser = ChessGame(enable_engine=False)
    opening_library = OpeningLibrary(OPENINGS_ROOT)
    opening_library.load(opening_parser)
    opening_parser.close()
    analysis_window = StockfishAnalysisWindow()
    opening_panel = OpeningGuidePanel()
    notation_window = NotationWindow()
    menu = AppMenu()
    modal = None
    ui_theme_name = "Dark"
    learn_opening_mode = False

    def ensure_learn_opening_start_selection():
        if learn_opening_mode and game.current_move_index == 0 and game.selected_piece is None:
            game.select_piece_for_move_to_square("d4")

    running = True
    while running:
        game.show_square_overlay = bool(pygame.key.get_mods() & KMOD_CTRL)
        opening_panel_active = lambda: learn_opening_mode and game.selected_piece is not None
        fen = game.to_fen()
        analysis_window.update(fen)

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == WINDOWCLOSE:
                running = False
            elif modal:
                result = modal.handle_event(event)
                if not result:
                    continue

                action, value = result
                if action == "cancel":
                    modal = None
                    continue

                try:
                    if action == "import_path":
                        path = resolve_user_path(value)
                        content = path.read_text(encoding="utf-8", errors="ignore")
                        _, message = game.import_game_text(content)
                        game.engine_status = message
                        modal = None
                    elif action == "export_path":
                        path = resolve_user_path(value)
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(game.export_pgn(), encoding="utf-8")
                        game.engine_status = f"Exported {path.name}"
                        modal = None
                    elif action == "paste_game":
                        _, message = game.import_game_text(value)
                        game.engine_status = message
                        modal = None
                except OSError as exc:
                    modal.message = str(exc)
            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                action = menu.handle_click(event.pos)
                if action:
                    if action == "import_path":
                        path, message = choose_import_pgn_path()
                        if message:
                            game.engine_status = message
                        elif path:
                            try:
                                content = path.read_text(encoding="utf-8", errors="ignore")
                                _, message = game.import_game_text(content)
                                game.engine_status = f"{message}: {path.name}"
                            except OSError as exc:
                                game.engine_status = str(exc)
                    elif action == "export_path":
                        modal = TextModal(
                            "Export PGN File",
                            "Enter a destination path for standard PGN export.",
                            "export_path",
                            "game_export.pgn",
                        )
                    elif action == "paste_game":
                        modal = TextModal(
                            "Paste PGN",
                            "Paste PGN/SAN or coordinate moves. Press Ctrl+Enter to import.",
                            "paste_game",
                            "",
                            multiline=True,
                        )
                    elif action == "exit":
                        running = False
                    elif action.startswith("theme:"):
                        ui_theme_name = action.split(":", 1)[1]
                        apply_ui_theme(ui_theme_name)
                    elif action.startswith("board:"):
                        game.set_board_theme(action.split(":", 1)[1])
                    elif action == "learn_openings":
                        learn_opening_mode = not learn_opening_mode
                        opening_panel.clear_hover()
                        ensure_learn_opening_start_selection()
                    continue

                if opening_panel_active() and opening_panel.contains(event.pos):
                    move = opening_panel.handle_click(event.pos)
                    if move:
                        game.preview_uci_move(move)
                    game.clear_drag()
                    game.clear_control_hover()
                    analysis_window.clear_hover()
                    notation_window.clear_hover()
                elif analysis_window.contains(event.pos):
                    move = analysis_window.handle_click(event.pos)
                    if move == EXECUTE_BEST_MOVE:
                        best_move = analysis_window.get_execute_move()
                        if best_move:
                            game.execute_uci_move_with_animation(best_move)
                            game.engine_status = f"Stockfish played {best_move}"
                    elif move:
                        game.preview_uci_move(move)
                elif notation_window.contains(event.pos):
                    move_index = notation_window.handle_click(event.pos)
                    if move_index is not None:
                        game.restore_state(move_index)
                    game.clear_drag()
                    game.clear_control_hover()
                    analysis_window.clear_hover()
                    opening_panel.clear_hover()
                else:
                    analysis_window.clear_hover()
                    opening_panel.clear_hover()
                    game.handle_mouse_down(event.pos)
            elif event.type == MOUSEBUTTONUP and event.button == 1:
                if (
                    (opening_panel_active() and opening_panel.contains(event.pos))
                    or analysis_window.contains(event.pos)
                    or notation_window.contains(event.pos)
                ):
                    game.clear_drag()
                else:
                    game.handle_mouse_up(event.pos)
            elif event.type == MOUSEMOTION:
                menu.handle_mouse_motion(event.pos)
                if opening_panel_active() and opening_panel.contains(event.pos):
                    game.hover_square = None
                    game.clear_control_hover()
                    notation_window.clear_hover()
                    analysis_window.clear_hover()
                    opening_panel.handle_mouse_motion(event.pos)
                elif analysis_window.contains(event.pos):
                    game.hover_square = None
                    game.clear_control_hover()
                    notation_window.clear_hover()
                    opening_panel.clear_hover()
                    analysis_window.handle_mouse_motion(event.pos)
                elif notation_window.contains(event.pos) or event.pos[1] < MENU_HEIGHT:
                    game.hover_square = None
                    game.clear_control_hover()
                    analysis_window.clear_hover()
                    opening_panel.clear_hover()
                    if notation_window.contains(event.pos):
                        notation_window.handle_mouse_motion(event.pos)
                    else:
                        notation_window.clear_hover()
                else:
                    analysis_window.clear_hover()
                    opening_panel.clear_hover()
                    notation_window.clear_hover()
                    game.handle_mouse_motion(event.pos)
            elif event.type == MOUSEWHEEL:
                mouse_pos = pygame.mouse.get_pos()
                if opening_panel_active() and opening_panel.contains(mouse_pos):
                    opening_panel.handle_scroll(event.y)
                elif notation_window.contains(mouse_pos):
                    notation_window.handle_scroll(event.y)
            elif event.type == KEYDOWN:
                if event.key == K_e:
                    game.make_engine_move()
                elif event.key == K_LEFT:
                    game.go_prev()
                elif event.key == K_RIGHT:
                    game.go_next()
                elif event.key == K_HOME:
                    game.go_to_start()
                elif event.key == K_END:
                    game.go_to_end()

        ensure_learn_opening_start_selection()

        screen.fill(UI_BG)
        stockfish_moves = analysis_window.get_moves()
        selected_square = game.selected_square_name()
        selected_analysis_move = game.preview_move['uci'] if game.preview_move else None
        show_opening_panel = learn_opening_mode and bool(selected_square)
        opening_choices = (
            opening_library.choices_for_game(game, selected_square)
            if show_opening_panel
            else None
        )
        matching_opening_lines = len(opening_library.matching_lines(game)) if show_opening_panel else 0
        notation_window.draw(screen, game.move_log, game.current_move_index)
        game.draw_game_state(screen, stockfish_moves, opening_choices)
        if show_opening_panel:
            opening_panel.draw(
                screen,
                game,
                opening_choices or [],
                selected_square,
                matching_opening_lines,
                selected_analysis_move,
            )
        else:
            analysis_window.draw(screen, game, selected_square, selected_analysis_move)
        menu.draw(screen, ui_theme_name, game.board_theme_name, learn_opening_mode)
        if modal:
            modal.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    analysis_window.close()
    notation_window.close()
    game.close()
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
