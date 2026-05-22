"""
detector_contours.py — Método 2: Detección de obstáculos por análisis de contornos.

Algoritmo:
  1. Recibir imagen binaria de la ROI (blanco=obstáculo, negro=fondo).
  2. cv2.findContours() con RETR_EXTERNAL para obtener solo contornos exteriores.
  3. Filtrar contornos por área mínima (eliminar ruido) y máxima (evitar suelo).
  4. Para cada contorno: calcular boundingRect.
  5. Clasificación por aspect ratio + posición Y del centroide:
     - Aspect ratio >= 1.3 (más ancho que alto) → ave
       - center_y < 0.30 → bird_high (el dino pasa por debajo)
       - center_y < 0.55 → bird_mid (agacharse)
       - center_y >= 0.55 → bird_low (ave a nivel de suelo → saltar)
     - Aspect ratio < 1.3 → cactus (saltar)
  6. Distancia: posición X del bounding box normalizada al ancho de la ROI.
"""

import cv2
import numpy as np
from typing import List
from config import GameConfig
from detector_pixels import Detection


class ContourDetector:
    """Detector de obstáculos basado en análisis de contornos."""

    def __init__(self, config: GameConfig):
        self.cfg = config

    def detect(self, binary_roi: np.ndarray) -> List[Detection]:
        """Analiza la ROI binaria con findContours y retorna detecciones.

        Args:
            binary_roi: imagen binaria (0/255) de la ROI.
                         Píxeles blancos = obstáculo.

        Returns:
            Lista de Detection ordenada por distancia (más cercano primero).
        """
        if binary_roi is None or binary_roi.size == 0:
            return []

        h, w = binary_roi.shape[:2]

        # Encontrar contornos externos
        contours, _ = cv2.findContours(
            binary_roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        detections = []

        for cnt in contours:
            area = cv2.contourArea(cnt)

            # Filtrar por área (eliminar ruido y objetos demasiado grandes)
            if area < self.cfg.min_contour_area:
                continue
            if area > self.cfg.max_contour_area:
                continue

            # Bounding box
            x, y, bw, bh = cv2.boundingRect(cnt)

            # Centroide Y normalizado
            center_y = (y + bh / 2.0) / h

            # Distancia X normalizada (borde izquierdo del bbox)
            distance_x = x / w

            # Aspect ratio para clasificación
            aspect_ratio = bw / max(bh, 1)

            # Clasificación
            obstacle_type = self._classify(center_y, aspect_ratio)

            # Confianza basada en el área relativa al bbox
            bbox_area = bw * bh
            if bbox_area > 0:
                solidity = area / bbox_area
            else:
                solidity = 0.0
            confidence = min(1.0, solidity)

            det = Detection(
                obstacle_type=obstacle_type,
                distance_x=distance_x,
                bbox=(x, y, bw, bh),
                confidence=confidence,
                center_y=center_y,
            )
            detections.append(det)

        # Ordenar por distancia (más cercano primero)
        detections.sort(key=lambda d: d.distance_x)
        return detections

    def _classify(self, center_y: float, aspect_ratio: float) -> str:
        """Clasifica el tipo de obstáculo.

        Args:
            center_y: posición Y normalizada del centroide (0=arriba, 1=abajo).
            aspect_ratio: ancho/alto del bounding box.

        Returns:
            "cactus", "bird_high", "bird_mid", o "bird_low".
        """
        if aspect_ratio >= self.cfg.bird_aspect_ratio_min:
            # Parece un ave (forma horizontal/ancha)
            if center_y < self.cfg.bird_high_y_max:
                return "bird_high"
            elif center_y < self.cfg.bird_mid_y_max:
                return "bird_mid"
            elif center_y > self.cfg.bird_mid_y_max:
                return "bird_low"  # ave a nivel de suelo

        # Forma vertical o cuadrada → cactus
        return "cactus"

    def draw_detections(self, roi_image: np.ndarray,
                        detections: List[Detection]) -> np.ndarray:
        """Dibuja los bounding boxes y etiquetas sobre una imagen de la ROI.

        Args:
            roi_image: imagen BGR o gris de la ROI (se copia internamente).
            detections: lista de detecciones a dibujar.

        Returns:
            Imagen con las detecciones dibujadas.
        """
        if len(roi_image.shape) == 2:
            vis = cv2.cvtColor(roi_image, cv2.COLOR_GRAY2BGR)
        else:
            vis = roi_image.copy()

        colors = {
            "cactus": (0, 0, 255),      # rojo
            "bird_high": (255, 200, 0),  # cyan
            "bird_mid": (0, 165, 255),   # naranja
            "bird_low": (0, 255, 255),   # amarillo
        }

        for det in detections:
            x, y, bw, bh = det.bbox
            color = colors.get(det.obstacle_type, (255, 255, 255))

            cv2.rectangle(vis, (x, y), (x + bw, y + bh), color, 2)

            label = f"{det.obstacle_type} d={det.distance_x:.2f}"
            cv2.putText(vis, label, (x, max(y - 5, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        return vis
