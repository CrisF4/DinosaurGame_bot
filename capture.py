"""
capture.py — Captura de pantalla usando mss.
La clase ScreenCapture expone una interfaz simple para capturar frames
de una región específica de la pantalla o la pantalla completa.
"""

import time
import numpy as np
import cv2
import mss

class ScreenCapture:
    """Captura de pantalla usando mss."""

    def __init__(self, region: dict = None):
        """
        Args:
            region: {"top": int, "left": int, "width": int, "height": int}
                    Región de captura en coordenadas absolutas de la pantalla.
        """
        self._region = region or {}
        self._sct = mss.mss()
        self._frame_times = []
        self._fps_window = 30

    def grab_frame(self) -> np.ndarray:
        """Captura un frame de la región configurada.

        Returns:
            Imagen BGR como numpy array (H, W, 3).
        """
        raw = self._sct.grab(self._region)
        frame = np.array(raw, dtype=np.uint8)
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        now = time.perf_counter()
        self._frame_times.append(now)
        if len(self._frame_times) > self._fps_window:
            self._frame_times.pop(0)

        return frame_bgr

    def get_fps(self) -> float:
        """FPS promedio sobre ventana deslizante."""
        if len(self._frame_times) < 2:
            return 0.0
        elapsed = self._frame_times[-1] - self._frame_times[0]
        return (len(self._frame_times) - 1) / elapsed if elapsed > 0 else 0.0

    def grab_full_screen(self) -> np.ndarray:
        """Captura pantalla completa (para calibración)."""
        monitor = self._sct.monitors[1]  # monitor principal
        raw = self._sct.grab(monitor)
        frame = np.array(raw, dtype=np.uint8)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    def update_region(self, region: dict) -> None:
        """Actualiza la región de captura."""
        self._region = region

    def close(self) -> None:
        """Libera recursos de la captura."""
        self._sct.close()
        print("[Capture] Captura cerrada.")
