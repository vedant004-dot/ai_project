"""
Checkers Frontend — Main Application Loop
Full-screen board, chess timers, difficulty auto-maps to algorithm,
toggleable analysis, post-game accuracy screen.
"""

import pygame
import sys
import time as _time
from enum import Enum

from backend.game_logic import CheckersGame
from backend.ai_engine import CheckersAI
from backend.enums import Difficulty

from frontend.renderer import (
    CheckersRenderer, WIN_W, WIN_H, BOARD_Y, SQ, BAR_Y,
    DARK_BG, BRIGHT_GREEN, GREEN, ORANGE, RED, DARK_RED, PURPLE, CYAN, GOLD,
)
from frontend.ui_components import Button

BTN_W, BTN_H = 200, 55
TIMER_TOTAL = 600.0  # 10 minutes per player


class Screen(Enum):
    MENU = 1
    DIFFICULTY = 2
    PLAYING = 3
    GAME_OVER = 4
    ANALYSIS = 5


def compute_accuracy(history):
    """Compute accuracy (0-100) for human and AI from eval history."""
    if len(history) < 2:
        return 50.0, 50.0
    h_scores, a_scores = [], []
    for i in range(1, len(history)):
        prev_ev = history[i - 1].eval_score
        curr_ev = history[i].eval_score
        change = curr_ev - prev_ev  # positive = AI gained
        if history[i].player == 'human':
            loss = max(0, change)
            if loss <= 0.3: q = 100
            elif loss <= 1.0: q = 85
            elif loss <= 2.0: q = 55
            elif loss <= 4.0: q = 20
            else: q = 0
            h_scores.append(q)
        else:
            loss = max(0, -change)
            if loss <= 0.3: q = 100
            elif loss <= 1.0: q = 85
            elif loss <= 2.0: q = 55
            elif loss <= 4.0: q = 20
            else: q = 0
            a_scores.append(q)
    h_acc = sum(h_scores) / len(h_scores) if h_scores else 50
    a_acc = sum(a_scores) / len(a_scores) if a_scores else 50
    return h_acc, a_acc


def main():
    pygame.init()
    pygame.font.init()
    win = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Checkers AI")
    clock = pygame.time.Clock()
    renderer = CheckersRenderer(win)

    game = CheckersGame()
    ai = CheckersAI(game)
    screen = Screen.MENU
    difficulty = None
    ai_thinking = False
    analysis_open = False
    scroll = 0

    # Timer state
    h_time = TIMER_TOTAL
    a_time = TIMER_TOTAL
    turn_start = 0.0
    prev_hist_len = 0

    # Accuracy (computed on game over)
    h_acc, a_acc = 50.0, 50.0

    # ---- Buttons ----
    cx = WIN_W // 2
    menu_btns = [Button(cx - BTN_W // 2, WIN_H // 2, BTN_W, BTN_H, "START", BRIGHT_GREEN, GREEN)]

    diff_btns = [
        Button(cx - 310, 320, BTN_W, BTN_H, "EASY", BRIGHT_GREEN, GREEN),
        Button(cx - BTN_W // 2, 320, BTN_W, BTN_H, "MEDIUM", ORANGE, (255, 165, 0)),
        Button(cx + 110, 320, BTN_W, BTN_H, "HARD", RED, DARK_RED),
    ]

    go_new_btn = Button(cx - BTN_W - 20, WIN_H // 2 + 50, BTN_W, BTN_H, "New Game", BRIGHT_GREEN, GREEN)
    go_analysis_btn = Button(cx + 20, WIN_H // 2 + 50, BTN_W, BTN_H, "Analysis", CYAN, (0, 170, 170))
    go_btns = [go_new_btn, go_analysis_btn]

    pa_new_btn = Button(cx - BTN_W // 2, 940, BTN_W, 45, "New Game", BRIGHT_GREEN, GREEN)

    all_btns = menu_btns + diff_btns + go_btns + [pa_new_btn]

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        mouse = pygame.mouse.get_pos()
        for b in all_btns:
            b.update_hover(mouse)

        # ---- Timer update ----
        if screen == Screen.PLAYING and not game.game_over:
            elapsed = _time.time() - turn_start if turn_start > 0 else 0
            if game.player_turn:
                disp_h = h_time - elapsed
                disp_a = a_time
                if disp_h <= 0:
                    game.game_over, game.winner = True, "AI"
                    game.draw_reason = None
                    screen = Screen.GAME_OVER
                    h_acc, a_acc = compute_accuracy(game.move_history)
            else:
                disp_h = h_time
                disp_a = a_time - elapsed
                if disp_a <= 0:
                    game.game_over, game.winner = True, "HUMAN"
                    game.draw_reason = None
                    screen = Screen.GAME_OVER
                    h_acc, a_acc = compute_accuracy(game.move_history)
        else:
            disp_h = h_time
            disp_a = a_time

        # ---- Events ----
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            elif ev.type == pygame.MOUSEWHEEL:
                if screen in (Screen.PLAYING, Screen.ANALYSIS):
                    scroll = min(0, scroll + ev.y)

            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if screen == Screen.MENU:
                    for b in menu_btns:
                        if b.is_clicked(mouse):
                            screen = Screen.DIFFICULTY

                elif screen == Screen.DIFFICULTY:
                    for i, d in enumerate([Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]):
                        if diff_btns[i].is_clicked(mouse):
                            difficulty = d
                            game = CheckersGame()
                            ai = CheckersAI(game)
                            h_time = TIMER_TOTAL
                            a_time = TIMER_TOTAL
                            turn_start = _time.time()
                            prev_hist_len = 0
                            analysis_open = False
                            scroll = 0
                            screen = Screen.PLAYING
                            break

                elif screen == Screen.PLAYING:
                    # Analysis toggle (click bottom bar)
                    if mouse[1] >= BAR_Y:
                        analysis_open = not analysis_open
                    elif game.player_turn and mouse[1] >= BOARD_Y and mouse[1] < BAR_Y:
                        r, c = renderer.mouse_to_rc(mouse)
                        if game.selected_piece and (r, c) in game.valid_moves:
                            game.handle_piece_move(r, c)
                        else:
                            game.handle_piece_selection(r, c)

                elif screen == Screen.GAME_OVER:
                    if go_new_btn.is_clicked(mouse):
                        screen = Screen.DIFFICULTY
                    elif go_analysis_btn.is_clicked(mouse):
                        scroll = 0
                        screen = Screen.ANALYSIS

                elif screen == Screen.ANALYSIS:
                    if pa_new_btn.is_clicked(mouse):
                        screen = Screen.DIFFICULTY

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if screen == Screen.PLAYING:
                        screen = Screen.MENU
                    elif screen in (Screen.DIFFICULTY, Screen.GAME_OVER, Screen.ANALYSIS):
                        screen = Screen.MENU

        # ---- Track eval after each move ----
        if screen == Screen.PLAYING and len(game.move_history) > prev_hist_len:
            # Deduct time from the player who just moved
            elapsed = _time.time() - turn_start
            if not game.player_turn:
                # Human just moved (player_turn is now False)
                h_time -= elapsed
            else:
                # AI just moved (player_turn is now True)
                a_time -= elapsed
            turn_start = _time.time()

            # Record eval for accuracy tracking
            ev_score = CheckersAI.evaluate_position(game.board)
            game.move_history[-1].eval_score = ev_score
            prev_hist_len = len(game.move_history)

        # ---- Rendering ----
        if screen == Screen.MENU:
            renderer.draw_menu()
            for b in menu_btns:
                b.draw(win)
            pygame.display.update()

        elif screen == Screen.DIFFICULTY:
            renderer.draw_difficulty_select(diff_btns)
            pygame.display.update()

        elif screen == Screen.PLAYING:
            win.fill(DARK_BG)
            renderer.draw_hud(game, difficulty, ai_thinking, disp_h, disp_a)
            renderer.draw_board()
            renderer.draw_pieces(game)
            renderer.highlight_moves(game.valid_moves)
            renderer.draw_bottom_bar(analysis_open)
            if analysis_open:
                renderer.draw_analysis_overlay(game, ai.last_stats, scroll)
            pygame.display.update()

            # AI turn
            if not game.player_turn and not ai_thinking and not game.game_over:
                ai_thinking = True
                win.fill(DARK_BG)
                renderer.draw_hud(game, difficulty, ai_thinking, disp_h, disp_a)
                renderer.draw_board()
                renderer.draw_pieces(game)
                renderer.draw_bottom_bar(analysis_open)
                pygame.display.update()
                pygame.time.delay(300)
                ai.make_move_by_difficulty(difficulty)
                ai_thinking = False

            game.check_game_over()
            if game.game_over:
                h_acc, a_acc = compute_accuracy(game.move_history)
                screen = Screen.GAME_OVER

        elif screen == Screen.GAME_OVER:
            win.fill(DARK_BG)
            renderer.draw_hud(game, difficulty, False, disp_h, disp_a)
            renderer.draw_board()
            renderer.draw_pieces(game)
            renderer.draw_game_over(game, difficulty, go_btns)
            pygame.display.update()

        elif screen == Screen.ANALYSIS:
            renderer.draw_post_analysis(game, ai.last_stats, h_acc, a_acc, difficulty, scroll, pa_new_btn)
            pygame.display.update()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
