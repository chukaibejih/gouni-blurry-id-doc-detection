# BlurDetect — Automated Identity Document Image Quality System

A classical computer vision system for detecting blur in identity document images,
built with **FastAPI (Python)** and **React**. Uses **Laplacian Variance** and
**Tenengrad Gradient Magnitude** to compute a single composite quality score and
decide whether an uploaded ID is sharp enough to use downstream.

> **Academic project.** DESIGN AND IMPLEMENTATION OF AN AUTOMATED BLURRY IDENTITY DOCUMENT IMAGE DETECTION SYSTEM.

---

## 1. Quick Start (Docker — recommended)

```bash
docker-compose up --build
```

| Service     | URL                          |
|-------------|------------------------------|
| Frontend    | http://localhost:3000        |
| Backend API | http://localhost:8000        |
| API docs    | http://localhost:8000/docs   |

---

## 2. Manual Start (without Docker)

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows
source venv/bin/activate         # Mac/Linux
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend (new terminal)
```bash
cd frontend
npm install
npm run dev
```

---

## 3. How the Detection Works

```
Image Upload
      │
      ▼
Preprocess  (grayscale → resize to fit 640×480 preserving aspect ratio)
      │
      ▼
Laplacian Variance   +   Tenengrad Gradient Magnitude
      │
      ▼
Normalise each to 0–100   →   Weighted average (0.5 / 0.5)
      │
      ▼
Composite Score   →   Quality Grade (Good / Mild / Moderate / Severe)
      │
      ▼
Compare to threshold   →   Accept or Reject
      │
      ▼
Store record   →   Return JSON to UI
```

### Calibrated constants
| Constant         | Value |
|------------------|-------|
| `MAX_LAPLACIAN`  | 500.0 |
| `MAX_TENENGRAD`  | 80.0  |
| `THRESHOLD`      | 50.0 (configurable from Admin Dashboard) |
| Processing size  | 640 × 480 max, aspect ratio preserved |

### Grade scale
| Composite score | Grade    | Decision   |
|-----------------|----------|------------|
| 75 – 100        | Good     | Accepted   |
| 50 – 74.99      | Mild     | Accepted   |
| 25 – 49.99      | Moderate | Rejected   |
| 0 – 24.99       | Severe   | Rejected   |

---

## 4. Evaluation Methodology

The system is evaluated against a **fully synthetic, PII-free** dataset of
ID-card-style images with **mathematically defined blur levels**. No real
identity documents are used at any point — see [§ 6 Ethics](#6-ethics--data-handling)
below.

### Pipeline

```
generate_synthetic_ids.py        evaluate.py --generate            evaluate.py
─────────────────────────  ───►  ──────────────────────────  ───►  ───────────
25 clear synthetic IDs           4 Gaussian-blur variants per      Accuracy,
(3 templates, fixed seed)        source → 100 labelled images      F1, FAR,
                                                                   confusion
                                                                   matrix
```

### Blur generation parameters

| Folder      | Kernel    | σ    | Ground-truth label |
|-------------|-----------|------|--------------------|
| `good/`     | —         | —    | usable             |
| `mild/`     | (5, 5)    | 1.5  | usable             |
| `moderate/` | (15, 15)  | 4.0  | unusable           |
| `severe/`   | (31, 31)  | 10.0 | unusable           |

Because the blur is generated from known Gaussian kernels, the ground truth is
exact and the entire dataset is reproducible from a single random seed.

### Run the full evaluation

```bash
# 1. Generate 25 clear synthetic source IDs (deterministic, seed=42)
python generate_synthetic_ids.py --count 25 --out synthetic_sources

# 2. Apply the four blur kernels and run the evaluation
python evaluate.py --generate --source synthetic_sources
```

Outputs:
- `evaluation_results.txt` — human-readable report
- `evaluation_results.csv` — per-image scores for further analysis
- `evaluation_dataset/{good,mild,moderate,severe}/` — the labelled images

To re-evaluate an existing dataset without regenerating:
```bash
python evaluate.py
```

To sweep the acceptance threshold:
```bash
python evaluate.py --threshold 45
```

### Reproduced results (n = 100, seed = 42)

| Metric                | Value     |
|-----------------------|-----------|
| Accuracy              | **94.0 %** |
| Precision             | **100.0 %** |
| Recall                | **88.0 %** |
| F1-Score              | **93.62 %** |
| False Acceptance Rate | **0.0 %**  |
| Avg processing time   | 38 ms / image |

Confusion matrix: **TP = 44, FN = 6, FP = 0, TN = 50**.

All six errors occurred at the mild-blur boundary (scores 46.27 – 49.64),
just under the 50.0 acceptance threshold. The zero false-acceptance rate
demonstrates that no unusable image was wrongly admitted.

---

## 5. API Endpoints

| Method | Endpoint                | Description                              |
|--------|-------------------------|------------------------------------------|
| POST   | `/api/upload`           | Upload an image for blur analysis        |
| GET    | `/api/records`          | List all upload records                  |
| GET    | `/api/config/threshold` | Get current acceptance threshold         |
| PUT    | `/api/config/threshold` | Update acceptance threshold              |
| GET    | `/api/stats`            | Grade distribution and totals            |
| GET    | `/docs`                 | Interactive API documentation (Swagger)  |

---

## 6. Ethics & Data Handling

- The evaluation dataset is **100 % synthetic**. All names, dates, ID numbers,
  faces, and document layouts are procedurally generated from random data.
  No real identity document is used or stored at any point in the research.
- The backend's SQLite database (`backend/blur_system.db`) is created at
  runtime, used only for demo uploads, and is excluded from version control.
- Any image you upload through the demo UI is stored locally only and never
  transmitted off your machine.

---

## 7. Repository Layout

```
blur-system/
├── backend/                       # FastAPI service
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                      # React + Vite UI
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── evaluate.py                    # Evaluation harness + synthetic blur generator
├── generate_synthetic_ids.py      # Procedural synthetic ID-card generator (PII-free)
├── evaluation_dataset/            # Created at evaluation time (gitignored)
├── evaluation_results.txt         # Latest evaluation report
├── evaluation_results.csv         # Per-image results
├── docker-compose.yml
├── LICENSE
└── README.md
```

---

## 8. Tech Stack

- **Backend:** FastAPI, OpenCV (headless), NumPy, Pillow, SQLAlchemy
- **Frontend:** React, Vite
- **Database:** SQLite (default) — PostgreSQL supported via `DATABASE_URL`
- **Containerisation:** Docker, docker-compose

---

## License

[MIT](LICENSE)
