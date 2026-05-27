from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import cv2
import numpy as np
from PIL import Image
import io
import os

# ── Database setup ──────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./blur_system.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ImageUpload(Base):
    __tablename__ = "image_uploads"
    id            = Column(Integer, primary_key=True, index=True)
    file_name     = Column(String(255))
    file_format   = Column(String(10))
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    laplacian_score  = Column(Float)
    tenengrad_score  = Column(Float)
    composite_score  = Column(Float)
    grade            = Column(String(20))
    decision         = Column(String(10))

class SystemConfig(Base):
    __tablename__ = "system_config"
    id           = Column(Integer, primary_key=True, index=True)
    config_key   = Column(String(100), unique=True)
    config_value = Column(String(255))
    updated_at   = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Seed default threshold
def seed_db():
    db = SessionLocal()
    existing = db.query(SystemConfig).filter_by(config_key="blur_threshold").first()
    if not existing:
        db.add(SystemConfig(config_key="blur_threshold", config_value="50.0"))
        db.commit()
    db.close()

seed_db()

# ── FastAPI app ─────────────────────────────────────────────────────────────
app = FastAPI(title="Blur Detection System API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Blur detection logic ────────────────────────────────────────────────────
MAX_LAPLACIAN  = 500.0
MAX_TENENGRAD  = 80.0
MAX_PROCESSING_WIDTH = 640
MAX_PROCESSING_HEIGHT = 480

def preprocess(image_bytes: bytes) -> tuple[np.ndarray, dict]:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_array = np.array(img)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    resized = False

    if w > MAX_PROCESSING_WIDTH or h > MAX_PROCESSING_HEIGHT:
        scale = min(MAX_PROCESSING_WIDTH / w, MAX_PROCESSING_HEIGHT / h)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
        resized = True

    ph, pw = gray.shape
    return gray, {
        "original_width": w,
        "original_height": h,
        "processed_width": pw,
        "processed_height": ph,
        "resized": resized,
        "aspect_ratio_preserved": True,
    }

def compute_laplacian(gray: np.ndarray) -> float:
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return float(lap.var())

def compute_tenengrad(gray: np.ndarray) -> float:
    sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(sx**2 + sy**2)
    return float(mag.mean())

def compute_composite(lap: float, ten: float) -> float:
    norm_lap = min(lap / MAX_LAPLACIAN, 1.0) * 100
    norm_ten = min(ten / MAX_TENENGRAD, 1.0) * 100
    return round((0.5 * norm_lap) + (0.5 * norm_ten), 2)

def build_process_log(file: UploadFile, size_bytes: int, meta: dict, lap: float, ten: float, score: float, grade: str, threshold: float, decision: str) -> list[str]:
    norm_lap = min(lap / MAX_LAPLACIAN, 1.0) * 100
    norm_ten = min(ten / MAX_TENENGRAD, 1.0) * 100
    resize_text = (
        f"resized to {meta['processed_width']}x{meta['processed_height']} with aspect ratio preserved"
        if meta["resized"]
        else "kept at original size"
    )
    return [
        f"Received {file.filename} ({file.content_type}, {round(size_bytes / 1024, 1)} KB).",
        "Validated file type and confirmed the file is below the 10 MB limit.",
        "Decoded image, converted it to RGB, then converted it to grayscale for edge analysis.",
        f"Original image size: {meta['original_width']}x{meta['original_height']}; processed image size: {meta['processed_width']}x{meta['processed_height']} ({resize_text}).",
        f"Laplacian variance: {round(lap, 4)}. Normalized contribution: {round(norm_lap, 2)}/100 using max {MAX_LAPLACIAN}.",
        f"Tenengrad gradient mean: {round(ten, 4)}. Normalized contribution: {round(norm_ten, 2)}/100 using max {MAX_TENENGRAD}.",
        f"Composite score = (0.5 x {round(norm_lap, 2)}) + (0.5 x {round(norm_ten, 2)}) = {score}/100.",
        f"Grade assigned: {grade}. Threshold used: {threshold}/100.",
        f"Final decision: {decision.upper()} because {score} {'>=' if score >= threshold else '<'} {threshold}.",
    ]

def assign_grade(score: float) -> str:
    if score >= 75:  return "Good"
    if score >= 50:  return "Mild"
    if score >= 25:  return "Moderate"
    return "Severe"

def get_threshold(db: Session) -> float:
    cfg = db.query(SystemConfig).filter_by(config_key="blur_threshold").first()
    return float(cfg.config_value) if cfg else 50.0

# ── Routes ──────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "Blur Detection System API", "status": "running"}

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Validate format
    allowed = {"image/jpeg", "image/jpg", "image/png"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG files are accepted.")

    contents = await file.read()

    # Validate size (10MB)
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds the 10MB limit.")

    try:
        gray, image_meta = preprocess(contents)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not process the uploaded image.")

    lap   = compute_laplacian(gray)
    ten   = compute_tenengrad(gray)
    score = compute_composite(lap, ten)
    grade = assign_grade(score)
    threshold = get_threshold(db)
    decision  = "accepted" if score >= threshold else "rejected"
    process_log = build_process_log(file, len(contents), image_meta, lap, ten, score, grade, threshold, decision)

    print(f"[blur-analysis] {file.filename} -> score={score}, grade={grade}, threshold={threshold}, decision={decision}")
    for step in process_log:
        print(f"[blur-analysis] {step}")

    ext = file.filename.rsplit(".", 1)[-1].upper() if "." in file.filename else "UNKNOWN"

    record = ImageUpload(
        file_name        = file.filename,
        file_format      = ext,
        laplacian_score  = round(lap, 4),
        tenengrad_score  = round(ten, 4),
        composite_score  = score,
        grade            = grade,
        decision         = decision,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id":              record.id,
        "file_name":       record.file_name,
        "laplacian_score": record.laplacian_score,
        "tenengrad_score": record.tenengrad_score,
        "composite_score": record.composite_score,
        "grade":           record.grade,
        "decision":        record.decision,
        "threshold_used":  threshold,
        "process_log":     process_log,
        "timestamp":       record.upload_timestamp.isoformat(),
        "message": (
            "Image accepted. The document is sufficiently clear for verification."
            if decision == "accepted"
            else "Image rejected. The document image is too blurry. Please ensure adequate lighting, hold the device steady, and confirm the document is in focus before re-uploading."
        )
    }

@app.get("/api/records")
def get_records(db: Session = Depends(get_db)):
    records = db.query(ImageUpload).order_by(ImageUpload.upload_timestamp.desc()).all()
    return [
        {
            "id":              r.id,
            "file_name":       r.file_name,
            "file_format":     r.file_format,
            "composite_score": r.composite_score,
            "grade":           r.grade,
            "decision":        r.decision,
            "timestamp":       r.upload_timestamp.isoformat() if r.upload_timestamp else None,
        }
        for r in records
    ]

@app.get("/api/config/threshold")
def get_threshold_endpoint(db: Session = Depends(get_db)):
    return {"threshold": get_threshold(db)}

@app.put("/api/config/threshold")
def update_threshold(payload: dict, db: Session = Depends(get_db)):
    value = payload.get("threshold")
    if value is None or not (0 <= float(value) <= 100):
        raise HTTPException(status_code=400, detail="Threshold must be between 0 and 100.")
    cfg = db.query(SystemConfig).filter_by(config_key="blur_threshold").first()
    if cfg:
        cfg.config_value = str(float(value))
        cfg.updated_at   = datetime.utcnow()
    else:
        db.add(SystemConfig(config_key="blur_threshold", config_value=str(float(value))))
    db.commit()
    return {"message": "Threshold updated.", "threshold": float(value)}

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    records = db.query(ImageUpload).all()
    total     = len(records)
    accepted  = sum(1 for r in records if r.decision == "accepted")
    rejected  = total - accepted
    grade_counts = {"Good": 0, "Mild": 0, "Moderate": 0, "Severe": 0}
    for r in records:
        if r.grade in grade_counts:
            grade_counts[r.grade] += 1
    avg_score = round(sum(r.composite_score for r in records) / total, 2) if total else 0
    return {
        "total": total,
        "accepted": accepted,
        "rejected": rejected,
        "avg_score": avg_score,
        "grade_distribution": grade_counts,
    }
