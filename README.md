# Dino Bot - Visión por Computadora

## Descripción del Proyecto
Este proyecto consiste en un sistema de visión por computadora diseñado para jugar automáticamente el juego del dinosaurio de Chrome (`chrome://dino`). El bot captura la pantalla, procesa las imágenes en tiempo real y controla el teclado para evadir los obstáculos. Además, permite comparar el rendimiento de dos métodos de detección distintos:
- **Conteo de píxeles**
- **Detección de contornos**

---

## Instrucciones de Instalación
Para ejecutar este proyecto, se recomienda aislar las dependencias creando un entorno virtual (`venv`). Sigue estos pasos:

1. **Abre una terminal** o consola de comandos en la carpeta raíz del proyecto.
2. **Crea el entorno virtual** ejecutando:
   ```bash
   python -m venv venv
   ```
3. **Activa el entorno virtual**:
   - En *cmd* de Windows:
     ```cmd
     venv\Scripts\activate
     ```
4. **Instala las dependencias** necesarias mediante el archivo `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

---

## Instrucciones de Uso Rápido
**Requisitos previos:** 
- Abre el navegador Chrome y dirígete a `chrome://dino`. 
- Ajusta la ventana para que el juego sea visible en la pantalla.
- Asegúrate también de tener tu entorno virtual activado.

### Comandos de uso:

Calibrar el área de captura del juego primero (**Paso indispensable**):
```bash
python main.py --calibrate
```

Jugar con el método de conteo de píxeles:
```bash
python main.py --method pixel
```

Jugar con el método de detección de contornos:
```bash
python main.py --method contour
```

Comparar ambos métodos ejecutándolos 'n' veces (ej. `--runs 5`):
```bash
python main.py --method both --runs 5
```

Jugar sin ventana de visualización (recomendado para maximizar los FPS):
```bash
python main.py --no-visual
```

---

## Compatibilidad

> [!WARNING]
> El funcionamiento de este bot ha sido probado única y exclusivamente en sistemas operativos **Windows**. Su compatibilidad y correcto desempeño en distribuciones de Linux es completamente desconocido; es altamente probable que librerías como *PyAutoGUI* requieran configuraciones adicionales o presenten problemas en entornos como Wayland.
