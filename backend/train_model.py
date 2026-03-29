"""
train_model.py
Fine-tune YOLOv8 on the Nigerian license plate dataset for CVT-VACS.

HOW TO RUN:
    python train_model.py

WHAT THIS DOES:
    1. Loads the pre-trained YOLOv8n base model
    2. Fine-tunes it on your Nigerian plate images
    3. Saves the best weights to:
       runs/train/nigeria_plates_v1/weights/best.pt
    4. Validates on the test split and prints final metrics

WHAT THIS DOES NOT DO:
    - It does NOT touch main.py, app/, or any backend code
    - It does NOT start the server
    - It does NOT modify your database or existing models
    - Running it again will create nigeria_plates_v2, v3, etc.
      (existing runs are never overwritten)

AFTER TRAINING:
    Update your .env file:
        YOLO_MODEL_PATH=runs/train/nigeria_plates_v1/weights/best.pt
    Then restart the backend. That is the only change needed.
"""

import os
import sys
from pathlib import Path


# ── Dependency check ──────────────────────────────────────────────────────────

def check_dependencies():
    """Warn early if required packages are missing."""
    missing = []
    try:
        import ultralytics
    except ImportError:
        missing.append("ultralytics")
    try:
        import torch
    except ImportError:
        missing.append("torch")

    if missing:
        print("❌  Missing packages. Install them first:")
        for pkg in missing:
            print(f"    pip install {pkg}")
        sys.exit(1)


# ── Dataset check ─────────────────────────────────────────────────────────────

def check_dataset(yaml_path: str = "nigeria_plates.yaml"):
    """Verify the dataset folder structure exists before training."""
    required = [
        "nigeria_plates/images/train",
        "nigeria_plates/images/val",
        "nigeria_plates/images/test",
        "nigeria_plates/labels/train",
        "nigeria_plates/labels/val",
        "nigeria_plates/labels/test",
    ]
    missing = [p for p in required if not Path(p).exists()]
    if missing:
        print("❌  Dataset folders not found. Create these first:")
        for p in missing:
            print(f"    {p}/")
        print("\nSee the project README or the supervisor notes for dataset setup.")
        sys.exit(1)

    if not Path(yaml_path).exists():
        print(f"❌  {yaml_path} not found. Make sure it is in the project root.")
        sys.exit(1)

    # Count images
    train_imgs = list(Path("nigeria_plates/images/train").glob("*.[jJpP][pPnN][gG]"))
    val_imgs   = list(Path("nigeria_plates/images/val").glob("*.[jJpP][pPnN][gG]"))
    test_imgs  = list(Path("nigeria_plates/images/test").glob("*.[jJpP][pPnN][gG]"))

    print(f"✅  Dataset found:")
    print(f"    Train : {len(train_imgs)} images")
    print(f"    Val   : {len(val_imgs)} images")
    print(f"    Test  : {len(test_imgs)} images")
    print(f"    Total : {len(train_imgs) + len(val_imgs) + len(test_imgs)} images")
    print()

    if len(train_imgs) < 50:
        print("⚠️  Warning: fewer than 50 training images detected.")
        print("   Consider adding more images for better model accuracy.")
        print()


# ── Training ──────────────────────────────────────────────────────────────────

def train(
    yaml_path:   str = "nigeria_plates.yaml",
    base_model:  str = "yolov8n.pt",
    epochs:      int = 50,
    batch:       int = 16,
    img_size:    int = 640,
    device:      str = "auto",
    run_name:    str = "nigeria_plates_v1",
):
    """
    Fine-tune YOLOv8 on the Nigerian plate dataset.

    Args:
        yaml_path:  Path to the dataset YAML config file.
        base_model: YOLOv8 weights to start from. 'yolov8n.pt' is
                    downloaded automatically if not present locally.
        epochs:     Number of training epochs (50 is a good starting
                    point; increase to 100 for higher accuracy).
        batch:      Batch size. Reduce to 8 if you get out-of-memory
                    errors on your GPU.
        img_size:   Input image size (must stay at 640 to match the
                    preprocessing in anpr_service.py).
        device:     'auto' lets YOLOv8 pick GPU if available, else CPU.
                    Use '0' to force GPU 0, or 'cpu' to force CPU.
        run_name:   Name of the output folder under runs/train/.
    """
    from ultralytics import YOLO
    import torch

    # ── Device info ───────────────────────────────────────────────────────────
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        print(f"🖥️   GPU detected: {gpu_name}")
        device = 0 if device == "auto" else device
    else:
        print("🖥️   No GPU detected — training on CPU (this will be slower).")
        device = "cpu" if device == "auto" else device

    print(f"⚙️   Configuration:")
    print(f"    Base model : {base_model}")
    print(f"    Dataset    : {yaml_path}")
    print(f"    Epochs     : {epochs}")
    print(f"    Batch size : {batch}")
    print(f"    Image size : {img_size}x{img_size}")
    print(f"    Device     : {device}")
    print(f"    Output     : runs/train/{run_name}/")
    print()

    # ── Load base model ───────────────────────────────────────────────────────
    print(f"📦  Loading base model: {base_model}")
    model = YOLO(base_model)

    # ── Fine-tune ─────────────────────────────────────────────────────────────
    print("🚀  Starting fine-tuning on Nigerian plate dataset...\n")
    results = model.train(
        data        = yaml_path,
        epochs      = epochs,
        imgsz       = img_size,
        batch       = batch,
        name        = run_name,
        project     = "runs/train",
        device      = device,
        patience    = 15,       # stop early if val loss does not improve
        save        = True,
        save_period = 10,       # checkpoint every 10 epochs
        plots       = True,     # saves loss/metric graphs as PNG
        verbose     = True,
        # Augmentation settings tuned for plate recognition
        hsv_h       = 0.015,    # hue shift
        hsv_s       = 0.7,      # saturation shift
        hsv_v       = 0.4,      # brightness shift
        degrees     = 5.0,      # rotation (plates rarely tilt more than 5°)
        translate   = 0.1,
        scale       = 0.5,
        shear       = 2.0,
        flipud      = 0.0,      # plates should not appear upside-down
        fliplr      = 0.0,      # plates should not appear mirrored
        mosaic      = 1.0,
        mixup       = 0.1,
    )

    # ── Results ───────────────────────────────────────────────────────────────
    best_weights = Path(f"runs/train/{run_name}/weights/best.pt")
    print("\n" + "=" * 60)
    print("✅  Training complete!")
    print(f"    Best weights saved to: {best_weights}")
    print("=" * 60)

    return model, best_weights


# ── Validation ────────────────────────────────────────────────────────────────

def validate(model, yaml_path: str = "nigeria_plates.yaml"):
    """Run final evaluation on the held-out test split."""
    print("\n📊  Running final evaluation on test split...")
    metrics = model.val(data=yaml_path, split="test")

    map50    = metrics.box.map50
    map50_95 = metrics.box.map
    precision = metrics.box.mp
    recall    = metrics.box.mr

    print("\n" + "=" * 60)
    print("📈  Final Test Metrics:")
    print(f"    mAP@0.5        : {map50 * 100:.2f}%")
    print(f"    mAP@0.5:0.95   : {map50_95 * 100:.2f}%")
    print(f"    Precision      : {precision * 100:.2f}%")
    print(f"    Recall         : {recall * 100:.2f}%")
    print("=" * 60)

    # Target guidance
    if map50 >= 0.94:
        print("🎉  Excellent! Model is ready for production use.")
    elif map50 >= 0.88:
        print("✅  Good performance. Consider training for more epochs")
        print("    (increase epochs to 100) for further improvement.")
    else:
        print("⚠️   Accuracy below 88%. Recommendations:")
        print("    - Increase epochs to 100")
        print("    - Check that your label .txt files are correctly formatted")
        print("    - Add more diverse training images")
        print("    - Ensure images include varied lighting and angles")

    return metrics


# ── Update .env helper ────────────────────────────────────────────────────────

def update_env(best_weights: Path):
    """
    Optionally update the YOLO_MODEL_PATH in .env automatically.
    Only runs if .env exists in the project root.
    """
    env_path = Path(".env")
    if not env_path.exists():
        return

    content = env_path.read_text()
    new_path = str(best_weights).replace("\\", "/")
    new_line = f"YOLO_MODEL_PATH={new_path}"

    if "YOLO_MODEL_PATH=" in content:
        lines = content.splitlines()
        updated = [new_line if l.startswith("YOLO_MODEL_PATH=") else l for l in lines]
        env_path.write_text("\n".join(updated) + "\n")
        print(f"\n✅  .env updated automatically:")
        print(f"    YOLO_MODEL_PATH={new_path}")
    else:
        with env_path.open("a") as f:
            f.write(f"\n{new_line}\n")
        print(f"\n✅  YOLO_MODEL_PATH added to .env:")
        print(f"    {new_path}")

    print("    Restart the backend server for the change to take effect.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  CVT-VACS  —  Nigerian Plate Model Fine-Tuning")
    print("=" * 60)
    print()

    # 1. Check dependencies
    check_dependencies()

    # 2. Check dataset structure
    check_dataset()

    # 3. Train
    # ── CONFIGURATION — edit these values if needed ──────────────
    EPOCHS     = 50    # increase to 100 for higher accuracy
    BATCH_SIZE = 16    # reduce to 8 if GPU memory error occurs
    # ─────────────────────────────────────────────────────────────
    model, best_weights = train(
        yaml_path  = "nigeria_plates.yaml",
        base_model = "yolov8n.pt",
        epochs     = EPOCHS,
        batch      = BATCH_SIZE,
        img_size   = 640,
        device     = "auto",
        run_name   = "nigeria_plates_v1",
    )

    # 4. Validate on test split
    validate(model)

    # 5. Auto-update .env
    update_env(best_weights)

    print("\n🏁  All done. Your fine-tuned model is ready.")
    print("    Restart the backend to start using it.")
