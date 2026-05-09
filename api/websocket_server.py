# Copyright 2026 Samuel Jackson Grim
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
api/websocket_server.py

WebSocket server — real-time stream of autonomous cycle state.

Streams StepState JSON to all connected clients on every cycle step.
Clients can also send commands to control the loop.

Message types (server → client)
--------------------------------
  {"type": "step",    "data": StepState.as_dict()}
  {"type": "field",   "data": FieldState summary}
  {"type": "dream",   "data": DreamCycleReport summary}
  {"type": "status",  "data": cycle.status()}
  {"type": "error",   "data": {"message": str}}

Commands (client → server)
--------------------------
  {"cmd": "status"}        → emits current status
  {"cmd": "dream"}         → triggers dream cycle
  {"cmd": "maintenance"}   → triggers generator maintenance
  {"cmd": "reset_field"}   → resets resonance field
  {"cmd": "pause"}         → pauses the loop
  {"cmd": "resume"}        → resumes the loop

Usage
-----
  python -m api.websocket_server

Requires: pip install websockets
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Set

import numpy as np

logger = logging.getLogger(__name__)

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False
    logger.warning("websockets not available. Install with: pip install websockets")


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types."""
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        return super().default(obj)


def _dumps(obj: dict) -> str:
    return json.dumps(obj, cls=NumpyEncoder)


class RFEWebSocketServer:
    """
    Real-time WebSocket server wrapping AutonomousCycle.

    Parameters
    ----------
    cycle : AutonomousCycle
    generator : Generator
    token_sequence : list of list of str
        Input token sequences cycled during the run loop.
    host : str
    port : int
    step_delay : float
        Seconds between autonomous cycle steps.
    broadcast_field_every : int
        Broadcast full field state every N steps.
    """

    def __init__(
        self,
        cycle,
        generator,
        token_sequence,
        host:                  str   = "0.0.0.0",
        port:                  int   = 8765,
        step_delay:            float = 0.05,
        broadcast_field_every: int   = 10,
    ):
        if not WS_AVAILABLE:
            raise ImportError("websockets required: pip install websockets")

        self.cycle                  = cycle
        self.generator              = generator
        self.token_sequence         = token_sequence
        self.host                   = host
        self.port                   = port
        self.step_delay             = step_delay
        self.broadcast_field_every  = broadcast_field_every

        self._clients:  Set[WebSocketServerProtocol] = set()
        self._paused:   bool = False
        self._step:     int  = 0
        self._running:  bool = False

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    async def start(self):
        """Start the WebSocket server and run loop."""
        self._running = True
        logger.info("RFE WebSocket server starting on ws://%s:%d", self.host, self.port)

        server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
        )

        # Run the autonomous loop concurrently
        await asyncio.gather(
            server.wait_closed(),
            self._run_loop(),
        )

    # ------------------------------------------------------------------
    # Client handler
    # ------------------------------------------------------------------

    async def _handle_client(self, ws: "WebSocketServerProtocol"):
        self._clients.add(ws)
        client_addr = ws.remote_address
        logger.info("Client connected: %s", client_addr)

        # Send current status on connect
        await self._send(ws, {"type": "status", "data": self.cycle.status()})

        try:
            async for raw_msg in ws:
                await self._handle_command(ws, raw_msg)
        except Exception:
            pass
        finally:
            self._clients.discard(ws)
            logger.info("Client disconnected: %s", client_addr)

    async def _handle_command(self, ws: "WebSocketServerProtocol", raw: str):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await self._send(ws, {"type": "error", "data": {"message": "Invalid JSON"}})
            return

        cmd = msg.get("cmd", "")

        if cmd == "status":
            await self._send(ws, {"type": "status", "data": self.cycle.status()})

        elif cmd == "dream":
            report = await asyncio.get_event_loop().run_in_executor(
                None, self._run_dream
            )
            await self._broadcast({"type": "dream", "data": report})

        elif cmd == "maintenance":
            await asyncio.get_event_loop().run_in_executor(
                None, self.generator.maintenance_step
            )
            await self._send(ws, {"type": "status", "data": self.cycle.status()})

        elif cmd == "reset_field":
            self.cycle.field.reset()
            await self._broadcast({"type": "status", "data": {"field_reset": True}})

        elif cmd == "pause":
            self._paused = True
            await self._broadcast({"type": "status", "data": {"paused": True}})

        elif cmd == "resume":
            self._paused = False
            await self._broadcast({"type": "status", "data": {"paused": False}})

        else:
            await self._send(ws, {"type": "error", "data": {"message": f"Unknown command: {cmd}"}})

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------

    async def _run_loop(self):
        """Autonomous cycle loop — runs indefinitely, broadcasts each step."""
        while self._running:
            if self._paused or not self._clients:
                await asyncio.sleep(0.1)
                continue

            tokens = self.token_sequence[self._step % len(self.token_sequence)]

            try:
                state = await asyncio.get_event_loop().run_in_executor(
                    None, self.cycle.step, tokens
                )
            except Exception as e:
                logger.error("Step error: %s", e)
                await asyncio.sleep(1.0)
                continue

            # Broadcast step state
            await self._broadcast({
                "type": "step",
                "data": state.as_dict(),
            })

            # Periodic field broadcast
            if self._step % self.broadcast_field_every == 0:
                obs = self.cycle.field.observe()
                await self._broadcast({
                    "type": "field",
                    "data": {
                        "energy":            obs.energy,
                        "rhythm":            obs.rhythm,
                        "internal_coherence": obs.internal_coherence,
                        "spectral_entropy":  obs.spectral.spectral_entropy,
                        "phase_coherence":   obs.spectral.phase_coherence,
                    },
                })

            self._step += 1
            await asyncio.sleep(self.step_delay)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_dream(self) -> dict:
        from loop.dream_cycle import DreamCycle
        dc = DreamCycle(
            dreamer       = self.cycle.dreamer,
            crystal_store = self.cycle.crystal_store,
            field         = self.cycle.field,
            attractor     = self.cycle.attractor,
            n_iterations  = 4,
        )
        report = dc.run(
            emotion   = self.cycle.emotion,
            watcher   = self.cycle.watcher,
            anchor    = self.cycle.witness.current_anchor(),
            generator = self.generator,
        )
        return {
            "iterations":  report.iterations,
            "products":    len(report.products),
            "injected":    report.injected,
            "crystallized": report.crystallized,
            "elapsed_s":   report.elapsed_s,
        }

    async def _send(self, ws: "WebSocketServerProtocol", msg: dict):
        try:
            await ws.send(_dumps(msg))
        except Exception:
            self._clients.discard(ws)

    async def _broadcast(self, msg: dict):
        if not self._clients:
            return
        payload = _dumps(msg)
        dead    = set()
        for ws in self._clients:
            try:
                await ws.send(payload)
            except Exception:
                dead.add(ws)
        self._clients -= dead


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    import sys
    sys.path.insert(0, ".")

    from agents.generator import Generator
    from loop.autonomous_cycle import AutonomousCycle
    from loop.recursion1188 import DEFAULT_TOKENS

    logging.basicConfig(level=logging.INFO)

    generator = Generator(vocab_size=8192, dim=128, depth=4, heads=4)
    cycle     = AutonomousCycle(generator=generator, dim=128, use_chorus=True)

    server = RFEWebSocketServer(
        cycle          = cycle,
        generator      = generator,
        token_sequence = DEFAULT_TOKENS,
        host           = "0.0.0.0",
        port           = 8765,
        step_delay     = 0.05,
    )

    asyncio.run(server.start())


if __name__ == "__main__":
    main()
