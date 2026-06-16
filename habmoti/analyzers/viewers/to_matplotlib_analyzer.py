from dataclasses import dataclass
from multiprocessing import Event, Process, Queue
import time
from queue import Empty, Full
from typing import TYPE_CHECKING, override

import numpy as np

from .data_viewer_analyzer import DataViewerAnalyzer

if TYPE_CHECKING:
    from ...habmoti import Habmoti
    from ...data.frame_data import FrameData


_INITIAL_CAMERA_ELEV = 90
_INITIAL_CAMERA_AZIM = 0
_INITIAL_CAMERA_ROLL = 90


@dataclass
class _BodyArtists:
    scatter: object
    lines: list[object]


@dataclass
class _SceneArtists:
    bodies: list[_BodyArtists]
    fixed_limits: tuple[tuple[float, float], tuple[float, float], tuple[float, float]] | None
    segment_links: list[tuple[int, int]]


def _matplotlib_viewer_process(data_queue, is_ready_event, stop_event) -> None:
    import matplotlib.pyplot as plt

    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    fig.canvas.manager.set_window_title("HABMOT-I Matplotlib Viewer")
    plt.show(block=False)
    fig.tight_layout()

    latest_bodies: list[np.ndarray] = []
    latest_segment_links: list[tuple[int, int]] = []
    scene: _SceneArtists | None = None
    is_ready_event.set()

    while not stop_event.is_set():
        has_new_payload = False

        # Keep only the freshest payload to avoid latency buildup.
        while True:
            try:
                bodies, segment_links = data_queue.get_nowait()
            except Empty:
                break
            latest_bodies = bodies
            latest_segment_links = segment_links
            has_new_payload = True

        if not plt.fignum_exists(fig.number):
            break

        if has_new_payload:
            if scene is None or not _scene_matches(scene, latest_bodies, latest_segment_links):
                scene = _build_scene(ax, latest_bodies, latest_segment_links)
            else:
                _update_scene(scene, latest_bodies)
            fig.canvas.draw_idle()

        # Keep GUI responsive without forcing a front-focus redraw every tick.
        fig.canvas.flush_events()
        stop_event.wait(0.03)

    if plt.fignum_exists(fig.number):
        plt.close(fig)


def _scene_matches(
    scene: _SceneArtists,
    bodies: list[np.ndarray],
    segment_links: list[tuple[int, int]],
) -> bool:
    if len(scene.bodies) != len(bodies):
        return False
    if scene.segment_links != segment_links:
        return False

    for body_artists, values in zip(scene.bodies, bodies, strict=False):
        if values.ndim != 2 or values.shape[1] < 3:
            return False
        if len(body_artists.lines) != len(segment_links):
            return False

    return True


def _build_scene(
    ax,
    bodies: list[np.ndarray],
    segment_links: list[tuple[int, int]],
) -> _SceneArtists:
    ax.clear()

    body_artists: list[_BodyArtists] = []
    fixed_limits = _compute_equal_limits(bodies)

    for body_index, values in enumerate(bodies):
        if values.ndim != 2 or values.shape[1] < 3:
            continue

        clr = ToMatplotlibAnalyzer._generate_color_id(body_index)

        finite_mask = np.all(np.isfinite(values[:, :3]), axis=1)
        points = values[finite_mask]
        scatter = ax.scatter(
            points[:, 0] if points.size > 0 else [],
            points[:, 1] if points.size > 0 else [],
            points[:, 2] if points.size > 0 else [],
            s=16,
            c=[clr],
            label=f"Body {body_index}",
        )

        line_artists: list[object] = []

        for idx_a, idx_b in segment_links:
            if idx_a >= values.shape[0] or idx_b >= values.shape[0]:
                continue

            point_a = values[idx_a]
            point_b = values[idx_b]
            if not (np.all(np.isfinite(point_a[:3])) and np.all(np.isfinite(point_b[:3]))):
                continue

            (line_artist,) = ax.plot(
                [point_a[0], point_b[0]],
                [point_a[1], point_b[1]],
                [point_a[2], point_b[2]],
                c=clr,
                linewidth=1.0,
            )
            line_artists.append(line_artist)

        body_artists.append(_BodyArtists(scatter=scatter, lines=line_artists))

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title("Body Kinematics")
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")
    ax.view_init(elev=_INITIAL_CAMERA_ELEV, azim=_INITIAL_CAMERA_AZIM, roll=_INITIAL_CAMERA_ROLL)

    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(loc="upper right")

    return _SceneArtists(bodies=body_artists, fixed_limits=fixed_limits, segment_links=list(segment_links))


def _update_scene(scene: _SceneArtists, bodies: list[np.ndarray]) -> None:
    for body_index, (body_artists, values) in enumerate(zip(scene.bodies, bodies, strict=False)):
        if values.ndim != 2 or values.shape[1] < 3:
            continue

        clr = ToMatplotlibAnalyzer._generate_color_id(body_index)

        finite_mask = np.all(np.isfinite(values[:, :3]), axis=1)
        points = values[finite_mask]
        body_artists.scatter._offsets3d = (
            points[:, 0] if points.size > 0 else np.array([]),
            points[:, 1] if points.size > 0 else np.array([]),
            points[:, 2] if points.size > 0 else np.array([]),
        )

        for line_artist, (idx_a, idx_b) in zip(body_artists.lines, scene.segment_links, strict=False):
            if idx_a >= values.shape[0] or idx_b >= values.shape[0]:
                line_artist.set_data_3d([], [], [])
                continue

            point_a = values[idx_a]
            point_b = values[idx_b]
            if not (np.all(np.isfinite(point_a[:3])) and np.all(np.isfinite(point_b[:3]))):
                line_artist.set_data_3d([], [], [])
                continue

            line_artist.set_data_3d(
                [point_a[0], point_b[0]],
                [point_a[1], point_b[1]],
                [point_a[2], point_b[2]],
            )

        body_artists.scatter.set_color([clr])
        for line_artist in body_artists.lines:
            line_artist.set_color(clr)


def _compute_equal_limits(
    bodies: list[np.ndarray],
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    finite_points: list[np.ndarray] = []
    for values in bodies:
        if values.ndim != 2 or values.shape[1] < 3:
            continue
        mask = np.all(np.isfinite(values[:, :3]), axis=1)
        pts = values[mask, :3]
        if pts.size > 0:
            finite_points.append(pts)

    if not finite_points:
        return (-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0)

    points = np.vstack(finite_points)
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    center = 0.5 * (mins + maxs)
    radius = 0.5 * max(float(maxs[0] - mins[0]), float(maxs[1] - mins[1]), float(maxs[2] - mins[2]))
    if radius <= 0.0:
        radius = 1.0

    return (
        (float(center[0] - radius), float(center[0] + radius)),
        (float(center[1] - radius), float(center[1] + radius)),
        (float(center[2] - radius), float(center[2] + radius)),
    )


class ToMatplotlibAnalyzer(DataViewerAnalyzer):
    """Render body kinematics in a live 3D Matplotlib view."""

    def __init__(self, show_body_coordinate_systems: bool = False) -> None:
        self._is_started = False
        self._habmoti: Habmoti | None = None
        self._viewer_process: Process | None = None
        self._viewer_stop_event = None
        self._viewer_queue: Queue | None = None
        self._stop_notified = False
        self._show_body_coordinate_systems = show_body_coordinate_systems

    @property
    @override
    def name(self) -> str:
        return "Matplotlib Viewer"

    @override
    def initialize(self, habmoti: Habmoti) -> None:
        try:
            import matplotlib.pyplot as plt
        except ImportError as e:
            raise ImportError("matplotlib is not installed. Install with: pip install matplotlib") from e
        finally:
            # Ensure lazy import check without keeping pyplot objects in this thread.
            try:
                del plt
            except UnboundLocalError:
                pass

        self._habmoti = habmoti
        self._is_started = True
        self._stop_notified = False
        self._viewer_is_ready_event = Event()
        self._viewer_stop_event = Event()
        self._viewer_queue = Queue(maxsize=1)
        self._viewer_process = Process(
            target=_matplotlib_viewer_process,
            args=(self._viewer_queue, self._viewer_is_ready_event, self._viewer_stop_event),
            daemon=True,
        )
        self._viewer_process.start()
        while not self._viewer_is_ready_event.is_set():
            time.sleep(0.01)

    @override
    def perform(self, frame_data: FrameData | None) -> None:
        if not self._is_started:
            return

        if self._viewer_stop_event is not None and self._viewer_stop_event.is_set():
            if not self._stop_notified and self._habmoti is not None:
                self._stop_notified = True
                self._habmoti.terminate()
            return

        if self._viewer_process is not None and not self._viewer_process.is_alive():
            if not self._stop_notified and self._habmoti is not None:
                self._stop_notified = True
                self._habmoti.terminate()
            return

        if frame_data is None:
            return

        body_kinematics = frame_data.body_kinematics
        segment_links = [
            (int(joint_a.value), int(joint_b.value)) for joint_a, joint_b in body_kinematics.body_model.segment_links()
        ]
        bodies = [np.asarray(joints, dtype=np.float64).copy() for joints in body_kinematics.body_list]

        if self._show_body_coordinate_systems:
            joint_coordinate_systems = frame_data.body_kinematics.body_coordinate_system
            for body_index, jcs in enumerate(joint_coordinate_systems):
                origin = jcs[:3, 3]
                axes = jcs[:3, :3] * 0.1
                translated_axes = axes + np.repeat(origin[:, None], 3, axis=1)
                body_count = bodies[body_index].shape[0]
                bodies[body_index] = np.concatenate((bodies[body_index], translated_axes.T, origin[None, :]), axis=0)
                segment_links.extend(
                    [
                        (body_count + 3, body_count + 0),
                        (body_count + 3, body_count + 1),
                        (body_count + 3, body_count + 2),
                    ]
                )

        if self._viewer_queue is None:
            return

        try:
            while True:
                self._viewer_queue.get_nowait()
        except Empty:
            pass

        try:
            self._viewer_queue.put_nowait((bodies, segment_links))
        except Full:
            pass

    @override
    def dispose(self) -> None:
        self._is_started = False
        self._habmoti = None
        self._stop_notified = False

        if self._viewer_stop_event is not None:
            self._viewer_stop_event.set()

        if self._viewer_process is not None and self._viewer_process.is_alive():
            self._viewer_process.join(timeout=1.0)

        self._viewer_process = None
        self._viewer_stop_event = None
        self._viewer_queue = None

    @staticmethod
    def _generate_color_id_u(idx: int) -> list[int]:
        if idx < 0:
            return [236, 184, 36, 255]

        colors = [(232, 176, 59), (175, 208, 25), (102, 205, 105), (185, 0, 255), (99, 107, 252)]
        color_idx = idx % len(colors)
        return [colors[color_idx][0], colors[color_idx][1], colors[color_idx][2], 255]

    @staticmethod
    def _generate_color_id(idx: int) -> tuple[float, float, float]:
        clr = np.divide(ToMatplotlibAnalyzer._generate_color_id_u(idx), 255.0)
        clr[0], clr[2] = clr[2], clr[0]
        return float(clr[0]), float(clr[1]), float(clr[2])
