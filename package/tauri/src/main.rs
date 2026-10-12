#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::menu::{MenuBuilder, MenuItemBuilder};
use tauri::tray::TrayIconBuilder;
use tauri::Manager;

const API_ADDR: &str = "127.0.0.1:8765";
const WEB_ADDR: &str = "127.0.0.1:3300";
const WEB_URL: &str = "http://127.0.0.1:3300";
const BOOT_TIMEOUT: Duration = Duration::from_secs(90);

/// Process con do shell spawn — giết hết khi app thoát.
struct Sidecars(Mutex<Vec<Child>>);

fn exe_dir() -> PathBuf {
    std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.to_path_buf()))
        .unwrap_or_else(|| PathBuf::from("."))
}

/// Tìm resource cạnh exe: install (NSIS đặt resources cạnh exe hoặc trong
/// subdir), rồi fallback ../ (layout package/ khi chạy thẳng target dir).
fn find_res(name: &str) -> Option<PathBuf> {
    let d = exe_dir();
    let cands = [
        d.join(name),
        // NSIS install: Tauri đặt bundle.resources vào _up_/
        d.join("_up_").join(name),
        d.join("resources").join(name),
        // dev: target/{debug,release} -> tauri/ -> package/
        d.join("..").join("..").join("..").join(name),
        d.join("..").join("..").join("..").join("..").join(name),
    ];
    cands.into_iter().find(|c| c.exists())
}

#[cfg(windows)]
fn hide_console(cmd: &mut Command) {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    cmd.creation_flags(CREATE_NO_WINDOW);
}
#[cfg(not(windows))]
fn hide_console(_cmd: &mut Command) {}

/// HTTP GET tối thiểu — đủ để probe /health không cần reqwest.
fn http_ok(addr: &str, path: &str) -> bool {
    let Ok(mut s) = TcpStream::connect(addr) else {
        return false;
    };
    let _ = s.set_read_timeout(Some(Duration::from_secs(2)));
    let _ = s.set_write_timeout(Some(Duration::from_secs(2)));
    let req = format!("GET {path} HTTP/1.1\r\nHost: {addr}\r\nConnection: close\r\n\r\n");
    if s.write_all(req.as_bytes()).is_err() {
        return false;
    }
    let mut buf = [0u8; 16];
    matches!(s.read(&mut buf), Ok(n) if n > 0 && buf[..n].starts_with(b"HTTP"))
}

fn spawn_child(app: &tauri::AppHandle, cmd: &mut Command) {
    hide_console(cmd);
    match cmd.spawn() {
        Ok(c) => app.state::<Sidecars>().0.lock().unwrap().push(c),
        Err(e) => eprintln!("[sidecar] spawn failed: {e}"),
    }
}

/// Port đang trống thì mới spawn — nếu đã có process cũ (zombie) nghe thì
/// tái dùng, tránh lỗi EADDRINUSE khi mở lại app sau crash.
fn spawn_sidecars(app: &tauri::AppHandle) {
    if !http_ok(API_ADDR, "/health") {
        if let Some(exe) = find_res("writer-api.exe") {
            eprintln!("[sidecar] start backend {}", exe.display());
            spawn_child(app, &mut Command::new(&exe));
        } else {
            eprintln!("[sidecar] writer-api.exe NOT FOUND");
        }
    }
    if !http_ok(WEB_ADDR, "/") {
        if let (Some(node), Some(server)) =
            (find_res("node.exe"), find_res("web/server.js"))
        {
            let workdir = server
                .parent()
                .and_then(|p| p.parent())
                .map(|p| p.to_path_buf());
            eprintln!("[sidecar] start frontend {}", server.display());
            let mut c = Command::new(&node);
            c.arg(&server)
                .env("PORT", "3300")
                .env("HOSTNAME", "127.0.0.1");
            if let Some(wd) = workdir {
                c.current_dir(wd);
            }
            spawn_child(app, &mut c);
        } else {
            eprintln!("[sidecar] node.exe/web NOT FOUND");
        }
    }
}

fn kill_sidecars(app: &tauri::AppHandle) {
    let state = app.state::<Sidecars>();
    let mut guard = state.0.lock().unwrap();
    for mut c in guard.drain(..) {
        let _ = c.kill();
        let _ = c.wait();
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(w) = app.get_webview_window("main") {
                let _ = w.unminimize();
                let _ = w.show();
                let _ = w.set_focus();
            }
        }))
        .manage(Sidecars(Mutex::new(Vec::new())))
        .setup(|app| {
            let handle = app.handle().clone();
            spawn_sidecars(&handle);

            // Tray: Mở / Thoát (đóng cửa sổ chỉ ẩn xuống tray)
            let open = MenuItemBuilder::with_id("open", "Mở AI Writer").build(app)?;
            let quit = MenuItemBuilder::with_id("quit", "Thoát").build(app)?;
            let menu = MenuBuilder::new(app).items(&[&open, &quit]).build()?;
            TrayIconBuilder::with_id("main")
                .menu(&menu)
                .tooltip("AI Writer Studio")
                .icon(app.default_window_icon().unwrap().clone())
                .on_menu_event(|app, ev| match ev.id.as_ref() {
                    "open" => {
                        if let Some(w) = app.get_webview_window("main") {
                            let _ = w.unminimize();
                            let _ = w.show();
                            let _ = w.set_focus();
                        }
                    }
                    "quit" => app.exit(0),
                    _ => {}
                })
                .build(app)?;

            // Nền: chờ backend+frontend sống rồi navigate splash -> app
            std::thread::spawn(move || {
                let deadline = Instant::now() + BOOT_TIMEOUT;
                loop {
                    if http_ok(API_ADDR, "/health") && http_ok(WEB_ADDR, "/") {
                        break;
                    }
                    if Instant::now() >= deadline {
                        break;
                    }
                    std::thread::sleep(Duration::from_millis(400));
                }
                if let Some(w) = handle.get_webview_window("main") {
                    if let Ok(url) = WEB_URL.parse() {
                        let _ = w.navigate(url);
                    }
                }
            });
            Ok(())
        })
        .on_window_event(|w, ev| {
            // X đóng = ẩn xuống tray (giữ phiên viết); tray "Thoát" mới exit
            if let tauri::WindowEvent::CloseRequested { api, .. } = ev {
                api.prevent_close();
                let _ = w.hide();
            }
        })
        .build(tauri::generate_context!())
        .expect("error building AI Writer Studio")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                kill_sidecars(app);
            }
        });
}
