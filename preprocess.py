"""
preprocess.py — Pipeline de preprocesamiento de imagen.

Pipeline:
  Frame BGR → Escala de grises → Suavizado Gaussiano → Detección de modo
  noche → Umbralización binaria → Extracción de ROI → Imagen binaria lista.

Modo noche:
  El juego del dinosaurio de Chrome alterna entre fondo claro (día) y fondo
  oscuro (noche). Se detecta automáticamente midiendo el brillo promedio de
  una muestra del fondo. En modo noche se invierte la umbralización para
  mantener la convención: obstáculos = píxeles blancos (255).
"""

import cv2
import numpy as np
from config import GameConfig


class Preprocessor:
    """Preprocesa frames del juego para facilitar la detección."""

    def __init__(self, config: GameConfig):
        self.cfg = config
        self._is_night_mode = False

    @property
    def is_night_mode(self) -> bool:
        return self._is_night_mode

    def detect_night_mode(self, gray: np.ndarray) -> bool:
        """Detecta si el juego está en modo noche.

        Muestrea una pequeña región del fondo (esquina superior izquierda
        de la zona de juego, que normalmente no tiene obstáculos) y calcula
        el brillo promedio.

        Args:
            gray: imagen en escala de grises del frame completo del juego.

        Returns:
            True si está en modo noche (fondo oscuro).
        """
        h, w = gray.shape[:2]
        # Muestrear esquina superior izquierda (5% del frame)
        sample_h = max(1, int(h * 0.10))
        sample_w = max(1, int(w * 0.10))
        sample = gray[2:sample_h, 2:sample_w]
        avg_brightness = float(np.mean(sample))
        self._is_night_mode = avg_brightness < self.cfg.night_mode_brightness_limit
        return self._is_night_mode

    def to_grayscale(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Convierte frame BGR a escala de grises."""
        return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    def apply_threshold(self, gray: np.ndarray) -> np.ndarray:
        """Aplica umbralización binaria adaptada al modo día/noche.

        Convención de salida:
            - Obstáculos (objetos de interés) → blanco (255)
            - Fondo → negro (0)

        En modo día: los obstáculos son oscuros sobre fondo claro → THRESH_BINARY_INV
        En modo noche: los obstáculos son claros sobre fondo oscuro → THRESH_BINARY
        """
        if self._is_night_mode:
            _, binary = cv2.threshold(
                gray, self.cfg.threshold_value, 255, cv2.THRESH_BINARY
            )
        else:
            _, binary = cv2.threshold(
                gray, self.cfg.threshold_value, 255, cv2.THRESH_BINARY_INV
            )
        return binary

    def extract_roi(self, image: np.ndarray) -> np.ndarray:
        """Extrae la región de interés (ROI) frente al dinosaurio.

        Las coordenadas de la ROI son relativas al frame del juego (porcentajes).

        Args:
            image: imagen (gris o binaria) del frame completo del juego.

        Returns:
            Sub-imagen recortada correspondiente a la ROI.
        """
        h, w = image.shape[:2]
        x1 = int(w * self.cfg.roi_x_start)
        x2 = int(w * self.cfg.roi_x_end)
        y1 = int(h * self.cfg.roi_y_start)
        y2 = int(h * self.cfg.roi_y_end)
        return image[y1:y2, x1:x2]

    def get_roi_coords(self, frame_shape: tuple) -> tuple:
        """Retorna coordenadas absolutas (x1, y1, x2, y2) de la ROI.

        Útil para dibujar el rectángulo de la ROI sobre el frame original.
        """
        h, w = frame_shape[:2]
        x1 = int(w * self.cfg.roi_x_start)
        x2 = int(w * self.cfg.roi_x_end)
        y1 = int(h * self.cfg.roi_y_start)
        y2 = int(h * self.cfg.roi_y_end)
        return x1, y1, x2, y2

    def process(self, frame_bgr: np.ndarray) -> tuple:
        """Pipeline completo de preprocesamiento.

        Args:
            frame_bgr: frame capturado en BGR.

        Returns:
            (gray, binary_full, binary_roi):
                gray: imagen en escala de grises.
                binary_full: imagen binaria completa (para visualización).
                binary_roi: imagen binaria recortada a la ROI (para detección).
        """
        gray = self.to_grayscale(frame_bgr)

        # Suavizado ligero para reducir ruido
        gray_smooth = cv2.GaussianBlur(gray, (3, 3), 0)

        # Detectar modo día/noche
        self.detect_night_mode(gray_smooth)

        # Umbralización
        binary_full = self.apply_threshold(gray_smooth)

        # Extraer ROI
        binary_roi = self.extract_roi(binary_full)

        return gray, binary_full, binary_roi
