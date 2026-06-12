"""
Бэкап конфигурации telemt — выгрузка TOML через API
"""

from datetime import datetime

from aiogram import Router, F
from aiogram.types import BufferedInputFile, CallbackQuery

router = Router()

# Секции API, которые экспортируются в TOML
_API_SECTIONS = [
    "general", "general.modes", "general.telemetry", "general.links",
    "network", "server", "timeouts", "censorship", "censorship.tls_fetch",
    "upstreams", "dc_overrides", "show_link",
]


def _json_val(v, indent=0) -> str:
    """Конвертирует JSON-значение в TOML-строку."""
    pad = "    " * indent
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return str(v)
    if isinstance(v, str):
        escaped = v.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(v, list):
        if not v:
            return "[]"
        if all(isinstance(x, (str, int, float, bool)) for x in v):
            items = ", ".join(_json_val(x) for x in v)
            return f"[{items}]"
        # Array of tables — возвращаем None, обрабатывается отдельно
        return None
    if isinstance(v, dict):
        return None  # Таблицы обрабатываются отдельно
    return f'"{v}"'


def _toml_section(name: str, data, indent=0) -> list[str]:
    """Генерирует TOML-строки для секции."""
    lines = []
    pad = "    " * indent

    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                lines.append(f"{pad}[{name}.{k}]" if indent == 0 else f"{pad}{k} = {{}}")
                lines += _toml_section(f"{name}.{k}", v, indent)
            elif isinstance(v, list):
                # Проверяем — массив таблиц или простой массив
                if v and isinstance(v[0], dict):
                    for item in v:
                        lines.append(f"{pad}[[{name}.{k}]]")
                        for ik, iv in item.items():
                            val = _json_val(iv)
                            if val is not None:
                                lines.append(f"{pad}{ik} = {val}")
                else:
                    val = _json_val(v)
                    if val is not None:
                        lines.append(f"{pad}{k} = {val}")
            else:
                val = _json_val(v)
                if val is not None:
                    lines.append(f"{pad}{k} = {val}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                lines.append(f"{pad}[[{name}]]")
                for ik, iv in item.items():
                    val = _json_val(iv)
                    if val is not None:
                        lines.append(f"{pad}{ik} = {val}")
            else:
                val = _json_val(item)
                if val is not None:
                    lines.append(f"{pad}{name} = {val}")
    return lines


def json_config_to_toml(data: dict) -> str:
    """Конвертирует JSON-ответ GET /v1/config в TOML-текст."""
    revision = data.get("revision", "")
    lines = []

    if revision:
        lines.append(f"# backup revision: {revision}")
        lines.append("")

    for section in _API_SECTIONS:
        section_data = data.get(section)
        if section_data is None:
            continue

        # Вложенные секции (general.modes) — пропускаем на верхнем уровне,
        # они выводятся как [general.modes]
        if "." in section:
            continue

        lines.append(f"[{section}]")
        lines += _toml_section(section, section_data)
        lines.append("")

    return "\n".join(lines)


@router.callback_query(F.data == "users:export_toml")
async def export_toml_callback(cq: CallbackQuery, config):
    """Бэкап конфигурации через API."""
    from session import get_client
    from api_client import ApiError, cluster_read

    await cq.answer("⏳ Готовлю бэкап через API...", show_alert=False)

    try:
        uid = cq.from_user.id
        client, srv = await get_client(uid, config)
        members = config.get_group_members(srv)
        data = await cluster_read(members, "get_config")
    except ApiError as e:
        await cq.message.answer(f"❌ API ошибка: {e}")
        return
    except Exception as e:
        await cq.message.answer(f"❌ Ошибка: {type(e).__name__}: {e}")
        return

    toml_text = json_config_to_toml(data)

    if not toml_text.strip():
        await cq.message.answer("❌ Пустой конфиг")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    revision = data.get("revision", "")[:8]
    file_bytes = BufferedInputFile(
        toml_text.encode("utf-8"),
        filename=f"telemt_backup_{ts}.toml",
    )

    from keyboards import export_toml_kb
    caption = f"📦 <b>Бэкап конфигурации</b>\n"
    caption += f"<i>{ts}</i>"
    if revision:
        caption += f" | rev: {revision}"

    await cq.message.answer_document(
        document=file_bytes,
        caption=caption,
        reply_markup=export_toml_kb(),
    )
