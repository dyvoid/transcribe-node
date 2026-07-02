from catalog import MODEL_CATALOG, recommend_model


def test_recommends_largest_that_fits_with_headroom():
    # 8 GB comfortably fits large-v3 (6 GB + 1 GB headroom).
    assert recommend_model(8.0) == "large-v3"


def test_recommends_smaller_model_on_tight_memory():
    # 5 GB cannot fit large-v3 (needs 7), but fits distil-large-v3 (4 + 1).
    assert recommend_model(5.0) == "distil-large-v3"


def test_falls_back_to_smallest_when_nothing_fits():
    assert recommend_model(0.5) == MODEL_CATALOG[-1].name


def test_catalog_is_ordered_highest_quality_first():
    vrams = [spec.vram_gb for spec in MODEL_CATALOG]
    assert vrams == sorted(vrams, reverse=True)
