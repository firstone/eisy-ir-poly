#pylint: disable=redefined-outer-name

import pytest

from ir_button import IRButton, KeyState


class Controller:

    def __init__(self):
        self.release_threshold = 1
        self.idle_threshold = 2
        self.held_threshold = 10


@pytest.fixture(scope="session")
def controller():
    return Controller()


@pytest.fixture()
def timer():
    time = 1

    def inner(t=None):
        nonlocal time
        if t is not None:
            print(f'time value {t}')
            time = t
        return time

    return inner


@pytest.fixture()
def button(controller, timer):
    return IRButton(controller, timer)


def roll_to(button, timer, to_time, current_state, new_state=None):
    from_time = timer() + 1
    if new_state is None:
        to_time += 1

    for time_value in range(from_time, to_time):
        timer(time_value)
        assert not button.tick(), 'no change'
        assert button.state == current_state, 'current state'

    if new_state is not None:
        timer(to_time)
        assert button.tick(), 'state change'
        assert button.state == new_state, 'new state'


def test_press(button, timer):
    button.press()
    assert button.state == KeyState.IDLE

    timer(1)

    button.release()

    roll_to(button, timer, 3, KeyState.IDLE, KeyState.PRESSED)
    roll_to(button, timer, 4, KeyState.PRESSED, KeyState.IDLE)
    roll_to(button, timer, 10, KeyState.IDLE)


def test_multi_press(button, timer):
    timer(1)

    button.press()
    assert not button.tick()
    assert button.state == KeyState.IDLE

    timer(2)
    button.release()
    assert not button.tick()
    assert button.state == KeyState.IDLE

    timer(3)
    button.press()
    assert not button.tick()
    assert button.state == KeyState.IDLE

    timer(4)
    button.release()
    assert not button.tick()
    assert button.state == KeyState.IDLE

    timer(5)
    button.press()
    assert not button.tick()
    assert button.state == KeyState.IDLE

    timer(6)
    button.release()
    assert not button.tick()
    assert button.state == KeyState.IDLE

    roll_to(button, timer, 8, KeyState.IDLE, KeyState.PRESSED)
    roll_to(button, timer, 9, KeyState.PRESSED, KeyState.IDLE)
    roll_to(button, timer, 12, KeyState.IDLE)


def test_hold(button, timer):
    timer(1)
    button.press()
    assert button.state == KeyState.IDLE

    roll_to(button, timer, 12, KeyState.IDLE, KeyState.HELD)

    button.release()

    roll_to(button, timer, 14, KeyState.HELD, KeyState.RELEASED)

    roll_to(button, timer, 15, KeyState.RELEASED, KeyState.IDLE)

    roll_to(button, timer, 20, KeyState.IDLE)


def test_multi_hold(button, timer):
    timer(1)
    button.press()
    assert not button.tick()
    assert button.state == KeyState.IDLE

    timer(2)
    button.release()
    assert not button.tick()
    assert button.state == KeyState.IDLE

    timer(3)
    button.press()
    assert not button.tick()
    assert button.state == KeyState.IDLE

    roll_to(button, timer, 12, KeyState.IDLE, KeyState.HELD)

    button.release()
    assert not button.tick()
    assert button.state == KeyState.HELD

    timer(13)

    button.press()
    assert not button.tick()
    assert button.state == KeyState.HELD

    timer(14)

    button.release()
    assert not button.tick()
    assert button.state == KeyState.HELD

    timer(15)

    button.press()
    assert not button.tick()
    assert button.state == KeyState.HELD

    button.release()
    roll_to(button, timer, 17, KeyState.HELD, KeyState.RELEASED)

    roll_to(button, timer, 18, KeyState.RELEASED, KeyState.IDLE)

    roll_to(button, timer, 20, KeyState.IDLE)
