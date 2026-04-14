# Dolphin Fin Sorter (UI MVP)

Frontend-only NiceGUI interface for dolphin image sorting and fin annotation validation.

## Features

- Modular dashboard layout (topbar, sidebar, viewer, action toolbar, status panel)
- Mock image queue with statuses and fake dataset paths
- Bounding box overlay simulation in the center viewer
- Keyboard shortcuts for fast review (`<-`, `->`, `Enter`, `A`, `Delete`)
- Mock detection progress and mock export notifications

## Run

```bash
pip install -r requirements.txt
python main.py
```

Then open the local NiceGUI URL shown in the terminal.

## Plug YOLO Later

1. Replace `build_mock_images(...)` in `src/dolphin_fin_sorter/models/mock_data.py` with backend-fed records.
2. Map YOLO detections to `Detection` (`x1,y1,x2,y2,confidence`).
3. Bind `Run detection` to your asynchronous inference pipeline and keep progress updates in `DashboardState`.
4. Replace `/assets/placeholder.svg` with real image preview paths or an image streaming endpoint.

