from collections import deque
from itertools import permutations
import time


class Sudoku:
    def __init__(self, sudoku, base_delay=0.01, interval=10, threshold=5, handicap = 1):
        self.grid = sudoku
        self.recent_requests = deque()
        self.base_delay = base_delay * handicap
        self.interval = interval
        self.threshold = threshold
        self.solution = sudoku
        self.validation = 0

    def set_solution(self, solution):
        self.solution = solution

    def _limit_calls(self, base_delay=0.01, interval=10, threshold=5):
        """Limit the number of requests made to the Sudoku object."""
        self.validation += 1
        if base_delay is None:
            base_delay = self.base_delay
        if interval is None:
            interval = self.interval
        if threshold is None:
            threshold = self.threshold

        current_time = time.time()
        self.recent_requests.append(current_time)
        num_requests = len(
            [t for t in self.recent_requests if current_time - t < interval]
        )

        if num_requests > threshold:
            delay = base_delay * (num_requests - threshold + 1)
            time.sleep(delay)

    def __str__(self):
        string_representation = "| - - - - - - - - - - - |\n"

        for i in range(9):
            string_representation += "| "
            for j in range(9):
                string_representation += (
                    str(self.solution[i][j])
                    if self.solution[i][j] != 0
                    else f"\033[93m{self.solution[i][j]}\033[0m"
                )
                string_representation += " | " if j % 3 == 2 else " "

            if i % 3 == 2:
                string_representation += "\n| - - - - - - - - - - - |"
            string_representation += "\n"

        return string_representation
    
    def check_row(self, row, base_delay=None, interval=None, threshold=None):
        """Check if the given row is correct."""
        self._limit_calls(base_delay, interval, threshold)

        # Check row
        if sum(self.solution[row]) != 45 or len(set(self.solution[row])) != 9:
            return False

        return True

    def check_column(self, col, base_delay=None, interval=None, threshold=None):
        """Check if the given row is correct."""
        self._limit_calls(base_delay, interval, threshold)

        # Check col
        if (
            sum([self.solution[row][col] for row in range(9)]) != 45
            or len(set([self.solution[row][col] for row in range(9)])) != 9
        ):
            return False

        return True

    def check_square(self, row, col, base_delay=None, interval=None, threshold=None):
        """Check if the given 3x3 square is correct."""
        self._limit_calls(base_delay, interval, threshold)

        # Check square
        if (
            sum([self.solution[row + i][col + j] for i in range(3) for j in range(3)]) != 45
            or len(
                set([self.solution[row + i][col + j] for i in range(3) for j in range(3)])
            )
            != 9
        ):
            return False

        return True

    def check(self, base_delay=None, interval=None, threshold=None):
        """Check if the given Sudoku solution is correct.

        You MUST incorporate this method without modifications into your final solution.
        """

        for row in range(9):
            if not self.check_row(row, base_delay, interval, threshold):
                return False

        # Check columns
        for col in range(9):
            if not self.check_column(col, base_delay, interval, threshold):
                return False

        # Check 3x3 squares
        for i in range(3):
            for j in range(3):
                if not self.check_square(i * 3, j * 3, base_delay, interval, threshold):
                    return False

        return True


    def get_possible_solutions_for_row(self, row_index):
        row = self.grid[row_index]
        missing_numbers = [i for i in range(1, 10) if i not in row]
        permutations_list = permutations(missing_numbers)
        todas_permutacoes = list(permutations_list)
        solutions = []

        for perm_tuple in todas_permutacoes:
            nova = []
            perm = list(perm_tuple)
            for i in range(0, 9):
                if row[i] == 0:
                    nova.append(perm.pop())
                else:
                    nova.append(row[i])
            solutions.append(nova)

        return solutions if solutions != [] else row
    

    