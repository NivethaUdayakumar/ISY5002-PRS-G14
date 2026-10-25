from threading import Lock

import cv2

from constants.file_paths import CameraFilePaths

# Stepping forward frame by frame is cheaper than a seek for short jumps; beyond
# this many seconds ahead (or any jump backwards) we seek instead.
MAX_FORWARD_SECONDS = 3


class _CameraStream:
    """Keeps one camera's video open between requests so consecutive offsets
    can be read by stepping forward instead of reopening and seeking the file."""

    def __init__(self, file_path):
        self.file_path = file_path
        self.lock = Lock()
        self.cap = None
        self.fps = None
        self.next_frame = 0  # index of the frame the next read() will return

    def _open(self):
        self.cap = cv2.VideoCapture(self.file_path)
        if not self.cap.isOpened():
            self.cap = None
            return False
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.next_frame = 0
        return True

    def read(self, offset):
        with self.lock:
            if self.cap is None and not self._open():
                return None

            target_frame = int(round(offset * self.fps))
            frames_ahead = target_frame - self.next_frame

            if frames_ahead < 0 or frames_ahead > MAX_FORWARD_SECONDS * self.fps:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            else:
                for _ in range(frames_ahead):
                    if not self.cap.grab():
                        self.next_frame = float("inf")
                        return None

            success, frame = self.cap.read()
            if not success:
                # Past the end of the video; force a seek on the next request.
                self.next_frame = float("inf")
                return None

            self.next_frame = target_frame + 1
            return frame


_streams = {}
_streams_lock = Lock()


def read_frame(camera_id, offset):
    """Returns the frame at `offset` seconds for `camera_id`, or None if it
    can't be read (unknown camera, unreadable video, or offset past the end)."""
    file_path = CameraFilePaths.get(camera_id)
    if file_path is None:
        return None

    with _streams_lock:
        stream = _streams.get(camera_id)
        if stream is None:
            stream = _streams[camera_id] = _CameraStream(file_path)

    return stream.read(offset)
