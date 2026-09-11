from pathlib import Path

from database.cnn_dataset import assign_split, maybe_export_cnn_sample
from database.store import Store
from PIL import Image


def test_assign_split_is_stable():
    a = assign_split("aaaaaaaa")
    b = assign_split("aaaaaaaa")
    assert a == b
    assert a in {"train", "val", "test"}


def test_store_mining_run_and_cnn_sample(tmp_path, monkeypatch):
    monkeypatch.setenv("TNB_MYSQL", "0")
    db = tmp_path / "tnb.db"
    store = Store(db)
    store.insert_mining_run(
        {
            "cycle_id": "CYC-TEST",
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:01:00+00:00",
            "articles_new": 2,
            "images_new": 1,
            "errors": 0,
        }
    )
    last = store.last_mining_run()
    assert last and last["articles_new"] == 2
    assert store.count_cnn_samples() == 0
    store.close()


def test_cnn_export_only_high_confidence(tmp_path, monkeypatch):
    monkeypatch.setenv("TNB_MYSQL", "0")
    monkeypatch.setenv("TNB_CNN_DATASET_MIN_CONF", "0.5")
    dataset = tmp_path / "dataset"
    monkeypatch.setattr("database.cnn_dataset.CNN_DATASET_DIR", dataset)
    img_path = tmp_path / "rss_photo.jpg"
    Image.new("RGB", (32, 32), (20, 80, 20)).save(img_path)
    store = Store(tmp_path / "tnb.db")
    low = maybe_export_cnn_sample(
        store,
        {
            "image_id": "IMG-low",
            "content_id": "CNT-1",
            "storage_key": str(img_path),
            "sha256": "ab" * 32,
            "cnn_class": "PHOTOGRAPH",
            "cnn_confidence": 0.2,
            "source_url": "https://woah.org/photo.jpg",
        },
    )
    assert low is None
    high = maybe_export_cnn_sample(
        store,
        {
            "image_id": "IMG-high",
            "content_id": "CNT-1",
            "storage_key": str(img_path),
            "sha256": "cd" * 32,
            "cnn_class": "PHOTOGRAPH",
            "cnn_confidence": 0.81,
            "source_url": "https://woah.org/photo.jpg",
        },
    )
    assert high is not None
    assert high["split"] in {"train", "val", "test"}
    dest = Path(high["path"])
    assert dest.is_file()
    assert dest.parent.name == "PHOTOGRAPH"
    again = maybe_export_cnn_sample(
        store,
        {
            "image_id": "IMG-high",
            "content_id": "CNT-1",
            "storage_key": str(img_path),
            "sha256": "cd" * 32,
            "cnn_class": "PHOTOGRAPH",
            "cnn_confidence": 0.99,
            "source_url": "https://woah.org/photo.jpg",
        },
    )
    assert again is None
    assert store.count_cnn_samples() == 1
    junk = tmp_path / "fb_drawing.png"
    Image.new("RGB", (32, 32), (9, 9, 9)).save(junk)
    skipped = maybe_export_cnn_sample(
        store,
        {
            "image_id": "IMG-fb",
            "content_id": "CNT-1",
            "storage_key": str(junk),
            "sha256": "ee" * 32,
            "cnn_class": "PHOTOGRAPH",
            "cnn_confidence": 0.99,
            "source_url": str(junk),
            "synthetic": True,
        },
    )
    assert skipped is None
    store.close()
