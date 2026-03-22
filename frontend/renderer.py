"""
Checkers Frontend — Rendering Engine
Full-screen board with toggleable analysis overlay and post-game analysis.
"""

import pygame
from backend.game_logic import ROWS, COLS

# ==================== LAYOUT ====================
WIN_W = 800
WIN_H = 1000
SQ = 100
HUD_H = 90
BOARD_Y = HUD_H
BAR_Y = BOARD_Y + SQ * ROWS  # 890
BAR_H = WIN_H - BAR_Y        # 110

# ==================== COLOURS ====================
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_BG = (22, 22, 32)
PANEL_BG = (18, 18, 28)
PANEL_BORDER = (55, 55, 80)
LIGHT_GREY = (210, 210, 210)
DIM = (90, 90, 110)
RED = (220, 50, 50)
DARK_RED = (170, 20, 20)
BLUE = (100, 150, 255)
DARK_BLUE = (50, 100, 200)
GREEN = (76, 175, 80)
BRIGHT_GREEN = (140, 255, 90)
YELLOW = (255, 223, 0)
ORANGE = (255, 140, 0)
PURPLE = (180, 100, 255)
HIGHLIGHT = (150, 255, 150)
SELECTED = (255, 215, 0)
BOARD_DARK = (139, 90, 43)
BOARD_LIGHT = (222, 184, 135)
GOLD = (255, 200, 50)
CYAN = (0, 210, 210)
TIMER_LOW = (255, 80, 80)

DIFF_COLORS = {"EASY": BRIGHT_GREEN, "MEDIUM": ORANGE, "HARD": RED}


def fmt_time(secs):
    secs = max(0, secs)
    m, s = int(secs) // 60, int(secs) % 60
    return f"{m:02d}:{s:02d}"


class CheckersRenderer:
    def __init__(self, surface):
        self.win = surface
        self.ft = pygame.font.Font(None, 48)
        self.fl = pygame.font.Font(None, 36)
        self.fm = pygame.font.Font(None, 28)
        self.fs = pygame.font.Font(None, 22)
        self.fx = pygame.font.Font(None, 18)
        self.fmono = pygame.font.SysFont("consolas", 15)

    @staticmethod
    def mouse_to_rc(pos):
        x, y = pos
        return max(0, min((y - BOARD_Y) // SQ, ROWS - 1)), max(0, min(x // SQ, COLS - 1))

    # ---------- MENUS ----------
    def draw_menu(self):
        self.win.fill(DARK_BG)
        self._center(self.ft, "CHECKERS AI", YELLOW, WIN_W // 2, 120)
        self._center(self.fl, "Challenge the Computer", BRIGHT_GREEN, WIN_W // 2, 200)
        self._center(self.fs, "Click START to begin", LIGHT_GREY, WIN_W // 2, 340)

    def draw_difficulty_select(self, buttons):
        self.win.fill(DARK_BG)
        self._center(self.ft, "SELECT DIFFICULTY", YELLOW, WIN_W // 2, 100)
        self._center(self.fm, "AI algorithm is auto-selected", DIM, WIN_W // 2, 160)
        descs = {"EASY": "Random moves", "MEDIUM": "Alpha-Beta depth 3", "HARD": "Alpha-Beta depth 5 (dynamic)"}
        for b in buttons:
            b.draw(self.win)
            if b.text in descs:
                d = self.fx.render(descs[b.text], True, DIM)
                self.win.blit(d, d.get_rect(center=(b.rect.centerx, b.rect.bottom + 18)))

    # ---------- HUD ----------
    def draw_hud(self, game, diff, ai_thinking, h_time, a_time):
        pygame.draw.rect(self.win, DARK_BG, (0, 0, WIN_W, HUD_H))
        # Difficulty badge
        dn = diff.name if diff else "?"
        bc = DIFF_COLORS.get(dn, DIM)
        badge = pygame.Rect(15, 12, 90, 30)
        pygame.draw.rect(self.win, bc, badge, border_radius=6)
        self.win.blit(self.fx.render(dn, True, BLACK), self.fx.render(dn, True, BLACK).get_rect(center=badge.center))
        # Turn indicator
        tt = "YOUR TURN" if game.player_turn else ("AI THINKING..." if ai_thinking else "AI MOVING...")
        tc = BRIGHT_GREEN if game.player_turn else ORANGE
        self.win.blit(self.fs.render(tt, True, tc), (120, 14))
        # Piece counts
        h, a = game.count_pieces()
        self.win.blit(self.fs.render(f"You: {h}   AI: {a}   Move: {game.moves_count}", True, LIGHT_GREY), (15, 55))
        # Timers
        htc = TIMER_LOW if h_time < 60 else WHITE
        atc = TIMER_LOW if a_time < 60 else WHITE
        self.win.blit(self.fs.render(f"You  {fmt_time(h_time)}", True, htc), (WIN_W - 180, 14))
        self.win.blit(self.fs.render(f"AI   {fmt_time(a_time)}", True, atc), (WIN_W - 180, 40))
        # No-capture streak
        self.win.blit(self.fx.render(f"No-capture: {game.moves_without_capture}/40", True, DIM), (WIN_W - 180, 65))
        pygame.draw.line(self.win, YELLOW, (0, HUD_H - 2), (WIN_W, HUD_H - 2), 2)

    # ---------- BOARD ----------
    def draw_board(self):
        for r in range(ROWS):
            for c in range(COLS):
                x, y = c * SQ, r * SQ + BOARD_Y
                cl = BOARD_LIGHT if (r + c) % 2 == 0 else BOARD_DARK
                pygame.draw.rect(self.win, cl, (x, y, SQ, SQ))
        for i in range(ROWS):
            self.win.blit(self.fx.render(str(8 - i), True, DIM), (2, i * SQ + BOARD_Y + 2))
        for j in range(COLS):
            self.win.blit(self.fx.render(chr(97 + j), True, DIM), (j * SQ + SQ - 14, BOARD_Y + ROWS * SQ - 16))

    def draw_pieces(self, game):
        rad = SQ // 2 - 15
        for r in range(ROWS):
            for c in range(COLS):
                p = game.board[r][c]
                if p == 0:
                    continue
                x, y = c * SQ + SQ // 2, r * SQ + SQ // 2 + BOARD_Y
                col = RED if p > 0 else BLUE
                out = DARK_RED if p > 0 else DARK_BLUE
                sh = pygame.Surface((rad * 2 + 4, rad * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(sh, (0, 0, 0, 60), (rad + 2, rad + 2), rad)
                self.win.blit(sh, (x - rad + 1, y - rad + 1))
                pygame.draw.circle(self.win, col, (x, y), rad)
                pygame.draw.circle(self.win, out, (x, y), rad, 3)
                hl = tuple(min(v + 40, 255) for v in col)
                pygame.draw.circle(self.win, hl, (x, y), rad - 8, 2)
                if abs(p) == 2:
                    pygame.draw.circle(self.win, YELLOW, (x, y), 12)
                    pygame.draw.circle(self.win, BLACK, (x, y), 12, 2)
                    self.win.blit(self.fx.render("K", True, BLACK),
                                  self.fx.render("K", True, BLACK).get_rect(center=(x, y)))
                if game.selected_piece == (r, c):
                    pygame.draw.circle(self.win, SELECTED, (x, y), rad + 5, 4)

    def highlight_moves(self, moves):
        for r, c in moves:
            x, y = c * SQ + SQ // 2, r * SQ + SQ // 2 + BOARD_Y
            pygame.draw.circle(self.win, HIGHLIGHT, (x, y), 15)
            pygame.draw.circle(self.win, GREEN, (x, y), 15, 3)

    # ---------- BOTTOM BAR ----------
    def draw_bottom_bar(self, analysis_open):
        pygame.draw.rect(self.win, DARK_BG, (0, BAR_Y, WIN_W, BAR_H))
        pygame.draw.line(self.win, YELLOW, (0, BAR_Y), (WIN_W, BAR_Y), 2)
        label = "▲ Hide Analysis" if analysis_open else "▼ Show Analysis"
        self._center(self.fs, label, CYAN, WIN_W // 2, BAR_Y + 20)

    # ---------- ANALYSIS OVERLAY (during game) ----------
    def draw_analysis_overlay(self, game, ai_stats, scroll):
        ov = pygame.Surface((WIN_W, 520), pygame.SRCALPHA)
        ov.fill((10, 10, 20, 230))
        self.win.blit(ov, (0, 480))
        y = 490
        self._center(self.fm, "MOVE ANALYSIS", GOLD, WIN_W // 2, y)
        y += 30
        # Column headers
        self.win.blit(self.fx.render("#", True, DIM), (30, y))
        self.win.blit(self.fx.render("HUMAN", True, BLUE), (65, y))
        self.win.blit(self.fx.render("AI", True, RED), (320, y))
        self.win.blit(self.fx.render("EVAL", True, DIM), (530, y))
        y += 18
        pygame.draw.line(self.win, PANEL_BORDER, (20, y), (WIN_W - 20, y))
        y += 4
        # Move pairs
        pairs = []
        hist = game.move_history
        i = 0
        while i < len(hist):
            pairs.append((hist[i], hist[i + 1] if i + 1 < len(hist) else None))
            i += 2
        max_vis = 10
        start = max(0, len(pairs) - max_vis + scroll)
        start = max(0, min(start, max(0, len(pairs) - max_vis)))
        for idx, (hm, am) in enumerate(pairs[start:start + max_vis]):
            ty = y + idx * 18
            tn = start + idx + 1
            if idx % 2 == 0:
                pygame.draw.rect(self.win, (25, 25, 40), (20, ty - 1, WIN_W - 40, 18))
            self.win.blit(self.fmono.render(f"{tn:>2}.", True, DIM), (30, ty))
            if hm:
                c = (130, 200, 255) if hm.is_capture else BLUE
                self.win.blit(self.fmono.render(hm.notation, True, c), (65, ty))
            if am:
                c = (255, 160, 160) if am.is_capture else RED
                self.win.blit(self.fmono.render(am.notation, True, c), (320, ty))
                self.win.blit(self.fmono.render(f"{am.eval_score:+.1f}", True, DIM), (530, ty))
        # AI stats
        sy = 710
        pygame.draw.line(self.win, PANEL_BORDER, (20, sy), (WIN_W - 20, sy))
        sy += 8
        if ai_stats and ai_stats.algorithm_name:
            info = (f"Algo: {ai_stats.algorithm_name}  |  Depth: {ai_stats.search_depth}  |  "
                    f"Nodes: {ai_stats.nodes_evaluated:,}  |  Pruned: {ai_stats.branches_pruned:,}  |  "
                    f"Time: {ai_stats.time_taken_ms:.0f}ms")
            self.win.blit(self.fx.render(info, True, LIGHT_GREY), (25, sy))
            sy += 18
            self.win.blit(self.fx.render(
                f"Time Complexity: {ai_stats.time_complexity}   Space: {ai_stats.space_complexity}",
                True, BRIGHT_GREEN), (25, sy))

    # ---------- GAME OVER SCREEN ----------
    def draw_game_over(self, game, diff, buttons):
        ov = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 210))
        self.win.blit(ov, (0, 0))
        cy = WIN_H // 2 - 60
        if game.winner == "DRAW":
            self._center(self.ft, "DRAW!", ORANGE, WIN_W // 2, cy - 80)
            self._center(self.fm, game.draw_reason or "", LIGHT_GREY, WIN_W // 2, cy - 30)
        else:
            self._center(self.ft, f"{game.winner} WINS!", YELLOW, WIN_W // 2, cy - 80)
        self._center(self.fm, f"Total moves: {game.moves_count}", LIGHT_GREY, WIN_W // 2, cy)
        dn = diff.name if diff else ""
        self._center(self.fs, f"Mode: {dn}", DIM, WIN_W // 2, cy + 30)
        for b in buttons:
            b.draw(self.win)

    # ---------- POST-GAME ANALYSIS SCREEN ----------
    def draw_post_analysis(self, game, ai_stats, h_acc, a_acc, diff, scroll, btn):
        self.win.fill(DARK_BG)
        y = 20
        self._center(self.ft, "POST-GAME ANALYSIS", GOLD, WIN_W // 2, y)
        y += 50
        dn = diff.name if diff else ""
        result = game.winner if game.winner != "DRAW" else f"DRAW — {game.draw_reason}"
        self._center(self.fs, f"Mode: {dn}   |   Result: {result}   |   Moves: {game.moves_count}", LIGHT_GREY, WIN_W // 2, y)
        y += 40
        # Accuracy bars
        self._draw_bar(50, y, 320, 30, h_acc, BLUE, "Human")
        self._draw_bar(430, y, 320, 30, a_acc, RED, "AI")
        y += 55
        pygame.draw.line(self.win, PANEL_BORDER, (20, y), (WIN_W - 20, y))
        y += 10
        # Move list
        self.win.blit(self.fx.render("#", True, DIM), (30, y))
        self.win.blit(self.fx.render("HUMAN", True, BLUE), (65, y))
        self.win.blit(self.fx.render("AI", True, RED), (300, y))
        self.win.blit(self.fx.render("EVAL", True, DIM), (500, y))
        self.win.blit(self.fx.render("QUALITY", True, DIM), (600, y))
        y += 18
        pygame.draw.line(self.win, PANEL_BORDER, (20, y), (WIN_W - 20, y))
        y += 4
        pairs = []
        hist = game.move_history
        i = 0
        while i < len(hist):
            pairs.append((hist[i], hist[i + 1] if i + 1 < len(hist) else None))
            i += 2
        max_vis = 25
        start = max(0, len(pairs) - max_vis + scroll)
        start = max(0, min(start, max(0, len(pairs) - max_vis)))
        for idx, (hm, am) in enumerate(pairs[start:start + max_vis]):
            ty = y + idx * 17
            if ty > 870:
                break
            tn = start + idx + 1
            if idx % 2 == 0:
                pygame.draw.rect(self.win, (25, 25, 40), (20, ty - 1, WIN_W - 40, 17))
            self.win.blit(self.fmono.render(f"{tn:>2}.", True, DIM), (30, ty))
            if hm:
                c = (130, 200, 255) if hm.is_capture else BLUE
                self.win.blit(self.fmono.render(hm.notation, True, c), (65, ty))
            if am:
                c = (255, 160, 160) if am.is_capture else RED
                self.win.blit(self.fmono.render(am.notation, True, c), (300, ty))
                self.win.blit(self.fmono.render(f"{am.eval_score:+.1f}", True, DIM), (500, ty))
                # Move quality
                if idx > 0:
                    prev = pairs[start + idx - 1]
                    prev_ev = prev[1].eval_score if prev[1] else (prev[0].eval_score if prev[0] else 0)
                    loss = max(0, -(am.eval_score - prev_ev))
                    q, qc = self._quality(loss)
                    self.win.blit(self.fmono.render(q, True, qc), (600, ty))
        # AI performance summary
        sy = 900
        pygame.draw.line(self.win, PANEL_BORDER, (20, sy), (WIN_W - 20, sy))
        sy += 10
        if ai_stats and ai_stats.algorithm_name:
            self.win.blit(self.fx.render(
                f"AI: {ai_stats.algorithm_name}  |  Time: {ai_stats.time_complexity}  |  Space: {ai_stats.space_complexity}",
                True, BRIGHT_GREEN), (25, sy))
        sy += 25
        btn.draw(self.win)

    # ---------- HELPERS ----------
    def _center(self, font, text, color, cx, cy):
        s = font.render(text, True, color)
        self.win.blit(s, s.get_rect(center=(cx, cy)))

    def _draw_bar(self, x, y, w, h, pct, color, label):
        pygame.draw.rect(self.win, (40, 40, 55), (x, y, w, h), border_radius=6)
        fw = int(w * min(pct, 100) / 100)
        if fw > 0:
            pygame.draw.rect(self.win, color, (x, y, fw, h), border_radius=6)
        txt = f"{label}: {pct:.0f}%"
        self.win.blit(self.fs.render(txt, True, WHITE), (x + 10, y + (h - 18) // 2))

    @staticmethod
    def _quality(loss):
        if loss <= 0.3:
            return "Best", BRIGHT_GREEN
        elif loss <= 1.0:
            return "Good", (100, 200, 100)
        elif loss <= 2.0:
            return "Okay", YELLOW
        elif loss <= 4.0:
            return "Inaccuracy", ORANGE
        else:
            return "Mistake", RED
