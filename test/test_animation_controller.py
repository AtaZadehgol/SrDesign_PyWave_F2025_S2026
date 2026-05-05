"""Tests for animation controller default frame behavior."""

import os
import sys

import numpy as np
import pytest

pytest.importorskip("PyQt5")

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "PyQt5-test",
        "input-screen",
    ),
)

from gui.visualizer.components.animation_controller import AnimationController


class _DummySignal:
    def connect(self, _callback):
        return None


class _DummyBlocker:
    def __init__(self, _widget):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyTimer:
    def __init__(self):
        self.timeout = _DummySignal()

    def setInterval(self, _interval):
        return None

    def start(self):
        return None

    def stop(self):
        return None


class _DummySlider:
    def __init__(self):
        self._value = 0

    def setMinimum(self, _value):
        return None

    def setMaximum(self, _value):
        return None

    def setValue(self, value):
        self._value = int(value)

    def setEnabled(self, _enabled):
        return None

    def value(self):
        return self._value


class _DummyLabel:
    def __init__(self):
        self._text = ""

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text


class _DummyButton:
    def setChecked(self, _checked):
        return None

    def setText(self, _text):
        return None

    def setEnabled(self, _enabled):
        return None


def test_configure_for_data_starts_at_first_frame():
    slider = _DummySlider()
    label = _DummyLabel()
    play_button = _DummyButton()

    import gui.visualizer.components.animation_controller as animation_controller_module

    original_timer = animation_controller_module.QTimer
    original_blocker = animation_controller_module.QSignalBlocker
    animation_controller_module.QTimer = _DummyTimer
    animation_controller_module.QSignalBlocker = _DummyBlocker

    controller = AnimationController(slider, label, play_button)

    try:
        surface_data = [np.zeros((3, 4, 5)), np.ones((3, 4, 5))]
        controller.configure_for_data(surface_data)

        assert controller.frame_index == 0
        assert slider.value() == 0
        assert label.text() == "1/5"
    finally:
        animation_controller_module.QTimer = original_timer
        animation_controller_module.QSignalBlocker = original_blocker
