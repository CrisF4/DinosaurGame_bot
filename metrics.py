"""
metrics.py — Recopilación y reporte de métricas de desempeño.
"""
import time, csv, os
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class FrameRecord:
    timestamp: float
    fps: float
    num_detections: int
    action: str
    detection_latency_ms: float

@dataclass
class RunMetrics:
    method_name: str
    run_number: int
    survival_time_s: float
    estimated_score: float
    avg_fps: float
    min_fps: float
    max_fps: float
    total_frames: int
    total_jumps: int
    total_ducks: int
    total_no_action: int
    avg_detection_latency_ms: float
    total_detections: int

class MetricsCollector:
    def __init__(self):
        self._runs: List[RunMetrics] = []
        self._current_method: Optional[str] = None
        self._current_run: int = 0
        self._start_time: float = 0.0
        self._frames: List[FrameRecord] = []

    def start_run(self, method_name: str, run_number: int):
        self._current_method = method_name
        self._current_run = run_number
        self._start_time = time.perf_counter()
        self._frames = []
        print(f"\n[Metrics] Run #{run_number} — método: {method_name}")

    def record_frame(self, fps, num_detections, action, detection_latency_ms):
        self._frames.append(FrameRecord(time.perf_counter(), fps, num_detections, action, detection_latency_ms))

    def end_run(self) -> RunMetrics:
        survival = time.perf_counter() - self._start_time
        if not self._frames:
            m = RunMetrics(self._current_method or "", self._current_run, survival, 0,0,0,0,0,0,0,0,0,0)
            self._runs.append(m); return m
        fps_vals = [f.fps for f in self._frames if f.fps > 0]
        lats = [f.detection_latency_ms for f in self._frames]
        m = RunMetrics(
            method_name=self._current_method or "",
            run_number=self._current_run,
            survival_time_s=survival,
            estimated_score=survival * 10.0,
            avg_fps=sum(fps_vals)/len(fps_vals) if fps_vals else 0,
            min_fps=min(fps_vals) if fps_vals else 0,
            max_fps=max(fps_vals) if fps_vals else 0,
            total_frames=len(self._frames),
            total_jumps=sum(1 for f in self._frames if f.action=="jump"),
            total_ducks=sum(1 for f in self._frames if f.action=="duck"),
            total_no_action=sum(1 for f in self._frames if f.action=="none"),
            avg_detection_latency_ms=sum(lats)/len(lats) if lats else 0,
            total_detections=sum(f.num_detections for f in self._frames),
        )
        self._runs.append(m)
        self._print_summary(m)
        return m

    def _print_summary(self, m: RunMetrics):
        print(f"\n{'='*60}")
        print(f"  RESUMEN — {m.method_name} | Run #{m.run_number}")
        print(f"{'='*60}")
        print(f"  Supervivencia:    {m.survival_time_s:.1f} s")
        print(f"  Puntaje estimado: {m.estimated_score:.0f}")
        print(f"  FPS prom/min/max: {m.avg_fps:.1f}/{m.min_fps:.1f}/{m.max_fps:.1f}")
        print(f"  Frames:           {m.total_frames}")
        print(f"  Saltos:           {m.total_jumps}")
        print(f"  Agachadas:        {m.total_ducks}")
        print(f"  Latencia prom.:   {m.avg_detection_latency_ms:.2f} ms")
        print(f"{'='*60}\n")

    def get_all_runs(self): return self._runs

    def print_comparison_table(self):
        if not self._runs: return
        methods = {}
        for r in self._runs:
            methods.setdefault(r.method_name, []).append(r)
        print(f"\n{'='*80}\n  COMPARACIÓN DE MÉTODOS\n{'='*80}")
        print(f"  {'Método':<18}{'Runs':>5}{'Surv(s)':>9}{'Score':>8}{'FPS':>7}{'Lat(ms)':>9}{'Saltos':>8}{'Agach':>7}")
        for name, runs in methods.items():
            n=len(runs)
            print(f"  {name:<18}{n:>5}{sum(r.survival_time_s for r in runs)/n:>9.1f}"
                  f"{sum(r.estimated_score for r in runs)/n:>8.0f}"
                  f"{sum(r.avg_fps for r in runs)/n:>7.1f}"
                  f"{sum(r.avg_detection_latency_ms for r in runs)/n:>9.2f}"
                  f"{sum(r.total_jumps for r in runs)/n:>8.0f}"
                  f"{sum(r.total_ducks for r in runs)/n:>7.0f}")
        print(f"{'='*80}\n")

    def export_csv(self, path: str):
        if not self._runs: return
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        fields = ["method_name","run_number","survival_time_s","estimated_score",
                   "avg_fps","min_fps","max_fps","total_frames","total_jumps",
                   "total_ducks","total_no_action","avg_detection_latency_ms","total_detections"]
        with open(path,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
            for r in self._runs:
                w.writerow({k:f"{getattr(r,k):.2f}" if isinstance(getattr(r,k),float) else getattr(r,k) for k in fields})
        print(f"[Metrics] CSV exportado: {path}")
