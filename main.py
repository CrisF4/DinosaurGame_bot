"""
main.py — flujo principal del Dino Bot.

Sistema de visión por computadora que juega automáticamente el juego del
dinosaurio de Chrome. Compara dos métodos de detección: conteo de píxeles
y detección de contornos.

Uso:
  python main.py --calibrate              # Calibrar primero
  python main.py --method pixel           # Jugar con método de píxeles
  python main.py --method contour         # Jugar con método de contornos
  python main.py --method both --runs n   # Comparar ambos métodos (n runs c/u)
  python main.py --no-visual              # Sin visualización (máx FPS)

Requisitos previos:
  1. Abrir Chrome en chrome://dino
  2. Tener las dependencias instaladas (pip install -r requirements.txt)
"""

import argparse
import time
import sys
import os
import cv2
import numpy as np

from config import GameConfig, DEFAULT_CONFIG_PATH
from calibration import run_calibration
from capture import ScreenCapture
from preprocess import Preprocessor
from detector_pixels import PixelDetector
from detector_contours import ContourDetector
from controller import GameController
from metrics import MetricsCollector
from visualizer import Visualizer


def decide_action(detections, config, elapsed_time):
    """Regla de decisión: determina qué acción tomar.

    Implementa adaptación dinámica a la velocidad del juego:
    a mayor tiempo transcurrido, el juego es más rápido, así que
    se aumenta el umbral de distancia para reaccionar antes.

    Args:
        detections: lista de Detection (ordenada por distancia).
        config: GameConfig con los umbrales.
        elapsed_time: segundos desde inicio del juego.

    Returns:
        "jump", "duck", o "none".
    """
    if not detections:
        return "none"

    # Factor de velocidad dinámico: crece con el tiempo
    speed_factor = 1.0 + (elapsed_time * config.speed_increase_rate)
    speed_factor = min(speed_factor, config.max_speed_factor)

    # Umbrales dinámicos (a mayor velocidad, reaccionar antes = umbral mayor)
    jump_thresh = min(0.95, config.base_jump_distance * speed_factor)
    duck_thresh = min(0.95, config.base_duck_distance * speed_factor)

    # Evaluar el obstáculo más cercano
    det = detections[0]

    if det.obstacle_type == "cactus" and det.distance_x < jump_thresh:
        return "jump"
    elif det.obstacle_type == "bird_low" and det.distance_x < jump_thresh:
        # Ave a nivel de suelo → saltar
        return "jump"
    elif det.obstacle_type == "cactus_or_bird_low" and det.distance_x < jump_thresh:
        # Píxeles: objeto en el suelo → saltar
        return "jump"
    elif det.obstacle_type == "bird_mid" and det.distance_x < duck_thresh:
        return "duck"
    elif det.obstacle_type == "bird_high":
        # Ave alta → el dino pasa por debajo, no hacer nada
        return "none"

    return "none"

def run_game(config, method_name, detector, capture, preprocessor,
             controller, metrics, visualizer, run_number):
    """Ejecuta una partida completa.

    Args:
        config: GameConfig.
        method_name: "pixel" o "contour".
        detector: instancia del detector (PixelDetector o ContourDetector).
        capture: ScreenCapture.
        preprocessor: Preprocessor.
        controller: GameController.
        metrics: MetricsCollector.
        visualizer: Visualizer o None.
        run_number: número de la partida.
    """
    metrics.start_run(method_name, run_number)

    # Iniciar el juego
    print(f"\n[Main] Iniciando partida #{run_number} con método '{method_name}'...")
    print("[Main] Presiona ESPACIO en la ventana del juego o espera 3s...")
    time.sleep(1.0)
    controller.start_game()
    time.sleep(0.5)  # Esperar a que el juego arranque

    game_start = time.perf_counter()
    prev_gray = None
    game_over_counter = 0

    print("[Main] ¡Jugando! Presiona 'Q' en la ventana de visualización para detener.")

    try:
        while True:
            t_frame_start = time.perf_counter()

            # 1. Capturar frame
            frame = capture.grab_frame()
            if frame is None:
                continue
            fps = capture.get_fps()

            # 2. Preprocesar
            gray, binary_full, binary_roi = preprocessor.process(frame)

            # 3. Detectar obstáculos
            t_detect = time.perf_counter()
            detections = detector.detect(binary_roi)
            detection_latency = (time.perf_counter() - t_detect) * 1000.0

            # 4. Decidir acción
            elapsed = time.perf_counter() - game_start
            action = decide_action(detections, config, elapsed)

            # 5. Ejecutar acción
            if action == "jump":
                controller.jump()
            elif action == "duck":
                controller.duck()
            elif action == "none":
                controller.idle()

            # 6. Registrar métricas
            metrics.record_frame(fps, len(detections), action, detection_latency)

            # 7. Visualizar
            if visualizer is not None:
                roi_coords = preprocessor.get_roi_coords(frame.shape)
                visualizer.render(
                    frame, gray, binary_roi, detections, fps, action,
                    method_name, elapsed, preprocessor.is_night_mode, roi_coords
                )

            # Control de ventana
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q'):
                print("[Main] Detenido por el usuario.")
                break

    except KeyboardInterrupt:
        print("\n[Main] Interrumpido por el usuario (Ctrl+C).")

    return metrics.end_run()

def main():
    parser = argparse.ArgumentParser(
        description="Dino Bot — Juega el dinosaurio de Chrome con visión por computadora.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""

Ejemplos:
  python main.py --calibrate
  python main.py --method pixel
  python main.py --method both --runs 3
  python main.py --no-visual --method contour
        """
    )
    parser.add_argument(
        "--method", choices=["pixel", "contour", "both"], default="both",
        help="Método de detección (default: both)."
    )
    parser.add_argument(
        "--calibrate", action="store_true",
        help="Ejecutar calibración antes de jugar."
    )
    parser.add_argument(
        "--no-visual", action="store_true",
        help="Desactivar visualización (máximo FPS)."
    )
    parser.add_argument(
        "--runs", type=int, default=1,
        help="Número de partidas por método (default: 1)."
    )
    parser.add_argument(
        "--config", type=str, default=DEFAULT_CONFIG_PATH,
        help="Ruta al archivo de configuración YAML."
    )
    parser.add_argument(
        "--export-csv", type=str, default="results.csv",
        help="Ruta del archivo CSV de resultados (default: results.csv)."
    )

    args = parser.parse_args()

    # Cargar o crear configuración
    if args.calibrate or not os.path.exists(args.config):
        print("[Main] Iniciando calibración...")
        config = run_calibration(save_path=args.config)
    else:
        config = GameConfig.load(args.config)
        print(f"[Main] Configuración cargada de: {args.config}")

    # Configurar visualización
    config.show_visualization = not args.no_visual

    # Inicializar módulos
    capture = ScreenCapture(config.game_region)
    preprocessor = Preprocessor(config)
    pixel_detector = PixelDetector(config)
    contour_detector = ContourDetector(config)
    controller = GameController(
        cooldown_ms=config.action_cooldown_ms,
        jump_hold_ms=config.jump_hold_ms,
        duck_hold_ms=config.duck_hold_ms,
    )
    metrics_collector = MetricsCollector()
    visualizer = Visualizer() if config.show_visualization else None

    # Inicializar controlador de teclado
    if not controller.initialize():
        print("[Main] ERROR: No se pudo inicializar el controlador de teclado.")
        sys.exit(1)

    # Determinar métodos a ejecutar
    methods = []
    if args.method in ("pixel", "both"):
        methods.append(("pixel", pixel_detector))
    if args.method in ("contour", "both"):
        methods.append(("contour", contour_detector))

    print(f"\n[Main] Métodos a ejecutar: {[m[0] for m in methods]}")
    print(f"[Main] Partidas por método: {args.runs}")
    print(f"[Main] Visualización: {'SI' if config.show_visualization else 'NO'}")
    print("\n" + "="*50)
    print("  INSTRUCCIONES:")
    print("  1. Abre Chrome en chrome://dino")
    print("  2. Posiciona la ventana del juego según la calibración")
    print("  3. El bot iniciará el juego automáticamente")
    print("="*50)

    input("\nPresiona ENTER cuando estés listo...")

    try:
        for method_name, detector in methods:
            for run_num in range(1, args.runs + 1):
                print(f"\n{'─'*50}")
                print(f"  {method_name.upper()} — Run {run_num}/{args.runs}")
                print(f"{'─'*50}")

                if run_num > 1 or methods.index((method_name, detector)) > 0:
                    print("\n[Main] Esperando 3 segundos antes de la siguiente partida...")
                    time.sleep(3.0)

                run_game(
                    config, method_name, detector, capture, preprocessor,
                    controller, metrics_collector, visualizer, run_num
                )

    except KeyboardInterrupt:
        print("\n[Main] Programa interrumpido.")

    finally:
        # Mostrar resultados finales
        metrics_collector.print_comparison_table()

        # Exportar CSV
        csv_path = os.path.join(os.path.dirname(__file__), args.export_csv)
        metrics_collector.export_csv(csv_path)

        # Limpieza
        controller.close()
        capture.close()
        if visualizer:
            visualizer.close()

    print("\n[Main] ¡Programa finalizado!")


if __name__ == "__main__":
    main()
