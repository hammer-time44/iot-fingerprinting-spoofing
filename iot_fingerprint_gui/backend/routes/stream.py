"""
Streaming endpoints: WebSocket replay of 27 benchmark devices and live network packet capture.
"""
import os
import json
import time
import asyncio
from typing import Optional, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import numpy as np
from ..pipeline import (
    CALIBRATED_THRESHOLD,
    FEATURE_NAMES,
    scale_features,
    predict_window,
    compute_raw_stats,
    process_packet_timestamps
)

router = APIRouter()

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUI_DIR = os.path.dirname(BACKEND_DIR)
REPLAY_DIR = os.path.join(GUI_DIR, "assets", "replay_data")


@router.get("/stream/interfaces")
def get_interfaces():
    """List available network interfaces for live capture."""
    try:
        from scapy.all import get_if_list
        interfaces = get_if_list()
        return {"interfaces": interfaces, "status": "ok"}
    except Exception as e:
        return {
            "interfaces": [],
            "status": "error",
            "message": f"Unable to list interfaces (Npcap or administrative privileges may be required): {str(e)}"
        }


@router.websocket("/stream/replay/{device_name}")
async def replay_device_stream(
    websocket: WebSocket,
    device_name: str,
    threshold: Optional[float] = Query(CALIBRATED_THRESHOLD)
):
    """
    WebSocket streaming endpoint that replays held-out windows of any of the 27 devices.
    Streams each window live with its 128 IAT values, 13 features, probability distribution, and verdict.
    """
    await websocket.accept()
    dev_path = os.path.join(REPLAY_DIR, f"{device_name}.json")

    if not os.path.exists(dev_path):
        await websocket.send_json({
            "type": "error",
            "message": f"Device '{device_name}' not found in replay repository."
        })
        await websocket.close()
        return

    with open(dev_path, "r") as f:
        windows = json.load(f)

    if not windows:
        await websocket.send_json({
            "type": "error",
            "message": f"Device '{device_name}' has 0 recorded windows (offline during benchmark capture)."
        })
        await websocket.close()
        return

    current_threshold = threshold if threshold is not None else CALIBRATED_THRESHOLD
    threshold_holder = [current_threshold]
    stop_event = asyncio.Event()

    async def client_listener():
        try:
            while not stop_event.is_set():
                msg = await websocket.receive_text()
                data = json.loads(msg)
                if data.get("action") == "set_threshold":
                    threshold_holder[0] = float(data.get("threshold", threshold_holder[0]))
                elif data.get("action") == "stop":
                    stop_event.set()
                    break
        except Exception:
            stop_event.set()

    listener_task = asyncio.create_task(client_listener())

    # Replay loop
    total_streamed = 0
    correct_matches = 0
    flagged_unknowns = 0

    try:
        w_idx = 0
        while not stop_event.is_set():
            active_threshold = threshold_holder[0]

            # Get current window
            win_data = windows[w_idx % len(windows)]
            if "iats" in win_data and len(win_data["iats"]) >= 128:
                raw_feats = compute_raw_stats(win_data["iats"][:128])
                scaled_vec = scale_features(raw_feats)
            elif "scaled_features" in win_data:
                raw_feats = win_data.get("features", win_data["scaled_features"])
                scaled_vec = np.array([[win_data["scaled_features"][fn] for fn in FEATURE_NAMES]], dtype=np.float64)
            else:
                raw_feats = win_data.get("features", {})
                scaled_vec = scale_features(raw_feats)

            pred_res = predict_window(
                scaled_vec,
                raw_feats,
                window_index=total_streamed,
                threshold=active_threshold
            )

            true_label = win_data.get("true_label", device_name)
            total_streamed += 1

            if pred_res["verdict"] == "KNOWN" and pred_res["label"] == true_label:
                correct_matches += 1
            if pred_res["verdict"] == "UNKNOWN":
                flagged_unknowns += 1

            payload = {
                "type": "window",
                "device_name": device_name,
                "window_index": total_streamed,
                "iats": win_data.get("iats", [])[:128],
                "features": pred_res["features"],
                "verdict": pred_res["verdict"],
                "label": pred_res["label"],
                "closest_profile": pred_res["closest_profile"],
                "top_prob": pred_res["top_prob"],
                "probs": pred_res["probs"],
                "threshold": active_threshold,
                "running_stats": {
                    "total_windows": total_streamed,
                    "accuracy_pct": round(correct_matches / total_streamed * 100, 1),
                    "flagged_unknown_pct": round(flagged_unknowns / total_streamed * 100, 1),
                }
            }

            await websocket.send_json(payload)
            w_idx += 1
            await asyncio.sleep(0.5)  # responsive 500ms pacing

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        stop_event.set()
        listener_task.cancel()


@router.websocket("/stream/live")
async def live_capture_stream(
    websocket: WebSocket,
    interface: Optional[str] = Query(None),
    filter_mac: Optional[str] = Query(None),
    filter_ip: Optional[str] = Query(None),
    threshold: Optional[float] = Query(CALIBRATED_THRESHOLD)
):
    """
    Live packet capture WebSocket stream using Scapy.
    Captures packet arrival timestamps on the selected interface, filtered by MAC or IP.
    Every 128 packets, extracts 13 features, executes inference, and pushes results live.
    """
    await websocket.accept()

    try:
        from scapy.all import sniff
    except ImportError:
        await websocket.send_json({
            "type": "error",
            "message": "Scapy is not installed. Live packet capture is disabled."
        })
        await websocket.close()
        return

    bpf_filter = []
    if filter_ip:
        bpf_filter.append(f"host {filter_ip}")
    if filter_mac:
        bpf_filter.append(f"ether host {filter_mac}")

    filter_str = " and ".join(bpf_filter) if bpf_filter else ""
    current_threshold = threshold if threshold is not None else CALIBRATED_THRESHOLD

    packet_timestamps: List[float] = []
    total_windows = 0

    # Notification of capture started
    await websocket.send_json({
        "type": "status",
        "message": f"Listening for packets on interface '{interface or 'default'}' (Filter: '{filter_str or 'none'}')...",
        "threshold": current_threshold
    })

    stop_sniffing = False

    def packet_handler(pkt):
        nonlocal packet_timestamps
        packet_timestamps.append(float(pkt.time))

    async def sniffer_loop():
        nonlocal stop_sniffing
        while not stop_sniffing:
            try:
                # Sniff in small batches non-blockingly
                await asyncio.to_thread(
                    sniff,
                    iface=interface,
                    filter=filter_str if filter_str else None,
                    prn=packet_handler,
                    count=10,
                    timeout=1.0,
                    store=False
                )
            except PermissionError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Permission Denied: Administrative / root privileges or Npcap are required for live promiscuous packet capture."
                })
                stop_sniffing = True
                break
            except Exception as capture_err:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Capture error: {str(capture_err)}"
                })
                stop_sniffing = True
                break

    sniffer_task = asyncio.create_task(sniffer_loop())

    try:
        while not stop_sniffing:
            # Check for client messages
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                data = json.loads(msg)
                if data.get("action") == "stop":
                    stop_sniffing = True
                    break
                elif data.get("action") == "set_threshold":
                    current_threshold = float(data.get("threshold", current_threshold))
            except asyncio.TimeoutError:
                pass

            # Check if 129 timestamps collected (128 IATs)
            if len(packet_timestamps) >= 129:
                win_ts = packet_timestamps[:129]
                packet_timestamps = packet_timestamps[128:]  # slide window

                iats = [float(win_ts[i] - win_ts[i - 1]) for i in range(1, len(win_ts))]
                log1p_iats = np.log1p(np.maximum(iats, 0.0))
                feats = compute_raw_stats(log1p_iats)
                scaled = scale_features(feats)
                total_windows += 1

                pred_res = predict_window(
                    scaled,
                    feats,
                    window_index=total_windows,
                    threshold=current_threshold
                )

                payload = {
                    "type": "window",
                    "window_index": total_windows,
                    "iats": [round(float(v), 6) for v in iats],
                    "features": pred_res["features"],
                    "verdict": pred_res["verdict"],
                    "label": pred_res["label"],
                    "closest_profile": pred_res["closest_profile"],
                    "top_prob": pred_res["top_prob"],
                    "probs": pred_res["probs"],
                    "threshold": current_threshold,
                    "total_windows": total_windows
                }
                await websocket.send_json(payload)

            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        pass
    finally:
        stop_sniffing = True
        sniffer_task.cancel()
