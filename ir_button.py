from enum import Enum


class KeyState(Enum):
    IDLE = 0
    PRESSED = 1
    HELD = 2
    RELEASED = 3
    OFFLINE = 4


class Modifiers(Enum):
    LEFT_CONTROL = 1
    LEFT_SHIFT = 2
    LEFT_ALT = 4
    LEFT_CMD = 8
    RIGHT_CONTROL = 0x10
    RIGHT_SHIFT = 0x20
    RIGHT_ALT = 0x40
    RIGHT_CMD = 0x80


class IRButton:

    MOD_DESC = {
        Modifiers.LEFT_CONTROL: 'LC',
        Modifiers.LEFT_SHIFT: 'LS',
        Modifiers.LEFT_ALT: 'LA',
        Modifiers.LEFT_CMD: 'LCMD',
        Modifiers.RIGHT_CONTROL: 'RC',
        Modifiers.RIGHT_SHIFT: 'RS',
        Modifiers.RIGHT_ALT: 'RA',
        Modifiers.RIGHT_CMD: 'RCMD',
    }

    SPECIAL_SECTION = 'Special Keys'
    SPECIAL_CODE = 2

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

    @staticmethod
    def get_modifier_desc(mod):
        result = []
        for val in Modifiers:
            if mod & val.value != 0:
                print(mod, val.value, mod & val.value)
                result.append(IRButton.MOD_DESC[val])

        return result

    @staticmethod
    def get_code(buffer):
        if buffer[0] == IRButton.SPECIAL_CODE:
            code = buffer[0] << 8 | buffer[1]
        elif buffer[1] != 0:  # modifier present
            code = buffer[0] << 16 | buffer[1] << 8 | buffer[2]
        else:
            code = buffer[0] << 8 | buffer[2]

        return code

    @staticmethod
    def get_code_desc(buffer, codes):
        desc = []
        if buffer[0] == IRButton.SPECIAL_CODE:
            codes = codes[IRButton.SPECIAL_SECTION]
            code = buffer[1]
        else:
            code = buffer[2]
            desc = IRButton.get_modifier_desc(buffer[1])

        code_desc = codes.get(code)
        if code_desc is None:
            code_desc = f'code {code}'
        elif not isinstance(code_desc, str):
            code_desc = desc[0]

        desc.append(code_desc)

        return '+'.join(desc)
