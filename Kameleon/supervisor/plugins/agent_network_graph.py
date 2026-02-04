#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
from pathlib import Path
from collections import defaultdict
from loguru import logger
import networkx as nx

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    logger.warning("AGENT GRAPH: matplotlib ni nameščen, vizualni grafi onemogočeni")

AGENT_LOG = Path("logs/system.log")
GRAPH_JSON = Path("runtime/agent_network_graph.json")
GRAPH_PNG = Path("runtime/agent_network_graph.png")

REFRESH_INTERVAL = 120  # sekund

def extract_interactions_from_logs():
    if not AGENT_LOG.exists():
        logger.warning("AGENT GRAPH: log datoteka ne obstaja")
        return []

    interactions = []
    try:
        with AGENT_LOG.open("r", encoding="utf-8") as f:
            for line in f:
                if "AGENT_INTERACT:" in line:
                    try:
                        parts = line.strip().split("AGENT_INTERACT:")[1].strip()
                        a, b = parts.split("->")
                        interactions.append((a.strip(), b.strip()))
                    except Exception:
                        continue
    except Exception as e:
        logger.error(f"AGENT GRAPH: napaka pri branju loga: {e}")

    return interactions

def build_agent_graph(interactions):
    graph = defaultdict(lambda: defaultdict(int))
    for src, dst in interactions:
        graph[src][dst] += 1
    return graph

def save_graph_json(graph):
    try:
        with GRAPH_JSON.open("w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2)
        logger.info("AGENT GRAPH: JSON graf shranjen")
    except Exception as e:
        logger.error(f"AGENT GRAPH: napaka pri shranjevanju JSON grafa: {e}")

def render_graph_image(graph):
    if not HAS_MATPLOTLIB:
        return
    try:
        G = nx.DiGraph()
        for src, targets in graph.items():
            for dst, weight in targets.items():
                G.add_edge(src, dst, weight=weight)

        plt.figure(figsize=(10, 7))
        pos = nx.spring_layout(G)
        nx.draw(G, pos, with_labels=True, node_color='skyblue', edge_color='gray', node_size=2000, font_size=10)
        edge_labels = {(u, v): d['weight'] for u, v, d in G.edges(data=True)}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
        plt.tight_layout()
        plt.savefig(GRAPH_PNG)
        plt.close()
        logger.info("AGENT GRAPH: grafična slika grafa ustvarjena")
    except Exception as e:
        logger.error(f"AGENT GRAPH: napaka pri upodabljanju grafa: {e}")

def run(stop_event):
    logger.info("🕸️ AGENT GRAPH: modul aktiviran")
    while not stop_event.is_set():
        interactions = extract_interactions_from_logs()
        graph = build_agent_graph(interactions)
        save_graph_json(graph)
        render_graph_image(graph)
        time.sleep(REFRESH_INTERVAL)
    logger.info("🕸️ AGENT GRAPH: modul zaustavljen")
