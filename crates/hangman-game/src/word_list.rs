use rand::seq::SliceRandom;
use rand::thread_rng;

#[derive(Debug)]
pub struct WordList {
    words: Vec<&'static str>,
}

impl WordList {
    pub fn new() -> Self {
        Self {
            words: vec![
                // Animals
                "elephant",
                "giraffe",
                "kangaroo",
                "penguin",
                "dolphin",
                "cheetah",
                "rhinoceros",
                "alligator",
                "butterfly",
                "octopus",
                "flamingo",
                "leopard",
                "walrus",
                "zebra",
                "hamster",
                // Food
                "pizza",
                "hamburger",
                "spaghetti",
                "chocolate",
                "strawberry",
                "avocado",
                "blueberry",
                "watermelon",
                "pineapple",
                "broccoli",
                "cinnamon",
                "paprika",
                "vanilla",
                "croissant",
                "pretzel",
                // Technology
                "computer",
                "keyboard",
                "internet",
                "algorithm",
                "software",
                "database",
                "javascript",
                "python",
                "blockchain",
                "cybersecurity",
                "artificial",
                "quantum",
                "microchip",
                "bandwidth",
                "encryption",
                // Nature
                "mountain",
                "volcano",
                "hurricane",
                "rainbow",
                "waterfall",
                "lightning",
                "avalanche",
                "earthquake",
                "tsunami",
                "glacier",
                "canyon",
                "desert",
                "forest",
                "meadow",
                "cliff",
                // Objects
                "umbrella",
                "telescope",
                "microscope",
                "camera",
                "guitar",
                "piano",
                "trumpet",
                "saxophone",
                "violin",
                "drums",
                "binoculars",
                "compass",
                "parachute",
                "bicycle",
                "helicopter",
                // Professions
                "architect",
                "astronaut",
                "musician",
                "engineer",
                "scientist",
                "veterinarian",
                "firefighter",
                "detective",
                "journalist",
                "photographer",
                "magician",
                "librarian",
                "carpenter",
                "plumber",
                "electrician",
                // Abstract concepts
                "democracy",
                "imagination",
                "philosophy",
                "revolution",
                "knowledge",
                "adventure",
                "harmony",
                "mystery",
                "creativity",
                "freedom",
                "justice",
                "wisdom",
                "courage",
                "patience",
                "gratitude",
                // Geography
                "continent",
                "antarctica",
                "archipelago",
                "peninsula",
                "equator",
                "latitude",
                "longitude",
                "hemisphere",
                "plateau",
                "savanna",
                "tundra",
                "prairie",
                "oasis",
                "fjord",
                "lagoon",
                // Sports
                "basketball",
                "volleyball",
                "badminton",
                "gymnastics",
                "swimming",
                "marathon",
                "wrestling",
                "archery",
                "fencing",
                "skateboarding",
                "surfing",
                "cycling",
                "boxing",
                "karate",
                "judo",
                // Space
                "galaxy",
                "nebula",
                "asteroid",
                "comet",
                "meteor",
                "satellite",
                "telescope",
                "supernova",
                "constellation",
                "blackhole",
                "universe",
                "planet",
                "orbit",
                "gravity",
                "cosmos",
            ],
        }
    }

    pub fn get_random_word(&self) -> String {
        let mut rng = thread_rng();
        self.words
            .choose(&mut rng)
            .unwrap_or(&"hangman")
            .to_string()
    }

    pub fn get_word_count(&self) -> usize {
        self.words.len()
    }
}

impl Default for WordList {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_word_list_not_empty() {
        let word_list = WordList::new();
        assert!(word_list.get_word_count() > 0);
    }

    #[test]
    fn test_get_random_word() {
        let word_list = WordList::new();
        let word = word_list.get_random_word();
        assert!(!word.is_empty());
        assert!(word.chars().all(|c| c.is_ascii_lowercase()));
    }

    #[test]
    fn test_randomness() {
        let word_list = WordList::new();
        let mut words = std::collections::HashSet::new();

        // Get 20 random words - should get some variety
        for _ in 0..20 {
            words.insert(word_list.get_random_word());
        }

        // We should get at least a few different words (not all the same)
        assert!(words.len() > 1);
    }
}
