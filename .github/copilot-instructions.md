# Инструкции для AI‑агентов по работе с этим репозиторием

Среда: Windows + PowerShell (pwsh). Проект хранит данные эфемерид JPL и сторонний код чтения/вычисления.

## Архитектура и директории
- `data/ephemerides/jpl/de440/` — бинарные эфемериды JPL DE440: `linux_p1550p2650.440` (~97.5 MB), `header.440`, тест `testpo.440`.
- `vendor/jpl_eph/` — исходники Project Pluto (Bill Gray) для работы с JPL DE: распакованный архив `jpl_eph-master/` и `jpl_eph.zip`.
- `.github/` — правила для агентов и автоматизации.

Принципы:
- Не коммитьте тяжёлые бинарные данные (ephemerides) — держим их в `data/ephemerides/` и игнорируем в VCS (см. `.gitignore`).
- Эндиланность файлов: папка JPL `Linux/` — little‑endian; `SunOS/` — big‑endian. Код из `vendor/jpl_eph` сам определяет порядок байт и работает с обоими.
- Рекомендуемая серия: DE‑44x. Используйте DE440 (1550–2650). Для длинного диапазона (-13200…17191) — DE441 (~2.6 GB).

## Ключевые рабочие команды (pwsh)
- Загрузка DE440 из JPL:
  - URLы: `.../Linux/de440/linux_p1550p2650.440`, `header.440`, `testpo.440`.
- Построение утилит из `vendor/jpl_eph/jpl_eph-master/`:
  - MSVC (Developer PowerShell): `cl /EHsc /O2 jpleph.cpp dump_eph.cpp` (или используйте имеющиеся makefile'ы: `linmake`, `makefile` с `MSWIN=1`).
  - MinGW/clang: `g++ -O2 jpleph.cpp dump_eph.cpp -o dump_eph.exe`.
- Проверка данных: запустите `dump_eph.exe <путь к .440> 2451545.0 0` или используйте `testeph` с `testpo.440`.

## Паттерны использования
- Для чтения/вычислений подключайте функции из `jpleph.cpp`; код определяет версию DE и TT‑TDB расширения автоматически (DE430t/DE432t поддерживаются).
- IMCCE INPOP файлы в формате JPL возможны, но имеют сдвиг «полдень» — в `jpleph.cpp` уже есть обработка.
- Если нужен свой диапазон дат или точность — скачайте ASCII и соберите бинарь через `asc2eph` из `vendor/jpl_eph`.

## Изменения и согласование
- Любые сетевые загрузки/объёмы >200 MB согласуйте заранее (например, DE441).
- При добавлении кода — обновляйте `README.md` разделы «как собрать/проверить» для pwsh.
- В коммитах указывайте: какую версию DE и из какого источника использовали (JPL Linux/SunOS, дата скачивания).

## Ссылки
- Обзор и код Project Pluto: https://github.com/Bill-Gray/jpl_eph
- Каталоги JPL (Linux, little‑endian): https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/
- Док по версиям DE и выбору файлов: https://projectpluto.com/jpl_eph.htm#getting_de
