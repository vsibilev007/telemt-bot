# v1.7 — Bilingual UI and Bulk Creation Wizard / Двуязычный интерфейс и визард массового создания

Image: `docker pull ghcr.io/vsibilev007/telemt-bot:1.7` (or `:latest`)

**English**

## Bulk creation wizard

- Step-by-step wizard instead of one text line: **name template** -> **count** (5/10/25/50 or custom) -> **expiry** (+7/+30/+90 days, none or a concrete date) -> **quota** (none/10/50/100 GB or custom)
- **Preview before creating**: shows the generated names (guest1...guestN), the concrete expiry date, quota and a WEB-profiles toggle — nothing is created until "Create N" is pressed
- Fast path kept: the line `guest 5 30` in the template step jumps straight to the preview
- WEB profiles are added with a single `PATCH /v1/config?reload=instant`, only when enabled in the preview
- **Repeat** button in the report: create another batch with the same parameters (existing names are skipped, not failed)

## Bilingual interface (ru/en)

- All UI strings (commands, buttons, handler texts, formatters, alerts, /help) live in `i18n_*.py` tables
- Switched by the environment variable **`BOT_LANG=ru|en`** (default `ru` — unchanged behavior)
- `/help`, command descriptions and the Telegram main menu are fully translated

## Also

- CI: the tag trigger is widened to `v*` — two-component tags like v1.6 never fired the release job before; a rolling pre-release is auto-updated on every successful `main` build with a fresh commit list and image info
- The `/start` greeting uses a localized fallback name ("друг"/"friend") when the profile has no first name
- New i18n coverage tests — 5 tests, total **88**

---

**По-русски**

## Визард массового создания

- Вместо одной текстовой строки — пошаговый визард: **шаблон имени** -> **количество** (5/10/25/50 или своё) -> **срок** (+7/+30/+90 дней, без срока или конкретная дата) -> **квота** (без/10/50/100 ГБ или своя)
- **Превью перед созданием**: показывает предлагаемые имена (guest1...guestN), конкретную дату истечения, квоту и переключатель WEB-профилей — можно отказаться; ничего не создаётся, пока не нажато «Создать N»
- Быстрый путь сохранён: строка `guest 5 30` в шаге шаблона сразу открывает превью
- WEB-профили добавляются одним `PATCH /v1/config?reload=instant` и только если включены в превью
- Кнопка **«Повторить»** в отчёте: создать ещё пачку с теми же параметрами (существующие имена пропускаются, а не валятся ошибкой)

## Двуязычный интерфейс (ru/en)

- Все строки интерфейса (команды, кнопки, тексты хендлеров, форматтеры, алерты, /help) разнесены по таблицам `i18n_*.py`
- Переключение через переменную окружения **`BOT_LANG=ru|en`** (по умолчанию `ru` — прежнее поведение)
- Справка `/help`, описания команд и главное меню Telegram переведены полностью

## Прочее

- CI: триггер по тегам расширен до `v*` — двухкомпонентные теги вроде v1.6 раньше не запускали релизную джобу; после каждого билда `main` обновляется rolling-pre-release со свежим списком коммитов и образом
- Приветствие `/start` использует локализованный запасной вариант имени («друг»/«friend»), если у профиля Telegram его нет
- Новые тесты покрытия i18n — 5 тестов, всего **88**
