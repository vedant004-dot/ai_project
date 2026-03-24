"""
Checkers AI — Single-File Game
================================
Run:  python main.py

Difficulty maps directly to AI algorithm:
  Easy   → Random move  (O(b) time, O(1) space)
  Medium → Minimax d=3  (O(b^d) time, O(d) space)
  Hard   → Alpha-Beta d=5 + Dynamic Heuristic (O(b^d/2) best, O(d) space)
"""

import pygame
import sys
import random
from enum import Enum

# ══════════════════════════════════════════════════════════════
#  LAYOUT CONSTANTS
# ══════════════════════════════════════════════════════════════
ROWS, COLS    = 8, 8
SQUARE_SIZE   = 88               # each square in px
BOARD_PX      = COLS * SQUARE_SIZE    # 704  — board pixel width
LOG_W         = 218              # move-log panel width
WIDTH         = BOARD_PX + LOG_W      # 922
HEIGHT        = 920              # total window height
UI_HEIGHT     = 110              # in-game top header height
BOARD_Y       = UI_HEIGHT        # board starts here
BUTTON_H      = 52

# ══════════════════════════════════════════════════════════════
#  COLOUR PALETTE
# ══════════════════════════════════════════════════════════════
BG_DARK        = ( 16,  20,  34)
PANEL_DARK     = ( 24,  30,  50)
PANEL_MID      = ( 32,  40,  65)
SEPARATOR      = ( 65,  78, 118)

BOARD_LIGHT    = (234, 213, 178)
BOARD_DARK     = ( 97,  58,  22)

PIECE_RED      = (205,  50,  50)
PIECE_RED_D    = (140,  18,  18)
PIECE_BLUE     = ( 50, 115, 200)
PIECE_BLUE_D   = ( 25,  65, 145)

GOLD           = (212, 175,  55)
GREEN_SOFT     = (100, 220, 130)
SELECTED_RING  = (255, 220,  60)
HIGHLIGHT_DOT  = (100, 220, 130)

WHITE          = (255, 255, 255)
TEXT_LIGHT     = (200, 212, 238)
TEXT_DIM       = (120, 135, 165)
TEXT_YOU       = (100, 215, 125)   # green — human moves in log
TEXT_AI        = (210, 100, 100)   # red   — AI moves in log

BTN_START      = ( 60, 120, 175)
BTN_START_H    = ( 90, 155, 210)
BTN_EASY       = ( 30, 128,  30)
BTN_EASY_H     = ( 50, 165,  50)
BTN_MEDIUM     = ( 28,  88, 175)
BTN_MEDIUM_H   = ( 48, 118, 210)
BTN_HARD       = (155,  28,  28)
BTN_HARD_H     = (195,  48,  48)
BTN_NEUTRAL    = ( 45,  58,  88)
BTN_NEUTRAL_H  = ( 65,  82, 120)
BTN_END_RED    = (120,  30,  30)
BTN_END_RED_H  = (170,  48,  48)

# ══════════════════════════════════════════════════════════════
#  PYGAME INIT
# ══════════════════════════════════════════════════════════════
pygame.init()
pygame.font.init()
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Checkers AI")

FNT_TITLE  = pygame.font.Font(None, 52)
FNT_LARGE  = pygame.font.Font(None, 38)
FNT_MED    = pygame.font.Font(None, 28)
FNT_SM     = pygame.font.Font(None, 22)
FNT_XS     = pygame.font.Font(None, 18)

# ══════════════════════════════════════════════════════════════
#  ENUMS
# ══════════════════════════════════════════════════════════════
class GameState(Enum):
    MENU             = 1
    DIFF_SELECT      = 2
    PLAYING          = 3
    GAME_OVER        = 4   # 2-second auto-transition
    ANALYSIS         = 5   # post-game full-screen analysis

class Difficulty(Enum):
    EASY   = 1
    MEDIUM = 2
    HARD   = 3

# ══════════════════════════════════════════════════════════════
#  COMPLEXITY DATA (per difficulty)
# ══════════════════════════════════════════════════════════════
LEVEL_INFO = {
    Difficulty.EASY: {
        "label":       "Random Move",
        "algorithm":   "Random Selection",
        "eval_fn":     "None  (no evaluation)",
        "time_best":   "O(b)       b ≈ 7 legal moves",
        "time_worst":  "O(b)       always one pass",
        "space":       "O(1)       constant — no recursion",
        "note":        "No look-ahead. Picks uniformly at random.",
        "color":       BTN_EASY,
    },
    Difficulty.MEDIUM: {
        "label":       "Minimax  (depth 3)",
        "algorithm":   "Minimax  d = 3",
        "eval_fn":     "Positional  (material + advancement + edge)",
        "time_best":   "O(b^d) = O(7³) ≈ 343 nodes",
        "time_worst":  "O(b^d) = O(7³) ≈ 343 nodes  (no pruning)",
        "space":       "O(d)   = O(3)  recursive call stack",
        "note":        "Exhaustive search — no Alpha-Beta cutoffs.",
        "color":       BTN_MEDIUM,
    },
    Difficulty.HARD: {
        "label":       "Alpha-Beta  (depth 5)  + Dynamic Heuristic",
        "algorithm":   "Alpha-Beta Pruning  d = 5",
        "eval_fn":     "Dynamic  (phase-aware: opening / midgame / endgame)",
        "time_best":   "O(b^(d/2)) = O(7^2.5) ≈ 130 nodes  (perfect order)",
        "time_worst":  "O(b^d)     = O(7^5) ≈ 16 807 nodes",
        "space":       "O(d)       = O(5)   recursive call stack",
        "note":        "Pruning skips unpromising branches; adaptive weights.",
        "color":       BTN_HARD,
    },
}

# ══════════════════════════════════════════════════════════════
#  GLOBALS
# ══════════════════════════════════════════════════════════════
game_state         = GameState.MENU
current_difficulty = None
board              = None
selected_piece     = None
valid_moves        = []
player_turn        = True
game_over          = False
winner             = None
ai_thinking        = False
human_captured     = 0
ai_captured        = 0
moves_count        = 0
move_log           = []    # list of strings: "YOU: A6→B5", "AI: C3→D4" …
game_over_tick     = 0     # pygame tick when game ended (for auto-transition)
GAME_OVER_DELAY    = 1800  # ms before auto-switching to ANALYSIS


# ══════════════════════════════════════════════════════════════
#  NOTATION HELPERS
# ══════════════════════════════════════════════════════════════
def sq(r, c):
    """Convert (row, col) → 'A1'-style label. Cols = A…H,  Rows = 1…8 (top=1)."""
    return f"{chr(65 + c)}{r + 1}"

def log_move(who, fr, fc, tr, tc, capture=False):
    """Append a move to the live move log."""
    suffix = " ✕" if capture else ""
    move_log.append(f"{who}: {sq(fr,fc)}→{sq(tr,tc)}{suffix}")


# ══════════════════════════════════════════════════════════════
#  BOARD INIT
# ══════════════════════════════════════════════════════════════
def initialize_board():
    global board, selected_piece, valid_moves, player_turn
    global game_over, winner, human_captured, ai_captured, moves_count
    global move_log, game_over_tick

    board = [
        [0,  1, 0,  1, 0,  1, 0,  1],
        [1,  0, 1,  0, 1,  0, 1,  0],
        [0,  1, 0,  1, 0,  1, 0,  1],
        [0,  0, 0,  0, 0,  0, 0,  0],
        [0,  0, 0,  0, 0,  0, 0,  0],
        [-1, 0, -1, 0, -1, 0, -1, 0],
        [0, -1, 0, -1, 0, -1, 0, -1],
        [-1, 0, -1, 0, -1, 0, -1, 0],
    ]
    selected_piece = None
    valid_moves    = []
    player_turn    = True
    game_over      = False
    winner         = None
    human_captured = 0
    ai_captured    = 0
    moves_count    = 0
    move_log       = []
    game_over_tick = 0


# ══════════════════════════════════════════════════════════════
#  BUTTON CLASS
# ══════════════════════════════════════════════════════════════
class Button:
    def __init__(self, x, y, w, h, text, color, hover_color, sub=""):
        self.rect    = pygame.Rect(x, y, w, h)
        self.text    = text
        self.color   = color
        self.hcolor  = hover_color
        self.sub     = sub
        self.hovered = False

    def update_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

    def draw(self, surf):
        c = self.hcolor if self.hovered else self.color
        pygame.draw.rect(surf, c, self.rect, border_radius=10)
        border = tuple(min(v + 55, 255) for v in c)
        pygame.draw.rect(surf, border, self.rect, 2, border_radius=10)

        if self.sub:
            t = FNT_SM.render(self.text, True, WHITE)
            surf.blit(t, t.get_rect(center=(self.rect.centerx, self.rect.centery - 7)))
            s = FNT_XS.render(self.sub, True, TEXT_DIM)
            surf.blit(s, s.get_rect(center=(self.rect.centerx, self.rect.centery + 13)))
        else:
            t = FNT_SM.render(self.text, True, WHITE)
            surf.blit(t, t.get_rect(center=self.rect.center))


# ══════════════════════════════════════════════════════════════
#  DRAW — MENU
# ══════════════════════════════════════════════════════════════
def draw_menu(start_btn):
    WIN.fill(BG_DARK)
    # top gradient stripe
    pygame.draw.rect(WIN, PANEL_DARK, (0, 0, WIDTH, 200))
    pygame.draw.line(WIN, SEPARATOR, (0, 200), (WIDTH, 200), 2)

    t = FNT_TITLE.render("CHECKERS  AI", True, GOLD)
    WIN.blit(t, t.get_rect(center=(WIDTH // 2, 80)))
    s = FNT_SM.render("Classic strategy — challenge the machine", True, TEXT_DIM)
    WIN.blit(s, s.get_rect(center=(WIDTH // 2, 140)))

    feature_lines = [
        "▸  Easy → Random Move   |   Medium → Minimax (depth 3)   |   Hard → Alpha-Beta (depth 5)",
        "▸  Forced-capture rule  •  King promotion  •  Multi-jump  •  Live move log",
        "▸  Post-game analysis: algorithm, time & space complexity, full stats",
    ]
    for i, line in enumerate(feature_lines):
        ls = FNT_XS.render(line, True, TEXT_DIM)
        WIN.blit(ls, ls.get_rect(center=(WIDTH // 2, 250 + i * 28)))

    start_btn.draw(WIN)
    foot = FNT_XS.render("ESC — back to menu at any time", True, TEXT_DIM)
    WIN.blit(foot, foot.get_rect(center=(WIDTH // 2, HEIGHT - 18)))
    pygame.display.update()


# ══════════════════════════════════════════════════════════════
#  DRAW — DIFFICULTY SELECT
# ══════════════════════════════════════════════════════════════
def draw_diff_select(btns):
    WIN.fill(BG_DARK)
    pygame.draw.rect(WIN, PANEL_DARK, (0, 0, WIDTH, 130))
    pygame.draw.line(WIN, SEPARATOR, (0, 130), (WIDTH, 130), 2)
    t = FNT_TITLE.render("SELECT  DIFFICULTY", True, GOLD)
    WIN.blit(t, t.get_rect(center=(WIDTH // 2, 65)))

    # Info cards
    card_data = [
        (Difficulty.EASY,   BTN_EASY,   "Random Move",
         "AI picks any legal move at random — perfect for beginners."),
        (Difficulty.MEDIUM, BTN_MEDIUM, "Minimax  (depth 3)",
         "AI looks 3 moves ahead — moderate challenge."),
        (Difficulty.HARD,   BTN_HARD,   "Alpha-Beta + Dynamic heuristic  (depth 5)",
         "Deep pruned search with phase-aware evaluation — expert."),
    ]
    cy = 155
    for _, col, alg, desc in card_data:
        card = pygame.Rect(40, cy, WIDTH - 80, 68)
        pygame.draw.rect(WIN, PANEL_MID, card, border_radius=8)
        pygame.draw.rect(WIN, col, card, 2, border_radius=8)
        lbl = FNT_SM.render(f"Algorithm:  {alg}", True, GOLD)
        WIN.blit(lbl, (60, cy + 8))
        dl = FNT_XS.render(desc, True, TEXT_DIM)
        WIN.blit(dl, (60, cy + 36))
        cy += 80

    for b in btns:
        b.draw(WIN)

    foot = FNT_XS.render("ESC — back to menu", True, TEXT_DIM)
    WIN.blit(foot, foot.get_rect(center=(WIDTH // 2, HEIGHT - 18)))
    pygame.display.update()


# ══════════════════════════════════════════════════════════════
#  DRAW — IN-GAME HEADER
# ══════════════════════════════════════════════════════════════
def draw_header(end_btn=None):
    pygame.draw.rect(WIN, PANEL_DARK, (0, 0, WIDTH, UI_HEIGHT))
    pygame.draw.line(WIN, SEPARATOR, (0, UI_HEIGHT), (BOARD_PX, UI_HEIGHT), 2)

    # Left — title + algorithm label
    diff_name = current_difficulty.name if current_difficulty else ""
    tl = FNT_LARGE.render(f"Checkers AI  —  {diff_name}", True, GOLD)
    WIN.blit(tl, (14, 10))
    if current_difficulty:
        alg = LEVEL_INFO[current_difficulty]["label"]
        als = FNT_XS.render(f"AI: {alg}", True, TEXT_DIM)
        WIN.blit(als, (14, 46))

    # Captured + moves
    cap = FNT_XS.render(
        f"You captured: {human_captured}    AI captured: {ai_captured}    Moves: {moves_count}",
        True, TEXT_DIM)
    WIN.blit(cap, (14, 72))

    # Right — turn indicator + piece count
    if player_turn:
        st, sc = "Your Turn  ▴", (90, 210, 120)
    elif ai_thinking:
        st, sc = "AI Thinking…", (210, 165, 50)
    else:
        st, sc = "AI Moving…",  (210, 165, 50)
    ss = FNT_MED.render(st, True, sc)
    WIN.blit(ss, (BOARD_PX - ss.get_width() - 14, 10))

    hp = sum(1 for r in board for c in r if c < 0)
    ap = sum(1 for r in board for c in r if c > 0)
    ps = FNT_XS.render(f"You: {hp} pcs   AI: {ap} pcs", True, TEXT_LIGHT)
    WIN.blit(ps, (BOARD_PX - ps.get_width() - 14, 42))

    # End Game button in header
    if end_btn:
        end_btn.draw(WIN)


# ══════════════════════════════════════════════════════════════
#  DRAW — BOARD + PIECES + HIGHLIGHTS
# ══════════════════════════════════════════════════════════════
def draw_board():
    for row in range(ROWS):
        for col in range(COLS):
            color = BOARD_LIGHT if (row + col) % 2 == 0 else BOARD_DARK
            pygame.draw.rect(WIN, color,
                             (col * SQUARE_SIZE, row * SQUARE_SIZE + BOARD_Y,
                              SQUARE_SIZE, SQUARE_SIZE))
    for i in range(ROWS):
        lbl = FNT_XS.render(str(i + 1), True, TEXT_DIM)
        WIN.blit(lbl, (3, i * SQUARE_SIZE + BOARD_Y + 3))
    for j in range(COLS):
        lbl = FNT_XS.render(chr(65 + j), True, TEXT_DIM)
        WIN.blit(lbl, (j * SQUARE_SIZE + 3,
                       BOARD_Y + ROWS * SQUARE_SIZE - 14))


def draw_pieces():
    rad = SQUARE_SIZE // 2 - 10
    for row in range(ROWS):
        for col in range(COLS):
            p = board[row][col]
            if p == 0:
                continue
            cx = col * SQUARE_SIZE + SQUARE_SIZE // 2
            cy = row * SQUARE_SIZE + SQUARE_SIZE // 2 + BOARD_Y
            color = PIECE_RED  if p > 0 else PIECE_BLUE
            dark  = PIECE_RED_D if p > 0 else PIECE_BLUE_D

            # Shadow
            sh = pygame.Surface((rad*2+6, rad*2+6), pygame.SRCALPHA)
            pygame.draw.circle(sh, (0,0,0,60), (rad+3, rad+3), rad)
            WIN.blit(sh, (cx-rad-3+4, cy-rad-3+4))
            # Disc
            pygame.draw.circle(WIN, color, (cx, cy), rad)
            pygame.draw.circle(WIN, dark,  (cx, cy), rad, 3)
            # Inner ring
            hi = tuple(min(v+42, 255) for v in color)
            pygame.draw.circle(WIN, hi, (cx, cy), rad - 8, 2)
            # King
            if abs(p) == 2:
                pygame.draw.circle(WIN, GOLD, (cx, cy), 12)
                pygame.draw.circle(WIN, (0,0,0), (cx, cy), 12, 2)
                k = FNT_XS.render("K", True, (0,0,0))
                WIN.blit(k, k.get_rect(center=(cx, cy)))
            # Selection
            if selected_piece == (row, col):
                pygame.draw.circle(WIN, SELECTED_RING, (cx, cy), rad+6, 4)


def draw_highlights():
    for row, col in valid_moves:
        cx = col * SQUARE_SIZE + SQUARE_SIZE // 2
        cy = row * SQUARE_SIZE + SQUARE_SIZE // 2 + BOARD_Y
        pygame.draw.circle(WIN, HIGHLIGHT_DOT, (cx, cy), 13)
        pygame.draw.circle(WIN, (35, 155, 75), (cx, cy), 13, 3)


# ══════════════════════════════════════════════════════════════
#  DRAW — LIVE MOVE LOG PANEL (right side during play)
# ══════════════════════════════════════════════════════════════
def draw_move_log():
    px  = BOARD_PX           # left-edge of panel
    py  = UI_HEIGHT          # top of panel (below header)
    pw  = LOG_W
    ph  = HEIGHT - UI_HEIGHT

    # Panel background + border
    pygame.draw.rect(WIN, PANEL_MID, (px, py, pw, ph))
    pygame.draw.line(WIN, SEPARATOR, (px, py), (px, HEIGHT), 2)

    # Header strip
    pygame.draw.rect(WIN, PANEL_DARK, (px, py, pw, 32))
    ht = FNT_SM.render("  MOVE  LOG", True, GOLD)
    WIN.blit(ht, (px + 8, py + 6))
    move_n = FNT_XS.render(f"{len(move_log)} moves", True, TEXT_DIM)
    WIN.blit(move_n, (px + pw - move_n.get_width() - 8, py + 8))
    pygame.draw.line(WIN, SEPARATOR, (px, py + 32), (px + pw, py + 32), 1)

    # Legend
    you_dot = FNT_XS.render("■ YOU", True, TEXT_YOU)
    ai_dot  = FNT_XS.render("■ AI",  True, TEXT_AI)
    WIN.blit(you_dot, (px + 8,  py + 38))
    WIN.blit(ai_dot,  (px + 80, py + 38))
    pygame.draw.line(WIN, SEPARATOR, (px, py + 56), (px + pw, py + 56), 1)

    # Move entries — show last N that fit (newest at bottom)
    entry_h   = 20
    list_top  = py + 60
    list_h    = ph - 70
    max_shown = list_h // entry_h
    recent    = move_log[-max_shown:]

    for idx, mv in enumerate(recent):
        ey    = list_top + idx * entry_h
        # alternating row bg
        row_col = (28, 36, 58) if idx % 2 == 0 else (22, 28, 48)
        pygame.draw.rect(WIN, row_col, (px, ey, pw, entry_h))

        is_you = mv.startswith("YOU")
        num_s = FNT_XS.render(
            f"{len(move_log) - len(recent) + idx + 1}.", True, TEXT_DIM)
        WIN.blit(num_s, (px + 4, ey + 2))

        mv_s = FNT_XS.render(mv, True, TEXT_YOU if is_you else TEXT_AI)
        WIN.blit(mv_s, (px + 28, ey + 2))


# ══════════════════════════════════════════════════════════════
#  DRAW — GAME-OVER FLASH  (2 s, then auto-goes to ANALYSIS)
# ══════════════════════════════════════════════════════════════
def draw_game_over_flash():
    overlay = pygame.Surface((BOARD_PX, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    WIN.blit(overlay, (0, 0))

    if winner == "FORFEIT":
        result = "Game Forfeited"
        col    = GOLD
    elif winner == "HUMAN":
        result = "You  Win! 🎉"
        col    = (90, 215, 115)
    else:
        result = "AI  Wins!"
        col    = (215, 85, 85)

    t = FNT_TITLE.render(result, True, col)
    WIN.blit(t, t.get_rect(center=(BOARD_PX // 2, HEIGHT // 2 - 60)))

    note = FNT_SM.render("Loading analysis…", True, TEXT_DIM)
    WIN.blit(note, note.get_rect(center=(BOARD_PX // 2, HEIGHT // 2 + 20)))


# ══════════════════════════════════════════════════════════════
#  DRAW — POST-GAME ANALYSIS SCREEN  (auto-shown after game)
# ══════════════════════════════════════════════════════════════
def draw_analysis_screen(new_game_btn, exit_btn):
    WIN.fill(BG_DARK)

    # ── Title bar ────────────────────────────────────────────
    pygame.draw.rect(WIN, PANEL_DARK, (0, 0, WIDTH, 88))
    pygame.draw.line(WIN, SEPARATOR, (0, 88), (WIDTH, 88), 2)
    t = FNT_TITLE.render("GAME  ANALYSIS", True, GOLD)
    WIN.blit(t, t.get_rect(center=(WIDTH // 2, 46)))

    if current_difficulty is None:
        return

    info = LEVEL_INFO[current_difficulty]
    CX   = WIDTH // 2
    y    = 100

    # ── Result banner ─────────────────────────────────────────
    if winner == "FORFEIT":
        res_text, res_col = "Game Forfeited", GOLD
    elif winner == "HUMAN":
        res_text, res_col = "You  Won!", (85, 210, 110)
    else:
        res_text, res_col = "AI  Won!", (210, 80, 80)
    rt = FNT_LARGE.render(res_text, True, res_col)
    WIN.blit(rt, rt.get_rect(center=(CX, y + 28)))
    y += 65

    # ── Section renderer ──────────────────────────────────────
    def section(title, rows, head_col=GOLD):
        nonlocal y
        # section header pill
        pygame.draw.rect(WIN, PANEL_DARK,
                         pygame.Rect(28, y, WIDTH - 56, 30), border_radius=5)
        hs = FNT_SM.render(f"  {title}", True, head_col)
        WIN.blit(hs, (36, y + 6))
        y += 36

        for label, value in rows:
            card = pygame.Rect(28, y, WIDTH - 56, 32)
            alt  = (20, 26, 44) if (rows.index((label, value)) % 2 == 0) else (26, 34, 56)
            pygame.draw.rect(WIN, alt, card, border_radius=4)
            pygame.draw.rect(WIN, SEPARATOR, card, 1, border_radius=4)
            ls = FNT_XS.render(label, True, TEXT_DIM)
            vs = FNT_XS.render(str(value), True, TEXT_LIGHT)
            WIN.blit(ls, (42, y + 8))
            WIN.blit(vs, (card.right - vs.get_width() - 14, y + 8))
            y += 34
        y += 8

    # ── AI MODEL section ──────────────────────────────────────
    eval_fn = ("Dynamic phase-aware"  if current_difficulty == Difficulty.HARD  else
               "Positional"           if current_difficulty == Difficulty.MEDIUM else
               "None  (random)")
    section("AI  MODEL  USED", [
        ("Difficulty",       current_difficulty.name),
        ("Algorithm",        info["algorithm"]),
        ("Evaluation Fn",    eval_fn),
        ("Heuristic depth",  "d = 5" if current_difficulty == Difficulty.HARD else
                             "d = 3" if current_difficulty == Difficulty.MEDIUM else "N/A"),
    ], head_col=GOLD)

    # ── COMPLEXITY section ────────────────────────────────────
    section("COMPLEXITY  ANALYSIS", [
        ("Time  (best case)",  info["time_best"]),
        ("Time  (worst case)", info["time_worst"]),
        ("Space complexity",   info["space"]),
        ("Note",               info["note"]),
    ], head_col=(130, 195, 255))

    # ── GAME STATS section ────────────────────────────────────
    hp = sum(1 for r in board for c in r if c < 0) if board else 0
    ap = sum(1 for r in board for c in r if c > 0) if board else 0
    section("GAME  STATISTICS", [
        ("Total moves",          moves_count),
        ("Your pieces captured", human_captured),
        ("AI pieces captured",   ai_captured),
        ("Your pieces left",     hp),
        ("AI pieces left",       ap),
        ("Total log entries",    len(move_log)),
    ], head_col=(120, 215, 135))

    # ── Move log  mini-preview ────────────────────────────────
    section("LAST  5  MOVES", [
        (mv.split(":")[0],  mv.split(":", 1)[1].strip())
        for mv in move_log[-5:]
    ] if move_log else [("—", "No moves recorded")],
        head_col=(200, 170, 90))

    # ── Buttons ───────────────────────────────────────────────
    new_game_btn.draw(WIN)
    exit_btn.draw(WIN)


# ══════════════════════════════════════════════════════════════
#  GAME LOGIC
# ══════════════════════════════════════════════════════════════
def pos_from_mouse(pos):
    x, y = pos
    y -= BOARD_Y
    return max(0, min(y // SQUARE_SIZE, ROWS-1)), max(0, min(x // SQUARE_SIZE, COLS-1))


def jump_moves(r, c, bs):
    p = bs[r][c]
    if p == 0: return []
    king = abs(p) == 2
    out = []
    for dr, dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
        if not king:
            if p > 0 and dr < 0: continue
            if p < 0 and dr > 0: continue
        jr, jc = r+2*dr, c+2*dc
        mr, mc = r+dr,   c+dc
        if 0 <= jr < ROWS and 0 <= jc < COLS:
            if bs[jr][jc] == 0 and bs[mr][mc] != 0:
                mid = bs[mr][mc]
                if (p>0 and mid<0) or (p<0 and mid>0):
                    out.append((jr, jc))
    return out


def all_valid(r, c, bs=None):
    if bs is None: bs = board
    p = bs[r][c]
    if p == 0: return []
    king = abs(p) == 2
    moves, jumps = [], []
    for dr, dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
        if not king:
            if p > 0 and dr < 0: continue
            if p < 0 and dr > 0: continue
        nr, nc = r+dr, c+dc
        if 0 <= nr < ROWS and 0 <= nc < COLS and bs[nr][nc] == 0:
            moves.append((nr, nc))
        jr, jc = r+2*dr, c+2*dc
        mr, mc = r+dr, c+dc
        if 0 <= jr < ROWS and 0 <= jc < COLS:
            if bs[jr][jc] == 0 and bs[mr][mc] != 0:
                mid = bs[mr][mc]
                if (p>0 and mid<0) or (p<0 and mid>0):
                    jumps.append((jr, jc))
    return jumps if jumps else moves


def has_jumps(is_ai, bs=None):
    if bs is None: bs = board
    for r in range(ROWS):
        for c in range(COLS):
            p = bs[r][c]
            if p == 0: continue
            if is_ai and p < 0: continue
            if not is_ai and p > 0: continue
            if jump_moves(r, c, bs): return True
    return False


def side_moves(is_ai, bs=None):
    if bs is None: bs = board
    jonly = has_jumps(is_ai, bs)
    out = []
    for r in range(ROWS):
        for c in range(COLS):
            p = bs[r][c]
            if p == 0: continue
            if is_ai and p < 0: continue
            if not is_ai and p > 0: continue
            mvs = jump_moves(r,c,bs) if jonly else all_valid(r,c,bs)
            for (tr,tc) in mvs:
                out.append((r,c,tr,tc))
    return out


def apply_move(bs, fr, fc, tr, tc):
    nb = [row[:] for row in bs]
    p  = nb[fr][fc]
    nb[tr][tc] = p
    nb[fr][fc] = 0
    if abs(tr-fr) == 2:
        nb[(fr+tr)//2][(fc+tc)//2] = 0
    if p ==  1 and tr == ROWS-1: nb[tr][tc] = 2
    if p == -1 and tr == 0:      nb[tr][tc] = -2
    return nb


# ── PLAYER INTERACTION ────────────────────────────────────────
def handle_selection(row, col):
    global selected_piece, valid_moves
    if board[row][col] < 0:
        forced = has_jumps(False)
        jmvs   = jump_moves(row, col, board)
        if forced:
            selected_piece = (row, col) if jmvs else None
            valid_moves    = jmvs
        else:
            selected_piece = (row, col)
            valid_moves    = all_valid(row, col)
    else:
        selected_piece = None
        valid_moves    = []


def handle_move(to_r, to_c):
    global selected_piece, valid_moves, player_turn, moves_count, human_captured

    if not selected_piece or (to_r, to_c) not in valid_moves:
        return
    fr, fc = selected_piece
    p = board[fr][fc]
    board[to_r][to_c] = p
    board[fr][fc] = 0

    captured = False
    if abs(to_r - fr) == 2:
        mr, mc = (fr+to_r)//2, (fc+to_c)//2
        if board[mr][mc] > 0:
            board[mr][mc] = 0
            human_captured += 1
            captured = True
        further = jump_moves(to_r, to_c, board)
        if further:
            if p == -1 and to_r == 0:
                board[to_r][to_c] = -2
            selected_piece = (to_r, to_c)
            valid_moves    = further
            log_move("YOU", fr, fc, to_r, to_c, capture=captured)
            return   # multi-jump continues

    if p == -1 and to_r == 0:
        board[to_r][to_c] = -2

    log_move("YOU", fr, fc, to_r, to_c, capture=captured)
    selected_piece = None
    valid_moves    = []
    player_turn    = False
    moves_count   += 1


# ══════════════════════════════════════════════════════════════
#  EVALUATION FUNCTIONS
# ══════════════════════════════════════════════════════════════
def eval_pos(bs):
    score = 0
    for r in range(ROWS):
        for c in range(COLS):
            p = bs[r][c]
            if p == 0: continue
            base = {1:5, 2:12, -1:-5, -2:-12}.get(p, 0)
            adv  = (r*0.5) if p>0 else (-(ROWS-1-r)*0.5)
            edge = (0.3 if p>0 else -0.3) if c in (0, COLS-1) else 0
            ctr  = (0.2 if p>0 else -0.2) if (2<=c<=5 and 2<=r<=5) else 0
            score += base + adv + edge + ctr
    return score


def eval_dyn(bs):
    ap  = sum(1 for r in bs for c in r if c > 0)
    hp  = sum(1 for r in bs for c in r if c < 0)
    tot = ap + hp
    ph  = "opening" if tot >= 18 else ("midgame" if tot >= 10 else "endgame")
    sc  = 0
    for r in range(ROWS):
        for c in range(COLS):
            p = bs[r][c]
            if p == 0: continue
            sign = 1 if p>0 else -1
            king = abs(p) == 2
            mat  = ({"opening":5,"midgame":6,"endgame":7}[ph]
                    if not king else
                    {"opening":10,"midgame":14,"endgame":16}[ph])
            adv  = r if p>0 else (ROWS-1-r)
            aw   = {"opening":0.3,"midgame":0.6,"endgame":1.0}[ph]
            ctr  = max(0, 4-(abs(c-3.5)+abs(r-3.5)))
            cw   = 0.5 if ph=="opening" else 0.2
            mob  = len(all_valid(r, c, bs))
            mw   = 0.2 if (king and ph=="endgame") else 0.1
            sc  += sign*(mat + adv*aw + ctr*cw + mob*mw)
    sc += (ap-hp)*(3 if ph=="endgame" else 1.5)
    return sc


# ══════════════════════════════════════════════════════════════
#  MINIMAX & ALPHA-BETA
# ══════════════════════════════════════════════════════════════
def minimax(bs, depth, maxing, ef):
    ap = sum(1 for r in bs for c in r if c > 0)
    hp = sum(1 for r in bs for c in r if c < 0)
    if ap == 0: return -10000-depth, None
    if hp == 0: return  10000+depth, None
    mvs = side_moves(maxing, bs)
    if not mvs: return (-10000-depth if maxing else 10000+depth), None
    if depth == 0: return ef(bs), None
    best = None
    if maxing:
        val = float('-inf')
        for m in mvs:
            sc,_ = minimax(apply_move(bs,*m), depth-1, False, ef)
            if sc > val: val, best = sc, m
        return val, best
    else:
        val = float('inf')
        for m in mvs:
            sc,_ = minimax(apply_move(bs,*m), depth-1, True, ef)
            if sc < val: val, best = sc, m
        return val, best


def alpha_beta(bs, depth, maxing, alpha, beta, ef):
    ap = sum(1 for r in bs for c in r if c > 0)
    hp = sum(1 for r in bs for c in r if c < 0)
    if ap == 0: return -10000-depth, None
    if hp == 0: return  10000+depth, None
    mvs = side_moves(maxing, bs)
    if not mvs: return (-10000-depth if maxing else 10000+depth), None
    if depth == 0: return ef(bs), None
    best = None
    if maxing:
        val = float('-inf')
        for m in mvs:
            sc,_ = alpha_beta(apply_move(bs,*m), depth-1, False, alpha, beta, ef)
            if sc > val: val, best = sc, m
            alpha = max(alpha, sc)
            if beta <= alpha: break
        return val, best
    else:
        val = float('inf')
        for m in mvs:
            sc,_ = alpha_beta(apply_move(bs,*m), depth-1, True, alpha, beta, ef)
            if sc < val: val, best = sc, m
            beta = min(beta, sc)
            if beta <= alpha: break
        return val, best


# ══════════════════════════════════════════════════════════════
#  AI MOVE (level → algorithm)
# ══════════════════════════════════════════════════════════════
def execute_ai(fr, fc, tr, tc, first=True):
    """Apply AI move on the live board. Logs only the first call."""
    global ai_captured
    p = board[fr][fc]
    board[tr][tc] = p
    board[fr][fc] = 0
    captured = False
    if abs(tr-fr) == 2:
        mr, mc = (fr+tr)//2, (fc+tc)//2
        if board[mr][mc] < 0:
            board[mr][mc] = 0
            ai_captured += 1
            captured = True
        further = jump_moves(tr, tc, board)
        if further:
            if first:
                log_move("AI", fr, fc, tr, tc, capture=captured)
            execute_ai(tr, tc, further[0][0], further[0][1], first=False)
            return
    if p == 1 and tr == ROWS-1:
        board[tr][tc] = 2
    if first:
        log_move("AI", fr, fc, tr, tc, capture=captured)


def do_ai_move():
    global player_turn, ai_thinking, moves_count

    ai_thinking = True
    WIN.fill(BG_DARK)
    draw_header()
    draw_board(); draw_pieces()
    draw_move_log()
    pygame.display.update()
    pygame.time.delay(320)

    bc = [row[:] for row in board]
    moved = False

    if current_difficulty == Difficulty.EASY:
        mvs = side_moves(True)
        if mvs:
            execute_ai(*random.choice(mvs))
            moved = True

    elif current_difficulty == Difficulty.MEDIUM:
        _, best = minimax(bc, 3, True, eval_pos)
        if best:
            execute_ai(*best); moved = True
        else:
            mvs = side_moves(True)
            if mvs: execute_ai(*random.choice(mvs)); moved = True

    elif current_difficulty == Difficulty.HARD:
        _, best = alpha_beta(bc, 5, True, float('-inf'), float('inf'), eval_dyn)
        if best:
            execute_ai(*best); moved = True
        else:
            mvs = side_moves(True)
            if mvs: execute_ai(*random.choice(mvs)); moved = True

    ai_thinking = False
    if moved: moves_count += 1
    player_turn = True


# ══════════════════════════════════════════════════════════════
#  GAME-OVER CHECK
# ══════════════════════════════════════════════════════════════
def check_game_over():
    global game_over, winner, game_over_tick
    hp = sum(1 for r in board for c in r if c < 0)
    ap = sum(1 for r in board for c in r if c > 0)
    if hp == 0:
        game_over, winner = True, "AI"
    elif ap == 0:
        game_over, winner = True, "HUMAN"
    elif player_turn and not side_moves(False):
        game_over, winner = True, "AI"
    elif not player_turn and not side_moves(True):
        game_over, winner = True, "HUMAN"
    if game_over and game_over_tick == 0:
        game_over_tick = pygame.time.get_ticks()


# ══════════════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════════════
def main():
    global game_state, current_difficulty, player_turn
    global ai_thinking, board, game_over, winner, game_over_tick

    clock = pygame.time.Clock()
    CX = WIDTH // 2

    # ── Buttons ───────────────────────────────────────────────
    start_btn   = Button(CX-110, 380, 220, BUTTON_H, "START GAME",
                         BTN_START, BTN_START_H)

    diff_btns   = [
        Button(CX-330, 550, 200, BUTTON_H, "EASY",   BTN_EASY,  BTN_EASY_H,
               "Random move"),
        Button(CX-100, 550, 200, BUTTON_H, "MEDIUM", BTN_MEDIUM,BTN_MEDIUM_H,
               "Minimax d=3"),
        Button(CX+130, 550, 200, BUTTON_H, "HARD",   BTN_HARD,  BTN_HARD_H,
               "Alpha-Beta d=5"),
    ]

    # Small "End Game" button inside the in-game header
    end_btn     = Button(BOARD_PX - 130, 72, 118, 32,
                         "End Game", BTN_END_RED, BTN_END_RED_H)

    # Analysis screen buttons
    new_game_btn = Button(CX - 240, HEIGHT - 78, 210, BUTTON_H,
                          "New Game", BTN_MEDIUM, BTN_MEDIUM_H)
    exit_btn     = Button(CX +  30, HEIGHT - 78, 210, BUTTON_H,
                          "Exit",     BTN_END_RED, BTN_END_RED_H)

    all_btns = [start_btn] + diff_btns + [end_btn, new_game_btn, exit_btn]

    running = True
    while running:
        clock.tick(60)
        mouse_pos = pygame.mouse.get_pos()
        for b in all_btns:
            b.update_hover(mouse_pos)

        # ── EVENTS ───────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game_state == GameState.ANALYSIS:
                        game_state = GameState.DIFF_SELECT
                    elif game_state in (GameState.DIFF_SELECT,
                                        GameState.PLAYING,
                                        GameState.GAME_OVER):
                        game_state = GameState.MENU

            elif event.type == pygame.MOUSEBUTTONDOWN:

                if game_state == GameState.MENU:
                    if start_btn.is_clicked(mouse_pos):
                        game_state = GameState.DIFF_SELECT

                elif game_state == GameState.DIFF_SELECT:
                    for i, diff in enumerate([Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]):
                        if diff_btns[i].is_clicked(mouse_pos):
                            current_difficulty = diff
                            initialize_board()
                            game_state = GameState.PLAYING

                elif game_state == GameState.PLAYING:
                    if end_btn.is_clicked(mouse_pos):
                        game_over      = True
                        winner         = "FORFEIT"
                        game_over_tick = pygame.time.get_ticks()
                        game_state     = GameState.GAME_OVER
                    elif player_turn:
                        x, y = mouse_pos
                        if y >= BOARD_Y and x < BOARD_PX:
                            r, c = pos_from_mouse(mouse_pos)
                            if selected_piece and (r, c) in valid_moves:
                                handle_move(r, c)
                            else:
                                handle_selection(r, c)

                elif game_state == GameState.ANALYSIS:
                    if new_game_btn.is_clicked(mouse_pos):
                        game_state = GameState.DIFF_SELECT
                    elif exit_btn.is_clicked(mouse_pos):
                        running = False

        # ── RENDERING ────────────────────────────────────────
        if game_state == GameState.MENU:
            draw_menu(start_btn)

        elif game_state == GameState.DIFF_SELECT:
            draw_diff_select(diff_btns)

        elif game_state == GameState.PLAYING:
            WIN.fill(BG_DARK)
            draw_header(end_btn)
            draw_board()
            draw_pieces()
            draw_highlights()
            draw_move_log()
            pygame.display.update()

            if not player_turn and not ai_thinking and not game_over:
                do_ai_move()

            check_game_over()
            if game_over:
                game_state = GameState.GAME_OVER

        elif game_state == GameState.GAME_OVER:
            # Show board + flash overlay for GAME_OVER_DELAY ms, then auto-go to ANALYSIS
            WIN.fill(BG_DARK)
            draw_header()
            draw_board()
            draw_pieces()
            draw_move_log()
            draw_game_over_flash()
            pygame.display.update()

            if pygame.time.get_ticks() - game_over_tick >= GAME_OVER_DELAY:
                game_state = GameState.ANALYSIS

        elif game_state == GameState.ANALYSIS:
            draw_analysis_screen(new_game_btn, exit_btn)
            pygame.display.update()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
