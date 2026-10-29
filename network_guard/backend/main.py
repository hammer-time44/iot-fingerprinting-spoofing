"""
FastAPI Application for Network Defense Lab.
Exposes REST APIs, WebSocket live simulation streaming, and benchmark execution.
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from .config import (
    BACKEND_PORT,
    DEFAULT_TAU,
    LOGS_DIR,
    RESULTS_DIR,
    REGISTERED_HOSTS,
    GATEWAY_INFO,
    DEFAULT_MODEL_PATH,
    DEFAULT_SCALER_PATH
)
from .simulation import SimulationEngine
from .benchmark import run_benchmark
from .model_loader import ModelManager

# Configure Structured Logging
log_file = LOGS_DIR / "network_guard_backend.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("network_guard")

app = FastAPI(
    title="Network Defense Lab - Gateway Timing Monitor API",
    description="Real-time passive timing fingerprinting & anti-spoofing defense simulation.",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singleton Simulation Engine
sim_engine = SimulationEngine()
active_websockets: List[WebSocket] = []
simulation_task: Optional[asyncio.Task] = None


# --- Pydantic Schemas ---
class ScenarioStartRequest(BaseModel):
    scenario: str = Field(default="BASELINE", description="Scenario name")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Scenario parameters")
    speed: Optional[float] = Field(default=1.0, ge=0.25, le=8.0, description="Simulation speed")

class SpeedRequest(BaseModel):
    speed: float = Field(ge=0.25, le=8.0)

class TauRequest(BaseModel):
    tau: float = Field(ge=0.1, le=1.0)

class BenchmarkRunRequest(BaseModel):
    n_trials: int = Field(default=20, ge=5, le=100)
    max_ticks_per_trial: int = Field(default=15, ge=5, le=30)
    tau: Optional[float] = Field(default=None)


# --- Background Simulation Loop for WebSocket Streaming ---
async def simulation_loop():
    logger.info("Simulation background loop started.")
    try:
        while sim_engine.is_running:
            tick_data = sim_engine.tick()

            # Broadcast to all connected WebSockets
            if active_websockets:
                msg = json.dumps(tick_data)
                dead_sockets = []
                for ws in active_websockets:
                    try:
                        await ws.send_text(msg)
                    except Exception:
                        dead_sockets.append(ws)
                for ws in dead_sockets:
                    if ws in active_websockets:
                        active_websockets.remove(ws)

            # Sleep according to simulation speed
            interval = max(0.1, 1.0 / sim_engine.speed)
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("Simulation background loop cancelled.")
    except Exception as e:
        logger.error(f"Error in simulation loop: {e}", exc_info=True)


# --- REST Endpoints ---

@app.get("/health")
def get_health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "network_guard_defense_lab",
        "tick_count": sim_engine.tick_count,
        "is_running": sim_engine.is_running,
        "active_scenario": sim_engine.active_scenario,
        "active_ws_clients": len(active_websockets)
    }

@app.get("/model/info")
def get_model_info():
    """Returns model metadata, classes, features, and active thresholds."""
    mm = sim_engine.model_manager
    return {
        "model_type": "RandomForestClassifier",
        "n_estimators": getattr(mm.model, "n_estimators", 100),
        "classes": mm.classes,
        "feature_count": len(mm.feature_names),
        "feature_names": mm.feature_names,
        "tau": sim_engine.tau,
        "model_artifact": str(DEFAULT_MODEL_PATH),
        "scaler_artifact": str(DEFAULT_SCALER_PATH),
        "unknown_devices_available": mm.unknown_device_names
    }

@app.get("/topology")
def get_topology():
    """Returns network topology: Gateway, Home LAN, and Attacker Subnet."""
    return {
        "gateway": GATEWAY_INFO,
        "home_lan": {
            "subnet": GATEWAY_INFO["lan_subnet"],
            "hosts": list(REGISTERED_HOSTS.values())
        },
        "attacker_net": {
            "subnet": GATEWAY_INFO["attacker_subnet"],
            "has_active_attacker": any(h.get("is_attacker") for h in sim_engine.hosts.values()),
            "attacker_hosts": [h for h in sim_engine.hosts.values() if h.get("is_attacker")]
        }
    }

@app.get("/registry")
def get_registry():
    """Returns official registered host mappings."""
    return REGISTERED_HOSTS

@app.get("/hosts")
def get_hosts():
    """Returns current state of all active hosts in the lab."""
    return {
        "tick": sim_engine.tick_count,
        "scenario": sim_engine.active_scenario,
        "is_running": sim_engine.is_running,
        "speed": sim_engine.speed,
        "tau": sim_engine.tau,
        "hosts": sim_engine.hosts
    }

@app.post("/sim/start")
async def start_simulation(req: ScenarioStartRequest):
    """Start or change a simulation scenario."""
    global simulation_task
    sim_engine.configure_scenario(req.scenario, req.params)
    sim_engine.speed = req.speed
    sim_engine.is_running = True

    if simulation_task is None or simulation_task.done():
        simulation_task = asyncio.create_task(simulation_loop())

    logger.info(f"Started scenario {req.scenario} with speed {req.speed}x")
    return {
        "status": "started",
        "scenario": sim_engine.active_scenario,
        "speed": sim_engine.speed,
        "hosts": sim_engine.hosts
    }

@app.post("/sim/stop")
async def stop_simulation():
    """Pause/stop current simulation run."""
    global simulation_task
    sim_engine.is_running = False
    if simulation_task and not simulation_task.done():
        simulation_task.cancel()
    logger.info("Simulation paused.")
    return {"status": "stopped", "tick": sim_engine.tick_count}

@app.post("/sim/reset")
async def reset_simulation():
    """Reset simulation to clean initial state."""
    global simulation_task
    sim_engine.is_running = False
    if simulation_task and not simulation_task.done():
        simulation_task.cancel()
    sim_engine.reset()
    logger.info("Simulation reset.")
    return {"status": "reset", "hosts": sim_engine.hosts}

@app.post("/sim/speed")
def set_speed(req: SpeedRequest):
    """Update simulation speed factor."""
    sim_engine.speed = req.speed
    return {"status": "ok", "speed": sim_engine.speed}

@app.post("/config/tau")
def update_tau(req: TauRequest):
    """Update anomaly decision threshold tau."""
    sim_engine.set_tau(req.tau)
    logger.info(f"Updated tau threshold to {req.tau:.2f}")
    return {"status": "ok", "tau": sim_engine.tau}

@app.get("/events")
def get_events(
    limit: int = Query(default=100, ge=1, le=1000),
    host_id: Optional[str] = None,
    format: str = Query(default="json", regex="^(json|csv)$")
):
    """Returns event history, with optional host filter and CSV export."""
    filtered = sim_engine.events
    if host_id:
        filtered = [e for e in filtered if e.get("host_id") == host_id]

    items = filtered[-limit:]

    if format == "csv":
        import pandas as pd
        if not items:
            return Response(content="No events recorded yet\n", media_type="text/csv")
        df = pd.DataFrame(items)
        csv_data = df.to_csv(index=False)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=defense_events.csv"}
        )

    return {"count": len(items), "events": items}

@app.post("/benchmark/run")
def trigger_benchmark(req: BenchmarkRunRequest):
    """Trigger a fresh batch benchmark run."""
    tau = req.tau if req.tau is not None else sim_engine.tau
    logger.info(f"Starting batch benchmark with {req.n_trials} trials, tau={tau}...")
    results = run_benchmark(n_trials=req.n_trials, max_ticks_per_trial=req.max_ticks_per_trial, tau=tau)
    return results

@app.get("/benchmark/results")
def get_benchmark_results():
    """Get latest saved benchmark results."""
    latest_file = RESULTS_DIR / "benchmark_latest.json"
    if not latest_file.exists():
        # Run one quick benchmark if none exists
        logger.info("No prior benchmark found; running initial benchmark...")
        return run_benchmark(n_trials=20, tau=sim_engine.tau)

    with open(latest_file, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/report")
def get_full_report():
    """Returns full status report of the network defense lab."""
    return {
        "gateway": GATEWAY_INFO,
        "tau": sim_engine.tau,
        "active_scenario": sim_engine.active_scenario,
        "total_ticks": sim_engine.tick_count,
        "hosts": sim_engine.hosts,
        "scenario_metrics": sim_engine.scenario_metrics,
        "total_events": len(sim_engine.events),
        "recent_events": sim_engine.events[-20:]
    }

# --- WebSocket Endpoint ---
@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """Live WebSocket stream broadcasting simulation ticks, states, and rules."""
    await websocket.accept()
    active_websockets.append(websocket)
    logger.info(f"WebSocket client connected. Total active: {len(active_websockets)}")
    try:
        # Send initial snapshot immediately upon connect
        initial_payload = {
            "type": "SNAPSHOT",
            "tick": sim_engine.tick_count,
            "scenario": sim_engine.active_scenario,
            "hosts": sim_engine.hosts,
            "events": sim_engine.events[-10:]
        }
        await websocket.send_text(json.dumps(initial_payload))

        while True:
            # Keep connection alive; accept commands if sent
            data = await websocket.receive_text()
            try:
                cmd = json.loads(data)
                if cmd.get("action") == "TICK":
                    tick_res = sim_engine.tick()
                    await websocket.send_text(json.dumps(tick_res))
            except Exception:
                pass
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    finally:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

