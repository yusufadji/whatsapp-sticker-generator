# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-04-30

### Added
- **Batch Processing**: Feature to process an entire folder of videos automatically.
- **Adaptive Quality Search**: Implemented linear interpolation and ratio-based estimation to find the optimal quality closest to 500 KB in minimal iterations.
- **Automatic Cleanup**: Logic to delete oversized, failed, or cancelled output files to keep the output directory clean.
- **Detailed Progress Log**: UI console that displays real-time compression iterations, quality levels, and file sizes.
- **Precise Duration Detection**: Fast video duration analysis without full frame extraction for batch efficiency.

### Changed
- **Architectural Refactor**: Modularized codebase by moving core logic to the `src/` directory.
- **Adaptive Render Engine**: Updated the rendering core to support smart quality stepping (Extreme reduction for large files, fine-tuning for near-target files).
- **Quality Standards**: Increased max compression iterations to 40 and set default initial quality to 75.

### Fixed
- **PEP 8 Compliance**: Fixed violations regarding multiple statements on one line and bare except blocks.
- **Dependency Management**: Aligned `requirements.txt` with local environment and added missing `numpy` dependency.

## [1.1.0] - 2026-04-30
- Initial modularization and GUI separation.
- Integrated `tkinterdnd2` for drag-and-drop.
- Added timeline range selector and frame preview.

## [1.0.0] - 2026-04-30
- Initial release with basic FFmpeg integration.
