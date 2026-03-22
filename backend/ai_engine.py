"""
Checkers AI Engine (Backend)
All AI algorithms, evaluation heuristics, and performance tracking.
Optimizations: transposition table + move ordering.
"""

import random
import time
from backend.game_logic import CheckersGame, ROWS, COLS
from backend.enums import Algorithm, Difficulty


class AIStats:
    """Performance statistics for the last AI move."""
    def __init__(self):
        self.algorithm_name = ""
        self.search_depth = 0
        self.nodes_evaluated = 0
        self.branches_pruned = 0
        self.time_taken_ms = 0.0
        self.best_score = 0.0
        self.tt_hits = 0
        self.tt_size = 0

    @property
    def effective_branching_factor(self):
        if self.search_depth == 0 or self.nodes_evaluated == 0:
            return 0
        return round(self.nodes_evaluated ** (1.0 / self.search_depth), 2)

    @property
    def time_complexity(self):
        b = self.effective_branching_factor
        d = self.search_depth
        if self.algorithm_name in ('Alpha-Beta', 'Dynamic'):
            return f"O(b^(d/2)) ≈ O({b}^{d // 2})"
        elif self.algorithm_name == 'Minimax':
            return f"O(b^d) ≈ O({b}^{d})"
        return "O(n)"

    @property
    def space_complexity(self):
        b = self.effective_branching_factor
        d = self.search_depth
        if self.algorithm_name == 'Random':
            return "O(1)"
        return f"O(b×d) ≈ O({b}×{d})"


class CheckersAI:
    """AI engine with performance tracking and optimizations."""

    def __init__(self, game: CheckersGame):
        self.game = game
        self.last_stats = AIStats()
        self._nodes = 0
        self._pruned = 0
        self._tt_hits = 0
        self._tt = {}

    def _reset(self):
        self._nodes = 0
        self._pruned = 0
        self._tt_hits = 0
        self._tt.clear()

    # ==================== EVALUATION FUNCTIONS ====================

    @staticmethod
    def evaluate_board_simple(board_state):
        score = 0
        for row in range(ROWS):
            for col in range(COLS):
                p = board_state[row][col]
                if p == 1: score += 5
                elif p == 2: score += 10
                elif p == -1: score -= 5
                elif p == -2: score -= 10
        return score

    @staticmethod
    def evaluate_board_positional(board_state):
        score = 0
        for row in range(ROWS):
            for col in range(COLS):
                p = board_state[row][col]
                if p == 0:
                    continue
                pv = {1: 5, 2: 12, -1: -5, -2: -12}.get(p, 0)
                adv = row * 0.5 if p > 0 else -(ROWS - 1 - row) * 0.5
                edge = (0.3 if p > 0 else -0.3) if col in (0, COLS - 1) else 0
                ctr = (0.2 if p > 0 else -0.2) if 2 <= col <= 5 and 2 <= row <= 5 else 0
                score += pv + adv + edge + ctr
        return score

    @staticmethod
    def evaluate_board_dynamic(board_state):
        ai_p = sum(1 for r in board_state for c in r if c > 0)
        hu_p = sum(1 for r in board_state for c in r if c < 0)
        total = ai_p + hu_p
        phase = "opening" if total >= 18 else ("midgame" if total >= 10 else "endgame")
        score = 0
        for row in range(ROWS):
            for col in range(COLS):
                p = board_state[row][col]
                if p == 0:
                    continue
                sign = 1 if p > 0 else -1
                ik = abs(p) == 2
                mat = {("opening", False): 5, ("opening", True): 10,
                       ("midgame", False): 6, ("midgame", True): 14,
                       ("endgame", False): 7, ("endgame", True): 16}[(phase, ik)]
                adv = row if p > 0 else (ROWS - 1 - row)
                adv_w = {"opening": 0.3, "midgame": 0.6, "endgame": 1.0}[phase]
                adv_s = adv * adv_w
                cd = abs(col - 3.5) + abs(row - 3.5)
                ctr_s = max(0, 4 - cd) * (0.5 if phase == "opening" else 0.2)
                br = 0
                if phase != "endgame":
                    if (p > 0 and row == 0) or (p < 0 and row == ROWS - 1):
                        br = 0.8
                mob = len(CheckersGame.get_all_valid_moves(row, col, board_state)) * 0.1
                if ik and phase == "endgame":
                    mob *= 2
                score += sign * (mat + adv_s + ctr_s + br + mob)
        pa = ai_p - hu_p
        score += pa * (3 if phase == "endgame" else 1.5)
        return score

    # ==================== MOVE ORDERING ====================

    @staticmethod
    def _order_moves(moves):
        """Captures first for better pruning."""
        caps, reg = [], []
        for m in moves:
            (caps if abs(m[2] - m[0]) == 2 else reg).append(m)
        return caps + reg

    # ==================== SEARCH ALGORITHMS ====================

    def minimax(self, board_state, depth, is_maximizing, eval_func):
        self._nodes += 1
        ai_p = sum(1 for r in board_state for c in r if c > 0)
        hu_p = sum(1 for r in board_state for c in r if c < 0)
        if ai_p == 0: return -10000 - depth, None
        if hu_p == 0: return 10000 + depth, None
        all_moves = CheckersGame.get_all_moves_for_side(is_maximizing, board_state)
        if not all_moves:
            return (-10000 - depth if is_maximizing else 10000 + depth), None
        if depth == 0:
            return eval_func(board_state), None
        all_moves = self._order_moves(all_moves)
        best_move = None
        if is_maximizing:
            best = float('-inf')
            for m in all_moves:
                nb, _ = CheckersGame.apply_move(board_state, *m)
                s, _ = self.minimax(nb, depth - 1, False, eval_func)
                if s > best: best, best_move = s, m
            return best, best_move
        else:
            best = float('inf')
            for m in all_moves:
                nb, _ = CheckersGame.apply_move(board_state, *m)
                s, _ = self.minimax(nb, depth - 1, True, eval_func)
                if s < best: best, best_move = s, m
            return best, best_move

    def alpha_beta(self, board_state, depth, is_maximizing, alpha, beta, eval_func):
        self._nodes += 1
        # Transposition table lookup
        bk = tuple(tuple(r) for r in board_state)
        if bk in self._tt:
            ed, es, em = self._tt[bk]
            if ed >= depth:
                self._tt_hits += 1
                return es, em
        ai_p = sum(1 for r in board_state for c in r if c > 0)
        hu_p = sum(1 for r in board_state for c in r if c < 0)
        if ai_p == 0: return -10000 - depth, None
        if hu_p == 0: return 10000 + depth, None
        all_moves = CheckersGame.get_all_moves_for_side(is_maximizing, board_state)
        if not all_moves:
            return (-10000 - depth if is_maximizing else 10000 + depth), None
        if depth == 0:
            sc = eval_func(board_state)
            self._tt[bk] = (depth, sc, None)
            return sc, None
        all_moves = self._order_moves(all_moves)
        best_move = None
        cutoff = False
        if is_maximizing:
            best = float('-inf')
            for m in all_moves:
                nb, _ = CheckersGame.apply_move(board_state, *m)
                s, _ = self.alpha_beta(nb, depth - 1, False, alpha, beta, eval_func)
                if s > best: best, best_move = s, m
                alpha = max(alpha, s)
                if beta <= alpha:
                    self._pruned += 1
                    cutoff = True
                    break
        else:
            best = float('inf')
            for m in all_moves:
                nb, _ = CheckersGame.apply_move(board_state, *m)
                s, _ = self.alpha_beta(nb, depth - 1, True, alpha, beta, eval_func)
                if s < best: best, best_move = s, m
                beta = min(beta, s)
                if beta <= alpha:
                    self._pruned += 1
                    cutoff = True
                    break
        if not cutoff:
            self._tt[bk] = (depth, best, best_move)
        return best, best_move

    # ==================== MOVE STRATEGIES ====================

    def ai_move_random(self):
        all_moves = CheckersGame.get_all_moves_for_side(True, self.game.board)
        if not all_moves: return False
        self.game.execute_ai_move(*random.choice(all_moves))
        return True

    def _run_search(self, algo_name, depth, search_fn):
        self._reset()
        t0 = time.perf_counter()
        board_copy = [r[:] for r in self.game.board]
        score, move = search_fn(board_copy, depth)
        elapsed = (time.perf_counter() - t0) * 1000
        self.last_stats = AIStats()
        self.last_stats.algorithm_name = algo_name
        self.last_stats.search_depth = depth
        self.last_stats.nodes_evaluated = self._nodes
        self.last_stats.branches_pruned = self._pruned
        self.last_stats.time_taken_ms = elapsed
        self.last_stats.best_score = score if score else 0
        self.last_stats.tt_hits = self._tt_hits
        self.last_stats.tt_size = len(self._tt)
        if move:
            self.game.execute_ai_move(*move)
            return True
        return self.ai_move_random()

    def ai_move_minimax(self):
        return self._run_search("Minimax", 3,
            lambda b, d: self.minimax(b, d, True, self.evaluate_board_positional))

    def ai_move_alpha_beta(self):
        return self._run_search("Alpha-Beta", 5,
            lambda b, d: self.alpha_beta(b, d, True, float('-inf'), float('inf'),
                                         self.evaluate_board_positional))

    def ai_move_dynamic_heuristic(self):
        return self._run_search("Dynamic", 5,
            lambda b, d: self.alpha_beta(b, d, True, float('-inf'), float('inf'),
                                         self.evaluate_board_dynamic))

    def make_move(self, algorithm):
        moved = False
        if algorithm == Algorithm.RANDOM:
            self.last_stats = AIStats()
            self.last_stats.algorithm_name = "Random"
            moved = self.ai_move_random()
        elif algorithm == Algorithm.MINIMAX:
            moved = self.ai_move_minimax()
        elif algorithm == Algorithm.ALPHA_BETA:
            moved = self.ai_move_alpha_beta()
        elif algorithm == Algorithm.DYNAMIC_HEURISTIC:
            moved = self.ai_move_dynamic_heuristic()
        if moved:
            self.game.finish_ai_turn()
        return moved

    def make_move_by_difficulty(self, difficulty):
        """Auto-select algorithm based on difficulty level."""
        if difficulty == Difficulty.EASY:
            self.last_stats = AIStats()
            self.last_stats.algorithm_name = "Random"
            moved = self.ai_move_random()
        elif difficulty == Difficulty.MEDIUM:
            moved = self._run_search("Alpha-Beta (d3)", 3,
                lambda b, d: self.alpha_beta(b, d, True, float('-inf'), float('inf'),
                                             self.evaluate_board_positional))
        else:  # HARD
            moved = self._run_search("Alpha-Beta (d5)", 5,
                lambda b, d: self.alpha_beta(b, d, True, float('-inf'), float('inf'),
                                             self.evaluate_board_dynamic))
        if moved:
            self.game.finish_ai_turn()
        return moved

    @staticmethod
    def evaluate_position(board_state):
        """Quick evaluation for accuracy tracking. Positive = AI advantage."""
        return CheckersAI.evaluate_board_dynamic(board_state)

