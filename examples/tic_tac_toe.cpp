#include <array>
#include <iostream>
#include <string>

class TicTacToe {
public:
    void run() {
        reset();
        std::cout << "Welcome to Tic Tac Toe! Players are X and O." << std::endl;

        while (true) {
            draw_board();
            if (!prompt_move()) {
                continue;
            }

            if (has_winner()) {
                draw_board();
                std::cout << "Player " << current_player_ << " wins!" << std::endl;
                break;
            }

            if (is_draw()) {
                draw_board();
                std::cout << "It's a draw!" << std::endl;
                break;
            }

            swap_player();
        }
    }

private:
    void reset() {
        board_.fill(' ');
        current_player_ = 'X';
    }

    void draw_board() const {
        std::cout << "\n";
        for (int row = 0; row < 3; ++row) {
            for (int col = 0; col < 3; ++col) {
                const int index = row * 3 + col;
                const char cell = board_[index];
                const char display = cell == ' ' ? static_cast<char>('1' + index) : cell;
                std::cout << " " << display << " ";
                if (col < 2) {
                    std::cout << "|";
                }
            }
            std::cout << std::endl;
            if (row < 2) {
                std::cout << "-----------" << std::endl;
            }
        }
        std::cout << std::endl;
    }

    bool prompt_move() {
        std::cout << "Player " << current_player_ << ", choose a square (1-9): ";
        std::string line;
        if (!std::getline(std::cin, line)) {
            std::cout << "Input stream closed. Exiting." << std::endl;
            std::exit(0);
        }

        try {
            const int choice = std::stoi(line);
            if (place_mark(choice)) {
                return true;
            }
            std::cout << "Invalid move. Try again." << std::endl;
        } catch (const std::exception &) {
            std::cout << "Please enter a number between 1 and 9." << std::endl;
        }
        return false;
    }

    bool place_mark(int position) {
        if (position < 1 || position > 9) {
            return false;
        }
        const int index = position - 1;
        if (board_[index] != ' ') {
            return false;
        }
        board_[index] = current_player_;
        return true;
    }

    bool has_winner() const {
        constexpr int wins[8][3] = {
            {0, 1, 2}, {3, 4, 5}, {6, 7, 8},
            {0, 3, 6}, {1, 4, 7}, {2, 5, 8},
            {0, 4, 8}, {2, 4, 6},
        };

        for (const auto &line : wins) {
            const char a = board_[line[0]];
            const char b = board_[line[1]];
            const char c = board_[line[2]];
            if (a != ' ' && a == b && b == c) {
                return true;
            }
        }
        return false;
    }

    bool is_draw() const {
        for (const char cell : board_) {
            if (cell == ' ') {
                return false;
            }
        }
        return true;
    }

    void swap_player() {
        current_player_ = current_player_ == 'X' ? 'O' : 'X';
    }

    std::array<char, 9> board_{};
    char current_player_ = 'X';
};

int main() {
    TicTacToe game;
    game.run();
    return 0;
}
