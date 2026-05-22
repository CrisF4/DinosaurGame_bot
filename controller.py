"""
controller.py — Control de teclado para el juego del dinosaurio usando PyAutoGUI.
Utiliza la librería PyAutoGUI para inyectar eventos de teclado.

Virtual Key Strings utilizados:
  'space' — iniciar juego
  'up'    — saltar (flecha arriba)
  'down'  — agacharse (flecha abajo)
"""

import time
import threading
import pyautogui

# Desactivar la pausa automática de pyautogui para no ralentizar el juego
pyautogui.PAUSE = 0
# Desactivar el failsafe (mover el mouse a la esquina superior izquierda detiene el script)
# ya que en este caso no controlamos el mouse y podría interferir si el usuario lo mueve.
pyautogui.FAILSAFE = False

class GameController:
    """Controla el juego del dinosaurio simulando pulsaciones de teclado usando pyautogui."""

    def __init__(self, cooldown_ms: float = 250.0,
                 jump_hold_ms: float = 150.0,
                 duck_hold_ms: float = 400.0):
        """
        Args:
            cooldown_ms: tiempo mínimo entre acciones consecutivas (ms).
            jump_hold_ms: duración de la pulsación de salto (ms).
            duck_hold_ms: duración de la pulsación de agacharse (ms).
        """
        self.cooldown = cooldown_ms / 1000.0
        self.jump_hold = jump_hold_ms / 1000.0
        self.duck_hold = duck_hold_ms / 1000.0

        self.last_action_time = 0.0
        self._is_ducking = False
        self._initialized = False

    def initialize(self) -> bool:
        """Inicializa el controlador de teclado.

        Returns:
            True si la inicialización fue exitosa.
        """
        try:
            self._initialized = True
            print("[Controller] Controlador de teclado (PyAutoGUI) inicializado.")
            return True
        except Exception as e:
            print(f"[Controller] ERROR al inicializar PyAutoGUI: {e}")
            return False

    def _can_act(self) -> bool:
        """Verifica si ha pasado suficiente tiempo desde la última acción."""
        return (time.perf_counter() - self.last_action_time) >= self.cooldown

    def jump(self) -> bool:
        """Ejecuta un salto (presiona y suelta flecha arriba).

        Returns:
            True si la acción se ejecutó, False si estaba en cooldown.
        """
        if not self._can_act():
            return False

        # Si estamos agachados, primero soltar
        if self._is_ducking:
            self.release_duck()

        self.last_action_time = time.perf_counter()
        pyautogui.keyDown('up')

        # Soltar después de jump_hold_ms en un hilo separado para no bloquear
        def _release():
            time.sleep(self.jump_hold)
            pyautogui.keyUp('up')

        threading.Thread(target=_release, daemon=True).start()
        return True

    def duck(self) -> bool:
        """Se agacha (mantiene presionada flecha abajo).

        Returns:
            True si la acción se ejecutó.
        """
        if not self._can_act():
            return False

        self.last_action_time = time.perf_counter()
        self._is_ducking = True
        pyautogui.keyDown('down')

        # Auto-release después de duck_hold_ms
        def _auto_release():
            time.sleep(self.duck_hold)
            if self._is_ducking:
                self.release_duck()

        threading.Thread(target=_auto_release, daemon=True).start()
        return True

    def idle(self) -> None:
        """El dino no hace nada."""
        pass

    def release_duck(self) -> None:
        """Suelta la tecla de agacharse."""
        self._is_ducking = False
        pyautogui.keyUp('down')

    def start_game(self) -> None:
        """Inicia el juego presionando espacio."""
        if not self._initialized:
            return
        pyautogui.keyDown('space')
        time.sleep(0.05)
        pyautogui.keyUp('space')
        self.last_action_time = time.perf_counter()

    def close(self) -> None:
        """Libera recursos del controlador."""
        if self._is_ducking:
            self.release_duck()
        self._initialized = False
        print("[Controller] Controlador de teclado cerrado.")
