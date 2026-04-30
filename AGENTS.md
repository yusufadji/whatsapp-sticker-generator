# AI Agent Operating Rules for WhatsApp Sticker Generator (Python)

## 1. Strict Type Safety & Python Standards
- **PEP 8 Compliance:** Strictly adhere to PEP 8 style guidelines for all Python code.
- **Type Hinting:** All functions, methods, and variables MUST use Python type hints (e.g., `def process_image(file_path: str) -> bool:`). Do not leave function signatures untyped.
- **Virtual Environment:** Assume all code runs within a virtual environment. Do not suggest global `pip` installs. Always update `requirements.txt` if a new dependency is added.

## 2. Architecture & Modularity
- **Entry Point Only:** Keep `main.py` as clean as possible. It should only act as the main entry point (using `if __name__ == "__main__":`).
- **Separation of Concerns:** Extract heavy logic into separate modules inside a `/src/` or `/utils/` directory:
  - Media processing (resizing, padding).
  - Format conversion (WebP encoding).
  - EXIF metadata injection.

## 3. Media Processing Constraints (Sticker Specs)
- **Dimensions:** WhatsApp requires stickers to be exactly 512x512 pixels. Ensure images are resized/padded proportionally without distortion.
- **Format:** Output MUST always be in `.webp` format.
- **File Size Constraint:** Aim to keep generated `.webp` files under 100KB (for static) and 500KB (for animated).
- **Error Handling:** Media processing is prone to corrupted files. ALWAYS wrap file I/O, PIL, or FFmpeg operations in strict `try-except` blocks to prevent the main script from crashing.

## 4. Inline Code Documentation (Strictly Indonesian)
- **Docstrings:** Use standard Python docstrings (`""" """`) for all classes and functions to explain parameters and return values.
- **Inline Comments:** You MUST add brief, clear inline comments to explain important logic or data flows.
- **Language Constraint:** All comments and docstrings MUST be written in Indonesian (Bahasa Indonesia).
- **Format Constraint:** Use short, straightforward, and professional sentences. STRICTLY NO EMOJIS.