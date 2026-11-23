"""Small reusable controls for the animations and the story tab.

Panel's built-in Player has nine buttons (slower, first, previous, reverse, pause, play,
next, last, faster), which users found confusing. These replace it with ONE Play/Pause
button (+ a slider or step buttons to jump). The animation itself is a periodic callback
on the server that moves to the next frame every `interval` milliseconds.
"""

from __future__ import annotations

from typing import Callable, Sequence

import panel as pn
import param
from panel.custom import JSComponent

from theme import BUTTON_CSS

PLAY, PAUSE = "▶  Play", "❚❚  Pause"


class PlayButton:
    """One button that plays / pauses a list of frames.

    on_frame(frame) draws one frame; start_index() says where playing starts
    (e.g. from the beginning, or from the current slider position).
    """

    def __init__(self, frames: Sequence, on_frame: Callable, interval: int,
                 start_index: Callable[[], int] = lambda: 0, label: str = PLAY):
        self.frames, self.on_frame, self.interval = list(frames), on_frame, interval
        self.start_index, self.label = start_index, label
        self.button = pn.widgets.Button(name=label, width=170, stylesheets=[BUTTON_CSS])
        self.button.on_click(lambda e: self.toggle())
        self._callback = None
        self._i = 0

    @property
    def playing(self) -> bool:
        return self._callback is not None

    def play(self) -> None:
        self.stop()
        self._i = self.start_index()
        self._callback = pn.state.add_periodic_callback(self._tick, period=self.interval)
        self.button.name = PAUSE

    def stop(self) -> None:
        if self._callback is not None:
            self._callback.stop()
            self._callback = None
        self.button.name = self.label

    def toggle(self) -> None:
        self.stop() if self.playing else self.play()

    def _tick(self) -> None:
        if self._i >= len(self.frames):
            self.stop()
            return
        self.on_frame(self.frames[self._i])
        self._i += 1


class SimplePlayer:
    """Play/Pause button + a slider that shows readable labels (e.g. dates, 'MD 3').

    `slider.value` is the current frame value: bind charts to it like any widget.
    """

    def __init__(self, name: str, values: Sequence, labels: Sequence[str], interval: int,
                 value=None, width: int = 420):
        self.values = list(values)
        self.slider = pn.widgets.DiscreteSlider(
            name=name, options=dict(zip(labels, self.values)),
            value=self.values[-1] if value is None else value, width=width)
        self.play_button = PlayButton(self.values, self._show, interval, self._start)
        self.view = pn.Row(self.play_button.button, self.slider, align="center")

    def _show(self, value) -> None:
        self.slider.value = value

    def _start(self) -> int:
        """Continue from the slider position; from the start if it is at the end."""
        i = self.values.index(self.slider.value)
        return 0 if i >= len(self.values) - 1 else i + 1

    def restart(self) -> None:
        """Play from the very first frame (used when a story step opens)."""
        self.slider.value = self.values[0]
        self.play_button.play()

    def stop(self) -> None:
        self.play_button.stop()


class ArrowKeys(JSComponent):
    """Invisible component: reports ← / → key presses to Python as `key`.

    Only active while it is on screen (the story tab), and ignores keys typed into
    inputs, sliders and dropdowns so they keep working normally.
    """

    key = param.String(default="")

    _esm = """
    export function render({ model }) {
      const onKey = (e) => {
        const target = e.composedPath()[0];
        const tag = (target && target.tagName) || "";
        if (["INPUT", "SELECT", "TEXTAREA"].includes(tag)) return;
        if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
          model.key = e.key + ":" + Date.now();   // timestamp: same key twice still changes
        }
      };
      document.addEventListener("keydown", onKey);
      model.on("remove", () => document.removeEventListener("keydown", onKey));
      return document.createElement("span");
    }
    """
