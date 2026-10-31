"""Bounded localhost TCP I/O overlap probe, not an external or hosted workload."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time

MAX_CLIENTS = 256


async def probe_local_tcp(clients: int = 256, timeout: float = 12.0) -> dict:
    if type(clients) is not int or not 1 <= clients <= MAX_CLIENTS:
        raise ValueError("INVALID_CLIENT_COUNT")
    if type(timeout) not in (float, int) or not 1 <= timeout <= 30:
        raise ValueError("INVALID_TIMEOUT")

    active = 0
    peak = 0
    arrivals = 0
    release = asyncio.Event()
    completed_ids = set()
    errors = []

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        nonlocal active, peak, arrivals
        counted = False
        try:
            request = await asyncio.wait_for(reader.readline(), timeout)
            if not request.startswith(b"PING "):
                raise ValueError("INVALID_REQUEST")
            job = int(request[5:].strip())
            if not 0 <= job < clients:
                raise ValueError("OUT_OF_RANGE")
            arrivals += 1
            active += 1
            counted = True
            peak = max(peak, active)
            if arrivals == clients:
                release.set()
            await asyncio.wait_for(release.wait(), timeout)
            writer.write(f"PONG {job}\n".encode("ascii"))
            await asyncio.wait_for(writer.drain(), timeout)
            completed_ids.add(job)
        except (OSError, ValueError, asyncio.TimeoutError) as exc:
            errors.append(type(exc).__name__)
        finally:
            if counted:
                active -= 1
            writer.close()
            await writer.wait_closed()

    began = time.perf_counter()
    server = await asyncio.start_server(handle, host="127.0.0.1", port=0, backlog=clients)
    port = server.sockets[0].getsockname()[1]

    async def client(i: int) -> bool:
        reader, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", port), timeout)
        try:
            writer.write(f"PING {i}\n".encode("ascii"))
            await asyncio.wait_for(writer.drain(), timeout)
            response = await asyncio.wait_for(reader.readline(), timeout)
            return response == f"PONG {i}\n".encode("ascii")
        finally:
            writer.close()
            await writer.wait_closed()

    try:
        received = await asyncio.wait_for(asyncio.gather(*(client(i) for i in range(clients))), timeout)
    finally:
        server.close()
        await server.wait_closed()
    elapsed_ms = round((time.perf_counter() - began) * 1000, 2)
    ok = len(completed_ids) == clients and all(received) and peak == clients and not errors
    return {"status": "PASS" if ok else "FAIL", "scope": "SINGLE_PROCESS_LOCALHOST_TCP_IO_ONLY",
            "clients": clients, "peak_server_connections_waiting": peak,
            "unique_completed": len(completed_ids), "responses_valid": sum(received),
            "errors": len(errors), "elapsed_ms": elapsed_ms,
            "os_process_count": 1, "external_network_used": False,
            "llm_calls": 0, "hosted_24h_verified": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clients", type=int, default=256)
    args = parser.parse_args()
    report = asyncio.run(probe_local_tcp(args.clients))
    print("V844_LOCAL_TCP_RESULT=" + json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
