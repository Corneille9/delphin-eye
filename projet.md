Excellente idée.
Avant de passer à l’agent IA qui va générer l’UI avec NiceGUI, le plus important est d’avoir une **fiche fonctionnelle claire et détaillée**.

Je te propose une **spécification produit / fiche de conception** que tu pourras directement donner à un agent IA ou à un développeur.

---

# FICHE LOGICIEL — TRI ET VALIDATION D’IMAGES DE DAUPHINS

## 1. Nom du logiciel

**Dolphin Fin Sorter**

Alternative :

* Dolphin Sort AI
* FinMatcher
* Dolphin Annotation Suite

---

## 2. Objectif du logiciel

Le logiciel a pour objectif de **faciliter le tri, la validation et l’annotation des images de dauphins** à partir de la détection automatique des ailerons par un modèle YOLO déjà entraîné.

Le système doit permettre à un utilisateur de :

* charger un dossier contenant un grand volume d’images
* lancer une détection automatique des ailerons
* vérifier rapidement les résultats
* corriger les erreurs de détection
* annoter manuellement les ailerons manquants
* classer les images validées
* générer les crops finaux des ailerons

L’application doit être **fluide, rapide et optimisée pour de gros volumes d’images haute résolution**.

---

## 3. Workflow global

```text
Import dossier images
        ↓
Détection automatique YOLO
        ↓
Pré-tri automatique
        ↓
Validation humaine rapide
        ↓
Correction manuelle si besoin
        ↓
Validation finale
        ↓
Crop des ailerons
        ↓
Export des résultats
```

---

## 4. Écran principal

L’interface principale doit être divisée en 3 zones.

---

## 4.1 Barre supérieure

Contient les actions globales.

```text
[ Choisir dossier ]
[ Lancer détection ]
[ Exporter résultats ]
[ Paramètres ]
[ Progression ]
```

### Fonctions

### Choisir dossier

Permet de sélectionner un dossier local contenant les images.

Formats supportés :

```text
jpg
jpeg
png
webp
```

---

### Lancer détection

Déclenche le traitement YOLO sur toutes les images du dossier.

Le traitement doit être exécuté en arrière-plan.

Affichage progression :

```text
Traitement : 235 / 1200 images
```

---

### Exporter résultats

Génère :

* images validées
* crops d’ailerons
* annotations JSON

---

## 4.2 Colonne gauche — Liste des images

Affiche toutes les images.

Exemple :

```text
img_001.jpg   ✓
img_002.jpg   ?
img_003.jpg   ✗
img_004.jpg   M
```

### Signification

* `✓` = validée
* `?` = à vérifier
* `✗` = rejetée
* `M` = modifiée manuellement

Clique sur une image → ouverture immédiate dans le viewer.

---

## 4.3 Zone centrale — Viewer image

C’est la partie la plus importante.

Affiche :

* image haute résolution
* bounding boxes YOLO
* labels d’identification

Exemple :

```text
+-----------------------------+
|                             |
|      image dauphin          |
|                             |
|   [bbox fin 1]              |
|   [bbox fin 2]              |
|                             |
+-----------------------------+
```

---

## 5. Détection automatique

Le modèle YOLO détecte les ailerons.

Sortie attendue :

```json
{
  "image": "img_001.jpg",
  "detections": [
    {
      "id": 1,
      "bbox": [120, 80, 250, 200],
      "confidence": 0.93
    }
  ]
}
```

---

## 6. Gestion des faux positifs

Chaque bbox doit être sélectionnable.

Actions disponibles :

```text
Valider
Supprimer
Modifier
Reclasser
```

Exemple :

clic bbox → menu rapide

```text
[ Validate ]
[ Delete ]
[ Edit ]
```

---

## 7. Annotation manuelle

L’utilisateur doit pouvoir ajouter une bbox manuellement.

Workflow :

```text
clic souris
drag
release
```

Puis formulaire :

```text
ID aileron : [ 1 ]
```

---

## 8. Navigation rapide

L’application doit être pensée pour une validation rapide.

Boutons :

```text
[ Prev ]
[ Next ]
[ Validate ]
[ Reject ]
[ Add Box ]
```

Raccourcis clavier recommandés :

```text
← image précédente
→ image suivante
Enter valider
Delete supprimer bbox
A ajouter bbox
```

---

## 9. États d’une image

Chaque image possède un statut.

```text
pending
validated
rejected
manual_edit
processed
```

Exemple :

```json
{
  "image": "img_001.jpg",
  "status": "manual_edit"
}
```

---

## 10. Étape finale — crop des ailerons

Après validation finale :

le logiciel découpe automatiquement chaque aileron.

Exemple :

```python
crop = image[y1:y2, x1:x2]
```

---

## 11. Arborescence export

```text
output/
│
├── validated_images/
│
├── cropped_fins/
│   ├── fin_1/
│   ├── fin_2/
│   └── fin_3/
│
├── rejected/
│
└── annotations/
    └── results.json
```

---

## 12. Fichier résultat JSON

```json
{
  "image": "img_001.jpg",
  "status": "validated",
  "fins": [
    {
      "id": 1,
      "bbox": [120, 80, 250, 200],
      "confidence": 0.93
    }
  ]
}
```

---

## 13. Contraintes techniques

### Framework UI

```text
NiceGUI
```

### Backend IA

```text
Python
YOLO ultralytics
OpenCV
```

### Performance

* lazy loading images
* préchargement image suivante
* traitement batch
* cache des previews

---

## 14. Priorité MVP

Ordre recommandé :

### Phase 1

* ouverture dossier
* viewer image
* next / prev
* affichage YOLO bbox

### Phase 2

* validation manuelle
* suppression bbox
* ajout bbox

### Phase 3

* export JSON
* crop automatique

---

Tu peux donner cette fiche telle quelle à un agent IA pour qu’il te génère l’architecture NiceGUI.

Si tu veux, je peux ensuite t’aider à **rédiger le prompt exact pour l’agent IA afin qu’il génère le projet NiceGUI proprement**.
