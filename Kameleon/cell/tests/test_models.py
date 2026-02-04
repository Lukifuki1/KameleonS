from system.orchestrator_shared import MODEL_REGISTRY, register_all_models


def test_model_registration():
    register_all_models()
    assert len(MODEL_REGISTRY) > 0, "Noben model ni bil naložen"
