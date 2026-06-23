# config.py

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
    "MP4 Video (*.mp4)": {
        "header": b"ftyp",
        "footer": None,
        "ext": ".mp4",
        "category": "Videolar"
    },
    "MP3 Ses Dosyası (*.mp3)": {
        "header": b"ID3",
        "footer": None,
        "ext": ".mp3",
        "category": "Ses"
    }
}
