use macroquad::prelude::*;

const GRID_SIZE: i32 = 20;
const CELL_SIZE: f32 = 30.0;
const GAME_SPEED: f32 = 0.15;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Direction {
    Up,
    Down,
    Left,
    Right,
}

impl Direction {
    fn opposite(&self) -> Direction {
        match self {
            Direction::Up => Direction::Down,
            Direction::Down => Direction::Up,
            Direction::Left => Direction::Right,
            Direction::Right => Direction::Left,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct Position {
    x: i32,
    y: i32,
}

impl Position {
    fn new(x: i32, y: i32) -> Self {
        Self { x, y }
    }

    fn move_in_direction(&self, direction: Direction) -> Self {
        match direction {
            Direction::Up => Self::new(self.x, self.y - 1),
            Direction::Down => Self::new(self.x, self.y + 1),
            Direction::Left => Self::new(self.x - 1, self.y),
            Direction::Right => Self::new(self.x + 1, self.y),
        }
    }
}

struct Snake {
    body: Vec<Position>,
    direction: Direction,
    next_direction: Direction,
    growing: bool,
}

impl Snake {
    fn new(start_pos: Position) -> Self {
        Self {
            body: vec![start_pos],
            direction: Direction::Right,
            next_direction: Direction::Right,
            growing: false,
        }
    }

    fn head(&self) -> Position {
        self.body[0]
    }

    fn change_direction(&mut self, new_direction: Direction) {
        if new_direction != self.direction.opposite() {
            self.next_direction = new_direction;
        }
    }

    fn advance(&mut self) {
        self.direction = self.next_direction;
        let new_head = self.head().move_in_direction(self.direction);
        self.body.insert(0, new_head);

        if !self.growing {
            self.body.pop();
        } else {
            self.growing = false;
        }
    }

    fn grow(&mut self) {
        self.growing = true;
    }

    fn collides_with_self(&self) -> bool {
        let head = self.head();
        self.body.iter().skip(1).any(|&pos| pos == head)
    }

    fn contains(&self, pos: Position) -> bool {
        self.body.contains(&pos)
    }
}

#[derive(PartialEq)]
enum GameState {
    Menu,
    Playing,
    Paused,
    GameOver,
}

struct Game {
    grid_size: i32,
    snake: Snake,
    food: Position,
    score: u32,
    state: GameState,
    last_update: f64,
    high_score: u32,
}

impl Game {
    fn new(grid_size: i32) -> Self {
        let start_pos = Position::new(grid_size / 2, grid_size / 2);
        let mut game = Self {
            grid_size,
            snake: Snake::new(start_pos),
            food: Position::new(0, 0),
            score: 0,
            state: GameState::Menu,
            last_update: 0.0,
            high_score: 0,
        };
        game.spawn_food();
        game
    }

    fn spawn_food(&mut self) {
        loop {
            let food_pos = Position::new(
                rand::gen_range(0, self.grid_size),
                rand::gen_range(0, self.grid_size),
            );
            if !self.snake.contains(food_pos) {
                self.food = food_pos;
                break;
            }
        }
    }

    fn update(&mut self, current_time: f64) {
        if self.state != GameState::Playing {
            return;
        }

        if current_time - self.last_update < GAME_SPEED as f64 {
            return;
        }

        self.last_update = current_time;
        self.snake.advance();

        let head = self.snake.head();
        if head.x < 0 || head.x >= self.grid_size || head.y < 0 || head.y >= self.grid_size {
            self.game_over();
            return;
        }

        if self.snake.collides_with_self() {
            self.game_over();
            return;
        }

        if head == self.food {
            self.score += 10;
            self.snake.grow();
            self.spawn_food();
        }
    }

    fn game_over(&mut self) {
        self.state = GameState::GameOver;
        if self.score > self.high_score {
            self.high_score = self.score;
        }
    }

    fn reset(&mut self) {
        let start_pos = Position::new(self.grid_size / 2, self.grid_size / 2);
        self.snake = Snake::new(start_pos);
        self.score = 0;
        self.spawn_food();
        self.state = GameState::Playing;
        self.last_update = get_time();
    }

    fn handle_input(&mut self) {
        match self.state {
            GameState::Menu => {
                if is_key_pressed(KeyCode::Space) || is_key_pressed(KeyCode::Enter) {
                    self.reset();
                }
                if is_key_pressed(KeyCode::Escape) || is_key_pressed(KeyCode::Q) {
                    std::process::exit(0);
                }
            }
            GameState::Playing => {
                if is_key_pressed(KeyCode::Up) || is_key_pressed(KeyCode::W) {
                    self.snake.change_direction(Direction::Up);
                }
                if is_key_pressed(KeyCode::Down) || is_key_pressed(KeyCode::S) {
                    self.snake.change_direction(Direction::Down);
                }
                if is_key_pressed(KeyCode::Left) || is_key_pressed(KeyCode::A) {
                    self.snake.change_direction(Direction::Left);
                }
                if is_key_pressed(KeyCode::Right) || is_key_pressed(KeyCode::D) {
                    self.snake.change_direction(Direction::Right);
                }
                if is_key_pressed(KeyCode::P) || is_key_pressed(KeyCode::Space) {
                    self.state = GameState::Paused;
                }
                if is_key_pressed(KeyCode::Escape) {
                    self.state = GameState::Menu;
                }
            }
            GameState::Paused => {
                if is_key_pressed(KeyCode::P) || is_key_pressed(KeyCode::Space) {
                    self.state = GameState::Playing;
                    self.last_update = get_time();
                }
                if is_key_pressed(KeyCode::Escape) {
                    self.state = GameState::Menu;
                }
            }
            GameState::GameOver => {
                if is_key_pressed(KeyCode::R) || is_key_pressed(KeyCode::Space) {
                    self.reset();
                }
                if is_key_pressed(KeyCode::Escape) || is_key_pressed(KeyCode::M) {
                    self.state = GameState::Menu;
                }
            }
        }
    }

    fn render(&self) {
        clear_background(Color::from_rgba(20, 20, 30, 255));

        let offset_x = (screen_width() - (self.grid_size as f32 * CELL_SIZE)) / 2.0;
        let offset_y = 80.0;

        match self.state {
            GameState::Menu => {
                self.draw_menu();
            }
            GameState::Playing | GameState::Paused => {
                self.draw_grid(offset_x, offset_y);
                self.draw_food(offset_x, offset_y);
                self.draw_snake(offset_x, offset_y);
                self.draw_hud();

                if self.state == GameState::Paused {
                    self.draw_pause_overlay();
                }
            }
            GameState::GameOver => {
                self.draw_grid(offset_x, offset_y);
                self.draw_food(offset_x, offset_y);
                self.draw_snake(offset_x, offset_y);
                self.draw_hud();
                self.draw_game_over();
            }
        }
    }

    fn draw_grid(&self, offset_x: f32, offset_y: f32) {
        for x in 0..self.grid_size {
            for y in 0..self.grid_size {
                let px = offset_x + x as f32 * CELL_SIZE;
                let py = offset_y + y as f32 * CELL_SIZE;

                let color = if (x + y) % 2 == 0 {
                    Color::from_rgba(40, 40, 50, 255)
                } else {
                    Color::from_rgba(35, 35, 45, 255)
                };

                draw_rectangle(px, py, CELL_SIZE, CELL_SIZE, color);
            }
        }

        let grid_width = self.grid_size as f32 * CELL_SIZE;
        let grid_height = self.grid_size as f32 * CELL_SIZE;
        draw_rectangle_lines(offset_x, offset_y, grid_width, grid_height, 3.0, LIGHTGRAY);
    }

    fn draw_food(&self, offset_x: f32, offset_y: f32) {
        let px = offset_x + self.food.x as f32 * CELL_SIZE + CELL_SIZE / 2.0;
        let py = offset_y + self.food.y as f32 * CELL_SIZE + CELL_SIZE / 2.0;

        draw_circle(px, py, CELL_SIZE * 0.4, RED);
        draw_circle(px, py, CELL_SIZE * 0.3, Color::from_rgba(255, 100, 100, 255));
    }

    fn draw_snake(&self, offset_x: f32, offset_y: f32) {
        for (i, pos) in self.snake.body.iter().enumerate() {
            let px = offset_x + pos.x as f32 * CELL_SIZE;
            let py = offset_y + pos.y as f32 * CELL_SIZE;

            let (color, size_mult) = if i == 0 {
                (Color::from_rgba(100, 255, 100, 255), 0.9)
            } else {
                let alpha = 255 - (i as u8 * 3).min(100);
                (Color::from_rgba(50, 200, 50, alpha), 0.8)
            };

            let size = CELL_SIZE * size_mult;
            let margin = (CELL_SIZE - size) / 2.0;
            draw_rectangle(px + margin, py + margin, size, size, color);

            if i == 0 {
                let eye_size = 3.0;
                let eye_offset = size / 3.0;
                match self.snake.direction {
                    Direction::Up => {
                        draw_circle(px + margin + eye_offset, py + margin + eye_offset, eye_size, BLACK);
                        draw_circle(px + margin + size - eye_offset, py + margin + eye_offset, eye_size, BLACK);
                    }
                    Direction::Down => {
                        draw_circle(px + margin + eye_offset, py + margin + size - eye_offset, eye_size, BLACK);
                        draw_circle(px + margin + size - eye_offset, py + margin + size - eye_offset, eye_size, BLACK);
                    }
                    Direction::Left => {
                        draw_circle(px + margin + eye_offset, py + margin + eye_offset, eye_size, BLACK);
                        draw_circle(px + margin + eye_offset, py + margin + size - eye_offset, eye_size, BLACK);
                    }
                    Direction::Right => {
                        draw_circle(px + margin + size - eye_offset, py + margin + eye_offset, eye_size, BLACK);
                        draw_circle(px + margin + size - eye_offset, py + margin + size - eye_offset, eye_size, BLACK);
                    }
                }
            }
        }
    }

    fn draw_hud(&self) {
        let title = "SNAKE GAME";
        let title_size = 40.0;
        let title_width = measure_text(title, None, title_size as u16, 1.0).width;
        draw_text(title, (screen_width() - title_width) / 2.0, 50.0, title_size, GREEN);

        let score_text = format!("Score: {}", self.score);
        draw_text(&score_text, 30.0, screen_height() - 60.0, 30.0, WHITE);

        let length_text = format!("Length: {}", self.snake.body.len());
        draw_text(&length_text, 30.0, screen_height() - 30.0, 25.0, LIGHTGRAY);

        if self.high_score > 0 {
            let high_score_text = format!("High Score: {}", self.high_score);
            let width = measure_text(&high_score_text, None, 30, 1.0).width;
            draw_text(&high_score_text, screen_width() - width - 30.0, screen_height() - 60.0, 30.0, YELLOW);
        }
    }

    fn draw_menu(&self) {
        let title = "SNAKE GAME";
        let title_size = 60.0;
        let title_width = measure_text(title, None, title_size as u16, 1.0).width;
        draw_text(title, (screen_width() - title_width) / 2.0, 200.0, title_size, GREEN);

        let subtitle = "Classic Snake with Modern Graphics";
        let subtitle_size = 25.0;
        let subtitle_width = measure_text(subtitle, None, subtitle_size as u16, 1.0).width;
        draw_text(subtitle, (screen_width() - subtitle_width) / 2.0, 250.0, subtitle_size, LIGHTGRAY);

        let instructions = vec![
            "",
            "HOW TO PLAY:",
            "",
            "Arrow Keys or WASD - Move Snake",
            "Space or P - Pause Game",
            "ESC - Return to Menu",
            "",
            "Eat the red food to grow longer!",
            "Don't hit the walls or yourself!",
            "",
        ];

        let mut y = 320.0;
        for instruction in &instructions {
            let width = measure_text(instruction, None, 20, 1.0).width;
            let color = if instruction.contains("HOW TO PLAY") {
                YELLOW
            } else if instruction.is_empty() {
                WHITE
            } else {
                LIGHTGRAY
            };
            draw_text(instruction, (screen_width() - width) / 2.0, y, 20.0, color);
            y += 28.0;
        }

        if self.high_score > 0 {
            let high_score_text = format!("High Score: {}", self.high_score);
            let width = measure_text(&high_score_text, None, 30, 1.0).width;
            draw_text(&high_score_text, (screen_width() - width) / 2.0, y + 20.0, 30.0, YELLOW);
        }

        let start_text = "Press SPACE or ENTER to Start";
        let start_width = measure_text(start_text, None, 35, 1.0).width;
        let pulse = (get_time() * 3.0).sin() * 0.3 + 0.7;
        let color = Color::from_rgba(
            (100.0 + 155.0 * pulse) as u8,
            (255.0 * pulse) as u8,
            (100.0 + 155.0 * pulse) as u8,
            255,
        );
        draw_text(start_text, (screen_width() - start_width) / 2.0, screen_height() - 100.0, 35.0, color);

        let quit_text = "Press Q or ESC to Quit";
        let quit_width = measure_text(quit_text, None, 20, 1.0).width;
        draw_text(quit_text, (screen_width() - quit_width) / 2.0, screen_height() - 50.0, 20.0, DARKGRAY);
    }

    fn draw_pause_overlay(&self) {
        draw_rectangle(0.0, 0.0, screen_width(), screen_height(), Color::from_rgba(0, 0, 0, 180));

        let pause_text = "PAUSED";
        let pause_size = 50.0;
        let pause_width = measure_text(pause_text, None, pause_size as u16, 1.0).width;
        draw_text(pause_text, (screen_width() - pause_width) / 2.0, screen_height() / 2.0 - 30.0, pause_size, YELLOW);

        let continue_text = "Press SPACE or P to Continue";
        let continue_width = measure_text(continue_text, None, 25, 1.0).width;
        draw_text(continue_text, (screen_width() - continue_width) / 2.0, screen_height() / 2.0 + 30.0, 25.0, WHITE);
    }

    fn draw_game_over(&self) {
        draw_rectangle(0.0, 0.0, screen_width(), screen_height(), Color::from_rgba(0, 0, 0, 200));

        let game_over_text = "GAME OVER";
        let go_size = 60.0;
        let go_width = measure_text(game_over_text, None, go_size as u16, 1.0).width;
        draw_text(game_over_text, (screen_width() - go_width) / 2.0, screen_height() / 2.0 - 80.0, go_size, RED);

        let score_text = format!("Final Score: {}", self.score);
        let score_width = measure_text(&score_text, None, 35, 1.0).width;
        draw_text(&score_text, (screen_width() - score_width) / 2.0, screen_height() / 2.0 - 10.0, 35.0, WHITE);

        let length_text = format!("Final Length: {}", self.snake.body.len());
        let length_width = measure_text(&length_text, None, 30, 1.0).width;
        draw_text(&length_text, (screen_width() - length_width) / 2.0, screen_height() / 2.0 + 30.0, 30.0, LIGHTGRAY);

        if self.score == self.high_score && self.score > 0 {
            let new_high = "NEW HIGH SCORE!";
            let nh_width = measure_text(new_high, None, 30, 1.0).width;
            let pulse = (get_time() * 5.0).sin() * 0.3 + 0.7;
            let color = Color::from_rgba(255, (255.0 * pulse) as u8, 0, 255);
            draw_text(new_high, (screen_width() - nh_width) / 2.0, screen_height() / 2.0 + 70.0, 30.0, color);
        }

        let restart_text = "Press SPACE or R to Restart";
        let restart_width = measure_text(restart_text, None, 25, 1.0).width;
        draw_text(restart_text, (screen_width() - restart_width) / 2.0, screen_height() / 2.0 + 120.0, 25.0, GREEN);

        let menu_text = "Press ESC or M for Menu";
        let menu_width = measure_text(menu_text, None, 20, 1.0).width;
        draw_text(menu_text, (screen_width() - menu_width) / 2.0, screen_height() / 2.0 + 160.0, 20.0, LIGHTGRAY);
    }
}

fn window_conf() -> Conf {
    Conf {
        window_title: "Snake Game".to_owned(),
        window_width: (GRID_SIZE as f32 * CELL_SIZE + 100.0) as i32,
        window_height: (GRID_SIZE as f32 * CELL_SIZE + 200.0) as i32,
        window_resizable: false,
        ..Default::default()
    }
}

#[macroquad::main(window_conf)]
async fn main() {
    let mut game = Game::new(GRID_SIZE);

    loop {
        game.handle_input();
        game.update(get_time());
        game.render();

        next_frame().await
    }
}
