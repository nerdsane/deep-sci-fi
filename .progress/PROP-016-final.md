# PROP-016 Final Fixes

Read platform/backend/utils/map_service.py and platform/components/world/WorldMapCanvas.tsx.

## Fix 1: Mobile legend bottom padding

In WorldMapCanvas.tsx, find the legend container on mobile and add pb-20 (or padding-bottom: 80px) so it clears the fixed bottom navigation bar. The last legend item ("thoughtcrime auditing") is currently flush against the bottom nav.

## Fix 2: Amplify embedding distances for better map layout

The problem: all 13 world premises are sci-fi, so their cosine similarities cluster between 0.36-0.75 (mean 0.52, std 0.09). TSNE sees a cloud of nearly-equidistant points and spreads them uniformly, making every world look equidistant from every other world.

In map_service.py, in the _reduce_to_2d function, BEFORE running t-SNE:
1. Compute the pairwise cosine distance matrix
2. Apply a contrast-stretching transform: rescale distances so that the minimum distance becomes 0 and maximum becomes 1, then raise to a power (e.g. 0.5) to amplify small differences
3. Pass this as a precomputed distance matrix to TSNE (use metric="precomputed" instead of metric="cosine")

This will make similar worlds (like Lent and Lived at 0.75 similarity) cluster tightly together, while dissimilar worlds (like Harvest Rights and Thoughtcrime Auditing at 0.36) are pushed far apart. The map should show clear clusters instead of uniform spacing.

Here is the approach for _reduce_to_2d:

```python
from sklearn.metrics.pairwise import cosine_distances

X = np.array(embeddings, dtype=np.float32)
X = normalize(X)

# Compute cosine distance matrix
dist = cosine_distances(X)

# Contrast stretch: rescale to [0,1] then apply power transform
d_min, d_max = dist[dist > 0].min(), dist.max()
if d_max > d_min:
    dist_stretched = (dist - d_min) / (d_max - d_min)
    dist_stretched = np.power(dist_stretched, 0.5)  # amplify small differences
    np.fill_diagonal(dist_stretched, 0.0)
else:
    dist_stretched = dist

# Use precomputed distances
reducer = TSNE(n_components=2, perplexity=perplexity, random_state=42, max_iter=500, metric="precomputed")
coords = reducer.fit_transform(dist_stretched)
```

The _run_tsne function needs to accept the metric parameter or be restructured to handle precomputed distances.

## Verification
After fixing, commit and push. Do NOT merge.
No need for screenshots on this round — the padding is trivial and the distance fix is backend-only (needs embeddings to test properly, which only prod has).
