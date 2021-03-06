import numpy
import random
import ErrorNote

# import sys
# sys.setrecursionlimit(1000000)

'''
Sweeper

A risk-evaluation based algorithm

Rules:

1. The risk of a cell is basically measured by the probability whether it is a mine
2. To evaluate a cell, we concern all surrounding uncovered cells, from these cells, we know the probability
    of current position (if a neighbour point has 1 unknown mine and 2 covered neighbours, the probability of 
    current location is a mine is 1/2). We use the max probability as the risk value.
3. If a probability of 0 occurred while calculating, which means some of its neighbours are sure that current 
    location is not a mine, then it cannot be mine. We can uncover it.
4. If a probability of 1 occurred while calculating, which means some of its neighbours are sure it is a mine,
    then it must be a mine, we can mark it as a mine directly.
5. If there is no position described in (3) and (4), we choice the minimum risk cell to uncover

P.S: After several attempts to improve the accuracy, I finally realize the fact that only rule 3 and 4 work. It
    does not change too much how the risk of a position is evaluated. =_=
    
    The following case cannot be solved using logical model only:
    [[ ?.  ?.  ?.
     [ ?.  1.  ?.
     [ ?.  ?.  ?. ]]

Known problems:

The following case can be solved manually, but the algorithm failed while testing

[[ 0.  0.  0.  0.  0.]
 [ 1.  2.  1.  1.  0.]
 [-1.  3. -1.  1.  0.]
 [ ?.  *.  3.  3.  2.]
 [ 1.  ?.  2. -1. -1.]]
 
(Only 1 mine left in this region. After evaluation on unknown positions (those marked as '*' and '?'),
 the algorithm found the remaining 3 unknown positions are all with a risk of .5. So it randomly decided 
 to uncover '*' position, which is actually a mine. However, as we can see, to satisfy both 3 nearby, '*' 
 must be a mine. In this case algorithm can do nothing but guess.
 The problem is we cannot try all the possible cases where remaining mines can be, we cannot afford the
 space and time cost)

Functions:

load(landscape): load a landscape to solve
run():  start to solve, terminated if uncover a mine or all cells are uncovered

'''


class Sweeper:
    problem = None
    problem_width = 0

    explored_map = []
    uncovered_location = []

    remain_mines = uncovered_count = 0

    error_note = ErrorNote.ErrorNote()
    error_note_enabled = True
    learning_mode = False  # random sampling to learn more pattern by making mistake

    inference_message = ''

    def load(self, problem):
        self.problem = problem
        self.problem_width = len(self.problem.data)

        self.explored_map = numpy.zeros([self.problem_width, self.problem_width])
        self.uncovered_location = numpy.zeros([self.problem_width, self.problem_width])
        self.remain_mines = self.problem.mines_count
        self.uncovered_count = 0

    def get_valid_neighbours(self, pos):
        neighbours = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if pos[0] + dx in range(self.problem_width) and pos[1] + dy in range(self.problem_width) \
                        and not (dx == 0 and dy == 0):
                    neighbours.append((pos[0] + dx, pos[1] + dy))
        return neighbours

    def get_valid_neighbours_number(self, pos):
        if pos[0] in (0, self.problem_width - 1) and pos[1] in (0, self.problem_width - 1):
            return 3
        if pos[0] in (0, self.problem_width - 1) or pos[1] in (0, self.problem_width - 1):
            return 5
        return 8

    def is_uncovered(self, pos):
        return self.uncovered_location[pos] == 1

    def get_uncovered_neighbours_number(self, pos):
        count = 0
        neighbours = self.get_valid_neighbours(pos)
        for neighbour in neighbours:
            count += 1 if self.is_uncovered(neighbour) else 0
        return count

    def get_covered_neighbours_number(self, pos):
        return self.get_valid_neighbours_number(pos) - self.get_uncovered_neighbours_number(pos)

    def _get_snapshot_key(self, pos):
        data = ''
        for dx in (-2, 0, 2):
            x = dx + pos[0]
            for dy in (-2, 0, 2):
                y = dy + pos[1]
                if x in range(self.problem_width) and y in range(self.problem_width):
                    n_pos = (x, y)
                    if self.is_uncovered(n_pos):
                        value = self.explored_map[n_pos]
                        if value == -1:
                            data += str(value)
                        else:
                            data += str(value - self.get_mines_nearby_number(n_pos))
                    else:
                        data += str(-2)
                    if self.explored_map[n_pos] == -1 and self.problem.detect(n_pos) != -1:
                        return "-1"  # abandoned because algorithm made wrong prediction before exploring a mine
                else:
                    data += str(-3)
        return data

    def record_note(self, pos, result):
        self.error_note.add_note(self._get_snapshot_key(pos), result)

    def get_mines_nearby_number(self, pos):
        count = 0
        neighbours = self.get_valid_neighbours(pos)
        for neighbour in neighbours:
            count += 1 if self.explored_map[neighbour] == -1 else 0
        return count

    def evaluate_risk(self, pos):
        # a basic risk is that we know there are certain mines in certain number cells
        risk = self.remain_mines / (self.problem_width * self.problem_width - self.uncovered_count)
        if self.remain_mines == 0:
            return 0  # if no unknown mines left, then no risk
        neighbours = self.get_valid_neighbours(pos)
        for neighbour in neighbours:
            if self.is_uncovered(neighbour) and not self.explored_map[neighbour] == -1:
                total_mines = self.explored_map[neighbour]
                if total_mines != -1:  # this neighbour is not a mine
                    # the risk of a position is the max risk of his uncovered neighbours think on this position
                    unknown_mines = total_mines - self.get_mines_nearby_number(neighbour)
                    unknown_cells = self.get_covered_neighbours_number(neighbour)
                    risk = max(risk, unknown_mines / unknown_cells)
                    # it cannot be a mine if any of its neighbour knows all the mines nearby
                    if unknown_mines == 0:
                        self.inference_message += '(%g, %g): unknown mines = 0 -> (%g, %g) is safe' % (
                            neighbour[0], neighbour[1], pos[0], pos[1]
                        ) + '\n'
                        return 0
                    # it must be a mine if any of its neighbour thinks it is a mine
                    if unknown_mines == unknown_cells:
                        self.inference_message += '(%g, %g): unknown mines = unknown neighbours' \
                                                  ' -> (%g, %g) is a mine' % (
                                                      neighbour[0], neighbour[1], pos[0], pos[1]
                                                  ) + '\n'
                        return 1
        if self.learning_mode:
            risk = .5
        if self.error_note_enabled and self.get_covered_neighbours_number(pos) <= 3 \
                and self.get_uncovered_neighbours_number(pos) >= 2:
            recorded_risk = self.error_note.get_evaluate(self._get_snapshot_key(pos))

            return max(min(round(risk + recorded_risk, 2), 0.95), 0.05)
            # learning from experience can lead us to a wrong decision
        return round(risk, 2)

    def mark_as_mine(self, mine_position):
        self.remain_mines -= 1
        self.explored_map[mine_position] = -1
        self.uncovered_location[mine_position] = 1
        self.uncovered_count += 1

    def explore(self, pos):
        value = self.problem.detect(pos) if self.uncovered_count > 0 else self.problem.first_detect(pos)
        if value == -1:  # if we detect a mine directly, game lost
            self.explored_map[pos] = -2
            return True
        self.explored_map[pos] = value
        self.uncovered_location[pos] = 1
        self.uncovered_count += 1

        if self.learning_mode and self.get_covered_neighbours_number(pos) < 3 \
                and self.get_uncovered_neighbours_number(pos) >= 2:
            self.record_note(pos, self.explored_map[pos])

        return False

    def get_covered_locations(self):
        locations = []
        for x in range(self.problem_width):
            for y in range(self.problem_width):
                if not self.is_uncovered((x, y)):
                    locations.append((x, y))
        return locations

    def demonstrate_half_auto(self):
        work_queue = self.get_covered_locations()
        risk_queue = [self.evaluate_risk(pos) for pos in work_queue]
        if self._remove_all_confirmed_position(work_queue, risk_queue):
            return self.demonstrate_half_auto()
        e_risk_queue = [self.error_note.get_evaluate(
            self._get_snapshot_key(pos)) if self.get_covered_neighbours_number(pos) <= 3 else 0 for pos in work_queue]
        return work_queue, risk_queue, e_risk_queue

    def stepbystep(self):
        work_queue = self.get_covered_locations()
        random.shuffle(work_queue)
        risk_queue = [self.evaluate_risk(pos) for pos in work_queue]
        if len(risk_queue) == 0 or \
                                self.uncovered_count + self.remain_mines == self.problem_width * self.problem_width or \
                        self.remain_mines == 0:
            return 0	# win
        min_index = 0
        for i in range(len(risk_queue)):
            if risk_queue[min_index] > risk_queue[i]:
                min_index = i
            if risk_queue[i] == 1:
                self.mark_as_mine(work_queue[i])
                return 1	# keep going
        if self.explore(work_queue[min_index]):
            return 2	# lose
        return 1 # keep going
                


    def _remove_all_confirmed_position(self, work_queue, risk_values):
        remove_list = []
        for i in range(len(risk_values)):
            if risk_values[i] == 1:
                mine_point = work_queue[i]
                self.mark_as_mine(mine_point)
                remove_list.append(mine_point)
            elif risk_values[i] == 0:
                self.explore(work_queue[i])
                remove_list.append(work_queue[i])
        for ptn in remove_list:
            work_queue.remove(ptn)
        return len(remove_list) > 0  # recalculate the risk list if we find confirmed some new locations

    def run(self):
        work_queue = self.get_covered_locations()
        while len(work_queue) > 0:
            risks = [self.evaluate_risk(pos) for pos in work_queue]
            if self._remove_all_confirmed_position(work_queue, risks):
                continue
            if len(work_queue) > 0:
                min_risk_point = work_queue[int(numpy.argmin(risks))]
                if self.explore(min_risk_point):
                    for point, value in zip(work_queue, risks):
                        if self.error_note_enabled and self.get_covered_neighbours_number(point) <= 3 \
                                and self.get_uncovered_neighbours_number(point) >= 2:
                            self.record_note(point, self.problem.detect(point))
                    break  # game over
                work_queue.remove(min_risk_point)

        return self.uncovered_count == self.problem_width * self.problem_width
