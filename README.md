# WhatsApp Sticker Generator (FFmpeg Pro)

![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.x-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-green.svg)
![FFmpeg](https://img.shields.io/badge/FFmpeg-Required-orange.svg)

## 🌟 Overview
**WhatsApp Sticker Generator** is a desktop application built with Python that allows you to easily create animated stickers for WhatsApp from any video file. It features a user-friendly GUI with drag-and-drop support, video trimming, and automatic compression to ensure your stickers meet WhatsApp's strict file size limits (< 500 KB).

## ✨ About the Project
This project simplifies the process of creating high-quality animated WebP stickers. Instead of manually using command-line tools, this app provides:
- **Drag & Drop**: Simply drop your video file into the app.
- **Video Preview & Trimming**: Choose exactly which part of the video you want to turn into a sticker using an interactive range slider.
- **Smart Compression**: The app automatically adjusts the quality iteratively until the file size is under 500 KB, preserving as much detail as possible.
- **Automated Workflow**: Uses OpenCV for frame extraction and FFmpeg for high-performance WebP encoding.

## ⚙️ Getting Started

Follow these instructions to set up the project on your local machine.

### Prerequisites
- **Python 3.x**: [Download Python](https://www.python.org/downloads/)
- **FFmpeg**: This tool is **required** for video processing.
  - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html), extract, and add the `bin` folder to your System PATH.
  - **Linux/macOS**: Use your package manager (e.g., `sudo apt install ffmpeg` or `brew install ffmpeg`).

### Installation
1. **Clone the repository**:
   ```sh
   git clone https://github.com/yusufadji/whatsapp-sticker-generator.git
   cd whatsapp-sticker-generator
   ```

2. **Set up a Virtual Environment** (Recommended):
   ```sh
   # Create virtual environment
   python -m venv venv

   # Activate virtual environment
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```sh
   pip install -r requirements.txt
   ```

## 📝 Usage
1. **Run the application**:
   ```sh
   python main.py
   ```
2. **Import Video**: Drag and drop a video file into the "Drag & Drop Video Di Sini" area.
3. **Select Range**: Use the green slider handles to select the start and end points of your sticker. You can preview the frames using the bottom slider.
4. **Set Initial Quality**: Enter a starting quality value (default is 75).
5. **Render**: Click **"Render Stiker WA"**. The app will process the video and automatically try to fit it under 500 KB.
6. **Output**: Once finished, click **"Buka Folder Output"** to see your new `.webp` sticker.

## 🤝 Contributing
Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## ⚖️ License
Distributed under the MIT License. See `LICENSE` for more information.

## 👤 Contact
[@yusufadji_asli](https://instagram.com/yusufadji_asli)

Project Link: [https://github.com/yusufadji/whatsapp-sticker-generator](https://github.com/yusufadji/whatsapp-sticker-generator)

