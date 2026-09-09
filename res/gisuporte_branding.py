#!/usr/bin/env python3
from pathlib import Path
import io
import re

APP_NAME = "GISuporte"
SERVER = "191.252.210.203"
KEY = "aUbDo6Map3oFCVpb9VB66sNTbuvz3bX3iCoKVBGVUe4="
SUPPORT_URL = "https://github.com/jrbpower/GI-SUPORTE-REMOTO"


def configure_server() -> None:
    path = Path("src/flutter_ffi.rs")
    text = path.read_text(encoding="utf-8")

    old = """    if custom_client_config.is_empty() {
        crate::load_custom_client();
    } else {
        crate::read_custom_client(custom_client_config);
    }
"""
    new = f"""    // GISuporte: force the self-hosted infrastructure on every startup.
    // RustDesk 1.4.9 read_custom_client() expects an encoded/signed payload, so
    // a plain host=...,key=...,relay=... string is intentionally not used here.
    *config::EXE_RENDEZVOUS_SERVER.write().unwrap() = "{SERVER}".to_owned();
    {{
        let mut settings = config::OVERWRITE_SETTINGS.write().unwrap();
        settings.insert("custom-rendezvous-server".to_owned(), "{SERVER}".to_owned());
        settings.insert("relay-server".to_owned(), "{SERVER}".to_owned());
        settings.insert("key".to_owned(), "{KEY}".to_owned());
    }}
"""
    if new not in text:
        if old not in text:
            raise RuntimeError("RustDesk Flutter custom-client initialization block was not found")
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

    # Flutter's loadIcon() looks for assets/icon.png first and only falls back
    # to assets/icon.svg (the upstream RustDesk logo) when the PNG is missing.
    flutter_icon = Path("flutter/assets/icon.png")
    flutter_icon.parent.mkdir(parents=True, exist_ok=True)
    square.resize((512, 512), Image.Resampling.LANCZOS).save(
        flutter_icon, "PNG", optimize=True
    )

    # Android 8+ resolves @mipmap/ic_launcher to the adaptive icon XML in
    # mipmap-anydpi-v26. That XML uses ic_launcher_foreground, so replacing
    # only ic_launcher.png leaves the RustDesk launcher icon visible.
    # Generate legacy, round and adaptive-foreground resources for every density.
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

        legacy = square.resize(
            (legacy_size, legacy_size), Image.Resampling.LANCZOS
        )
        legacy.save(folder / "ic_launcher.png", "PNG", optimize=True)
        legacy.save(folder / "ic_launcher_round.png", "PNG", optimize=True)

        # Adaptive foreground canvas is 108dp. Keep the actual logo inside the
        # central safe area so Android launcher masks do not crop it.
        foreground = Image.new("RGBA", (foreground_size, foreground_size), (0, 0, 0, 0))
        logo_size = int(foreground_size * 0.66)
        logo = square.resize((logo_size, logo_size), Image.Resampling.LANCZOS).convert("RGBA")
        offset = (foreground_size - logo_size) // 2
        foreground.alpha_composite(logo, (offset, offset))
        foreground.save(folder / "ic_launcher_foreground.png", "PNG", optimize=True)

    ico = Path("flutter/windows/runner/resources/app_icon.ico")
    ico.parent.mkdir(parents=True, exist_ok=True)
    square.save(
        ico,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("GISuporte Flutter, Android legacy/adaptive and Windows icons generated")


def validate_branding() -> None:
    ffi = Path("src/flutter_ffi.rs").read_text(encoding="utf-8")

    required = [
        f'EXE_RENDEZVOUS_SERVER.write().unwrap() = "{SERVER}"',
        f'"custom-rendezvous-server".to_owned(), "{SERVER}".to_owned()',
        f'"relay-server".to_owned(), "{SERVER}".to_owned()',
        f'"key".to_owned(), "{KEY}".to_owned()',
        f'APP_NAME.write().unwrap() = "{APP_NAME}"',
    ]
    missing = [item for item in required if item not in ffi]
    if missing:
        raise RuntimeError(f"GISuporte server/branding validation failed; missing: {missing}")
    if "crate::load_custom_client();" in ffi or "crate::read_custom_client(custom_client_config);" in ffi:
        raise RuntimeError("GISuporte validation failed: upstream custom-client fallback is still active")

    icon = Path("flutter/assets/icon.png")
    if not icon.exists() or not icon.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("GISuporte validation failed: Flutter in-app icon was not generated")

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

    adaptive_xml = (
        android_base / "mipmap-anydpi-v26" / "ic_launcher.xml"
    ).read_text(encoding="utf-8")
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
    print(f"GISuporte server fixed to {SERVER}; relay={SERVER}; launcher/in-app icons and links validated")


def main() -> None:
    configure_server()
    brand_platform_metadata()
    brand_flutter_ui()
    brand_translations()
    generate_icons()
    validate_branding()


if __name__ == "__main__":
    main()
