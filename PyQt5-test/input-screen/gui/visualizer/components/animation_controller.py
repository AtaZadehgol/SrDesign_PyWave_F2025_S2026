"""Animation frame controller for heatmap rendering."""

from typing import Callable, List, Optional

import numpy as np
from PyQt5.QtCore import QTimer, QSignalBlocker
from PyQt5.QtWidgets import QLabel, QSlider


class AnimationController:
    """Manages frame-by-frame animation for heatmap surface data."""

    def __init__(self, frame_slider: QSlider, frame_label: QLabel, play_button):
        """Initialize animation controller.

        Args:
            frame_slider: QSlider for frame selection
            frame_label: QLabel showing current frame/total
            play_button: QPushButton for play/pause control
        """
        self.frame_slider = frame_slider
        self.frame_label = frame_label
        self.play_button = play_button

        self.frame_index: int = 0
        self.current_surface_data_list: List[np.ndarray] = []

        self.animation_timer = QTimer()
        self.animation_timer.setInterval(120)
        self.animation_timer.timeout.connect(self._advance_frame)

        self._on_frame_changed: Optional[Callable[[int], None]] = None

    def set_on_frame_changed_callback(self, callback: Callable[[int], None]):
        """Set callback invoked when frame changes.

        Args:
            callback: Function called with new frame index
        """
        self._on_frame_changed = callback

    def configure_for_data(self, surface_data_list: List[np.ndarray]):
        """Configure animation for surface data.

        Args:
            surface_data_list: List of surface data arrays, each shape (x, y, frames)
        """
        self.current_surface_data_list = surface_data_list
        frame_counts = [data.shape[2] for data in surface_data_list]
        frame_count = min(frame_counts) if frame_counts else 0
        self.frame_index = 0
        self._configure_controls(frame_count)

    def _configure_controls(self, frame_count: int):
        """Update UI controls for given frame count.

        Args:
            frame_count: Total number of frames available
        """
        max_frame = max(0, frame_count - 1)
        slider_blocker = QSignalBlocker(self.frame_slider)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(max_frame)
        self.frame_slider.setValue(min(self.frame_index, max_frame))
        self.frame_slider.setEnabled(frame_count > 1)
        del slider_blocker

        self.play_button.setChecked(False)
        self.play_button.setText("Play")
        self.play_button.setEnabled(frame_count > 1)
        self._set_frame_label(min(self.frame_index, max_frame), frame_count)

    def disable_controls(self):
        """Disable all animation controls."""
        self.animation_timer.stop()
        self.play_button.setChecked(False)
        self.play_button.setText("Play")
        self.play_button.setEnabled(False)
        slider_blocker = QSignalBlocker(self.frame_slider)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(0)
        self.frame_slider.setValue(0)
        self.frame_slider.setEnabled(False)
        del slider_blocker
        self.frame_label.setText("0/0")

    def _set_frame_label(self, frame_index: int, frame_count: int):
        """Update frame label display.

        Args:
            frame_index: Current frame index (0-based)
            frame_count: Total frame count
        """
        self.frame_label.setText(f"{frame_index + 1}/{frame_count}")

    def on_frame_slider_changed(self, frame_index: int):
        """Handle frame slider value change.

        Args:
            frame_index: New frame index from slider
        """
        self.frame_index = int(frame_index)
        if self._on_frame_changed:
            self._on_frame_changed(self.frame_index)

    def toggle_animation(self, playing: bool):
        """Toggle animation playback.

        Args:
            playing: Whether animation should be playing
        """
        if not self.current_surface_data_list:
            self.play_button.setChecked(False)
            self.play_button.setText("Play")
            return

        if playing:
            self.play_button.setText("Pause")
            self.animation_timer.start()
        else:
            self.play_button.setText("Play")
            self.animation_timer.stop()

    def _advance_frame(self):
        """Advance animation to next frame."""
        if not self.current_surface_data_list:
            self.animation_timer.stop()
            return

        frame_count = min(data.shape[2] for data in self.current_surface_data_list)
        if frame_count <= 1:
            self.animation_timer.stop()
            return

        next_index = (self.frame_index + 1) % frame_count
        slider_blocker = QSignalBlocker(self.frame_slider)
        self.frame_slider.setValue(next_index)
        del slider_blocker
        self.frame_index = next_index
        if self._on_frame_changed:
            self._on_frame_changed(self.frame_index)

    def stop_animation(self):
        """Stop animation playback."""
        self.animation_timer.stop()
        self.play_button.setChecked(False)
        self.play_button.setText("Play")
