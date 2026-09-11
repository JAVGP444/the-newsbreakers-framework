"""Entrena el ciclo académico completo: dataset sintético variado, split 70/15/15.

Arquitectura: Conv2D32 → MaxPool → Conv2D64 → MaxPool → Conv2D64 → Flatten → Dense64 → Dense8
Optimizador Adam, pérdida CrossEntropy (= sparse_categorical_crossentropy), métrica accuracy.
"""
from __future__ import annotations

import json
import random
import shutil
import sys
from pathlib import Path

_FW = Path(__file__).resolve().parents[2]
if str(_FW) not in sys.path:
    sys.path.insert(0, str(_FW))
from bootstrap import CNN_DIR, CNN_DATASET_DIR, CNN_WEIGHTS, FRAMEWORK_ROOT, ensure_paths  # noqa: E402

ensure_paths()

from cnn import (  # noqa: E402
    ARCHITECTURE,
    FLATTEN_DIM,
    IMAGE_CLASSES,
    INPUT_SIZE,
    MiniCNN,
    MODEL_VERSION,
    reset_session,
)

DATA_DIR = FRAMEWORK_ROOT / "data" / "cnn_synth"
SAMPLES_DIR = CNN_DIR / "samples"
EPOCHS = 12
PER_CLASS = 80
SEED = 42
BATCH = 16
LR = 1e-3


def _jitter_color(rgb: tuple[int, int, int], rng: random.Random, span: int = 28) -> tuple[int, int, int]:
    return tuple(max(0, min(255, c + rng.randint(-span, span))) for c in rgb)  # type: ignore[return-value]


def _noise(img, rng: random.Random, amount: int = 80) -> None:
    pixels = img.load()
    w, h = img.size
    for _ in range(amount):
        x, y = rng.randint(0, w - 1), rng.randint(0, h - 1)
        r, g, b = pixels[x, y]
        pixels[x, y] = (
            max(0, min(255, r + rng.randint(-18, 18))),
            max(0, min(255, g + rng.randint(-18, 18))),
            max(0, min(255, b + rng.randint(-18, 18))),
        )


def _text(draw, rng: random.Random, lines: list[str], fill: tuple[int, int, int]) -> None:
    y = rng.randint(2, 10)
    for line in lines:
        x = rng.randint(2, 12)
        draw.text((x, y), line[:18], fill=fill)
        y += rng.randint(8, 12)


def _make_image(label: str, idx: int, rng: random.Random):
    from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

    palettes = {
        "OFFICIAL_DOCUMENT": [(238, 236, 228), (42, 42, 48), (170, 40, 40), (30, 80, 140)],
        "NEWS_SCREENSHOT": [(18, 38, 78), (230, 230, 232), (190, 28, 28), (12, 12, 16)],
        "SOCIAL_MEDIA": [(24, 150, 230), (250, 250, 252), (18, 18, 22), (80, 180, 90)],
        "MEME": [(252, 214, 0), (8, 8, 8), (255, 70, 170), (255, 255, 255)],
        "INFOGRAPHIC": [(8, 28, 48), (0, 188, 210), (240, 240, 245), (21, 101, 192)],
        "ANIMAL_HEALTH_CONTENT": [(48, 120, 52), (255, 230, 70), (10, 90, 160), (180, 90, 40)],
        "PHOTOGRAPH": [(70, 130, 60), (130, 90, 70), (140, 190, 140), (200, 180, 140)],
        "POTENTIALLY_MANIPULATED": [(180, 40, 40), (40, 180, 50), (40, 50, 190), (255, 255, 255)],
    }
    pal = palettes[label]
    bg = _jitter_color(pal[0], rng, 22)
    img = Image.new("RGB", (INPUT_SIZE, INPUT_SIZE), bg)
    draw = ImageDraw.Draw(img)
    accent = _jitter_color(pal[1], rng, 20)
    accent2 = _jitter_color(pal[2], rng, 20)
    variant = idx % 6

    if label == "OFFICIAL_DOCUMENT":
        draw.rectangle([3, 3, INPUT_SIZE - 4, INPUT_SIZE - 4], outline=accent, width=2)
        header_h = 10 + rng.randint(0, 6)
        draw.rectangle([4, 4, INPUT_SIZE - 5, 4 + header_h], fill=accent2)
        for y in range(header_h + 8, INPUT_SIZE - 6, 4 + rng.randint(0, 2)):
            wline = rng.randint(28, 54)
            draw.rectangle([6 + rng.randint(0, 4), y, 6 + wline, y + 1], fill=accent)
        if variant < 3:
            draw.ellipse([INPUT_SIZE - 22, INPUT_SIZE - 22, INPUT_SIZE - 6, INPUT_SIZE - 6], outline=accent2)
        _text(draw, rng, ["SENASICA", "OFICIO", f"FOLIO {idx:03d}"], accent)
    elif label == "NEWS_SCREENSHOT":
        draw.rectangle([0, 0, INPUT_SIZE, 12 + rng.randint(0, 6)], fill=accent)
        draw.rectangle([0, 0, rng.randint(10, 22), INPUT_SIZE], fill=_jitter_color(pal[3], rng, 10))
        draw.rectangle([18, 16, INPUT_SIZE - 4, 16 + rng.randint(10, 22)], fill=accent2)
        for y in range(40, INPUT_SIZE - 4, 5):
            draw.rectangle([18, y, rng.randint(40, 60), y + 2], fill=pal[1])
        _text(draw, rng, ["BREAKING", "H5N1 watch"], (255, 255, 255))
    elif label == "SOCIAL_MEDIA":
        draw.rounded_rectangle([4, 4, INPUT_SIZE - 5, INPUT_SIZE - 5], radius=8, fill=pal[1], outline=accent)
        r = rng.randint(8, 14)
        cx, cy = rng.randint(10, 18), rng.randint(10, 18)
        draw.ellipse([cx, cy, cx + r, cy + r], fill=accent)
        draw.rectangle([cx + r + 4, cy + 2, INPUT_SIZE - 10, cy + 8], fill=accent)
        draw.rectangle([8, 32, INPUT_SIZE - 8, INPUT_SIZE - 10], fill=_jitter_color(pal[3], rng, 40))
        _text(draw, rng, ["@usuario", "compartió"], pal[3])
    elif label == "MEME":
        draw.rectangle([0, 0, INPUT_SIZE, INPUT_SIZE], fill=_jitter_color(pal[3] if variant % 2 else pal[2], rng, 30))
        draw.rectangle([0, 0, INPUT_SIZE, 14 + rng.randint(0, 6)], fill=pal[0])
        draw.rectangle([0, INPUT_SIZE - 16, INPUT_SIZE, INPUT_SIZE], fill=pal[0])
        _text(draw, rng, ["TOP TEXT", "BOTTOM TEXT"], pal[1])
        if variant >= 3:
            draw.ellipse([16, 18, 48, 46], fill=accent2)
    elif label == "INFOGRAPHIC":
        draw.rectangle([0, 0, INPUT_SIZE, 12], fill=accent)
        n_bars = rng.randint(4, 6)
        for i in range(n_bars):
            h = rng.randint(10, 40)
            x = 4 + i * (INPUT_SIZE // n_bars)
            draw.rectangle([x, INPUT_SIZE - 6 - h, x + 6, INPUT_SIZE - 6], fill=accent2)
        if variant < 3:
            draw.pieslice([36, 8, 60, 32], 0, rng.randint(80, 300), fill=pal[1])
        else:
            draw.ellipse([40, 10, 58, 28], fill=pal[1])
        _text(draw, rng, ["CASOS", f"{idx}"], pal[2])
    elif label == "ANIMAL_HEALTH_CONTENT":
        # silueta animal + acento clínico
        draw.ellipse([8 + rng.randint(0, 8), 16, 34, 48], fill=_jitter_color(pal[3], rng, 25))
        draw.ellipse([26, 10, 44, 26], fill=accent)
        draw.rectangle([40, 8, 58, 56], fill=accent2)
        draw.rectangle([0, 50, INPUT_SIZE, INPUT_SIZE], fill=pal[2])
        if variant % 2:
            draw.line([(6, 20), (20, 8)], fill=(220, 40, 40), width=2)
        _text(draw, rng, ["HPAI", "GRANJA"], pal[1])
    elif label == "PHOTOGRAPH":
        for _ in range(rng.randint(10, 22)):
            x, y = rng.randint(0, 50), rng.randint(0, 50)
            col = _jitter_color(pal[rng.randint(0, 3)], rng, 35)
            draw.ellipse([x, y, x + rng.randint(6, 28), y + rng.randint(6, 28)], fill=col)
        if variant < 2:
            draw.polygon([(10, 50), (32, 18), (54, 50)], fill=pal[1])
    else:  # POTENTIALLY_MANIPULATED
        for y in range(0, INPUT_SIZE, rng.choice([4, 6, 8])):
            for x in range(0, INPUT_SIZE, rng.choice([4, 6, 8])):
                draw.rectangle([x, y, x + 6, y + 6], fill=pal[(x + y + idx) % 4])
        # seam / clone artifact
        box = [rng.randint(4, 20), rng.randint(4, 20), rng.randint(30, 50), rng.randint(30, 50)]
        crop = img.crop(tuple(box))
        img.paste(crop, (rng.randint(20, 36), rng.randint(20, 36)))
        draw = ImageDraw.Draw(img)
        for _ in range(8):
            draw.point((rng.randint(0, 63), rng.randint(0, 63)), fill=(255, 255, 255))

    _noise(img, rng, amount=rng.randint(30, 90))
    if rng.random() < 0.35:
        img = ImageEnhance.Brightness(img).enhance(rng.uniform(0.75, 1.25))
    if rng.random() < 0.3:
        img = img.filter(ImageFilter.SMOOTH)
    if rng.random() < 0.2:
        img = img.rotate(rng.choice([-8, -4, 4, 8]), fillcolor=bg)
    return img.convert("RGB").resize((INPUT_SIZE, INPUT_SIZE))


def generate_dataset(per_class: int = PER_CLASS) -> Path:
    rng = random.Random(SEED)
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for label in IMAGE_CLASSES:
        folder = DATA_DIR / "all" / label
        folder.mkdir(parents=True, exist_ok=True)
        for i in range(per_class):
            _make_image(label, i, rng).save(folder / f"{label.lower()}_{i:03d}.png")
    return DATA_DIR


MINED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def mined_paths(label: str) -> list[Path]:
    folder = CNN_DATASET_DIR / label
    if not folder.is_dir():
        return []
    return [p for p in sorted(folder.iterdir()) if p.is_file() and p.suffix.lower() in MINED_EXTS]


def collect_training_paths(per_class: int, use_mined: bool) -> tuple[dict[str, list[Path]], bool]:
    """Solo fotos reales si hay volumen; si no, sintético etiquetado como experimental."""
    mined_total = 0
    mined_map: dict[str, list[Path]] = {}
    for label in IMAGE_CLASSES:
        mined_map[label] = mined_paths(label) if use_mined else []
        mined_total += len(mined_map[label])
    real_enough = mined_total >= 24 and any(len(v) >= 3 for v in mined_map.values())
    if real_enough:
        print(f"  [cnn] entrenamiento en fotos minadas ({mined_total} archivos) — no sintético")
        return mined_map, False
    generate_dataset(per_class)
    out: dict[str, list[Path]] = {}
    for label in IMAGE_CLASSES:
        synth = sorted((DATA_DIR / "all" / label).glob("*.png"))
        out[label] = synth[:per_class]
        print(f"  [cnn] {label}: experimental sintético n={len(out[label])} (sin fotos reales suficientes)")
    return out, True


def _split_indices(n: int, rng: random.Random) -> tuple[list[int], list[int], list[int]]:
    idx = list(range(n))
    rng.shuffle(idx)
    n_train = int(n * 0.70)
    n_val = int(n * 0.15)
    return idx[:n_train], idx[n_train : n_train + n_val], idx[n_train + n_val :]


def _metrics(logits, y):  # noqa: ANN001
    pred = logits.argmax(1)
    correct = int((pred == y).sum().item())
    return correct, int(y.shape[0])


def train(epochs: int = EPOCHS, per_class: int = PER_CLASS, use_mined: bool = True) -> Path:
    import numpy as np
    import torch
    import torch.nn as nn
    from PIL import Image

    by_label, experimental = collect_training_paths(per_class, use_mined)
    rng = random.Random(SEED + 7)
    xs, ys, paths = [], [], []
    for yi, label in enumerate(IMAGE_CLASSES):
        for path in by_label[label]:
            arr = np.asarray(Image.open(path).convert("RGB").resize((INPUT_SIZE, INPUT_SIZE)), dtype="float32") / 255.0
            xs.append(np.transpose(arr, (2, 0, 1)))
            ys.append(yi)
            paths.append(path)

    x = torch.from_numpy(np.stack(xs))
    y = torch.tensor(ys, dtype=torch.long)
    n = x.shape[0]
    train_i, val_i, test_i = _split_indices(n, rng)

    def subset(indices: list[int]):
        t = torch.tensor(indices, dtype=torch.long)
        return x.index_select(0, t), y.index_select(0, t)

    x_tr, y_tr = subset(train_i)
    x_va, y_va = subset(val_i)
    x_te, y_te = subset(test_i)

    net = MiniCNN.build(nn)
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    loss_fn = nn.CrossEntropyLoss()  # sparse_categorical_crossentropy

    history = {"acc": [], "val_acc": [], "loss": [], "val_loss": []}

    def run_epoch(xb, yb, train_mode: bool) -> tuple[float, float]:
        if train_mode:
            net.train()
        else:
            net.eval()
        total_loss = 0.0
        correct = 0
        seen = 0
        order = torch.randperm(xb.shape[0]) if train_mode else torch.arange(xb.shape[0])
        ctx = torch.enable_grad() if train_mode else torch.no_grad()
        with ctx:
            for start in range(0, xb.shape[0], BATCH):
                idx = order[start : start + BATCH]
                batch_x, batch_y = xb[idx], yb[idx]
                if train_mode:
                    opt.zero_grad()
                logits = net(batch_x)
                loss = loss_fn(logits, batch_y)
                if train_mode:
                    loss.backward()
                    opt.step()
                total_loss += float(loss.item()) * len(idx)
                c, m = _metrics(logits, batch_y)
                correct += c
                seen += m
        return total_loss / max(seen, 1), correct / max(seen, 1)

    for epoch in range(epochs):
        loss, acc = run_epoch(x_tr, y_tr, True)
        val_loss, val_acc = run_epoch(x_va, y_va, False)
        history["loss"].append(round(loss, 4))
        history["acc"].append(round(acc, 4))
        history["val_loss"].append(round(val_loss, 4))
        history["val_acc"].append(round(val_acc, 4))
        print(
            f"epoch {epoch + 1}/{epochs}  "
            f"loss={loss:.4f} acc={acc:.3f}  val_loss={val_loss:.4f} val_acc={val_acc:.3f}"
        )

    net.eval()
    with torch.no_grad():
        logits = net(x_te)
        test_loss = float(loss_fn(logits, y_te).item())
        pred = logits.argmax(1)
        test_acc = float((pred == y_te).sum().item() / max(len(test_i), 1))
        matrix = [[0 for _ in IMAGE_CLASSES] for _ in IMAGE_CLASSES]
        per_class_metrics = []
        for i, label in enumerate(IMAGE_CLASSES):
            mask = y_te == i
            n_i = int(mask.sum().item())
            hit = int(((pred == i) & mask).sum().item()) if n_i else 0
            per_class_metrics.append({"class": label, "n": n_i, "accuracy": round(hit / n_i, 4) if n_i else 0.0})
        for t, p in zip(y_te.tolist(), pred.tolist()):
            matrix[t][p] += 1

    CNN_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for old in SAMPLES_DIR.glob("*"):
        old.unlink()
    samples_meta = []
    # 2 imágenes de test por clase (no vistas en entrenamiento)
    by_class: dict[int, list[int]] = {i: [] for i in range(len(IMAGE_CLASSES))}
    for local_k, global_i in enumerate(test_i):
        by_class[int(ys[global_i])].append(global_i)
    for ci, label in enumerate(IMAGE_CLASSES):
        for j, global_i in enumerate(by_class[ci][:2]):
            src = paths[global_i]
            dest = SAMPLES_DIR / f"{label.lower()}_unseen_{j}.png"
            shutil.copy2(src, dest)
            samples_meta.append({"id": dest.name, "class": label, "split": "test"})

    payload = {
        "state_dict": net.state_dict(),
        "classes": list(IMAGE_CLASSES),
        "model_version": MODEL_VERSION,
        "input_size": INPUT_SIZE,
        "flatten_dim": FLATTEN_DIM,
        "epochs": epochs,
        "per_class": per_class_metrics,
        "n_per_class": per_class,
        "architecture": ARCHITECTURE,
        "optimizer": "Adam",
        "loss": "sparse_categorical_crossentropy",
        "metrics": ["accuracy"],
        "split": [0.7, 0.15, 0.15],
    }
    torch.save(payload, CNN_WEIGHTS)

    (CNN_DIR / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    (CNN_DIR / "confusion_matrix.json").write_text(
        json.dumps({"labels": list(IMAGE_CLASSES), "matrix": matrix}, indent=2),
        encoding="utf-8",
    )
    (CNN_DIR / "test_metrics.json").write_text(
        json.dumps(
            {
                "test_accuracy": round(test_acc, 4),
                "test_loss": round(test_loss, 4),
                "n_test": len(test_i),
                "n_train": len(train_i),
                "n_val": len(val_i),
                "epochs": epochs,
                "split": [0.7, 0.15, 0.15],
                "per_class": per_class_metrics,
                "samples": samples_meta,
                "architecture": ARCHITECTURE,
                "model_version": MODEL_VERSION,
                "experimental_on_synthetic": experimental,
                "production_metric": False if experimental else True,
                "note": (
                    "CNN académica experimental sobre dibujos sintéticos. "
                    "Esta exactitud NO es métrica de producción ni generaliza a fotos de prensa."
                    if experimental
                    else "CNN académica entrenada en fotos minadas. El modelo productivo de ficha es CLIP/ResNet."
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    reset_session()
    print(f"saved {CNN_WEIGHTS}")
    print(f"test accuracy={test_acc:.3f}")
    return CNN_WEIGHTS


if __name__ == "__main__":
    train(use_mined=True)
