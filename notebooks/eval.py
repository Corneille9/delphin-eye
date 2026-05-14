
import os
from pathlib import Path
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)

DATA_YAML = str(PROJECT_ROOT / "data" / "data.yaml")
OUTPUT_MODELS = str(PROJECT_ROOT / "output" / "models" / "default" / "weights" / "best.pt")

OUTPUT_RUNS = str(PROJECT_ROOT / "output" / "models")

# Charger ton modèle entraîné
model = YOLO(OUTPUT_MODELS)

# Évaluer sur le dataset de validation/test
metrics = model.val(
    data=DATA_YAML,
    split='val',          # ou 'val'
    conf=0.001,            # seuil bas pour les courbes PR
    iou=0.6,
    plots=True,            # ⭐ génère TOUS les graphiques
    save_json=True,        # pour évaluation COCO si besoin

     # Nombre total d'epochs
    # 1 epoch = le modèle voit toutes les images une fois
    epochs=80,

    # Stoppe automatiquement si aucune amélioration
    # après 41 epochs
    patience=41,

    # Taille des images utilisées pendant l'entraînement
    # Plus grand = meilleure précision
    # mais plus lent et plus gourmand
    imgsz=640,

    # Nombre d'images traitées simultanément
    # Réduire si manque de mémoire
    batch=8,

    # GPU utilisé
    # 0 = premier GPU CUDA
    # "cpu" = utiliser uniquement le CPU
    #device=0,

    # Rotation aléatoire des images
    # entre -10° et +10°
    degrees=10,

    # Flip horizontal aléatoire
    # 0.5 = 50% des images
    fliplr=0.5,

    # Zoom aléatoire
    # 0.3 = entre 70% et 130%
    scale=0.3,

    # Combine plusieurs images en une
    # Très utile pour améliorer la généralisation
    mosaic=0.5,

    # Déplacement aléatoire de l'image
    translate=0.1,

    # Variation légère des couleurs
    # Très utile pour différentes lumières
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,

    project=OUTPUT_RUNS,
    name='default'
)

# Métriques accessibles directement
print(f"mAP@0.5     : {metrics.box.map50:.4f}")
print(f"mAP@0.5:0.95: {metrics.box.map:.4f}")
print(f"Precision   : {metrics.box.mp:.4f}")
print(f"Recall      : {metrics.box.mr:.4f}")