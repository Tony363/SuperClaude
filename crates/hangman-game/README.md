# Hangman Game

A comprehensive, feature-rich command-line Hangman game written in Rust.

## Features

- **Colorful Terminal UI**: Beautiful colored output using the `colored` crate
- **ASCII Art**: Progressive hangman drawings for each incorrect guess
- **Large Word Database**: 150+ words across multiple categories:
  - Animals (elephant, giraffe, kangaroo, etc.)
  - Food (pizza, chocolate, strawberry, etc.)
  - Technology (computer, algorithm, blockchain, etc.)
  - Nature (volcano, hurricane, waterfall, etc.)
  - Sports (basketball, gymnastics, marathon, etc.)
  - Professions (astronaut, engineer, scientist, etc.)
  - Abstract concepts (democracy, imagination, wisdom, etc.)
  - Geography (continent, archipelago, hemisphere, etc.)
  - Space (galaxy, nebula, supernova, etc.)
- **Input Validation**: Ensures valid single-letter guesses
- **Duplicate Detection**: Prevents guessing the same letter twice
- **Game State Display**: Clear visualization of:
  - Current hangman drawing
  - Incorrect guess count
  - Word progress with revealed letters
  - All guessed letters (color-coded: green for correct, red for wrong)
- **Replay Option**: Play multiple games in succession
- **Comprehensive Tests**: Full test coverage for game logic, word selection, and ASCII art

## Building

```bash
# Build the game
cargo build --package hangman-game --release

# Run tests
cargo test --package hangman-game
```

## Running

```bash
# From the workspace root
cargo run --package hangman-game

# Or run the binary directly after building
./target/release/hangman
```

## Gameplay

1. The game randomly selects a word from the word database
2. You have 6 incorrect guesses before losing
3. Enter one letter at a time to guess
4. The hangman drawing progresses with each incorrect guess
5. Win by revealing all letters before running out of guesses
6. Choose to play again or exit

## Example Session

```
╔═══════════════════════════════════════╗
║     WELCOME TO HANGMAN GAME!          ║
╚═══════════════════════════════════════╝

Guess the word letter by letter.
You have 6 incorrect guesses before you lose!


  +---+
  |   |
      |
      |
      |
      |
=========

Incorrect guesses: 0 / 6

Word: _ _ _ _ _ _ _ _

Guessed letters: none

Enter your guess (single letter): e

✓ Correct guess!

──────────────────────────────────────────────────

  +---+
  |   |
      |
      |
      |
      |
=========

Incorrect guesses: 0 / 6

Word: e _ e _ _ _ _ _

Guessed letters: e
```

## Code Structure

- `main.rs`: Game loop, user input handling, and display logic
- `game.rs`: Core game state management and logic
- `hangman_art.rs`: ASCII art for hangman stages (0-6)
- `word_list.rs`: Word database and random selection

## Testing

The game includes comprehensive unit tests:

```bash
cargo test --package hangman-game -- --nocapture
```

Test coverage includes:
- Game initialization
- Correct and incorrect guesses
- Duplicate guess detection
- Win/loss conditions
- ASCII art rendering
- Word selection randomness

## Dependencies

- `anyhow`: Error handling
- `rand`: Random word selection
- `colored`: Terminal color output

## License

MIT License (inherited from workspace)
