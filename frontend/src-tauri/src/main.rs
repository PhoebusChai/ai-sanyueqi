#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{CustomMenuItem, SystemTray, SystemTrayMenu, SystemTrayEvent, Manager};

fn main() {
    let show = CustomMenuItem::new("show".to_string(), "显示");
    let hide = CustomMenuItem::new("hide".to_string(), "隐藏");
    let quit = CustomMenuItem::new("quit".to_string(), "退出");
    
    let tray_menu = SystemTrayMenu::new()
        .add_item(show)
        .add_item(hide)
        .add_native_item(tauri::SystemTrayMenuItem::Separator)
        .add_item(quit);

    let system_tray = SystemTray::new().with_menu(tray_menu);

    tauri::Builder::default()
        .system_tray(system_tray)
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::LeftClick { .. } => {
                if let Some(window) = app.get_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
            SystemTrayEvent::MenuItemClick { id, .. } => {
                if let Some(window) = app.get_window("main") {
                    match id.as_str() {
                        "show" => { let _ = window.show(); }
                        "hide" => { let _ = window.hide(); }
                        "quit" => { std::process::exit(0); }
                        _ => {}
                    }
                }
            }
            _ => {}
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
