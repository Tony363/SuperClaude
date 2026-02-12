use crate::hangman_art::HangmanArt;
use crate::word_list::WordList;
use anyhow::{bail, Result};
use colored::*;
use std::collections::HashSet;

const MAX_INCORRECT_GUESSES: usize = 6;

#[derive(Debug)]
pub struct Game {
    word: String,
    guessed_letters: HashSet<char>,
    incorrect_guesses: usize,
}

impl Game {
    pub fn new() -> Self {
        let word_list = WordList::new();
        let word = word_list.get_random_word();

        Self {
            word,
            guessed_letters: HashSet::new(),
            incorrect_guesses: 0,
        }
    }

    pub fn make_guess(&mut self, letter: char) -> Result<bool> {
        if !letter.is_ascii_lowercase() {
            bail!("Letter must be lowercase a-z");
        }

        if self.guessed_letters.contains(&letter) {
            bail!("You already guessed '{}'", letter);
        }

        self.guessed_letters.insert(letter);

        if self.word.contains(letter) {
            Ok(true)
        } else {
            self.incorrect_guesses += 1;
            Ok(false)
        }
    }

    pub fn is_game_over(&self) -> bool {
        self.is_won() || self.is_lost()
    }

    pub fn is_won(&self) -> bool {
        self.word
            .chars()
            .all(|ch| self.guessed_letters.contains(&ch))
    }

    pub fn is_lost(&self) -> bool {
        self.incorrect_guesses >= MAX_INCORRECT_GUESSES
    }

    pub fn display_state(&self) {
        println!("\n{}", HangmanArt::get_art(self.incorrect_guesses));

        println!(
            "\n{} {} / {}",
            "Incorrect guesses:".bright_yellow(),
            self.incorrect_guesses.to_string().bright_red().bold(),
            MAX_INCORRECT_GUESSES
        );

        let word_display = self.get_word_display();
        println!("\n{} {}", "Word:".bright_cyan(), word_display);

        let guessed = self.get_guessed_letters_display();
        println!("\n{} {}", "Guessed letters:".bright_magenta(), guessed);
    }

    pub fn display_final_result(&self) {
        println!("\n{}", "═".repeat(50).bright_cyan());

        if self.is_won() {
            println!("\n{}", "🎉 CONGRATULATIONS! YOU WON! 🎉".bright_green().bold());
            println!("\n{} {}", "The word was:".bright_white(), self.word.bright_green().bold());
        } else {
            println!("\n{}", HangmanArt::get_art(self.incorrect_guesses));
            println!("\n{}", "💀 GAME OVER! YOU LOST! 💀".bright_red().bold());
            println!("\n{} {}", "The word was:".bright_white(), self.word.bright_yellow().bold());
        }

        println!("\n{}", "═".repeat(50).bright_cyan());
    }

    fn get_word_display(&self) -> String {
        self.word
            .chars()
            .map(|ch| {
                if self.guessed_letters.contains(&ch) {
                    format!("{} ", ch.to_string().bright_green().bold())
                } else {
                    "_ ".to_string()
                }
            })
            .collect()
    }

    fn get_guessed_letters_display(&self) -> String {
        if self.guessed_letters.is_empty() {
            return "none".bright_black().to_string();
        }

        let mut sorted: Vec<char> = self.guessed_letters.iter().copied().collect();
        sorted.sort();

        sorted
            .iter()
            .map(|ch| {
                if self.word.contains(*ch) {
                    ch.to_string().bright_green()
                } else {
                    ch.to_string().bright_red()
                }
            })
            .map(|s| s.to_string())
            .collect::<Vec<_>>()
            .join(", ")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_game() {
        let game = Game::new();
        assert!(!game.word.is_empty());
        assert_eq!(game.incorrect_guesses, 0);
        assert!(game.guessed_letters.is_empty());
    }

    #[test]
    fn test_correct_guess() {
        let mut game = Game::new();
        let word = game.word.clone();
        let first_char = word.chars().next().unwrap();

        let result = game.make_guess(first_char);
        assert!(result.is_ok());
        assert!(result.unwrap());
        assert_eq!(game.incorrect_guesses, 0);
    }

    #[test]
    fn test_incorrect_guess() {
        let mut game = Game::new();

        // Find a letter not in the word
        let letter = ('a'..='z')
            .find(|&ch| !game.word.contains(ch))
            .unwrap();

        let result = game.make_guess(letter);
        assert!(result.is_ok());
        assert!(!result.unwrap());
        assert_eq!(game.incorrect_guesses, 1);
    }

    #[test]
    fn test_duplicate_guess() {
        let mut game = Game::new();
        let word = game.word.clone();
        let first_char = word.chars().next().unwrap();

        game.make_guess(first_char).unwrap();
        let result = game.make_guess(first_char);

        assert!(result.is_err());
    }

    #[test]
    fn test_game_lost() {
        let mut game = Game::new();

        // Make MAX_INCORRECT_GUESSES wrong guesses
        let mut wrong_letters = Vec::new();
        for ch in 'a'..='z' {
            if !game.word.contains(ch) {
                wrong_letters.push(ch);
                if wrong_letters.len() >= MAX_INCORRECT_GUESSES {
                    break;
                }
            }
        }

        for &letter in &wrong_letters {
            game.make_guess(letter).unwrap();
        }

        assert!(game.is_lost());
        assert!(game.is_game_over());
    }
}
