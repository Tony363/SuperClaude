# Snake Game

A classic Snake game implementation in Rust with a modern graphical UI using Macroquad.

## Features

- Full graphical window-based UI with smooth rendering
- Classic snake gameplay with responsive controls
- Multiple game states: Menu, Playing, Paused, Game Over
- Score tracking with high score persistence
- Beautiful visual design with:
  - Checkered grid background
  - Animated snake with directional eyes
  - Glowing food particles
  - Smooth color transitions and animations
- Pause functionality
- Restart and return to menu options

## Controls

### Menu
- **SPACE** or **ENTER**: Start game
- **Q** or **ESC**: Quit game

### Playing
- **Arrow Keys** or **WASD**: Move the snake
- **SPACE** or **P**: Pause game
- **ESC**: Return to menu

### Paused
- **SPACE** or **P**: Resume game
- **ESC**: Return to menu

### Game Over
- **SPACE** or **R**: Restart game
- **ESC** or **M**: Return to menu

## How to Play

1. Build and run the game:
   ```bash
   cargo run -p snake-game --release
   ```
   Or from the snake-game directory:
   ```bash
   cargo run --release
   ```

2. The game will open in a new window with a menu screen
3. Press SPACE or ENTER to start playing
4. Control the snake to eat the red food circles
5. Each food increases your score by 10 and makes the snake grow
6. Avoid hitting the walls or yourself
7. Try to beat your high score!

## Game Elements

- **Green squares with eyes**: Snake (head has eyes facing the direction of movement)
- **Red glowing circles**: Food
- **Checkered grid**: Playing field
- **Border**: Game boundaries

## Technical Details

The game is built with:
- **macroquad**: Fast and simple 2D game framework with graphics rendering
- Runs at 60 FPS with smooth animations
- Game logic updates at configurable speed (default: 150ms per move)
- Clean architecture with:
  - `Position`: Coordinate representation
  - `Direction`: Movement direction with opposite checking
  - `Snake`: Snake state, movement, and collision detection
  - `Game`: Game state management with multiple states (Menu, Playing, Paused, GameOver)
  - Separate rendering functions for each game state

## Customization

You can easily customize the game by modifying these constants in `src/main.rs`:
- `GRID_SIZE`: Size of the game grid (default: 20x20)
- `CELL_SIZE`: Size of each cell in pixels (default: 30)
- `GAME_SPEED`: Time between snake moves in seconds (default: 0.15)

## Building

Requirements:
- Rust 1.65 or later
- Cargo

Build the release version for optimal performance:
```bash
cargo build --release
```

The executable will be located at `target/release/snake-game`.
