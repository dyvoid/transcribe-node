"""Model catalog and hardware-based recommendation.

Lives server-side so every caller (UI, CLI, script) gets the same answer.
"""

from dataclasses import dataclass

# Headroom to leave free above a model's footprint before recommending it.
HEADROOM_GB = 1.0


@dataclass(frozen=True)
class ModelSpec:
    name: str
    vram_gb: float
    quality: str
    use_case: str


# Ordered highest quality first. Recommendation walks this in order.
MODEL_CATALOG: list[ModelSpec] = [
    ModelSpec("large-v3", 6.0, "Best", "High quality batch transcription"),
    ModelSpec("distil-large-v3", 4.0, "Near-large", "Faster, smaller footprint"),
    ModelSpec("large-v3-turbo", 3.0, "Good", "Speed/quality balance"),
    ModelSpec("medium", 3.0, "Good", "Constrained VRAM"),
    ModelSpec("small", 2.0, "OK", "Fast previews"),
]

MODELS_BY_NAME: dict[str, ModelSpec] = {spec.name: spec for spec in MODEL_CATALOG}


def recommend_model(available_memory_gb: float) -> str:
    """Pick the highest-quality model that fits with headroom to spare.

    Advisory only. Falls back to the smallest model when nothing fits comfortably,
    since a slow transcription beats none.
    """
    for spec in MODEL_CATALOG:
        if available_memory_gb >= spec.vram_gb + HEADROOM_GB:
            return spec.name
    return MODEL_CATALOG[-1].name
