# Delphin Eye

Outil de détection automatique des nageoires dorsales de dauphins de Guyane (*Sotalia guianensis*) par photo-identification, développé pour le GEPOG dans le cadre du suivi de la Réserve Naturelle de l'Île du Grand-Connétable.

## Contexte

Le dauphin de Guyane est classé « En danger » en Guyane française. Le GEPOG mène depuis plusieurs années un programme de suivi par photo-identification : chaque dauphin est reconnu grâce aux marques naturelles de sa nageoire dorsale (encoches, cicatrices, déformations). Cette méthode génère des milliers d'images à traiter manuellement, un travail long et fastidieux.

Delphin Eye automatise la première étape : détecter et localiser les nageoires dorsales sur chaque image grâce à un modèle YOLO, et exporter les résultats sous une forme exploitable pour la comparaison et l'identification individuelle.

## Fonctionnalités

- **Chargement par dossier** - chargement récursif de toutes les images (`.jpg`, `.jpeg`, `.png`, `....`)
- **Détection automatique** - inférence YOLO en arrière-plan
- **Annotation manuelle** - ajout, suppression et correction de bounding boxes directement sur l'image
- **Export structuré** - images recadrées et numérotées dans `<dossier>_triees/`, corrections manuelles + labels YOLO dans `<dossier>_corrections/`
- **Persistance** - reprise automatique au dernier dossier et image consultés

## Prérequis

- Python 3.10 ou supérieur
- Un modèle YOLO entraîné (`output/models/default/weights/best.pt` par défaut)

## Installation et démarrage

```bash
git clone <url-du-repo>
cd delphin-eye
./run.sh
```

`run.sh` crée automatiquement un virtualenv `.venv/`, installe toutes les dépendances au premier lancement, puis démarre l'application. Si `requirements.txt` est modifié ultérieurement, la mise à jour des dépendances se fait automatiquement au prochain lancement.

L'interface s'ouvre dans le navigateur à l'adresse indiquée dans le terminal (par défaut `http://localhost:8080`).

Pour les lancements suivants :

```bash
./run.sh
```

### Installation manuelle (sans run.sh)

Si tu préfères gérer l'environnement toi-même :

```bash
# Créer et activer le virtualenv
python3 -m venv .venv
source .venv/bin/activate        # Linux / Mac
# .venv\Scripts\activate         # Windows

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# Lancer l'application
python run.py
```

Pour mettre à jour les dépendances après une modification de `requirements.txt` :

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Utilisation

1. Cliquer sur **Dossier** dans la barre du haut pour sélectionner un dossier d'images
2. Cliquer sur **Analyser** pour lancer la détection automatique
3. Parcourir les images dans la liste à gauche (ou avec les flèches `←` `→`)
4. Corriger si besoin : glisser sur l'image pour ajouter une bbox, cliquer sur une bbox pour la sélectionner, `Suppr` pour la supprimer
5. Cliquer sur **Exporter** pour générer les dossiers de sortie

## Structure des exports

```
<dossier>_triees/        ← images recadrées sur les ailerons, numérotées si plusieurs
<dossier>_corrections/   ← images modifiées manuellement + fichiers labels YOLO (.txt)
```

Si le dossier source contient `_sauvegarde` dans son nom, le suffixe est remplacé automatiquement.

## Raccourcis clavier

| Touche | Action |
|--------|--------|
| `←` / `→` | Image précédente / suivante |
| `A` | Hint ajout de bbox |
| `Suppr` | Supprimer la bbox sélectionnée |

## Configuration

Les paramètres (chemin du modèle, seuil de confiance, marge de recadrage) sont accessibles via l'icône ⚙️ dans la barre du haut et sauvegardés dans `config/user_settings.json`.
