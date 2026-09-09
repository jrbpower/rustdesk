#!/usr/bin/env python3
from pathlib import Path
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
    text = path.read_text(encoding="utf-8")

    old = """    if custom_client_config.is_empty() {
        crate::load_custom_client();
    } else {
        crate::read_custom_client(custom_client_config);
    }
"""
    new = f"""    // GISuporte: fixed self-hosted server configuration.
    // Internal RustDesk protocol/package identifiers are kept for compatibility.
    crate::read_custom_client("{CUSTOM_CONFIG}");
"""
    if new not in text:
        if old not in text:
            raise RuntimeError("RustDesk custom client configuration block was not found")
        text = text.replace(old, new, 1)

    app_name_line = f'    *config::APP_NAME.write().unwrap() = "{APP_NAME}".to_owned();\n'
    if app_name_line not in text:
        marker = "    // core_main's load_custom_client does not work for flutter since it is only applied to its load_library in main.c\n"
        if marker not in text:
            raise RuntimeError("RustDesk Flutter initialization marker was not found")
        text = text.replace(marker, app_name_line + marker, 1)

    path.write_text(text, encoding="utf-8")


def brand_flutter_ui() -> None:
    root = Path("flutter/lib")
    changed = 0
    for path in root.rglob("*.dart"):
        text = path.read_text(encoding="utf-8")
        if "RustDesk" in text:
            path.write_text(text.replace("RustDesk", APP_NAME), encoding="utf-8")
            changed += 1
    print(f"GISuporte branding applied to {changed} Flutter UI files")


def brand_translations() -> None:
    # Translation keys are API identifiers and must stay unchanged. Only the
    # displayed value (the part after the first tuple comma) is rebranded.
    changed_files = 0
    changed_lines = 0
    for path in Path("src/lang").rglob("*.rs"):
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        dirty = False
        for i, line in enumerate(lines):
            if "RustDesk" not in line or "," not in line:
                continue
            before, after = line.split(",", 1)
            if "RustDesk" in after:
                lines[i] = before + "," + after.replace("RustDesk", APP_NAME)
                dirty = True
                changed_lines += 1
        if dirty:
            path.write_text("".join(lines), encoding="utf-8")
            changed_files += 1
    print(f"GISuporte translations: {changed_lines} visible strings in {changed_files} files")


def brand_platform_metadata() -> None:
    manifest = Path("flutter/android/app/src/main/AndroidManifest.xml")
    text = manifest.read_text(encoding="utf-8")
    text = text.replace('android:label="RustDesk"', f'android:label="{APP_NAME}"')
    text = text.replace('android:label="RustDesk Input"', f'android:label="{APP_NAME} Input"')
    manifest.write_text(text, encoding="utf-8")

    strings = Path("flutter/android/app/src/main/res/values/strings.xml")
    text = strings.read_text(encoding="utf-8").replace("RustDesk", APP_NAME)
    strings.write_text(text, encoding="utf-8")

    runner = Path("flutter/windows/runner/Runner.rc")
    text = runner.read_text(encoding="utf-8")
    replacements = {
        'VALUE "CompanyName", "Purslane Tech Pte. Ltd." "\\0"': 'VALUE "CompanyName", "GISuporte" "\\0"',
        'VALUE "FileDescription", "RustDesk Remote Desktop" "\\0"': 'VALUE "FileDescription", "GISuporte - Suporte Remoto" "\\0"',
        'VALUE "LegalCopyright", "Copyright © 2026 Purslane Tech Pte. Ltd. All rights reserved." "\\0"': 'VALUE "LegalCopyright", "GISuporte" "\\0"',
        'VALUE "ProductName", "RustDesk" "\\0"': 'VALUE "ProductName", "GISuporte" "\\0"',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    runner.write_text(text, encoding="utf-8")
    print("GISuporte Android/Windows metadata applied")


def load_logo_bytes() -> bytes:
    binary_path = Path("res/gisuporte_logo.jpg")
    if not binary_path.exists():
        raise RuntimeError("GISuporte logo asset is missing: res/gisuporte_logo.jpg")

    raw = binary_path.read_bytes()
    if len(raw) < 4 or raw[:3] != b"\xff\xd8\xff":
        raise RuntimeError("GISuporte logo asset is invalid: expected a JPEG image")
    return raw


def generate_icons() -> None:
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        raise RuntimeError("Pillow is required: python -m pip install pillow") from exc

    raw = load_logo_bytes()
    try:
        with Image.open(io.BytesIO(raw)) as source:
            source.verify()
        image = Image.open(io.BytesIO(raw)).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise RuntimeError("GISuporte logo asset is invalid or corrupted") from exc

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
    brand_platform_metadata()
    brand_flutter_ui()
    brand_translations()
    generate_icons()
    print(f"Configured {APP_NAME} ID/relay server: {SERVER}")


if __name__ == "__main__":
    main()
