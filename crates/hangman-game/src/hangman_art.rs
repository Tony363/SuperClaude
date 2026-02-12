use colored::*;

pub struct HangmanArt;

impl HangmanArt {
    pub fn get_art(stage: usize) -> ColoredString {
        let art = match stage {
            0 => Self::stage_0(),
            1 => Self::stage_1(),
            2 => Self::stage_2(),
            3 => Self::stage_3(),
            4 => Self::stage_4(),
            5 => Self::stage_5(),
            6 => Self::stage_6(),
            _ => Self::stage_6(),
        };

        art.bright_yellow()
    }

    fn stage_0() -> String {
        r#"
  +---+
  |   |
      |
      |
      |
      |
========="#
            .to_string()
    }

    fn stage_1() -> String {
        r#"
  +---+
  |   |
  O   |
      |
      |
      |
========="#
            .to_string()
    }

    fn stage_2() -> String {
        r#"
  +---+
  |   |
  O   |
  |   |
      |
      |
========="#
            .to_string()
    }

    fn stage_3() -> String {
        r#"
  +---+
  |   |
  O   |
 /|   |
      |
      |
========="#
            .to_string()
    }

    fn stage_4() -> String {
        r#"
  +---+
  |   |
  O   |
 /|\  |
      |
      |
========="#
            .to_string()
    }

    fn stage_5() -> String {
        r#"
  +---+
  |   |
  O   |
 /|\  |
 /    |
      |
========="#
            .to_string()
    }

    fn stage_6() -> String {
        r#"
  +---+
  |   |
  O   |
 /|\  |
 / \  |
      |
========="#
            .to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_all_stages() {
        for stage in 0..=6 {
            let art = HangmanArt::get_art(stage);
            assert!(!art.is_empty());
        }
    }

    #[test]
    fn test_stage_0_empty() {
        let art = HangmanArt::get_art(0);
        assert!(art.contains("+---+"));
        assert!(!art.contains('O')); // No head yet
    }

    #[test]
    fn test_stage_6_complete() {
        let art = HangmanArt::get_art(6);
        assert!(art.contains('O')); // Head
        assert!(art.contains('|')); // Body
        assert!(art.contains('/')); // Arms and legs
        assert!(art.contains('\\')); // Arms and legs
    }
}
