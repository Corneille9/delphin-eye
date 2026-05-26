import os
from pathlib import Path
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)

DATA_YAML = str(PROJECT_ROOT / "data" / "data.yaml")
OUTPUT_RUNS = str(PROJECT_ROOT / "output" / "models")

for model_size in ['n', 's', 'm']:
    model = YOLO(f"yolo26{model_size}.pt")

    model.train(
        data=DATA_YAML,
        epochs=200,
        patience=40,
        imgsz=960,
        batch=-1,
        degrees=5,
        fliplr=0.5,
        flipud=0.0, # dorsal fins are never upside-down
        scale=0.5,
        translate=0.1,
        mosaic=1.0,
        close_mosaic=10,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        cache="disk",
        save_period=10,
        project=OUTPUT_RUNS,
        name=f"delv2-i725-e200-inf960-{model_size}",
    )

    print(f"Saved model to delv2-i725-e200-inf960-{model_size}")