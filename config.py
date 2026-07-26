# config.py

# Project Metadata Configuration
APP_NAME = "NovaRecovery"
APP_VERSION = "2.1.0"
APP_DESCRIPTION = "Profesyonel Veri Kurtarma ve File Carver Yazılımı"
MIN_FILE_SIZE_BYTES = 100 * 1024  # 100 KB minimum size threshold to filter junk content

# Dark Theme Colors matching Disk Drill style
BG_DARK = "#1E1E24"
SIDEBAR_BG = "#F1F2F6"
CONTENT_BG = "#FFFFFF"
TEXT_DARK = "#2F3542"
TEXT_GRAY = "#747D8C"
ACCENT_BLUE = "#0084FF"
TEXT_WHITE = "#FFFFFF"

# Categories styling
CATEGORIES = {
    "Resim": {"color": "#0984E3", "icon": "📷"},
    "Videolar": {"color": "#E17055", "icon": "🎬"},
    "Ses": {"color": "#00CEC9", "icon": "🎵"},
    "Belge": {"color": "#D63031", "icon": "📄"},
    "Arşiv": {"color": "#6C5CE7", "icon": "📦"},
    "Diğer": {"color": "#636E72", "icon": "⚙️"}
}

# Supported file types and their signatures
# No artificial max_size limits for file carving
FILE_SIGNATURES = {
    "JPEG Görsel (*.jpg, *.jpeg)": {
        "header": b"\xff\xd8\xff",
        "footer": b"\xff\xd9",
        "ext": ".jpg",
        "category": "Resim"
    },
    "PNG Görsel (*.png)": {
        "header": b"\x89PNG\r\n\x1a\n",
        "footer": b"\x49\x45\x4e\x44\xae\x42\x60\x82",
        "ext": ".png",
        "category": "Resim"
    },
    "GIF Görsel (*.gif)": {
        "header": b"GIF8",
        "footer": b"\x3b",
        "ext": ".gif",
        "category": "Resim"
    },
    "BMP Görsel (*.bmp)": {
        "header": b"BM",
        "footer": None,
        "ext": ".bmp",
        "category": "Resim"
    },
    "WebP Görsel (*.webp)": {
        "header": b"RIFF",
        "footer": None,
        "ext": ".webp",
        "category": "Resim"
    },
    "TIFF Görsel (Intel) (*.tiff)": {
        "header": b"II*\x00",
        "footer": None,
        "ext": ".tiff",
        "category": "Resim"
    },
    "TIFF Görsel (Motorola) (*.tiff)": {
        "header": b"MM\x00*",
        "footer": None,
        "ext": ".tiff",
        "category": "Resim"
    },
    "PDF Belgesi (*.pdf)": {
        "header": b"%PDF-",
        "footer": b"%%EOF",
        "ext": ".pdf",
        "category": "Belge"
    },
    "ZIP Arşivi (*.zip)": {
        "header": b"PK\x03\x04",
        "footer": None,
        "ext": ".zip",
        "category": "Arşiv"
    },
    "RAR Arşivi (*.rar)": {
        "header": b"Rar!\x1a\x07\x00",
        "footer": None,
        "ext": ".rar",
        "category": "Arşiv"
    },
    "7Z Arşivi (*.7z)": {
        "header": b"7z\xbc\xaf\x27\x1c",
        "footer": None,
        "ext": ".7z",
        "category": "Arşiv"
    },
    "MP4 Video (*.mp4)": {
        "header": b"ftyp",
        "footer": None,
        "ext": ".mp4",
        "category": "Videolar"
    },
    "MKV Video (*.mkv)": {
        "header": b"\x1a\x45\xdf\xa3",
        "footer": None,
        "ext": ".mkv",
        "category": "Videolar"
    },
    "AVI Video (*.avi)": {
        "header": b"RIFF",
        "footer": None,
        "ext": ".avi",
        "category": "Videolar"
    },
    "MOV Video (*.mov)": {
        "header": b"ftyp",
        "footer": None,
        "ext": ".mov",
        "category": "Videolar"
    },
    "WebM Video (*.webm)": {
        "header": b"\x1a\x45\xdf\xa3",
        "footer": None,
        "ext": ".webm",
        "category": "Videolar"
    },
    "MP3 Ses Dosyası (*.mp3)": {
        "header": b"ID3",
        "footer": None,
        "ext": ".mp3",
        "category": "Ses"
    },
    "WAV Ses Dosyası (*.wav)": {
        "header": b"RIFF",
        "footer": None,
        "ext": ".wav",
        "category": "Ses"
    },
    "FLAC Ses Dosyası (*.flac)": {
        "header": b"fLaC",
        "footer": None,
        "ext": ".flac",
        "category": "Ses"
    },
    "M4A Ses Dosyası (*.m4a)": {
        "header": b"ftyp",
        "footer": None,
        "ext": ".m4a",
        "category": "Ses"
    }
}

