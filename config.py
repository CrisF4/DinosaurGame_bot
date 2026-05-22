"""
config.py — Configuración centralizada del sistema Dino Bot.
Formato de persistencia utilizado: YAML.
"""

import os
import yaml
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional


@dataclass
class GameConfig:
    """Configuración completa del sistema Dino Bot."""

    # === Región de captura (se llena durante calibración) ===
    game_region: Dict[str, int] = field(default_factory=lambda: {
        "top": 200, "left": 100, "width": 600, "height": 200
    })

    # === ROI relativa al game_region (porcentajes 0.0–1.0) ===
    # Define la zona frente al dinosaurio donde se buscan obstáculos
    roi_x_start: float = 0.10    # inicio horizontal
    roi_x_end: float = 0.55     # fin horizontal
    roi_y_start: float = 0.20   # inicio vertical (dejar margen arriba para score)
    roi_y_end: float = 0.95     # fin vertical (cerca del suelo)

    # === Umbralización ===
    threshold_value: int = 127   # valor para cv2.threshold
    # Modo noche: se detecta automáticamente por brillo promedio del fondo
    night_mode_brightness_limit: int = 128  # si avg < esto → modo noche

    # === Detector de píxeles (Método 1) ===
    pixel_density_threshold: float = 0.015  # % de píxeles activos para detección
    pixel_num_columns: int = 10             # bandas verticales para escaneo

    # === Detector de contornos (Método 2) ===
    min_contour_area: int = 80              # área mínima para no ser ruido
    max_contour_area: int = 50000           # área máxima (evitar detectar el suelo)

    # === Clasificación de obstáculos ===
    # Posición Y normalizada del centroide en la ROI (0.0=arriba, 1.0=abajo)
    bird_high_y_max: float = 0.29     # ave alta → el dino pasa por debajo
    bird_mid_y_max: float = 0.54      # ave media → agacharse
    # si center_y > bird_mid_y_max     → ave baja / a nivel de suelo → saltar
    # Aspect ratio para distinguir ave (ancha) de cactus (alto)
    bird_aspect_ratio_min: float = 1.3

    # === Regla de decisión. A mayor porcentaje, mas anticipada sera la acción ===
    base_jump_distance: float = 0.12   # distancia normalizada base para saltar
    base_duck_distance: float = 0.15   # distancia base para agacharse
    # Adaptación dinámica a la velocidad del juego
    speed_increase_rate: float = 0.01 # incremento del factor de velocidad por segundo
    max_speed_factor: float = 3.0      # tope del factor de velocidad

    # === Control de teclado ===
    action_cooldown_ms: float = 250.0  # ms entre acciones consecutivas
    jump_hold_ms: float = 150.0        # ms que se mantiene la tecla de salto
    duck_hold_ms: float = 400.0        # ms que se mantiene la tecla de agacharse

    # === Visualización ===
    show_visualization: bool = True
    visualization_scale: float = 1.0   # escala del panel de visualización

    def save(self, path: str) -> None:
        """Guarda la configuración en archivo YAML."""
        data = asdict(self)
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print(f"[Config] Configuración guardada en: {path}")

    @classmethod
    def load(cls, path: str) -> "GameConfig":
        """Carga configuración desde archivo YAML."""
        if not os.path.exists(path):
            print(f"[Config] Archivo no encontrado: {path}. Usando valores por defecto.")
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            return cls()
        return cls(**data)

    def save_json(self, path: str) -> None:
        """Exporta configuración en formato JSON (alternativa)."""
        data = asdict(self)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[Config] Configuración exportada a JSON: {path}")

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
