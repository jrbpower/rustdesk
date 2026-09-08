#!/usr/bin/env python3
from pathlib import Path

APP_NAME = "GISuporte"
SERVER = "191.252.210.203"
KEY = "aUbDo6Map3oFCVpb9VB66sNTbuvz3bX3iCoKVBGVUe4="
CUSTOM_CONFIG = f"host={SERVER},key={KEY}"


def replace_required(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected text not found in {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def configure_server() -> None:
    # Flutter desktop and Android both enter through initialize().
    # Force the custom-client configuration so the end user does not need
    # to configure ID/relay server or public key manually.
    path = Path("src/flutter_ffi.rs")
    old = '''    if custom_client_config.is_empty() {
        crate::load_custom_client();
    } else {
        crate::read_custom_client(custom_client_config);
    }
'''
    new = f'''    // GISuporte: fixed self-hosted server configuration.
    // Keep the internal RustDesk protocol/package identifiers for compatibility.
    crate::read_custom_client("{CUSTOM_CONFIG}");
'''
    replace_required(path, old, new)

    text = path.read_text(encoding="utf-8")
    marker = '    *config::APP_DIR.write().unwrap() = app_dir.to_owned();\n'
    app_name_line = f'    *config::APP_NAME.write().unwrap() = "{APP_NAME}".to_owned();\n'
    if app_name_line not in text:
        if marker not in text:
            raise RuntimeError("APP_DIR initialization marker not found")
        text = text.replace(marker, marker + app_name_line, 1)
        path.write_text(text, encoding="utf-8")


def brand_flutter_ui() -> None:
    # Replace only the product's user-visible proper name in Dart UI sources.
    # Lower-case internal identifiers, package names and rustdesk:// are untouched.
    root = Path("flutter/lib")
    changed = 0
    for path in root.rglob("*.dart"):
        text = path.read_text(encoding="utf-8")
        if "RustDesk" in text:
            path.write_text(text.replace("RustDesk", APP_NAME), encoding="utf-8")
            changed += 1
    print(f"GISuporte branding applied to {changed} Flutter UI files")


def main() -> None:
    configure_server()
    brand_flutter_ui()
    print(f"Configured {APP_NAME} for self-hosted server {SERVER}")


if __name__ == "__main__":
    main()
