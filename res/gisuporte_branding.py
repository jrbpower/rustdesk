#!/usr/bin/env python3
from pathlib import Path
import io
import re

APP_NAME = "GISuporte"
SERVER = "gisuporte.vps-kinghost.net"
KEY = "aUbDo6Map3oFCVpb9VB66sNTbuvz3bX3iCoKVBGVUe4="
SUPPORT_URL = "https://github.com/jrbpower/GI-SUPORTE-REMOTO"


def configure_server() -> None:
    """Make Flutter initialize the GISuporte identity before async/config access.

    Server/key defaults themselves live in src/lib.rs.  Keeping them there avoids
    a second, divergent runtime configuration path in flutter_ffi.rs.
    """
    path = Path("src/flutter_ffi.rs")
    text = path.read_text(encoding="utf-8")

    old_start = """fn initialize(app_dir: &str, custom_client_config: &str) {
    flutter::async_tasks::start_flutter_async_runner();
"""
    new_start = """fn initialize(app_dir: &str, custom_client_config: &str) {
    // GISuporte: establish APP_NAME/server defaults before any Flutter async task
    // can lazily initialize hbb_common configuration as RustDesk.
    crate::load_custom_client();
    if !custom_client_config.is_empty() {
        crate::read_custom_client(custom_client_config);
    }
    flutter::async_tasks::start_flutter_async_runner();
"""

    old_custom_block = """    // core_main's load_custom_client does not work for flutter since it is only applied to its load_library in main.c
    if custom_client_config.is_empty() {
        crate::load_custom_client();
    } else {
        crate::read_custom_client(custom_client_config);
    }
"""

    if new_start not in text:
        if old_start not in text:
            raise RuntimeError("RustDesk Flutter initialize() start block was not found")
        text = text.replace(old_start, new_start, 1)

    if old_custom_block in text:
        text = text.replace(old_custom_block, "", 1)

    path.write_text(text, encoding="utf-8")
    print(f"GISuporte runtime defaults use {SERVER}; Flutter initialization order fixed")


def brand_flutter_ui() -> None:
    root = Path("flutter/lib")
    changed = 0
    url_re = re.compile(r"https?://(?:www\.)?rustdesk\.com[^\s'\"\)<>]*", re.IGNORECASE)
    bare_site_re = re.compile(r"(?<!@)\b(?:www\.)?rustdesk\.com\b", re.IGNORECASE)

    for path in root.rglob("*.dart"):
        text = path.read_text(encoding="utf-8")
        branded = text.replace("RustDesk", APP_NAME)
        branded = url_re.sub(SUPPORT_URL, branded)
        branded = bare_site_re.sub("GISuporte", branded)
        if branded != text:
            path.write_text(branded, encoding="utf-8")
            changed += 1
    print(f"GISuporte branding/links applied to {changed} Flutter UI files")


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

    # Flutter in-app icon.
    flutter_icon = Path("flutter/assets/icon.png")
    flutter_icon.parent.mkdir(parents=True, exist_ok=True)
    square.resize((512, 512), Image.Resampling.LANCZOS).save(
        flutter_icon, "PNG", optimize=True
    )

    # Android legacy, round and adaptive foreground resources.
    android_sizes = {
        "mipmap-mdpi": (48, 108),
        "mipmap-hdpi": (72, 162),
        "mipmap-xhdpi": (96, 216),
        "mipmap-xxhdpi": (144, 324),
        "mipmap-xxxhdpi": (192, 432),
    }
    base = Path("flutter/android/app/src/main/res")
    for density, (legacy_size, foreground_size) in android_sizes.items():
        folder = base / density
        folder.mkdir(parents=True, exist_ok=True)

        legacy = square.resize((legacy_size, legacy_size), Image.Resampling.LANCZOS)
        legacy.save(folder / "ic_launcher.png", "PNG", optimize=True)
        legacy.save(folder / "ic_launcher_round.png", "PNG", optimize=True)

        foreground = Image.new("RGBA", (foreground_size, foreground_size), (0, 0, 0, 0))
        logo_size = int(foreground_size * 0.66)
        logo = square.resize((logo_size, logo_size), Image.Resampling.LANCZOS).convert("RGBA")
        offset = (foreground_size - logo_size) // 2
        foreground.alpha_composite(logo, (offset, offset))
        foreground.save(folder / "ic_launcher_foreground.png", "PNG", optimize=True)

    # Windows must use the exact approved GISuporteV2 .ico already committed to
    # res/icon.ico; do not regenerate a different ICO from the JPEG.
    approved_ico = Path("res/icon.ico")
    if not approved_ico.exists():
        raise RuntimeError("Approved GISuporte Windows icon is missing: res/icon.ico")
    runner_ico = Path("flutter/windows/runner/resources/app_icon.ico")
    runner_ico.parent.mkdir(parents=True, exist_ok=True)
    runner_ico.write_bytes(approved_ico.read_bytes())
    print("GISuporte Flutter/Android icons generated; approved V2 Windows ICO preserved")


def validate_branding() -> None:
    lib = Path("src/lib.rs").read_text(encoding="utf-8")
    ffi = Path("src/flutter_ffi.rs").read_text(encoding="utf-8")

    required_lib = [
        f'const GISUPORTE_APP_NAME: &str = "{APP_NAME}"',
        f'const GISUPORTE_RENDEZVOUS_SERVER: &str = "{SERVER}"',
        f'const GISUPORTE_RS_PUB_KEY: &str = "{KEY}"',
        '*hbb_common::config::APP_NAME.write().unwrap() = GISUPORTE_APP_NAME.to_owned()',
    ]
    missing = [item for item in required_lib if item not in lib]
    if missing:
        raise RuntimeError(f"GISuporte runtime validation failed; missing in src/lib.rs: {missing}")

    load_pos = ffi.find("crate::load_custom_client();")
    async_pos = ffi.find("flutter::async_tasks::start_flutter_async_runner();")
    if load_pos < 0 or async_pos < 0 or load_pos > async_pos:
        raise RuntimeError(
            "GISuporte validation failed: load_custom_client() must run before Flutter async runner"
        )
    if "EXE_RENDEZVOUS_SERVER.write().unwrap()" in ffi:
        raise RuntimeError("GISuporte validation failed: legacy Flutter server override is still active")

    icon = Path("flutter/assets/icon.png")
    if not icon.exists() or not icon.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("GISuporte validation failed: Flutter in-app icon was not generated")

    approved_ico = Path("res/icon.ico").read_bytes()
    runner_ico = Path("flutter/windows/runner/resources/app_icon.ico").read_bytes()
    if approved_ico != runner_ico:
        raise RuntimeError("GISuporte validation failed: Windows icon differs from approved GISuporteV2 ICO")

    android_base = Path("flutter/android/app/src/main/res")
    for density in [
        "mipmap-mdpi",
        "mipmap-hdpi",
        "mipmap-xhdpi",
        "mipmap-xxhdpi",
        "mipmap-xxxhdpi",
    ]:
        for name in ["ic_launcher.png", "ic_launcher_round.png", "ic_launcher_foreground.png"]:
            candidate = android_base / density / name
            if not candidate.exists() or not candidate.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
                raise RuntimeError(
                    f"GISuporte validation failed: Android launcher resource missing/invalid: {candidate}"
                )

    adaptive_xml = (android_base / "mipmap-anydpi-v26" / "ic_launcher.xml").read_text(encoding="utf-8")
    if '@mipmap/ic_launcher_foreground' not in adaptive_xml:
        raise RuntimeError("GISuporte validation failed: Android adaptive icon foreground is not configured")

    remaining_sites = []
    for path in Path("flutter/lib").rglob("*.dart"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"(?<!@)\b(?:www\.)?rustdesk\.com\b", text, re.IGNORECASE):
            remaining_sites.append(str(path))
    if remaining_sites:
        raise RuntimeError(
            "GISuporte validation failed: visible rustdesk.com references remain in: "
            + ", ".join(remaining_sites[:20])
        )

    print("GISUPORTE_VALIDATION_OK")
    print(f"GISuporte server fixed to {SERVER}; approved Windows icon and initialization order validated")


def main() -> None:
    configure_server()
    brand_platform_metadata()
    brand_flutter_ui()
    brand_translations()
    generate_icons()
    validate_branding()


if __name__ == "__main__":
    main()
