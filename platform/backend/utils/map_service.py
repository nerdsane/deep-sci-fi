"""World semantic map service.

Generates 2D coordinates and cluster labels for world nodes on the semantic map.
Uses embeddings stored in the database to compute semantic similarity layout.
"""

import asyncio
import logging
import math
import os
import random
from typing import Any
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Cluster palette — deterministic by cluster index
CLUSTER_COLORS = [
    "#00FFE5",  # neon-cyan
    "#8B5CF6",  # neon-purple
    "#FF2D92",  # neon-pink
    "#00FF9F",  # neon-green
    "#FFB800",  # neon-amber
    "#4B9EFF",  # electric-blue
    "#FF6B35",  # electric-orange
    "#C0FF00",  # acid-yellow
]

# Single shared executor for CPU-bound ML work
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="map-ml")


def _run_tsne(X: Any) -> Any:
    """Run t-SNE synchronously (called in thread executor)."""
    from sklearn.manifold import TSNE

    n = len(X)
    perplexity = min(30, n - 1)
    reducer = TSNE(
        n_components=2,
        perplexity=perplexity,
        random_state=42,
        max_iter=500,
        metric="cosine",
    )
    return reducer.fit_transform(X)


def _run_pca(X: Any) -> Any:
    """Run PCA synchronously (called in thread executor)."""
    from sklearn.decomposition import PCA

    pca = PCA(n_components=2, random_state=42)
    return pca.fit_transform(X)


def _run_kmeans(X: Any, k: int) -> Any:
    """Run KMeans synchronously (called in thread executor)."""
    from sklearn.cluster import KMeans

    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    return km.fit_predict(X)


async def _reduce_to_2d(embeddings: list[list[float]]) -> list[tuple[float, float]]:
    """Project high-dimensional embeddings to 2D using t-SNE or PCA fallback."""
    n = len(embeddings)
    if n == 0:
        return []
    if n == 1:
        return [(0.0, 0.0)]

    try:
        import numpy as np
        from sklearn.preprocessing import normalize

        X = np.array(embeddings, dtype=np.float32)
        X = normalize(X)  # unit sphere

        loop = asyncio.get_running_loop()

        if n >= 4:
            coords = await loop.run_in_executor(_executor, _run_tsne, X)
        else:
            coords = await loop.run_in_executor(_executor, _run_pca, X)

        # Normalize to [-1, 1] range
        for i in range(2):
            col = coords[:, i]
            span = col.max() - col.min()
            if span > 0:
                coords[:, i] = 2.0 * (col - col.min()) / span - 1.0

        return [(float(row[0]), float(row[1])) for row in coords]

    except ImportError:
        logger.warning("scikit-learn not available — using random 2D layout")
        rng = random.Random(42)
        return [(rng.uniform(-1, 1), rng.uniform(-1, 1)) for _ in range(n)]


async def _cluster(embeddings: list[list[float]], n_clusters: int | None = None) -> list[int]:
    """Assign cluster labels via k-means (runs in thread executor)."""
    n = len(embeddings)
    if n == 0:
        return []

    try:
        import numpy as np
        from sklearn.preprocessing import normalize

        X = np.array(embeddings, dtype=np.float32)
        X = normalize(X)

        k = n_clusters or max(2, min(8, n // 2))
        k = min(k, n)

        loop = asyncio.get_running_loop()
        labels = await loop.run_in_executor(_executor, _run_kmeans, X, k)
        return [int(lbl) for lbl in labels]

    except ImportError:
        logger.warning("scikit-learn not available — assigning cluster 0 to all worlds")
        return [0] * n


async def _label_cluster(world_names: list[str], world_premises: list[str]) -> str:
    """Use Claude to generate a 2-3 word cluster label from member worlds."""
    if not world_names:
        return "unknown"

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return " & ".join(w.lower() for w in world_names[:2])

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=api_key)

        worlds_desc = "\n".join(
            f"- {name}: {premise[:120]}"
            for name, premise in zip(world_names[:6], world_premises[:6])
        )

        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "These sci-fi worlds share a thematic cluster. "
                        "Give a 2-3 word label for this cluster (e.g. 'identity & memory', 'labor & autonomy'). "
                        "Output ONLY the label, no punctuation or quotes.\n\n"
                        f"Worlds:\n{worlds_desc}"
                    ),
                }
            ],
        )
        label = message.content[0].text.strip().lower()
        return label[:40]  # safety cap

    except Exception as e:
        logger.warning(f"Cluster labeling failed: {e}")
        return world_names[0].lower() if world_names else "unknown"


async def build_world_map(worlds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Given a list of world dicts (with optional 'embedding' field),
    compute 2D coordinates and cluster labels.

    Returns enriched world dicts with added fields:
      x, y         — floats in [-1, 1]
      cluster      — int cluster index
      cluster_label — human-readable string
      cluster_color — hex color for this cluster
    """
    # Separate worlds with and without embeddings
    with_emb = [(i, w) for i, w in enumerate(worlds) if w.get("embedding")]
    without_emb = [(i, w) for i, w in enumerate(worlds) if not w.get("embedding")]

    result: list[dict[str, Any] | None] = [None] * len(worlds)

    if with_emb:
        indices, emb_worlds = zip(*with_emb)
        embeddings = [w["embedding"] for w in emb_worlds]

        # Run 2D reduction and clustering concurrently
        coords, cluster_ids = await asyncio.gather(
            _reduce_to_2d(embeddings),
            _cluster(embeddings),
        )

        # Group worlds by cluster
        cluster_groups: dict[int, list[int]] = {}
        for pos, cid in enumerate(cluster_ids):
            cluster_groups.setdefault(cid, []).append(pos)

        # Generate cluster labels concurrently
        label_tasks = {}
        for cid, positions in cluster_groups.items():
            member_names = [emb_worlds[p]["name"] for p in positions]
            member_premises = [emb_worlds[p]["premise"][:120] for p in positions]
            label_tasks[cid] = _label_cluster(member_names, member_premises)

        label_results = await asyncio.gather(*label_tasks.values())
        cluster_labels = dict(zip(label_tasks.keys(), label_results))

        for pos, (orig_idx, world) in enumerate(zip(indices, emb_worlds)):
            cid = cluster_ids[pos]
            result[orig_idx] = {
                **{k: v for k, v in world.items() if k != "embedding"},
                "x": coords[pos][0],
                "y": coords[pos][1],
                "cluster": cid,
                "cluster_label": cluster_labels.get(cid, "unknown"),
                "cluster_color": CLUSTER_COLORS[cid % len(CLUSTER_COLORS)],
                "has_embedding": True,
            }

    # Worlds without embeddings get scattered on the periphery
    rng = random.Random(99)
    for pos, (orig_idx, world) in enumerate(without_emb):
        angle = (pos / max(len(without_emb), 1)) * 6.2832
        r = 0.9 + rng.uniform(0, 0.1)
        result[orig_idx] = {
            **{k: v for k, v in world.items() if k != "embedding"},
            "x": round(r * math.cos(angle), 4),
            "y": round(r * math.sin(angle), 4),
            "cluster": -1,
            "cluster_label": "uncharted",
            "cluster_color": "#52525B",  # zinc-600
            "has_embedding": False,
        }

    return result  # type: ignore[return-value]
