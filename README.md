# UK VRM Synthetic Dataset Generator

A reproducible Python pipeline for generating clean UK-style vehicle registration plate (VRM) images and paired degraded images for ANPR/computer-vision experimentation.

## Assessment mapping

- **Task 1:** random current-style UK VRM strings (`AA00 AAA` layout), white/yellow plate variants, tracked character rendering, spacing variation.
- **Task 2:** motion blur, defocus blur, dirt/mud overlays, sensor noise, scratches/wear, and optional low-light variation.
- **Deliverables:** clean/degraded image pairs, CSV manifest, source code, and this technical walkthrough.

## Important accuracy note

The generator creates **format-compliant UK-style VRMs**, not a list of confirmed DVLA-issued registrations. It does not query DVLA allocation records or implement every historical, diplomatic, military, Northern Ireland, or dateless registration scheme. Do not represent generated strings as real vehicle identities.

For typographic fidelity, supply a properly licensed **Charles Wright** font file using `--font`. The bundled fallback is DejaVu Sans Condensed Bold and is for demonstration only; it is not a claim of legal font compliance. Confirm exact plate dimensions, spacing, and font requirements against the applicable UK regulations and the employer's source dataset.

## Setup

Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## Generate the assessment dataset

```bash
python src/generate_dataset.py --count 100 --output dataset --seed 42
```

For a larger experiment:

```bash
python src/generate_dataset.py --count 1000 --output dataset --seed 42
```

## Output structure

```text
dataset/
  clean/
    plate_00001.png
    ...
  degraded/
    plate_00001.png
    ...
  manifest.csv
```

Each clean image has a degraded counterpart with the same filename. `manifest.csv` stores the VRM, background, image paths, spacing scale, degradation operations, and seed.

## Pipeline walkthrough

1. **VRM generation:** two permitted area-code letters + a two-digit age identifier + three permitted suffix letters. Characters excluded from the modern format include I and Q; Z is excluded from the area-code letters. The age identifier is generated from 01–99.
2. **Plate rendering:** creates a 1040 × 222 pixel canvas (520:111 proportion), white/yellow reflective-style background, dark border, centered text, controlled character/group spacing, and mounting details.
3. **Paired degradation:** applies all five required degradation families to each clean image. Strengths and operation order vary with a seeded random generator.
4. **Dataset and metadata:** saves paired PNGs and a CSV manifest to make the dataset traceable and reproducible.

## Quality checks recommended before submission

- Confirm exactly N clean files and N degraded files exist.
- Confirm every clean image has one same-named degraded counterpart.
- Verify both background colours occur and the manifest has no duplicate VRMs.
- Visually inspect a random sample and ensure degradation does not make every plate unreadable.
- Use a Charles Wright font supplied/licensed for the assessment if available.
- Compare generated plate dimensions, character height, stroke width, margins, and spacing against the source dataset and applicable UK standards.
- Keep a fixed seed for reproducibility; use different seeds for additional dataset diversity.

## Potential improvements

- Calibrate layout from measured source images instead of relying on approximate dimensions.
- Add perspective transforms, glare/reflections, rain, compression artifacts, shadows, and camera exposure variation.
- Use segmentation masks to keep mud and scratches spatially realistic.
- Add train/validation/test splits by VRM identity to reduce leakage.
- Store per-image parameters in JSON/Parquet for richer experiment tracking.
- Evaluate downstream ANPR OCR accuracy on clean vs degraded subsets.
