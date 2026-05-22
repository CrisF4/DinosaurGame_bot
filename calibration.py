"""
calibration.py — Pantalla de calibración interactiva.

Flujo:
  1. Captura pantalla completa con mss.
  2. El usuario selecciona la región del juego con cv2.selectROI.
  3. Ajuste fino de ROI y umbral con trackbars en tiempo real.
  4. Guarda la configuración en YAML.
"""

import cv2
import numpy as np
from capture import ScreenCapture
from config import GameConfig, DEFAULT_CONFIG_PATH


def run_calibration(config: GameConfig = None,
                    save_path: str = DEFAULT_CONFIG_PATH) -> GameConfig:
    """Ejecuta la calibración interactiva.

    Returns:
        GameConfig con los valores calibrados.
    """
    if config is None:
        config = GameConfig()

    # ── Paso 1: Capturar pantalla completa ──────────────────────
    capture = ScreenCapture()
    screen = capture.grab_full_screen()

    # ── Paso 2: Seleccionar región del juego ────────────────────
    print("\n[Calibración] Paso 1: Selecciona la región del juego del dinosaurio.")
    print("  → Arrastra un rectángulo sobre el área del juego.")
    print("  → Presiona ENTER para confirmar, o C para cancelar.\n")

    h, w = screen.shape[:2]
    scale = min(1.0, 1600 / w) if w > 1600 else 1.0
    display = cv2.resize(screen, None, fx=scale, fy=scale) if scale < 1.0 else screen.copy()

    roi = cv2.selectROI("Selecciona la region del juego", display, False, False)
    cv2.destroyAllWindows()

    if roi[2] == 0 or roi[3] == 0:
        print("[Calibración] Selección cancelada.")
        capture.close()
        return config

    x, y, rw, rh = roi
    config.game_region = {
        "top": int(y / scale),
        "left": int(x / scale),
        "width": int(rw / scale),
        "height": int(rh / scale),
    }
    print(f"[Calibración] Región seleccionada: {config.game_region}")

    # Actualizar la región de captura
    capture.update_region(config.game_region)

    # ── Paso 3: Ajuste fino con trackbars ───────────────────────
    print("\n[Calibración] Paso 2: Ajusta la ROI interna y el umbral.")
    print("  → 'S' para guardar, 'Q' para cancelar.\n")

    cv2.namedWindow("Calibracion")
    cv2.createTrackbar("Umbral", "Calibracion", config.threshold_value, 255, lambda x: None)
    cv2.createTrackbar("ROI X Ini%", "Calibracion", int(config.roi_x_start * 100), 100, lambda x: None)
    cv2.createTrackbar("ROI X Fin%", "Calibracion", int(config.roi_x_end * 100), 100, lambda x: None)
    cv2.createTrackbar("ROI Y Ini%", "Calibracion", int(config.roi_y_start * 100), 100, lambda x: None)
    cv2.createTrackbar("ROI Y Fin%", "Calibracion", int(config.roi_y_end * 100), 100, lambda x: None)

    while True:
        frame = capture.grab_frame()
        if frame is None:
            cv2.waitKey(30)
            continue

        thresh = cv2.getTrackbarPos("Umbral", "Calibracion")
        rx1 = cv2.getTrackbarPos("ROI X Ini%", "Calibracion") / 100.0
        rx2 = cv2.getTrackbarPos("ROI X Fin%", "Calibracion") / 100.0
        ry1 = cv2.getTrackbarPos("ROI Y Ini%", "Calibracion") / 100.0
        ry2 = cv2.getTrackbarPos("ROI Y Fin%", "Calibracion") / 100.0

        rx2 = max(rx2, rx1 + 0.01)
        ry2 = max(ry2, ry1 + 0.01)

        fh, fw = frame.shape[:2]
        x1, x2 = int(fw * rx1), int(fw * rx2)
        y1, y2 = int(fh * ry1), int(fh * ry2)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY_INV)
        roi_bin = binary[y1:y2, x1:x2] if y2 > y1 and x2 > x1 else binary

        vis_frame = frame.copy()
        cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(vis_frame, "ROI", (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        p1 = cv2.resize(vis_frame, (400, 200))
        p2 = cv2.resize(cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR), (400, 200))
        p3 = cv2.resize(cv2.cvtColor(roi_bin, cv2.COLOR_GRAY2BGR), (400, 200)) if roi_bin.size > 0 else np.zeros((200, 400, 3), dtype=np.uint8)

        info = np.zeros((200, 400, 3), dtype=np.uint8)
        cv2.putText(info, f"Umbral: {thresh}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(info, f"ROI X: {rx1:.2f}-{rx2:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(info, f"ROI Y: {ry1:.2f}-{ry2:.2f}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(info, "S=Guardar  Q=Cancelar", (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)

        canvas = np.vstack([np.hstack([p1, p2]), np.hstack([p3, info])])
        cv2.imshow("Calibracion", canvas)
        key = cv2.waitKey(30) & 0xFF

        if key in (ord('s'), ord('S')):
            config.threshold_value = thresh
            config.roi_x_start = rx1
            config.roi_x_end = rx2
            config.roi_y_start = ry1
            config.roi_y_end = ry2
            config.save(save_path)
            print("[Calibración] Configuración guardada.")
            break
        elif key in (ord('q'), ord('Q')):
            print("[Calibración] Cancelada.")
            break

    cv2.destroyAllWindows()
    capture.close()
    return config


if __name__ == "__main__":
    run_calibration()
