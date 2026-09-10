mod keyboard;
/// cbindgen:ignore
pub mod platform;
#[cfg(not(any(target_os = "android", target_os = "ios")))]
pub use platform::{
    clip_cursor, get_cursor, get_cursor_data, get_cursor_pos, get_focused_display,
    set_cursor_pos, start_os_service,
};
#[cfg(not(any(target_os = "ios")))]
/// cbindgen:ignore
mod server;
#[cfg(not(any(target_os = "ios")))]
pub use self::server::*;
mod client;
mod lan;
#[cfg(not(any(target_os = "ios")))]
mod rendezvous_mediator;
#[cfg(not(any(target_os = "ios")))]
pub use self::rendezvous_mediator::*;
/// cbindgen:ignore
pub mod common;
#[cfg(not(any(target_os = "ios")))]
pub mod ipc;
#[cfg(not(any(
    target_os = "android",
    target_os = "ios",
    feature = "flutter"
)))]
pub mod ui;
mod version;
pub use version::*;
#[cfg(any(target_os = "android", target_os = "ios", feature = "flutter"))]
mod bridge_generated;
#[cfg(any(target_os = "android", target_os = "ios", feature = "flutter"))]
pub mod flutter;
#[cfg(any(target_os = "android", target_os = "ios", feature = "flutter"))]
pub mod flutter_ffi;
use common::*;

const GISUPORTE_APP_NAME: &str = "GISuporte";
const GISUPORTE_RENDEZVOUS_SERVER: &str = "gisuporte.vps-kinghost.net";
const GISUPORTE_RS_PUB_KEY: &str = "aUbDo6Map3oFCVpb9VB66sNTbuvz3bX3iCoKVBGVUe4=";

/// Apply the GISuporte identity and self-hosted server defaults while keeping
/// the current RustDesk 1.4.9 runtime/service implementation intact.
///
/// We first honor any valid signed custom-client configuration supported by
/// upstream, then enforce the GISuporte values that are part of this build.
pub fn load_custom_client() {
    common::load_custom_client();

    *hbb_common::config::APP_NAME.write().unwrap() = GISUPORTE_APP_NAME.to_owned();
    *hbb_common::config::PROD_RENDEZVOUS_SERVER
        .write()
        .unwrap() = GISUPORTE_RENDEZVOUS_SERVER.to_owned();

    hbb_common::config::Config::set_option(
        "custom-rendezvous-server".to_owned(),
        GISUPORTE_RENDEZVOUS_SERVER.to_owned(),
    );
    hbb_common::config::Config::set_option("key".to_owned(), GISUPORTE_RS_PUB_KEY.to_owned());
}

mod auth_2fa;
#[cfg(not(target_os = "ios"))]
mod clipboard;
#[cfg(not(any(target_os = "android", target_os = "ios")))]
pub mod core_main;
mod custom_server;
mod lang;
#[cfg(not(any(target_os = "android", target_os = "ios")))]
mod port_forward;

#[cfg(all(feature = "flutter", feature = "plugin_framework"))]
#[cfg(not(any(target_os = "android", target_os = "ios")))]
pub mod plugin;

#[cfg(not(any(target_os = "android", target_os = "ios")))]
mod tray;

#[cfg(not(any(target_os = "android", target_os = "ios")))]
mod whiteboard;

#[cfg(not(any(target_os = "android", target_os = "ios")))]
mod updater;

mod ui_cm_interface;
mod ui_interface;
mod ui_session_interface;

mod hbbs_http;

#[cfg(any(target_os = "windows", target_os = "linux", target_os = "macos"))]
pub mod clipboard_file;

pub mod privacy_mode;

#[cfg(windows)]
pub mod virtual_display_manager;

mod kcp_stream;
