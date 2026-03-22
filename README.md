# ♟️ Checkers AI — Multiple Difficulty Levels

A fully-featured **Checkers (Draughts)** game where a human plays against an AI opponent. Built with **Python + Pygame**, featuring classic AI search algorithms.

## 🎮 Features

- **3 Difficulty Levels**: Easy (Random), Medium (Alpha-Beta d3), Hard (Alpha-Beta d5 + Dynamic Heuristic)
- **Chess-style Timers**: 10 minutes per player
- **Move Analysis Panel**: Toggleable during gameplay
- **Post-Game Analysis**: Accuracy bars, move quality classification, eval history
- **Full American Rules**: Forced capture, multi-jump, king promotion stops chain, draw detection

## 🧠 AI Algorithms

| Difficulty | Algorithm | Search Depth |
|---|---|---|
| Easy | Random | 0 |
| Medium | Alpha-Beta Pruning + Positional Eval | 3 |
| Hard | Alpha-Beta Pruning + Dynamic Heuristic | 5 |

### Optimizations
- **Move Ordering** — captures explored first for better pruning
- **Transposition Table** — caches evaluated positions

## 📐 Project Structure

```
├── main.py                  # Entry point
├── backend/
│   ├── enums.py             # Difficulty & Algorithm enums
│   ├── game_logic.py        # CheckersGame (rules, board, moves)
│   └── ai_engine.py         # CheckersAI (search + evaluation)
├── frontend/
│   ├── ui_components.py     # Button widget
│   ├── renderer.py          # Pygame drawing engine
│   └── app.py               # Main game loop + timers
```

## 🚀 How to Run

```bash
# Install pygame
pip install pygame

# Run the game
python main.py
```

## 📜 Rules Implemented (American Checkers)

- ✔ Diagonal movement only
- ✔ Forward-only for men, all directions for kings
- ✔ Mandatory/forced capture
- ✔ Multi-jump chain capture
- ✔ King promotion on opponent's last row
- ✔ Turn ends on promotion (American rules)
- ✔ Draw by threefold repetition
- ✔ Draw by 40 moves without capture
- ✔ Draw by insufficient material

## 👥 Team

AI Algorithms Project — 2026
