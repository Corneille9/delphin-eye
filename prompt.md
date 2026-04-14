You are a senior Python software architect, full-stack NiceGUI engineer, and computer vision application designer.

You are working on an existing Python project for **sorting and validating dolphin images based on dorsal fin detection using an already trained YOLO model**.

This is **NOT a UI mock task**.

This task is a **full functional refactor and integration task**.

The project already exists and must be **analyzed first before modifying anything**.

The product specification is attached in `projet.md`.

The notebooks used for model experimentation and training are located in:

```text
notebooks/
```

The trained model already exists in:

```text
output/models/default/
```

The entire application source code must remain under:

```text
src/
```

---

# PHASE 1 - PROJECT AUDIT (MANDATORY FIRST)

Before writing any code, first **explore the current project structure**.

Mandatory first steps:

1. inspect the full repository tree
2. inspect all files inside `src/`
3. inspect notebooks inside `notebooks/`
4. understand how training and prediction were previously implemented
5. identify any existing prediction pipeline
6. identify current UI issues
7. identify broken architecture areas
8. propose a clean backend integration strategy

Do NOT start rewriting immediately.

First produce:

* current architecture analysis
* detected technical issues
* proposed refactor plan

Only after that start implementation.

---

# PHASE 2 - FULL UI REBUILD

Completely rebuild the UI using **NiceGUI**.

Requirements:

* professional clean interface
* no gradients
* no emoji anywhere in code
* code in English
* all visible labels and UI text in French
* no spelling mistakes in visible text
* responsive layout is CRITICAL
* must work properly on laptop and desktop resolutions
* must adapt to smaller screens

The interface must feel like a professional annotation software.

Use configurable theme variables.

Example:

* primary color
* secondary color
* border color
* validation color
* warning color
* danger color

Theme must be centralized and configurable.

Example file:

```text
src/config/theme.py
```

---

# PHASE 3 - INTERACTIVE CANVAS REBUILD

The current annotation canvas must be completely redesigned.

This is one of the highest priority tasks.

Requirements:

* reactive canvas
* smooth interactions
* selectable bounding boxes
* draggable boxes
* resizable boxes
* delete selected box
* add new box manually
* secure and stable event handling
* avoid state corruption
* preserve coordinates correctly
* zoom support
* pan support
* image scaling support

Canvas must work reliably.

This part must be production quality.

---

# PHASE 4 - REAL BACKEND INTEGRATION

No mock data.

Everything must be real and connected.

Implement a real backend service layer.

Suggested structure:

```text
src/services/
    prediction_service.py
    image_queue_service.py
    persistence_service.py
    export_service.py
```

Prediction must load model from:

```text
output/models/default/
```

Use real YOLO inference.

The UI must call backend services through clear callbacks.

Example:

* load folder
* run prediction
* save annotation
* validate image
* export crops

---

# PHASE 5 - IMAGE QUEUE SYSTEM

Rebuild image queue system.

Requirements:

* use numeric indexes
* current index tracking
* previous / next navigation
* validated indicator
* rejected indicator
* manually edited indicator
* queue progress indicator

Example:

```text
Image 34 / 280
```

Must clearly show which images are already validated.

---

# PHASE 6 - VALIDATION FLOW

When user validates an image:

* save immediately
* persist annotation
* update queue state
* automatically go to next image

This behavior is mandatory.

---

# PHASE 7 - PERSISTENCE

Persistence is mandatory.

The application must resume after closing.

All progress must be saved.

Store:

* image status
* annotations
* current index
* validation state
* notes
* export configuration
* output directories

Use a local persistent database.

Preferred:

```text
SQLite
```

Do NOT use MySQL.

This is a local desktop-like application.

SQLite is the correct solution.

Suggested path:

```text
src/database/app.db
```

Implement migrations if necessary.

---

# PHASE 8 - CONFIGURATION SYSTEM

Everything must be configurable.

Create centralized config.

Example:

```text
src/config/settings.py
```

Must include:

* output directories
* crop output path
* model path
* autosave interval
* theme colors
* supported image formats

---

# IMPORTANT ENGINEERING RULES

* no mock code
* no placeholder logic
* everything must be functional
* modular architecture
* maintainable code
* clean separation of concerns
* service layer architecture
* reusable UI components
* robust state management

Start with project exploration and architecture analysis first.

Do NOT skip the audit phase.
