"""
visualizer.py — Panel de visualización en tiempo real (2×2 grid).

Paneles:
  ┌──────────────────┬──────────────────┐
  │ 1. Frame original│ 2. Escala grises │
  │    + ROI marcada │    + umbral      │
  ├──────────────────┼──────────────────┤
  │ 3. ROI binaria   │ 4. Panel estado  │
  │    + detecciones │    FPS, métricas │
  └──────────────────┴──────────────────┘
"""
import cv2
import numpy as np
from typing import List
from detector_pixels import Detection


class Visualizer:
    WINDOW_NAME = "Dino Bot - Vision por Computadora"

    def __init__(self, panel_width: int = 320, panel_height: int = 180):
        self.pw = panel_width
        self.ph = panel_height
        self._colors = {
            "cactus": (0, 0, 255), # Rojo
            "bird_high": (255, 200, 0), # Cyan
            "bird_mid": (0, 165, 255), # Naranja
            "bird_low": (0, 255, 255), # Amarillo
            "cactus_or_bird_low": (0, 0, 255), # Rojo
        }

    def render(self, frame_bgr, gray, binary_roi, detections, fps, action,
               method_name, survival_time, is_night, roi_coords):
        """Renderiza el panel 2×2 con toda la información.

        Args:
            frame_bgr: frame original BGR.
            gray: imagen en escala de grises.
            binary_roi: imagen binaria de la ROI.
            detections: lista de Detection.
            fps: FPS actual.
            action: última acción ("jump"/"duck"/"none").
            method_name: nombre del método activo.
            survival_time: tiempo de supervivencia en segundos.
            is_night: True si está en modo noche.
            roi_coords: (x1, y1, x2, y2) de la ROI en el frame.
        """
        # Panel 1: Frame original con ROI
        p1 = self._make_panel_original(frame_bgr, roi_coords, detections)

        # Panel 2: Escala de grises
        p2 = self._make_panel_gray(gray)

        # Panel 3: ROI binaria con detecciones
        p3 = self._make_panel_roi(binary_roi, detections)

        # Panel 4: Estado
        p4 = self._make_panel_status(fps, action, method_name, survival_time,
                                      is_night, len(detections))

        # Combinar 2×2
        top = np.hstack([p1, p2])
        bottom = np.hstack([p3, p4])
        canvas = np.vstack([top, bottom])

        cv2.imshow(self.WINDOW_NAME, canvas)

    def _resize(self, img):
        return cv2.resize(img, (self.pw, self.ph))

    def _to_bgr(self, img):
        if len(img.shape) == 2:
            return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        return img

    def _make_panel_original(self, frame, roi_coords, detections):
        vis = frame.copy()
        if roi_coords:
            x1, y1, x2, y2 = roi_coords
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(vis, "ROI", (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(vis, "Original + ROI", (5, 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        return self._resize(vis)

    def _make_panel_gray(self, gray):
        vis = self._to_bgr(gray)
        cv2.putText(vis, "Escala de Grises", (5, 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        return self._resize(vis)

    def _make_panel_roi(self, binary_roi, detections):
        if binary_roi is None or binary_roi.size == 0:
            vis = np.zeros((self.ph, self.pw, 3), dtype=np.uint8)
            cv2.putText(vis, "Sin ROI", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
            return vis
        vis = self._to_bgr(binary_roi)
        for det in detections:
            x, y, bw, bh = det.bbox
            color = self._colors.get(det.obstacle_type, (255, 255, 255))
            cv2.rectangle(vis, (x, y), (x + bw, y + bh), color, 2)
            cv2.putText(vis, det.obstacle_type, (x, max(y - 3, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)
        cv2.putText(vis, "ROI Binaria + Detecciones", (5, 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        return self._resize(vis)

    def _make_panel_status(self, fps, action, method, survival, is_night, n_det):
        panel = np.zeros((self.ph, self.pw, 3), dtype=np.uint8)
        y = 20
        dy = 22
        font = cv2.FONT_HERSHEY_SIMPLEX
        fs = 0.5
        c = (200, 200, 200)
        green = (0, 255, 0)
        red = (0, 0, 255)
        yellow = (0, 255, 255)

        cv2.putText(panel, f"Metodo: {method}", (10, y), font, fs, c, 1); y += dy
        cv2.putText(panel, f"FPS: {fps:.1f}", (10, y), font, fs, green, 1); y += dy
        cv2.putText(panel, f"Supervivencia: {survival:.1f}s", (10, y), font, fs, c, 1); y += dy
        cv2.putText(panel, f"Detecciones: {n_det}", (10, y), font, fs, c, 1); y += dy

        # Acción con color
        act_color = green if action == "none" else (yellow if action == "duck" else red)
        act_text = {"jump": "SALTAR!", "duck": "AGACHARSE!", "none": "---"}.get(action, action)
        cv2.putText(panel, f"Accion: {act_text}", (10, y), font, 0.6, act_color, 2); y += dy

        mode = "NOCHE" if is_night else "DIA"
        cv2.putText(panel, f"Modo: {mode}", (10, y), font, fs, c, 1)

        return panel

    def close(self):
        cv2.destroyAllWindows()
