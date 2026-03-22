"""
Checkers Game Logic (Backend) — American Rules
Pure game-state management with no UI dependencies.

Rules implemented:
  ✔ Diagonal movement only
  ✔ Forward-only for men, all directions for kings
  ✔ Mandatory/forced capture
  ✔ Multi-jump chain capture
  ✔ King promotion on opponent's last row
  ✔ Turn ends immediately on promotion (American rules)
  ✔ Win by elimination or stalemate
  ✔ Draw by threefold repetition
  ✔ Draw by 40 moves without capture
  ✔ Draw by insufficient material (King vs King)
  ✔ Move history with algebraic notation
"""

import time

ROWS, COLS = 8, 8
COL_LABELS = 'abcdefgh'


class MoveRecord:
    """Record of a single completed turn."""
    def __init__(self, move_number, player, from_pos, to_pos, notation,
                 is_capture=False, is_promotion=False, captures_count=0,
                 eval_score=0.0):
        self.move_number = move_number
        self.player = player
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.notation = notation
        self.is_capture = is_capture
        self.is_promotion = is_promotion
        self.captures_count = captures_count
        self.eval_score = eval_score
        self.timestamp = time.time()


class CheckersGame:
    """Encapsulates the full state and rules of American Checkers."""

    def __init__(self):
        self.board = []
        self.player_turn = True
        self.game_over = False
        self.winner = None
        self.draw_reason = None
        self.human_captured = 0
        self.ai_captured = 0
        self.moves_count = 0
        self.selected_piece = None
        self.valid_moves = []
        self.move_history = []
        self._move_chain = []
        self._ai_move_chain = []
        # Draw detection state
        self.moves_without_capture = 0
        self.position_history = {}
        self.initialize_board()

    # -------------------- Board Setup --------------------
    def initialize_board(self):
        """Reset the board to starting position (12 pieces each)."""
        self.board = [
            [0, 1, 0, 1, 0, 1, 0, 1],
            [1, 0, 1, 0, 1, 0, 1, 0],
            [0, 1, 0, 1, 0, 1, 0, 1],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [-1, 0, -1, 0, -1, 0, -1, 0],
            [0, -1, 0, -1, 0, -1, 0, -1],
            [-1, 0, -1, 0, -1, 0, -1, 0],
        ]
        self.selected_piece = None
        self.valid_moves = []
        self.player_turn = True
        self.game_over = False
        self.winner = None
        self.draw_reason = None
        self.human_captured = 0
        self.ai_captured = 0
        self.moves_count = 0
        self.move_history = []
        self._move_chain = []
        self._ai_move_chain = []
        self.moves_without_capture = 0
        self.position_history = {}
        # Record the initial board position
        self._record_position()

    # -------------------- Notation --------------------
    @staticmethod
    def get_square_name(row, col):
        """Convert (row, col) to algebraic notation like 'a8', 'h1'."""
        return f"{COL_LABELS[col]}{8 - row}"

    def _build_chain_notation(self, chain):
        if not chain:
            return ""
        parts = [self.get_square_name(chain[0][0], chain[0][1])]
        for step in chain:
            sep = '×' if abs(step[2] - step[0]) == 2 else '→'
            parts.append(f"{sep}{self.get_square_name(step[2], step[3])}")
        return ''.join(parts)

    # -------------------- Draw Detection Helpers --------------------
    def _get_board_key(self):
        """Hashable board state for repetition detection."""
        return (tuple(tuple(row) for row in self.board), self.player_turn)

    def _record_position(self):
        """Record current position for threefold repetition check."""
        key = self._get_board_key()
        self.position_history[key] = self.position_history.get(key, 0) + 1

    # -------------------- Move Recording --------------------
    def _commit_move_chain(self, player, chain, captures_in_chain):
        if not chain:
            return
        from_pos = (chain[0][0], chain[0][1])
        to_pos = (chain[-1][2], chain[-1][3])
        notation = self._build_chain_notation(chain)

        # Check if promotion happened
        dest_piece = self.board[to_pos[0]][to_pos[1]]
        is_promotion = False
        if abs(dest_piece) == 2:
            if (player == 'human' and to_pos[0] == 0) or \
               (player == 'ai' and to_pos[0] == ROWS - 1):
                notation += ' ♛'
                is_promotion = True

        self.moves_count += 1

        # Track captures for 40-move draw rule
        if captures_in_chain > 0:
            self.moves_without_capture = 0
        else:
            self.moves_without_capture += 1

        self.move_history.append(MoveRecord(
            move_number=self.moves_count, player=player,
            from_pos=from_pos, to_pos=to_pos, notation=notation,
            is_capture=captures_in_chain > 0, is_promotion=is_promotion,
            captures_count=captures_in_chain,
        ))

        # Record position after move for repetition detection
        self._record_position()

    # -------------------- Piece Counts --------------------
    def count_pieces(self, board_state=None):
        if board_state is None:
            board_state = self.board
        human = sum(1 for row in board_state for cell in row if cell < 0)
        ai = sum(1 for row in board_state for cell in row if cell > 0)
        return human, ai

    # -------------------- Move Validation --------------------
    @staticmethod
    def get_all_valid_moves(piece_row, piece_col, board_state):
        """Get all valid moves for a piece (forced capture enforced)."""
        piece = board_state[piece_row][piece_col]
        if piece == 0:
            return []
        moves, jump_moves = [], []
        is_king = abs(piece) == 2
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            if not is_king:
                if piece > 0 and dr < 0:   # AI men: forward = downward only
                    continue
                if piece < 0 and dr > 0:   # Human men: forward = upward only
                    continue
            # Regular move (1 square diagonal)
            nr, nc = piece_row + dr, piece_col + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS and board_state[nr][nc] == 0:
                moves.append((nr, nc))
            # Jump move (2 squares diagonal, capturing middle piece)
            jr, jc = piece_row + 2 * dr, piece_col + 2 * dc
            mr, mc = piece_row + dr, piece_col + dc
            if 0 <= jr < ROWS and 0 <= jc < COLS:
                if board_state[jr][jc] == 0 and board_state[mr][mc] != 0:
                    mp = board_state[mr][mc]
                    if (piece > 0 and mp < 0) or (piece < 0 and mp > 0):
                        jump_moves.append((jr, jc))
        # Forced capture: if jumps exist, must take them
        return jump_moves if jump_moves else moves

    @staticmethod
    def get_all_jump_moves_for_piece(piece_row, piece_col, board_state):
        """Get only jump moves for a piece (used for multi-jump)."""
        piece = board_state[piece_row][piece_col]
        if piece == 0:
            return []
        jump_moves = []
        is_king = abs(piece) == 2
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            if not is_king:
                if piece > 0 and dr < 0:
                    continue
                if piece < 0 and dr > 0:
                    continue
            jr, jc = piece_row + 2 * dr, piece_col + 2 * dc
            mr, mc = piece_row + dr, piece_col + dc
            if 0 <= jr < ROWS and 0 <= jc < COLS:
                if board_state[jr][jc] == 0 and board_state[mr][mc] != 0:
                    mp = board_state[mr][mc]
                    if (piece > 0 and mp < 0) or (piece < 0 and mp > 0):
                        jump_moves.append((jr, jc))
        return jump_moves

    @staticmethod
    def must_jump(is_ai, board_state):
        """Check if the given side has any forced jumps."""
        for row in range(ROWS):
            for col in range(COLS):
                p = board_state[row][col]
                if p == 0:
                    continue
                if is_ai and p < 0:
                    continue
                if not is_ai and p > 0:
                    continue
                if CheckersGame.get_all_jump_moves_for_piece(row, col, board_state):
                    return True
        return False

    @staticmethod
    def get_all_moves_for_side(is_ai, board_state):
        """Get all (from_r, from_c, to_r, to_c) moves for one side."""
        all_moves = []
        has_jumps = CheckersGame.must_jump(is_ai, board_state)
        for row in range(ROWS):
            for col in range(COLS):
                p = board_state[row][col]
                if p == 0:
                    continue
                if is_ai and p < 0:
                    continue
                if not is_ai and p > 0:
                    continue
                if has_jumps:
                    moves = CheckersGame.get_all_jump_moves_for_piece(row, col, board_state)
                else:
                    moves = CheckersGame.get_all_valid_moves(row, col, board_state)
                for (tr, tc) in moves:
                    all_moves.append((row, col, tr, tc))
        return all_moves

    @staticmethod
    def apply_move(board_state, from_row, from_col, to_row, to_col):
        """Apply a move to a board copy. Returns (new_board, captured_piece)."""
        new_board = [r[:] for r in board_state]
        piece = new_board[from_row][from_col]
        new_board[to_row][to_col] = piece
        new_board[from_row][from_col] = 0
        captured = None
        if abs(to_row - from_row) == 2:
            mr = (from_row + to_row) // 2
            mc = (from_col + to_col) // 2
            captured = new_board[mr][mc]
            new_board[mr][mc] = 0
        # King promotion
        if piece == 1 and to_row == ROWS - 1:
            new_board[to_row][to_col] = 2
        elif piece == -1 and to_row == 0:
            new_board[to_row][to_col] = -2
        return new_board, captured

    # -------------------- Player Actions --------------------
    def handle_piece_selection(self, row, col):
        """Select a human piece and compute its valid moves."""
        if self.board[row][col] < 0:
            forced = self.must_jump(is_ai=False, board_state=self.board)
            if forced:
                jumps = self.get_all_jump_moves_for_piece(row, col, self.board)
                if jumps:
                    self.selected_piece = (row, col)
                    self.valid_moves = jumps
                else:
                    self.selected_piece = None
                    self.valid_moves = []
            else:
                self.selected_piece = (row, col)
                self.valid_moves = self.get_all_valid_moves(row, col, self.board)
        else:
            self.selected_piece = None
            self.valid_moves = []

    def handle_piece_move(self, to_row, to_col):
        """Move the selected human piece. Returns True if turn ended."""
        if not (self.selected_piece and (to_row, to_col) in self.valid_moves):
            return False

        from_row, from_col = self.selected_piece
        piece = self.board[from_row][from_col]
        self._move_chain.append((from_row, from_col, to_row, to_col))

        # 1. Move piece
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = 0

        # 2. Handle capture (remove jumped piece)
        is_capture = abs(to_row - from_row) == 2
        if is_capture:
            mr = (from_row + to_row) // 2
            mc = (from_col + to_col) // 2
            if self.board[mr][mc] > 0:
                self.board[mr][mc] = 0
                self.human_captured += 1

        # 3. Check king promotion
        promoted = False
        if piece == -1 and to_row == 0:
            self.board[to_row][to_col] = -2
            promoted = True

        # 4. Multi-jump: continue ONLY if captured AND NOT promoted
        #    (American rules: turn ends immediately on promotion)
        if is_capture and not promoted:
            further = self.get_all_jump_moves_for_piece(to_row, to_col, self.board)
            if further:
                self.selected_piece = (to_row, to_col)
                self.valid_moves = further
                return False  # Chain continues — turn is NOT over

        # 5. Turn complete — commit the chain
        caps = sum(1 for s in self._move_chain if abs(s[2] - s[0]) == 2)
        self._commit_move_chain('human', self._move_chain, caps)
        self._move_chain = []
        self.selected_piece = None
        self.valid_moves = []
        self.player_turn = False
        return True

    # -------------------- AI Move Execution --------------------
    def execute_ai_move(self, from_row, from_col, to_row, to_col):
        """Execute an AI move on the live board, with multi-jump."""
        self._ai_move_chain.append((from_row, from_col, to_row, to_col))
        piece = self.board[from_row][from_col]

        # 1. Move piece
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = 0

        # 2. Handle capture
        is_capture = abs(to_row - from_row) == 2
        if is_capture:
            mr = (from_row + to_row) // 2
            mc = (from_col + to_col) // 2
            if self.board[mr][mc] < 0:
                self.board[mr][mc] = 0
                self.ai_captured += 1

        # 3. King promotion
        promoted = False
        if piece == 1 and to_row == ROWS - 1:
            self.board[to_row][to_col] = 2
            promoted = True

        # 4. Multi-jump (only if captured AND NOT promoted)
        if is_capture and not promoted:
            further = self.get_all_jump_moves_for_piece(to_row, to_col, self.board)
            if further:
                self.execute_ai_move(to_row, to_col, further[0][0], further[0][1])

    def finish_ai_turn(self):
        """Mark AI turn as complete and record the move."""
        caps = sum(1 for s in self._ai_move_chain if abs(s[2] - s[0]) == 2)
        self._commit_move_chain('ai', self._ai_move_chain, caps)
        self._ai_move_chain = []
        self.player_turn = True

    # -------------------- Game Over & Draw Detection --------------------
    def check_game_over(self):
        """Check win conditions AND draw conditions."""
        human, ai = self.count_pieces()

        # --- Win conditions ---
        if human == 0:
            self.game_over, self.winner = True, "AI"
            return True
        if ai == 0:
            self.game_over, self.winner = True, "HUMAN"
            return True

        # Stalemate: current player has no legal moves
        if self.player_turn:
            if not self.get_all_moves_for_side(False, self.board):
                self.game_over, self.winner = True, "AI"
                return True
        else:
            if not self.get_all_moves_for_side(True, self.board):
                self.game_over, self.winner = True, "HUMAN"
                return True

        # --- Draw conditions ---

        # 1. Threefold repetition
        key = self._get_board_key()
        if self.position_history.get(key, 0) >= 3:
            self.game_over = True
            self.winner = "DRAW"
            self.draw_reason = "Threefold Repetition"
            return True

        # 2. 40-move rule (40 consecutive moves with no capture)
        if self.moves_without_capture >= 40:
            self.game_over = True
            self.winner = "DRAW"
            self.draw_reason = "40 Moves Without Capture"
            return True

        # 3. Insufficient material (King vs King only)
        if human == 1 and ai == 1:
            h_kings = sum(1 for row in self.board for c in row if c == -2)
            a_kings = sum(1 for row in self.board for c in row if c == 2)
            if h_kings == 1 and a_kings == 1:
                self.game_over = True
                self.winner = "DRAW"
                self.draw_reason = "Insufficient Material (King vs King)"
                return True

        return False
