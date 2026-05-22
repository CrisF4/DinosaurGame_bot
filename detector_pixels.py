"""
detector_pixels.py — Método 1: Detección de obstáculos por conteo de píxeles.

Algoritmo:
  1. Dividir la ROI binaria en N bandas verticales (columnas).
  2. Para cada banda, calcular la densidad de píxeles blancos (obstáculo).
  3. Si la densidad supera el umbral → obstáculo detectado en esa banda.
  4. La primera banda con detección indica la distancia al obstáculo.
  5. Clasificación: se analiza la distribución vertical de los píxeles activos.
     - Si se concentran en la parte inferior → cactus
     - Si se concentran en la parte superior/media → ave (alta, media o baja)
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
from config import GameConfig


@dataclass
class Detection:
    """Resultado de detección de un obstáculo."""
    obstacle_type: str      # "cactus", "bird_high", "bird_mid", "bird_low"
    distance_x: float       # 0.0 (tocando al dino) → 1.0 (borde derecho de ROI)
    bbox: Tuple[int, int, int, int]  # (x, y, w, h) en coordenadas de la ROI
    confidence: float        # 0.0 – 1.0
    center_y: float          # posición Y normalizada del centroide (0.0=arriba, 1.0=abajo)


class PixelDetector:
    """Detector de obstáculos basado en densidad de píxeles."""

    def __init__(self, config: GameConfig):
        self.cfg = config

    def detect(self, binary_roi: np.ndarray) -> List[Detection]:
        """Analiza la ROI binaria y retorna las detecciones encontradas.

        Args:
            binary_roi: imagen binaria (0/255) de la ROI.
                         Píxeles blancos = obstáculo.

        Returns:
            Lista de Detection ordenada por distancia (más cercano primero).
        """
        if binary_roi is None or binary_roi.size == 0:
            return []

        h, w = binary_roi.shape[:2]
        num_cols = self.cfg.pixel_num_columns
        col_width = max(1, w // num_cols)
        raw_detections = []

        for i in range(num_cols):
            x_start = i * col_width
            x_end = min((i + 1) * col_width, w)
            band = binary_roi[:, x_start:x_end]

            # Densidad de píxeles activos en esta banda
            total_pixels = band.size
            if total_pixels == 0:
                continue
            active_pixels = np.count_nonzero(band)
            density = active_pixels / total_pixels

            if density < self.cfg.pixel_density_threshold:
                continue

            # Hay obstáculo en esta banda → encontrar extensión vertical
            row_sums = np.sum(band, axis=1) / 255.0  # píxeles activos por fila
            active_rows = np.where(row_sums > 0)[0]

            if len(active_rows) == 0:
                continue

            y_min = int(active_rows[0])
            y_max = int(active_rows[-1])
            obj_h = y_max - y_min + 1
            obj_w = x_end - x_start

            # Centroide Y normalizado
            center_y = (y_min + y_max) / 2.0 / h

            # Distancia X normalizada
            distance_x = x_start / w

            # Confianza basada en la densidad
            confidence = min(1.0, density / (self.cfg.pixel_density_threshold * 3))

            # Añadimos detección "cruda" sin clasificar todavía
            det = Detection(
                obstacle_type="unknown",
                distance_x=distance_x,
                bbox=(x_start, y_min, obj_w, obj_h),
                confidence=confidence,
                center_y=center_y,
            )
            raw_detections.append(det)

        # Fusionar detecciones adyacentes (solo verificando cercanía espacial)
        merged = self._merge_adjacent(raw_detections, h)

        # AHORA clasificamos los objetos unidos estrictamente por su altura final unida
        final_detections = []
        for det in merged:
            obstacle_type = self._classify_by_height(det.center_y)
            det.obstacle_type = obstacle_type
            final_detections.append(det)

        # Ordenar por distancia (más cercano primero)
        final_detections.sort(key=lambda d: d.distance_x)
        return final_detections

    def _classify_by_height(self, center_y: float) -> str:
        """Clasifica el tipo de obstáculo estrictamente por su posición vertical.
        
        A esta resolución y con el método de píxeles, analizar la forma de las
        tiras puede causar parpadeo e inestabilidad en la clasificación. 
        Clasificar por la posición en Y garantiza resultados sólidos.
        """
        print("DEBUG: center_y", center_y)
        if center_y < self.cfg.bird_high_y_max:
            return "bird_high"
        elif center_y < self.cfg.bird_mid_y_max and center_y > self.cfg.bird_high_y_max:
            return "bird_mid"
        elif center_y > self.cfg.bird_mid_y_max:
            return "cactus_or_bird_low"

    def _merge_adjacent(self, detections: List[Detection],
                        roi_h: int) -> List[Detection]:
        """Fusiona detecciones de bandas adyacentes espacialmente.
        """
        if len(detections) <= 1:
            return detections

        merged = []
        current = detections[0]

        for det in detections[1:]:
            # Verificar si son adyacentes (bbox.x + bbox.w ≈ next.bbox.x)
            curr_x_end = current.bbox[0] + current.bbox[2]
            gap = det.bbox[0] - curr_x_end

            # FUSIONAR SIEMPRE QUE ESTÉN PEGADOS (IGNORAR TIPO)
            if gap <= 2:
                # Fusionar: expandir bbox
                x = current.bbox[0]
                y = min(current.bbox[1], det.bbox[1])
                w = (det.bbox[0] + det.bbox[2]) - x
                h = max(current.bbox[1] + current.bbox[3],
                        det.bbox[1] + det.bbox[3]) - y

                center_y = (y + h / 2.0) / roi_h
                confidence = max(current.confidence, det.confidence)

                current = Detection(
                    obstacle_type="unknown",
                    distance_x=current.distance_x,  # mantener la distancia más cercana
                    bbox=(x, y, w, h),
                    confidence=confidence,
                    center_y=center_y,
                )
            else:
                merged.append(current)
                current = det

        merged.append(current)
        return merged
