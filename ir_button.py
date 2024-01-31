from enum import Enum


class KeyState(Enum):
    IDLE = 0
    PRESSED = 1
    HELD = 2
    RELEASED = 3
    OFFLINE = 4


class IRButton:

    def __init__(self, controller, timer):
        self.controller = controller
        self.timer = timer
        self.state = KeyState.IDLE
        self.pressed_time = 0
        self.released_time = 0

    def idle(self):
        self.state = KeyState.IDLE
        self.pressed_time = 0
        self.released_time = 0

    def offline(self):
        self.state = KeyState.OFFLINE

    def is_idle(self):
        return self.state == KeyState.IDLE and self.pressed_time == 0 and self.released_time == 0

    def tick(self):
        cur_time = self.timer()
        if self.released_time > 0:
            lapsed = cur_time - self.released_time
            if lapsed > self.controller.release_threshold:
                self.pressed_time = 0
                if self.state == KeyState.IDLE:
                    self.state = KeyState.PRESSED
                    return True

                if self.state == KeyState.HELD:
                    self.state = KeyState.RELEASED
                    return True

                if lapsed > self.controller.idle_threshold:
                    self.state = KeyState.IDLE
                    self.released_time = 0
                    return True

        if self.pressed_time > 0 and self.state != KeyState.HELD:
            lapsed = cur_time - self.pressed_time
            if lapsed > self.controller.held_threshold:
                self.state = KeyState.HELD
                return True

        return False

    def press(self):
        self.released_time = 0
        if self.pressed_time == 0:
            self.pressed_time = self.timer()

    def release(self):
        if self.released_time == 0:
            self.released_time = self.timer()
