#!/usr/bin/env python3
from pathlib import Path
import base64
import io

APP_NAME = "GISuporte"
SERVER = "191.252.210.203"
KEY = "aUbDo6Map3oFCVpb9VB66sNTbuvz3bX3iCoKVBGVUe4="
CUSTOM_CONFIG = f"host={SERVER},key={KEY},relay={SERVER}"


def replace_required(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected text not found in {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def configure_server() -> None:
    path = Path("src/flutter_ffi.rs")
    old = '''    if custom_client_config.is_empty() {
        crate::load_custom_client();
    } else {
        crate::read_custom_client(custom_client_config);
    }
'''
    new = f'''    // GISuporte: fixed self-hosted server configuration.
    // Internal RustDesk protocol/package identifiers are kept for compatibility.
    crate::read_custom_client("{CUSTOM_CONFIG}");
'''
    replace_required(path, old, new)

    text = path.read_text(encoding="utf-8")
    marker = '    *config::APP_DIR.write().unwrap() = app_dir.to_owned();\n'
    app_name_line = f'    *config::APP_NAME.write().unwrap() = "{APP_NAME}".to_owned();\n'
    if app_name_line not in text:
        if marker not in text:
            raise RuntimeError("APP_DIR initialization marker not found")
        path.write_text(text.replace(marker, marker + app_name_line, 1), encoding="utf-8")


def brand_flutter_ui() -> None:
    root = Path("flutter/lib")
    changed = 0
    for path in root.rglob("*.dart"):
        text = path.read_text(encoding="utf-8")
        if "RustDesk" in text:
            path.write_text(text.replace("RustDesk", APP_NAME), encoding="utf-8")
            changed += 1
    print(f"GISuporte branding applied to {changed} Flutter UI files")


def generate_icons() -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required: python -m pip install pillow") from exc

    encoded = Path("res/gisuporte_logo.jpg.b64").read_text(encoding="utf-8").strip()
    image = Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")
    side = max(image.size)
    square = Image.new("RGB", (side, side), "black")
    square.paste(image, ((side - image.width) // 2, (side - image.height) // 2))

    android_sizes = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    base = Path("flutter/android/app/src/main/res")
    for density, size in android_sizes.items():
        target = base / density / "ic_launcher.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        square.resize((size, size), Image.Resampling.LANCZOS).save(target, "PNG", optimize=True)

    ico = Path("flutter/windows/runner/resources/app_icon.ico")
    ico.parent.mkdir(parents=True, exist_ok=True)
    square.save(
        ico,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("GISuporte Android and Windows icons generated")


def main() -> None:
    configure_server()
    brand_flutter_ui()
    generate_icons()
    print(f"Configured {APP_NAME} ID/relay server: {SERVER}")


if __name__ == "__main__":
    main()
