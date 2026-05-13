# for optimale training

from ultralytics import YOLO
from pathlib import Path

DATA_YAML = str(Path.cwd().parent / "data" / "data.yaml")
OUTPUT_RUNS = str(Path.cwd().parent / "output" / "models")

model = YOLO("yolo26s.pt")

model.train(
    # Fichier YAML du dataset
    # Contient :
    # - chemins des images
    # - classes
    # - nombre de classes
    data=DATA_YAML,

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

    # Dossier principal des résultats
    project=OUTPUT_RUNS,

    # Nom du run d'entraînement
    name="default",
)