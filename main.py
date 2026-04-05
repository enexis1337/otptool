#!/usr/bin/env python3
"""
Flipper Zero — OTP Generator / Reader  (Flet desktop GUI)
pip install flet
"""

import os, re, struct, datetime, threading
import usb.core, usb.util
try:
    import libusb_package
    libusb_package.get_libusb1_backend()   # register backend
except ImportError:
    pass
import flet as ft

OTP_MAGIC    = 0xBABE
OTP_VERSION  = 0x02
OTP_RESERVED = 0x00

OTP_COLORS   = {"unknown": 0x00, "black": 0x01, "white": 0x02, "transparent": 0x03}
OTP_REGIONS  = {"unknown": 0x00, "eu_ru": 0x01, "us_ca_au": 0x02, "jp": 0x03, "world": 0x04}
OTP_DISPLAYS = {"unknown": 0x00, "erc": 0x01, "mgg": 0x02}

COLORS_R   = {v: k for k, v in OTP_COLORS.items()}
REGIONS_R  = {v: k for k, v in OTP_REGIONS.items()}
DISPLAYS_R = {v: k for k, v in OTP_DISPLAYS.items()}

# OTP memory addresses (STM32WB55)
OTP_ADDR_FIRST  = 0x1FFF7000   # first block  (16 bytes)
OTP_ADDR_SECOND = 0x1FFF7010   # second block (16 bytes)

BG       = "#0F1117"
PANEL    = "#1A1D27"
BORDER   = "#2D3148"
ACCENT   = "#4D7CFE"
ACCENT_H = "#3D6AEE"
TEXT     = "#E2E8F0"
TEXT_DIM = "#4A5568"
INPUT_BG = "#13151F"
LOG_BG   = "#0C0E16"
LOG_FG   = "#7C8DB5"
ERR      = "#F87171"
OK_C     = "#4ADE80"
WARN     = "#FBBF24"
FONT     = "Segoe UI"

LANGS = {
    "ru": {
        "tab_generate": "Генерация", "tab_read": "Чтение",
        "ver": "Версия", "fw": "ПО", "body": "Корпус", "conn": "Разъём",
        "display": "Дисплей", "color": "Цвет", "region": "Регион",
        "name": "Имя", "outdir": "Папка вывода", "prefix": "Префикс",
        "timestamp": "Timestamp (unix, необяз.)",
        "log": "Лог", "clear": "Очистить",
        "generate": "Генерировать", "merge": "Объединить",
        "ready": "Готово",
        "status_ok": "Сгенерировано", "status_merged": "Файлы объединены",
        "status_err": "Ошибка", "status_inv": "Неверный ввод",
        "status_name": "Неверное имя",
        "started": "otptool запущен!",
        "err_int":      "ОШИБКА: числовые поля должны быть целыми числами",
        "err_name":     "ОШИБКА: Имя — только [a-zA-Z0-9.], от 1 до 8 символов",
        "err_ts":       "ОШИБКА: Timestamp должен быть целым числом",
        "err_merge":    "ОШИБКА: сначала сгенерируйте файлы",
        "err_merge_ex": "ОШИБКА объединения: ",
        "merge_ok":     "✓ Объединено →",
        "lang_btn":     "EN",
        "tooltip_browse": "Обзор",
        "tooltip_merge":  "Объединить два .bin в один файл",
        "color_opts":   [("unknown","Неизвестно"),("black","Чёрный"),
                         ("white","Белый"),("transparent","Прозрачный")],
        "region_opts":  [("unknown","Неизвестно"),("eu_ru","EU/RU"),
                         ("us_ca_au","US/CA/AU"),("jp","Япония"),("world","Мир")],
        "display_opts": [("unknown","Неизвестно"),("erc","ERC"),("mgg","MGG")],
        # read tab
        "read_btn":       "Прочитать OTP",
        "read_clear":     "Очистить",
        "read_hint":      "Переведите Flipper Zero в DFU режим (удерживайте Back+Left при включении), затем нажмите «Прочитать OTP»",
        "read_searching": "Поиск Flipper Zero в DFU режиме...",
        "read_reading":   "Чтение OTP из памяти...",
        "read_ok":        "OTP прочитан успешно",
        "read_err":       "Ошибка чтения",
        "read_no_device": "Flipper Zero в DFU режиме не найден",
        "read_no_backend":"libusb не найден. Установите: pip install libusb-package",
        "read_bad_magic": "ОШИБКА: неверный Magic (ожидается 0xBABE)",
        "read_bad_data":  "ОШИБКА: некорректные данные OTP",
        "dfu_device_lbl": "DFU устройство",
        "dfu_not_found":  "Устройство не найдено",
        "field_magic":    "Magic",
        "field_version":  "OTP Version",
        "field_ts":       "Timestamp",
        "field_ver":      "Версия",
        "field_fw":       "ПО",
        "field_body":     "Корпус",
        "field_conn":     "Разъём",
        "field_display":  "Дисплей",
        "field_color":    "Цвет",
        "field_region":   "Регион",
        "field_name":     "Имя",
    },
    "en": {
        "tab_generate": "Generate", "tab_read": "Read",
        "ver": "Ver", "fw": "FW", "body": "Body", "conn": "Conn",
        "display": "Display", "color": "Color", "region": "Region",
        "name": "Name", "outdir": "Output Dir", "prefix": "Prefix",
        "timestamp": "Timestamp (unix, optional)",
        "log": "Log", "clear": "Clear",
        "generate": "Generate", "merge": "Merge",
        "ready": "Ready",
        "status_ok": "Generated OK", "status_merged": "Files merged",
        "status_err": "Error", "status_inv": "Invalid input",
        "status_name": "Invalid name",
        "started": "otptool started!",
        "err_int":      "ERROR: numeric fields must be integers",
        "err_name":     "ERROR: Name must be [a-zA-Z0-9.], 1-8 chars",
        "err_ts":       "ERROR: Timestamp must be an integer",
        "err_merge":    "ERROR: generate files first",
        "err_merge_ex": "ERROR merging: ",
        "merge_ok":     "✓ Merged ->",
        "lang_btn":     "RU",
        "tooltip_browse": "Browse",
        "tooltip_merge":  "Merge two .bin files into one",
        "color_opts":   [("unknown","Unknown"),("black","Black"),
                         ("white","White"),("transparent","Transparent")],
        "region_opts":  [("unknown","Unknown"),("eu_ru","EU/RU"),
                         ("us_ca_au","US/CA/AU"),("jp","Japan"),("world","World")],
        "display_opts": [("unknown","Unknown"),("erc","ERC"),("mgg","MGG")],
        # read tab
        "read_btn":       "Read OTP",
        "read_clear":     "Clear",
        "read_hint":      "Put Flipper Zero into DFU mode (hold Back+Left on boot), then press «Read OTP»",
        "read_searching": "Searching for Flipper Zero in DFU mode...",
        "read_reading":   "Reading OTP from memory...",
        "read_ok":        "OTP read successfully",
        "read_err":       "Read error",
        "read_no_device": "Flipper Zero in DFU mode not found",
        "read_no_backend":"libusb not found. Install: pip install libusb-package",
        "read_bad_magic": "ERROR: invalid Magic (expected 0xBABE)",
        "read_bad_data":  "ERROR: invalid OTP data",
        "dfu_device_lbl": "DFU Device",
        "dfu_not_found":  "Device not found",
        "field_magic":    "Magic",
        "field_version":  "OTP Version",
        "field_ts":       "Timestamp",
        "field_ver":      "Ver",
        "field_fw":       "FW",
        "field_body":     "Body",
        "field_conn":     "Conn",
        "field_display":  "Display",
        "field_color":    "Color",
        "field_region":   "Region",
        "field_name":     "Name",
    },
}


# ── OTP pack / parse ──────────────────────────────────────────────────────────

def pack_first(ver, fw, body, conn, display, timestamp=None) -> bytes:
    ts = int(timestamp) if timestamp is not None else int(datetime.datetime.now().timestamp())
    return struct.pack(
        "<HBBLBBBBBBH",
        OTP_MAGIC, OTP_VERSION, OTP_RESERVED, ts,
        ver, fw, body, conn, OTP_DISPLAYS[display],
        OTP_RESERVED, OTP_RESERVED,
    )

def pack_second(color, region, name: str) -> bytes:
    return struct.pack(
        "<BBHL8s",
        OTP_COLORS[color], OTP_REGIONS[region],
        OTP_RESERVED, OTP_RESERVED,
        name.encode("ascii"),
    )

def validate_name(name: str) -> bool:
    return 1 <= len(name) <= 8 and bool(re.match(r"^[a-zA-Z0-9.]+$", name))

def merge_bins(path1: str, path2: str, out_path: str) -> int:
    with open(path1, "rb") as f1, open(path2, "rb") as f2:
        data = f1.read() + f2.read()
    with open(out_path, "wb") as fo:
        fo.write(data)
    return len(data)

def parse_otp(data: bytes) -> dict:
    """Parse OTP dump (at least 32 bytes). Layout matches STM32WB55 Flipper OTP."""
    if len(data) < 32:
        raise ValueError("bad_data")

    magic, otp_ver   = struct.unpack_from("<HH", data, 0)
    ts               = struct.unpack_from("<I",  data, 4)[0]
    ver              = data[8]
    fw               = data[9]
    body             = data[10]
    conn             = data[11]
    display_raw      = struct.unpack_from("<I",  data, 12)[0]
    color_raw        = data[16]
    region_raw       = data[17]
    name_raw         = data[24:32]

    if magic != OTP_MAGIC:
        raise ValueError("bad_magic")

    ts_human = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "—"
    name     = name_raw.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()

    return {
        "magic":    f"0x{magic:04X}",
        "otp_ver":  otp_ver,
        "ts_raw":   ts,
        "ts_human": ts_human,
        "ver":      ver,
        "fw":       fw,
        "body":     body,
        "conn":     conn,
        "display":  DISPLAYS_R.get(display_raw, f"unknown({display_raw})"),
        "color":    COLORS_R.get(color_raw,     f"unknown({color_raw})"),
        "region":   REGIONS_R.get(region_raw,   f"unknown({region_raw})"),
        "name":     name,
    }


# ── DFU OTP reader (based on dumper-otp-main logic) ──────────────────────────

import time as _time

_DFU_CLASS    = 0xFE
_DFU_SUBCLASS = 0x01
_DFU_PROTOCOL = 0x02

_REQ_DNLOAD    = 0x01
_REQ_UPLOAD    = 0x02
_REQ_GETSTATUS = 0x03
_REQ_CLRSTATUS = 0x04
_REQ_GETSTATE  = 0x05
_REQ_ABORT     = 0x06

_CMD_SET_ADDRESS = 0x21

_ST_IDLE        = 0x02
_ST_DNLOAD_SYNC = 0x03
_ST_DNBUSY      = 0x04
_ST_DNLOAD_IDLE = 0x05
_ST_UPLOAD_IDLE = 0x09
_ST_ERROR       = 0x0A

_TRANSFER_SIZE  = 2048


def _get_backend():
    try:
        import libusb_package
        return libusb_package.get_libusb1_backend()
    except ImportError:
        return None


def _iter_dfu_interfaces():
    """Yield dicts describing every DFU interface on every connected device."""
    backend = _get_backend()
    try:
        devices = list(usb.core.find(find_all=True, backend=backend))
    except usb.core.NoBackendError:
        raise RuntimeError("no_backend")

    result = []
    for dev in devices:
        for cfg in dev:
            for intf in cfg:
                if (intf.bInterfaceClass    == _DFU_CLASS and
                    intf.bInterfaceSubClass == _DFU_SUBCLASS and
                    intf.bInterfaceProtocol == _DFU_PROTOCOL):
                    result.append({
                        "dev": dev,
                        "cfg": cfg.bConfigurationValue,
                        "intf": intf.bInterfaceNumber,
                        "alt":  intf.bAlternateSetting,
                    })
    return result


def find_dfu_device():
    """Return first DFU interface info dict, or None."""
    devs = _iter_dfu_interfaces()
    return devs[0] if devs else None


class _Stm32Dfu:
    def __init__(self, info):
        self.dev  = info["dev"]
        self.info = info

    def _out(self, req, value, data=b""):
        try:
            self.dev.ctrl_transfer(0x21, req, value, self.info["intf"], data, 1000)
        except usb.core.USBError as e:
            raise RuntimeError(f"USB OUT 0x{req:02X} failed: {e}") from e

    def _in(self, req, value, length):
        try:
            return bytes(self.dev.ctrl_transfer(0xA1, req, value, self.info["intf"], length, 1000))
        except usb.core.USBError as e:
            raise RuntimeError(f"USB IN 0x{req:02X} failed: {e}") from e

    def get_state(self):
        return self._in(_REQ_GETSTATE, 0, 1)[0]

    def get_status(self):
        raw = self._in(_REQ_GETSTATUS, 0, 6)
        status      = raw[0]
        poll_ms     = raw[1] | (raw[2] << 8) | (raw[3] << 16)
        state       = raw[4]
        return status, poll_ms, state

    def clear_status(self):
        self._out(_REQ_CLRSTATUS, 0)

    def abort(self):
        self._out(_REQ_ABORT, 0)

    def ensure_idle(self):
        state = self.get_state()
        if state == _ST_IDLE:
            return
        if state == _ST_ERROR:
            self.clear_status()
            state = self.get_state()
        if state in (_ST_DNLOAD_IDLE, _ST_UPLOAD_IDLE):
            self.abort()
            state = self.get_state()
        if state != _ST_IDLE:
            raise RuntimeError(f"DFU not idle, state=0x{state:02X}")

    def wait_ready(self):
        for _ in range(200):
            status, poll_ms, state = self.get_status()
            if poll_ms:
                _time.sleep(poll_ms / 1000.0)
            if status != 0:
                raise RuntimeError(f"DFU status error 0x{status:02X} state=0x{state:02X}")
            if state not in (_ST_DNBUSY, _ST_DNLOAD_SYNC):
                return state
        raise RuntimeError("DFU device busy timeout")

    def set_address(self, address: int):
        self.ensure_idle()
        payload = bytes([_CMD_SET_ADDRESS]) + address.to_bytes(4, "little")
        self._out(_REQ_DNLOAD, 0, payload)
        state = self.wait_ready()
        if state != _ST_DNLOAD_IDLE:
            raise RuntimeError(f"unexpected state after set_address: 0x{state:02X}")
        self.abort()
        self.ensure_idle()

    def upload_block(self, block_num: int, length: int) -> bytes:
        data = self._in(_REQ_UPLOAD, block_num, length)
        _, _, state = self.get_status()
        if state not in (_ST_UPLOAD_IDLE, _ST_IDLE):
            self.wait_ready()
        return data

    def read_memory(self, address: int, size: int) -> bytes:
        self.set_address(address)
        out = bytearray()
        block_num = 2
        left = size
        while left > 0:
            chunk = min(left, _TRANSFER_SIZE)
            part  = self.upload_block(block_num, chunk)
            if len(part) != chunk:
                raise RuntimeError(f"short read at block {block_num}: {len(part)}/{chunk}")
            out.extend(part)
            left -= chunk
            block_num += 1
        self.abort()
        self.ensure_idle()
        return bytes(out)

    def open(self):
        try:
            self.dev.set_configuration(self.info["cfg"])
        except usb.core.USBError:
            pass
        try:
            if self.dev.is_kernel_driver_active(self.info["intf"]):
                self.dev.detach_kernel_driver(self.info["intf"])
        except (NotImplementedError, usb.core.USBError):
            pass
        try:
            usb.util.claim_interface(self.dev, self.info["intf"])
        except usb.core.USBError as e:
            raise RuntimeError(f"cannot claim DFU interface: {e}") from e
        try:
            self.dev.set_interface_altsetting(
                interface=self.info["intf"],
                alternate_setting=self.info["alt"])
        except usb.core.USBError as e:
            raise RuntimeError(f"cannot set alt setting: {e}") from e

    def close(self):
        try:
            usb.util.release_interface(self.dev, self.info["intf"])
        except usb.core.USBError:
            pass
        usb.util.dispose_resources(self.dev)


def read_otp_from_device() -> bytes:
    """
    Read 32 bytes of OTP (0x1FFF7000) from STM32WB55 via USB DFU.
    Flipper Zero must be in DFU mode (hold Back+Left on boot).
    On Windows: install WinUSB driver via Zadig for 'STM32 BOOTLOADER'.
    """
    info = find_dfu_device()
    if info is None:
        raise RuntimeError("no_device")

    dfu = _Stm32Dfu(info)
    dfu.open()
    try:
        return dfu.read_memory(OTP_ADDR_FIRST, 32)
    finally:
        dfu.close()


# ── GUI ───────────────────────────────────────────────────────────────────────

async def main(page: ft.Page):
    page.title            = "otptool"
    page.bgcolor          = BG
    page.window.width     = 640
    page.window.height    = 540
    page.window.resizable = False
    page.padding          = 0

    lang_state     = {"current": "ru"}
    last_generated = {"p1": None, "p2": None}

    def T(key: str) -> str:
        return LANGS[lang_state["current"]][key]

    TS = ft.TextStyle(size=12, color=TEXT, font_family=FONT)

    def tf(val="", expand=True, max_length=None, hint="") -> ft.TextField:
        return ft.TextField(
            value=val, expand=expand, max_length=max_length,
            hint_text=hint,
            hint_style=ft.TextStyle(size=11, color=TEXT_DIM),
            text_style=TS,
            border=ft.InputBorder.OUTLINE,
            bgcolor=INPUT_BG, border_color=BORDER,
            focused_border_color=ACCENT, focused_bgcolor=INPUT_BG,
            border_radius=6, border_width=1, dense=True,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=8),
            cursor_color=ACCENT,
        )

    def make_dd(opts_key: str, default: str) -> ft.Dropdown:
        return ft.Dropdown(
            value=default, expand=True,
            options=[ft.dropdown.Option(key=k, text=t) for k, t in T(opts_key)],
            text_style=TS,
            border=ft.InputBorder.OUTLINE,
            bgcolor=INPUT_BG, border_color=BORDER,
            focused_border_color=ACCENT,
            border_radius=6, border_width=1, dense=True,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=8),
        )

    gen_lbl_refs:  dict[str, ft.Text] = {}
    read_lbl_refs: dict[str, ft.Text] = {}

    def lbl(key: str, refs: dict) -> ft.Text:
        t = ft.Text(T(key), size=10, color=TEXT_DIM, font_family=FONT,
                    weight=ft.FontWeight.W_500)
        refs[key] = t
        return t

    def field(lbl_key: str, ctrl, refs: dict, expand=True):
        return ft.Column([lbl(lbl_key, refs), ctrl], spacing=3,
                         expand=expand, tight=True)

    def panel(content, expand=False, width=None):
        return ft.Container(
            content=content, bgcolor=PANEL,
            border=ft.Border.all(1, BORDER), border_radius=10,
            padding=12, expand=expand, width=width,
            shadow=ft.BoxShadow(blur_radius=8, spread_radius=0,
                                color="#40000000", offset=ft.Offset(0, 2)),
        )

    def filled_style(bg, bg_h, bg_p, px=20):
        return ft.ButtonStyle(
            bgcolor={ft.ControlState.DEFAULT: bg,
                     ft.ControlState.HOVERED: bg_h,
                     ft.ControlState.PRESSED: bg_p},
            color="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=8),
            text_style=ft.TextStyle(font_family=FONT, size=12,
                                    weight=ft.FontWeight.W_600),
            padding=ft.Padding.symmetric(horizontal=px, vertical=8),
        )

    # ── status bar ────────────────────────────────────────────────────────────
    status_dot  = ft.Container(width=7, height=7, bgcolor=ACCENT, border_radius=4)
    status_text = ft.Text(T("ready"), size=10, color=TEXT_DIM, font_family=FONT)

    def set_status(key: str, ok: bool = True):
        status_dot.bgcolor = OK_C if ok else ERR
        status_text.value  = T(key)
        page.update()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — GENERATE
    # ══════════════════════════════════════════════════════════════════════════

    tf_ver    = tf("15")
    tf_fw     = tf("7")
    tf_body   = tf("9")
    tf_conn   = tf("6")
    tf_name   = tf("flipname")
    tf_ts     = tf("", hint="auto")
    tf_outdir = tf(os.path.expanduser("~"))
    tf_prefix = tf("otp")

    sel_display = make_dd("display_opts", "mgg")
    sel_color   = make_dd("color_opts",   "white")
    sel_region  = make_dd("region_opts",  "world")

    gen_log_view = ft.ListView(expand=True, spacing=1, auto_scroll=True)

    def gen_log(msg: str, color=LOG_FG):
        gen_log_view.controls.append(
            ft.Text(msg, size=11, color=color, font_family="Courier New", selectable=True))
        page.update()

    def do_generate(e):
        try:
            ver  = int(tf_ver.value or 0)
            fw   = int(tf_fw.value or 0)
            body = int(tf_body.value or 0)
            conn = int(tf_conn.value or 0)
        except ValueError:
            gen_log(T("err_int"), ERR); set_status("status_inv", False); return

        ts_val = None
        if tf_ts.value and tf_ts.value.strip():
            try:
                ts_val = int(tf_ts.value.strip())
            except ValueError:
                gen_log(T("err_ts"), ERR); set_status("status_inv", False); return

        name = tf_name.value or ""
        if not validate_name(name):
            gen_log(T("err_name"), ERR); set_status("status_name", False); return

        outdir = tf_outdir.value or os.path.expanduser("~")
        prefix = os.path.join(outdir, tf_prefix.value or "otp")
        b1 = pack_first(ver, fw, body, conn, sel_display.value, timestamp=ts_val)
        b2 = pack_second(sel_color.value, sel_region.value, name)
        used_ts = ts_val if ts_val is not None else int(datetime.datetime.now().timestamp())

        try:
            p1, p2 = f"{prefix}_first.bin", f"{prefix}_second.bin"
            with open(p1, "wb") as f: f.write(b1)
            with open(p2, "wb") as f: f.write(b2)
            last_generated["p1"] = p1
            last_generated["p2"] = p2
            ts_str = datetime.datetime.fromtimestamp(used_ts).strftime("%Y-%m-%d %H:%M:%S")
            gen_log(f"✓ {p1}  [{len(b1)}B]", OK_C)
            gen_log(f"✓ {p2}  [{len(b2)}B]", OK_C)
            gen_log(f"  timestamp: {used_ts}  ({ts_str})", LOG_FG)
            set_status("status_ok")
        except Exception as ex:
            gen_log(f"{T('status_err')}: {ex}", ERR); set_status("status_err", False)

    def do_merge(e):
        p1 = last_generated.get("p1")
        p2 = last_generated.get("p2")
        if not p1 or not p2 or not os.path.exists(p1) or not os.path.exists(p2):
            gen_log(T("err_merge"), WARN); set_status("status_err", False); return
        outdir = tf_outdir.value or os.path.expanduser("~")
        out = os.path.join(outdir, (tf_prefix.value or "otp") + "_combined.bin")
        try:
            size = merge_bins(p1, p2, out)
            gen_log(f"{T('merge_ok')} {out}  [{size}B]", OK_C)
            set_status("status_merged")
        except Exception as ex:
            gen_log(f"{T('err_merge_ex')}{ex}", ERR); set_status("status_err", False)

    outdir_picker = ft.FilePicker()
    page.services.append(outdir_picker)

    async def do_browse(e):
        path = await outdir_picker.get_directory_path()
        if path:
            tf_outdir.value = path
            page.update()

    browse_btn = ft.IconButton(
        icon=ft.Icons.FOLDER_OPEN_OUTLINED,
        icon_color=TEXT_DIM, icon_size=15,
        on_click=do_browse,
        style=ft.ButtonStyle(padding=ft.Padding.all(2)),
        tooltip=T("tooltip_browse"),
    )

    gen_btn   = ft.FilledButton(content=T("generate"), on_click=do_generate,
                                style=filled_style(ACCENT, ACCENT_H, "#2D55CC", 24))
    merge_btn = ft.FilledButton(content=T("merge"),    on_click=do_merge,
                                style=filled_style("#2A4A2A", "#3A6A3A", "#1E361E", 16),
                                tooltip=T("tooltip_merge"))

    gen_log_title = ft.Text(T("log"), size=10, color=TEXT_DIM, font_family=FONT,
                            weight=ft.FontWeight.W_600)
    gen_clear_btn = ft.TextButton(
        T("clear"),
        on_click=lambda e: [gen_log_view.controls.clear(), page.update()],
        style=ft.ButtonStyle(
            color={ft.ControlState.DEFAULT: TEXT_DIM, ft.ControlState.HOVERED: ACCENT},
            padding=ft.Padding.symmetric(horizontal=4, vertical=0),
            text_style=ft.TextStyle(size=10, font_family=FONT),
        ),
    )

    gen_left = panel(ft.Column([
        ft.Row([
            field("ver",  tf_ver,  gen_lbl_refs),
            field("fw",   tf_fw,   gen_lbl_refs),
            field("body", tf_body, gen_lbl_refs),
            field("conn", tf_conn, gen_lbl_refs),
        ], spacing=6),
        ft.Row([
            field("display", sel_display, gen_lbl_refs),
            field("color",   sel_color,   gen_lbl_refs),
            field("region",  sel_region,  gen_lbl_refs),
        ], spacing=6),
        field("name",      tf_name,   gen_lbl_refs),
        field("timestamp", tf_ts,     gen_lbl_refs),
        field("outdir", ft.Row([tf_outdir, browse_btn], spacing=4, expand=True,
              vertical_alignment=ft.CrossAxisAlignment.CENTER), gen_lbl_refs),
        field("prefix", tf_prefix, gen_lbl_refs),
    ], spacing=6, tight=True), width=290)

    gen_right = panel(ft.Column([
        ft.Row([gen_log_title, ft.Container(expand=True), gen_clear_btn],
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Container(
            content=gen_log_view, bgcolor=LOG_BG,
            border=ft.Border.all(1, BORDER),
            border_radius=6, padding=8, expand=True,
        ),
    ], spacing=4, expand=True), expand=True)

    gen_tab_content = ft.Column([
        ft.Container(
            content=ft.Row([gen_left, gen_right], spacing=8, expand=True),
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            expand=True,
        ),
        ft.Container(
            content=ft.Row([
                ft.Container(expand=True), merge_btn,
                ft.Container(width=6), gen_btn,
            ]),
            padding=ft.Padding.only(left=10, right=10, bottom=6, top=0),
        ),
    ], spacing=0, expand=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — READ  (USB DFU / pyusb)
    # ══════════════════════════════════════════════════════════════════════════

    # DFU device status indicator
    dfu_status_text = ft.Text(
        T("dfu_not_found"), size=11, color=TEXT_DIM,
        font_family="Courier New",
    )

    def refresh_dfu_status(e=None):
        try:
            info = find_dfu_device()
            found = info is not None
            vid = info["dev"].idVendor if found else 0
            pid = info["dev"].idProduct if found else 0
        except RuntimeError:
            found = False
            vid = pid = 0
        if found:
            dfu_status_text.value = f"Flipper Zero DFU  [VID={vid:04X} PID={pid:04X}]"
            dfu_status_text.color = OK_C
        else:
            dfu_status_text.value = T("dfu_not_found")
            dfu_status_text.color = TEXT_DIM
        page.update()

    refresh_dfu_btn = ft.IconButton(
        icon=ft.Icons.REFRESH,
        icon_color=TEXT_DIM, icon_size=15,
        on_click=refresh_dfu_status,
        style=ft.ButtonStyle(padding=ft.Padding.all(2)),
        tooltip="Обновить",
    )

    read_hint_text = ft.Text(
        T("read_hint"), size=10, color=TEXT_DIM, font_family=FONT,
        text_align=ft.TextAlign.CENTER,
    )

    read_result_col = ft.Column(
        [read_hint_text],
        spacing=5,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    read_spinner = ft.ProgressRing(width=16, height=16, stroke_width=2,
                                   color=ACCENT, visible=False)

    def render_parse_result(parsed: dict):
        read_result_col.controls.clear()  # removes hint too
        L = LANGS[lang_state["current"]]

        def row(field_key: str, value, highlight=False):
            val_color = OK_C if highlight else TEXT
            read_result_col.controls.append(ft.Row([
                ft.Text(L[field_key], size=11, color=TEXT_DIM,
                        font_family=FONT, width=110),
                ft.Text(str(value), size=11, color=val_color,
                        font_family="Courier New", selectable=True, expand=True),
            ], spacing=8))

        def div():
            read_result_col.controls.append(
                ft.Container(height=1, bgcolor=BORDER,
                             margin=ft.Margin.symmetric(vertical=2)))

        row("field_magic",   parsed["magic"])
        row("field_version", parsed["otp_ver"])
        row("field_ts",      f"{parsed['ts_raw']}  ({parsed['ts_human']})")
        div()
        row("field_ver",     parsed["ver"])
        row("field_fw",      parsed["fw"])
        row("field_body",    parsed["body"])
        row("field_conn",    parsed["conn"])
        row("field_display", parsed["display"])
        if "color" in parsed:
            div()
            row("field_color",  parsed["color"])
            row("field_region", parsed["region"])
            row("field_name",   parsed["name"], highlight=True)

        page.update()

    read_log_view = ft.ListView(expand=True, spacing=1, auto_scroll=True)

    def read_log(msg: str, color=LOG_FG):
        read_log_view.controls.append(
            ft.Text(msg, size=11, color=color, font_family="Courier New", selectable=True))
        page.update()

    def set_read_busy(busy: bool):
        read_spinner.visible = busy
        read_btn.disabled    = busy
        page.update()

    def do_read_otp(e):
        def worker():
            set_read_busy(True)
            read_log(T("read_searching"), LOG_FG)
            try:
                raw = read_otp_from_device()
                read_log(T("read_reading"), LOG_FG)
                parsed = parse_otp(raw)
                render_parse_result(parsed)
                read_log(f"✓  {T('read_ok')}  [{len(raw)}B]", OK_C)
                set_status("read_ok")
            except RuntimeError as ex:
                if "no_device" in str(ex):
                    read_log(f"✗  {T('read_no_device')}", ERR)
                elif "no_backend" in str(ex):
                    read_log(f"✗  {T('read_no_backend')}", ERR)
                else:
                    read_log(f"✗  {ex}", ERR)
                set_status("read_err", False)
            except ValueError as ve:
                key = f"read_{ve}"
                msg = LANGS[lang_state["current"]].get(key, str(ve))
                read_log(f"✗  {msg}", ERR)
                set_status("read_err", False)
            except Exception as ex:
                read_log(f"✗  {T('read_err')}: {ex}", ERR)
                set_status("read_err", False)
            finally:
                set_read_busy(False)
                refresh_dfu_status()

        threading.Thread(target=worker, daemon=True).start()

    def do_read_clear(e):
        read_result_col.controls.clear()
        read_result_col.controls.append(read_hint_text)
        read_log_view.controls.clear()
        set_status("ready")
        page.update()

    read_btn = ft.FilledButton(
        content=T("read_btn"),
        on_click=do_read_otp,
        style=filled_style(ACCENT, ACCENT_H, "#2D55CC", 20),
    )
    read_clear_btn = ft.TextButton(
        T("read_clear"),
        on_click=do_read_clear,
        style=ft.ButtonStyle(
            color={ft.ControlState.DEFAULT: TEXT_DIM, ft.ControlState.HOVERED: ACCENT},
            padding=ft.Padding.symmetric(horizontal=4, vertical=0),
            text_style=ft.TextStyle(size=10, font_family=FONT),
        ),
    )

    read_port_lbl = ft.Text(T("dfu_device_lbl"), size=10, color=TEXT_DIM,
                             font_family=FONT, weight=ft.FontWeight.W_500)

    read_top = panel(ft.Column([
        ft.Row([
            ft.Column([read_port_lbl,
                       ft.Row([dfu_status_text, ft.Container(expand=True), refresh_dfu_btn],
                               vertical_alignment=ft.CrossAxisAlignment.CENTER)],
                      spacing=3, expand=True, tight=True),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.END),
    ], spacing=4, tight=True))

    read_left = panel(ft.Column([
        ft.Container(
            content=read_result_col,
            bgcolor=LOG_BG,
            border=ft.Border.all(1, BORDER),
            border_radius=6, padding=12, expand=True,
        ),
    ], expand=True, spacing=4), expand=True, width=280)

    read_right = panel(ft.Column([
        ft.Row([
            ft.Text("Log", size=10, color=TEXT_DIM, font_family=FONT,
                    weight=ft.FontWeight.W_600),
            ft.Container(expand=True),
            read_clear_btn,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Container(
            content=read_log_view, bgcolor=LOG_BG,
            border=ft.Border.all(1, BORDER),
            border_radius=6, padding=8, expand=True,
        ),
    ], spacing=4, expand=True), expand=True)

    read_tab_content = ft.Column([
        ft.Container(
            content=ft.Column([
                read_top,
                ft.Row([read_left, read_right], spacing=8, expand=True),
            ], spacing=8, expand=True),
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            expand=True,
        ),
        ft.Container(
            content=ft.Row([
                ft.Container(expand=True),
                read_spinner,
                ft.Container(width=8),
                read_btn,
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.only(left=10, right=10, bottom=6, top=0),
        ),
    ], spacing=0, expand=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB SWITCHER
    # ══════════════════════════════════════════════════════════════════════════

    tab_state   = {"current": "generate"}
    tab_content = ft.Container(content=gen_tab_content, expand=True)

    def tab_btn_style(active: bool):
        return ft.ButtonStyle(
            bgcolor={ft.ControlState.DEFAULT: ACCENT if active else "transparent"},
            color={ft.ControlState.DEFAULT: TEXT if active else TEXT_DIM,
                   ft.ControlState.HOVERED: TEXT},
            shape=ft.RoundedRectangleBorder(radius=6),
            text_style=ft.TextStyle(font_family=FONT, size=11,
                                    weight=ft.FontWeight.W_600),
            padding=ft.Padding.symmetric(horizontal=14, vertical=5),
        )

    tab_gen_btn  = ft.FilledButton(content=T("tab_generate"), style=tab_btn_style(True))
    tab_read_btn = ft.FilledButton(content=T("tab_read"),     style=tab_btn_style(False))

    def switch_tab(name: str):
        tab_state["current"] = name
        tab_gen_btn.style   = tab_btn_style(name == "generate")
        tab_read_btn.style  = tab_btn_style(name == "read")
        tab_content.content = gen_tab_content if name == "generate" else read_tab_content
        page.update()

    tab_gen_btn.on_click  = lambda e: switch_tab("generate")
    tab_read_btn.on_click = lambda e: switch_tab("read")

    # ── language button ───────────────────────────────────────────────────────
    lang_btn = ft.OutlinedButton(
        content=T("lang_btn"),
        style=ft.ButtonStyle(
            color={ft.ControlState.DEFAULT: TEXT_DIM, ft.ControlState.HOVERED: ACCENT},
            side=ft.BorderSide(1, BORDER),
            shape=ft.RoundedRectangleBorder(radius=6),
            text_style=ft.TextStyle(font_family=FONT, size=11, weight=ft.FontWeight.W_600),
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
        ),
    )

    def refresh_lang():
        for opts_key, ctrl in [("display_opts", sel_display),
                                ("color_opts",   sel_color),
                                ("region_opts",  sel_region)]:
            ctrl.options = [ft.dropdown.Option(key=k, text=t) for k, t in T(opts_key)]
        for key, txt in gen_lbl_refs.items():
            txt.value = T(key)
        for key, txt in read_lbl_refs.items():
            txt.value = T(key)
        gen_btn.content        = T("generate")
        merge_btn.content      = T("merge")
        merge_btn.tooltip      = T("tooltip_merge")
        browse_btn.tooltip     = T("tooltip_browse")
        gen_log_title.value    = T("log")
        gen_clear_btn.content  = T("clear")
        read_btn.content       = T("read_btn")
        read_clear_btn.content = T("read_clear")
        read_hint_text.value   = T("read_hint")
        read_port_lbl.value    = T("dfu_device_lbl")
        dfu_status_text.value  = T("dfu_not_found") if dfu_status_text.color == TEXT_DIM else dfu_status_text.value
        tab_gen_btn.content    = T("tab_generate")
        tab_read_btn.content   = T("tab_read")
        lang_btn.content       = T("lang_btn")
        status_text.value      = T("ready")
        status_dot.bgcolor     = ACCENT
        page.update()

    def toggle_lang(e):
        lang_state["current"] = "en" if lang_state["current"] == "ru" else "ru"
        refresh_lang()

    lang_btn.on_click = toggle_lang

    # ── root layout ───────────────────────────────────────────────────────────
    page.add(ft.Column([
        ft.Container(
            content=ft.Row([
                ft.Container(width=8, height=8, bgcolor=ACCENT, border_radius=4),
                ft.Text("otptool", size=13, color=TEXT, font_family=FONT,
                        weight=ft.FontWeight.W_700),
                ft.Container(width=10),
                ft.Container(
                    content=ft.Row([tab_gen_btn, tab_read_btn], spacing=4),
                    bgcolor=INPUT_BG,
                    border=ft.Border.all(1, BORDER),
                    border_radius=8, padding=3,
                ),
                ft.Container(expand=True),
                lang_btn,
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=PANEL,
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
        ),
        tab_content,
        ft.Container(
            content=ft.Row([status_dot, status_text], spacing=6),
            bgcolor=PANEL,
            padding=ft.Padding.symmetric(horizontal=14, vertical=5),
            border=ft.Border.only(top=ft.BorderSide(1, BORDER)),
        ),
    ], spacing=0, expand=True))

    gen_log(T("started"))


ft.run(main)
