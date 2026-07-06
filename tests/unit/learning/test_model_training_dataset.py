from events.ledger import EventLedger
from learning.model_training_dataset import ModelTrainingDataset


def test_creates_training_example(tmp_path):
    dataset = ModelTrainingDataset(ledger=EventLedger(path=str(tmp_path / "dataset.json")))

    examples = dataset.from_events([
        {"payload": {"source": "alpha", "realized_r": 1.25}},
        {"payload": {"source": "beta", "realized_r": -1}},
    ])

    assert len(examples) == 2
    assert examples[0].label == "win"
    assert examples[1].label == "loss"
    assert dataset.ledger.all_events()[0]["payload"]["event_type"] == "TRAINING_EXAMPLE_CREATED"


def test_refresh_dataset_reuses_event_pipeline(tmp_path):
    dataset = ModelTrainingDataset(ledger=EventLedger(path=str(tmp_path / "dataset.json")))

    examples = dataset.refresh_from_events([
        {"payload": {"source": "alpha", "realized_r": 1.25}},
    ])

    assert len(examples) == 1
    assert examples[0].features == {"realized_r": 1.25}
    assert dataset.ledger.find_by_stage("learning")
