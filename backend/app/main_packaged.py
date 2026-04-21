import importlib
import logging
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
import webbrowser


def _ensure_tiktoken_plugins_when_frozen() -> None:
    if not getattr(sys, "frozen", False):
        return
    import tiktoken.registry as tr

    def _plugin_modules():
        return ("tiktoken_ext.openai_public",)

    tr._available_plugin_modules = _plugin_modules


_ensure_tiktoken_plugins_when_frozen()

import uvicorn
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config.settings import settings
from app.main import app


def _get_frontend_dist_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "frontend_dist"
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


def _frontend_enabled() -> bool:
    dist_dir = _get_frontend_dist_dir()
    return dist_dir.exists() and (dist_dir / "index.html").exists()


def _display_host() -> str:
    host = (settings.service_host or "").strip()
    if host in {"", "0.0.0.0", "::"}:
        return "127.0.0.1"
    return host


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def _pick_runtime_port() -> int:
    configured_port = int(settings.service_port)
    dynamic_default = bool(getattr(sys, "frozen", False))
    dynamic = _env_flag("PANDO_DYNAMIC_PORT", dynamic_default)
    strict = _env_flag("PANDO_STRICT_PORT", False)

    if not dynamic:
        return configured_port

    host = (settings.service_host or "").strip() or "0.0.0.0"
    if _is_port_available(host, configured_port):
        return configured_port

    if strict:
        raise RuntimeError(f"配置端口已被占用: {host}:{configured_port}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return int(s.getsockname()[1])


def _wait_until_ready(url: str, timeout_seconds: int = 30) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if 200 <= resp.status < 500:
                    return True
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.2)
    return False


def _drop_existing_root_get_route() -> None:
    keep_routes = []
    for route in app.router.routes:
        route_path = getattr(route, "path", None)
        route_methods = getattr(route, "methods", set()) or set()
        if route_path == "/" and "GET" in route_methods:
            continue
        keep_routes.append(route)
    app.router.routes = keep_routes


if _frontend_enabled():
    dist_dir = _get_frontend_dist_dir()
    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    for name in ("favicon.svg", "moling-icon.svg", "pando-icon.png"):
        file_path = dist_dir / name
        if file_path.exists():
            app.mount(f"/{name}", StaticFiles(directory=str(dist_dir)), name=f"static-{name}")

_drop_existing_root_get_route()


@app.get("/", include_in_schema=False)
async def root_frontend():
    if _frontend_enabled():
        return FileResponse(str(_get_frontend_dist_dir() / "index.html"))
    raise HTTPException(status_code=404, detail="Frontend not found")


@app.get("/{path:path}", include_in_schema=False)
async def spa_fallback(path: str):
    if not _frontend_enabled():
        raise HTTPException(status_code=404, detail="Not Found")

    p = path.lstrip("/")
    if p.startswith("api/") or p in {"docs", "redoc", "openapi.json", "health", "log-level"}:
        raise HTTPException(status_code=404, detail="Not Found")

    dist_dir = _get_frontend_dist_dir()
    target = (dist_dir / p).resolve()
    if str(target).startswith(str(dist_dir.resolve())) and target.exists() and target.is_file():
        return FileResponse(str(target))
    return FileResponse(str(dist_dir / "index.html"))


def main():
    runtime_port = _pick_runtime_port()
    if os.getenv("PANDO_SERVER_ONLY", "").strip() == "1":
        uvicorn.run(
            "app.main_packaged:app",
            host=settings.service_host,
            port=runtime_port,
            reload=False,
            log_config=None,
        )
        return

    config = uvicorn.Config(
        app,
        host=settings.service_host,
        port=runtime_port,
        reload=False,
        log_config=None,
    )
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    display_url = f"http://{_display_host()}:{runtime_port}"
    health_url = f"{display_url}/health"
    if not _wait_until_ready(health_url, timeout_seconds=30):
        server.should_exit = True
        server_thread.join(timeout=5)
        raise RuntimeError(f"服务启动超时: {health_url}")

    try:
        webview_module = importlib.import_module("webview")
    except ModuleNotFoundError as exc:
        server.should_exit = True
        server_thread.join(timeout=5)
        raise RuntimeError("缺少 pywebview 依赖，无法启动桌面窗口") from exc

    if sys.platform == "win32":
        try:
            winforms_module = importlib.import_module("webview.platforms.winforms")
            renderer = str(getattr(winforms_module, "renderer", "")).lower()
            if renderer == "mshtml":
                webbrowser.open(display_url)
                raise RuntimeError(
                    "检测到当前仅可用 MSHTML（IE）内核，无法渲染现代前端页面。"
                    "请安装/修复 Microsoft Edge WebView2 Runtime。"
                    f"已回退到系统浏览器: {display_url}"
                )
        except RuntimeError:
            server.should_exit = True
            server_thread.join(timeout=5)
            raise
        except Exception as exc:
            logging.warning("检查 pywebview 渲染器失败，继续尝试启动: %s", exc)

    webview_module.create_window("Pando AI Assistant", display_url, width=1320, height=860)
    try:
        webview_module.start(gui="edgechromium", debug=_env_flag("PANDO_WEBVIEW_DEBUG", False))
    except Exception as exc:
        # WebView2 缺失或 EdgeChromium 初始化失败时，至少回退到系统浏览器可用。
        logging.exception("pywebview 启动失败，回退系统浏览器: %s", exc)
        webbrowser.open(display_url)
        raise RuntimeError(
            "桌面窗口初始化失败。请安装/修复 Microsoft Edge WebView2 Runtime。"
            f"已回退到系统浏览器: {display_url}"
        ) from exc
    finally:
        server.should_exit = True
        server_thread.join(timeout=10)


def _write_crash_log(text: str) -> Path:
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]
    log_path = base / "pando_startup_error.log"
    try:
        log_path.write_text(text, encoding="utf-8")
    except OSError:
        log_path = Path(os.environ.get("TEMP", ".")) / "pando_startup_error.log"
        log_path.write_text(text, encoding="utf-8")
    return log_path


def _show_windows_error(message: str) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message[:1024], "Pando 启动失败", 0x10)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        log_path = _write_crash_log(tb)
        msg = f"{exc}\n\n详情已写入:\n{log_path}"
        _show_windows_error(msg)
        raise
