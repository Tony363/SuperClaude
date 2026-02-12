mod game;
mod hangman_art;
mod word_list;

use anyhow::Result;
use colored::*;
use game::Game;
use std::io::{self, Write};

fn main() -> Result<()> {
    display_welcome();

    loop {
        let mut game = Game::new();
        play_game(&mut game)?;

        if !play_again()? {
            display_goodbye();
            break;
        }
    }

    Ok(())
}

fn display_welcome() {
    println!("\n{}", "╔═══════════════════════════════════════╗".bright_cyan());
    println!("{}", "║     WELCOME TO HANGMAN GAME!          ║".bright_cyan());
    println!("{}", "╚═══════════════════════════════════════╝".bright_cyan());
    println!("\n{}", "Guess the word letter by letter.".yellow());
    println!("{}", "You have 6 incorrect guesses before you lose!\n".yellow());
}

fn display_goodbye() {
    println!("\n{}", "╔═══════════════════════════════════════╗".bright_cyan());
    println!("{}", "║     THANKS FOR PLAYING HANGMAN!       ║".bright_cyan());
    println!("{}", "╚═══════════════════════════════════════╝".bright_cyan());
    println!();
}

fn play_game(game: &mut Game) -> Result<()> {
    while !game.is_game_over() {
        game.display_state();

        let guess = get_user_guess()?;

        match game.make_guess(guess) {
            Ok(true) => {
                println!("\n{}", "✓ Correct guess!".bright_green().bold());
            }
            Ok(false) => {
                println!("\n{}", "✗ Wrong guess!".bright_red().bold());
            }
            Err(e) => {
                println!("\n{}", format!("⚠ {}", e).yellow());
            }
        }

        println!("\n{}", "─".repeat(50).bright_black());
    }

    game.display_final_result();
    Ok(())
}

fn get_user_guess() -> Result<char> {
    loop {
        print!("\n{}", "Enter your guess (single letter): ".bright_white().bold());
        io::stdout().flush()?;

        let mut input = String::new();
        io::stdin().read_line(&mut input)?;

        let input = input.trim();

        if input.len() != 1 {
            println!("{}", "Please enter exactly one letter!".red());
            continue;
        }

        let ch = input.chars().next().unwrap();

        if !ch.is_alphabetic() {
            println!("{}", "Please enter a letter (a-z)!".red());
            continue;
        }

        return Ok(ch.to_ascii_lowercase());
    }
}

fn play_again() -> Result<bool> {
    loop {
        print!("\n{}", "Play again? (y/n): ".bright_white().bold());
        io::stdout().flush()?;

        let mut input = String::new();
        io::stdin().read_line(&mut input)?;

        match input.trim().to_lowercase().as_str() {
            "y" | "yes" => return Ok(true),
            "n" | "no" => return Ok(false),
            _ => println!("{}", "Please enter 'y' or 'n'!".red()),
        }
    }
}
