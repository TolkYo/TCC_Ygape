"""Motor de roteamento sobre a topologia real BHAE persistida no SQLite."""
from __future__ import annotations

import heapq
import math
import sqlite3
import struct
import threading
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


def _lines(wkb: bytes) -> list[list[list[float]]]:
    """Lê LineString/MultiLineString WKB (formato gravado por gerar_sqlite.py)."""
    def read_at(offset: int):
        endian = "<" if wkb[offset] == 1 else ">"
        kind = struct.unpack_from(endian + "I", wkb, offset + 1)[0]
        offset += 5
        if kind == 2:
            count = struct.unpack_from(endian + "I", wkb, offset)[0]; offset += 4
            points = []
            for _ in range(count):
                x, y = struct.unpack_from(endian + "2d", wkb, offset); offset += 16
                points.append([x, y])
            return [points], offset
        if kind == 5:
            count = struct.unpack_from(endian + "I", wkb, offset)[0]; offset += 4
            output = []
            for _ in range(count):
                nested, offset = read_at(offset)
                output.extend(nested)
            return output, offset
        return [], offset
    return read_at(0)[0]


def _distance_km(lines: list[list[list[float]]]) -> float:
    total = 0.0
    for line in lines:
        for a, b in zip(line, line[1:]):
            lat1, lon1, lat2, lon2 = map(math.radians, (a[1], a[0], b[1], b[0]))
            h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
            total += 6371.0088 * 2 * math.asin(math.sqrt(h))
    return total


@dataclass(frozen=True)
class Edge:
    fid: int
    source: int
    target: int
    distance_km: float
    depth_m: float | None
    geometry: list[list[list[float]]]


class RiverGraph:
    def __init__(self, database: Path):
        self.database = database
        self.edges: dict[int, Edge] = {}
        self.adjacency: dict[int, list[tuple[int, int]]] = defaultdict(list)
        self.station_edges: dict[str, int] = {}
        self._loaded = False
        self._lock = threading.Lock()

    def load(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            con = sqlite3.connect(f"file:{self.database}?mode=ro", uri=True)
            try:
                rows = con.execute("SELECT fid,noorigem,nodestino,hig_drn_depth_m,geom_wkb FROM trechos_navegaveis").fetchall()
                for fid, source, target, depth, geometry in rows:
                    lines = _lines(geometry) if geometry else []
                    distance = _distance_km(lines)
                    if not lines or distance <= 0:
                        continue
                    edge = Edge(int(fid), int(source), int(target), distance, float(depth) if depth is not None else None, lines)
                    self.edges[edge.fid] = edge
                    # Navegação precisa considerar os dois sentidos do corredor fluvial.
                    self.adjacency[edge.source].append((edge.target, edge.fid))
                    self.adjacency[edge.target].append((edge.source, edge.fid))
                self.station_edges = {str(code): int(fid) for code, fid in con.execute("SELECT codigo_estacao,fid_trecho FROM estacoes_trechos") if int(fid) in self.edges}
            finally:
                con.close()
            self._loaded = True

    def status(self) -> dict:
        self.load()
        return {"nos": len(self.adjacency), "arestas": len(self.edges), "portos_associados": len(self.station_edges)}

    def route(self, origin_code: str, destination_code: str, draft_m: float, margin_m: float) -> list[Edge]:
        self.load()
        origin_fid = self.station_edges.get(origin_code)
        destination_fid = self.station_edges.get(destination_code)
        if origin_fid is None or destination_fid is None:
            raise ValueError("Um dos portos não possui trecho hidroviário associado.")
        if origin_fid == destination_fid:
            return [self.edges[origin_fid]]

        origin_edge, destination_edge = self.edges[origin_fid], self.edges[destination_fid]
        starts = (origin_edge.source, origin_edge.target)
        targets = {destination_edge.source, destination_edge.target}
        required_depth = draft_m + margin_m
        distance = {node: 0.0 for node in starts}
        previous: dict[int, tuple[int, int]] = {}
        queue = [(0.0, node) for node in starts]
        heapq.heapify(queue)
        found = None

        while queue:
            current_distance, node = heapq.heappop(queue)
            if current_distance != distance.get(node):
                continue
            if node in targets:
                found = node
                break
            for neighbor, fid in self.adjacency.get(node, []):
                edge = self.edges[fid]
                if edge.depth_m is not None and edge.depth_m < required_depth:
                    continue
                candidate = current_distance + edge.distance_km
                if candidate < distance.get(neighbor, math.inf):
                    distance[neighbor] = candidate
                    previous[neighbor] = (node, fid)
                    heapq.heappush(queue, (candidate, neighbor))

        if found is None:
            raise LookupError("Não há rota transitável para o calado informado entre estes portos.")
        fids: list[int] = []
        cursor = found
        while cursor not in starts:
            cursor, fid = previous[cursor]
            fids.append(fid)
        fids.reverse()
        if origin_fid not in fids:
            fids.insert(0, origin_fid)
        if destination_fid not in fids:
            fids.append(destination_fid)
        return [self.edges[fid] for fid in dict.fromkeys(fids)]
