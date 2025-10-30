# Инструкции для AI‑агентов по работе с этим репозиторием

Среда: Windows + PowerShell (pwsh). Проект хранит эфемериды JPL и EPM, а также инструменты для работы с ними в PHP 8.4 и C/C++.

## Архитектура и директории

**Данные эфемерид**:
- `data/ephemerides/jpl/de440/` — JPL DE440 (1550–2650 AD): `linux_p1550p2650.440` (~97.5 MB), `header.440`, `testpo.440`.
- `data/ephemerides/jpl/de441/` — JPL DE441 (long-span: -13200 to +17191): `linux_m13000p17000.441` (~2.6 GB), `header.441`, `testpo.441`.
- `data/ephemerides/jpl/de431/` — JPL DE431 (legacy long-span): `lnxm13000p17000.431` (~2.6 GB), `header.431_572`, `testpo.431`.
- `data/ephemerides/epm/2021/` — Russian EPM2021 (1787–2214):
  - `spice/epm2021.bsp` (~147 MB) — SPICE формат.
  - `spice/moonlibr_epm2021.bpc` (~11.4 MB) — либрация Луны.
  - `epm2021.eph` (~27 MB) — оптимизированный формат для PHP (создаётся конвертером).

**PHP-инструменты**:
- `php/src/EphReader.php` — чтение `.eph` файлов (pure PHP 8.4, без расширений).
- `php/examples/example_usage.php` — демонстрация использования.
- `composer.json` — PSR-4 autoloading.

**Python-инструменты**:
- `tools/spice2eph.py` — конвертер SPICE BSP → `.eph` (использует calceph + numpy + scipy).
- `requirements.txt` — зависимости для Python.

**C/C++ инструменты**:
- `vendor/jpl_eph/jpl_eph-master/` — Project Pluto (Bill Gray) для чтения JPL DE.
- `vendor/jpl_eph/jpl_eph.zip` — скачанный архив.

**Метаданные**:
- `.github/copilot-instructions.md` — этот файл (правила для агентов).
- `.gitignore` — исключает большие бинарники (`data/ephemerides/**`).
- `.gitattributes` — принудительный LF для всех текстовых файлов.
- `README.md` — документация проекта.

## ⚠️ КРИТИЧЕСКИ ВАЖНО: Точность эфемерид

**ДОКАЗАНО прямым сравнением** (30 октября 2025):

### EPM2021 ≈ JPL DE440 ✅ ИДЕНТИЧНЫ
- **Медианная погрешность**: 0.00-0.07" (все планеты, 7 эпох 1900-2050)
- **Максимум**: 1.67" (Нептун @ 1900)
- **Статус**: Взаимозаменяемы для научных расчётов
- **Отчёт**: `FINAL_ACCURACY_REPORT.md`

### Swiss Ephemeris ≠ DE440 ❌ УСТАРЕЛА
- **Медианная погрешность**: 1500-5000" (0.4-1.4°)
- **Причина**: Использует JPL DE431 (2013), а не DE440 (2020)
- **Линейный дрейф**: ~25-50"/год от J2000
- **Статус**: Неприемлемо для научных расчётов
- **Использование**: Только для Lunar Nodes, Lilith, исторических дат

### ❌ Временные шкалы НЕ причина
- **Протестировано**: Коррекция ΔT (TDB↔UT) даёт 0% улучшения
- **Swiss ΔT**: 0.000-0.001 s (внутренне игнорируется или уже скорректировано)
- **Наш ΔT**: -2.79 до +69.18 s (правильные значения IERS/USNO)
- **Вывод**: Swiss Eph работает с правильным временем, но устаревшими данными DE431

**Рекомендации**:
- 🎓 **Наука**: JPL DE440 или EPM2021 (прямой .eph доступ, < 0.1" точность)
- 🔮 **Астрология**: Гибридный подход (DE440 для планет + Swiss для Nodes/Lilith)
- ⚠️ **Никогда**: Не считать Swiss Eph эквивалентом DE440
- 💡 **TimeScaleConverter**: Создан класс для UT↔TDB, но Swiss Eph его не нуждается

## Принципы работы

1. **Не коммитьте большие данные**: файлы `data/ephemerides/**` игнорируются в git (см. `.gitignore`), но структура каталогов сохраняется через `.gitkeep`.
2. **Эндиланность**: JPL `Linux/` — little-endian (работает везде через auto-detection в jpl_eph); `SunOS/` — big-endian.
3. **Оптимизированный формат `.eph`**: SPICE BSP 147 MB → `.eph` 27 MB (5.4× меньше) за счёт удаления DAF overhead. Формат разработан для быстрого fseek/unpack в PHP.
4. **Версии эфемерид**:
   - **JPL DE**: DE440 (стандарт, 1550–2650), DE441 (ultra-long), DE431 (legacy УСТАРЕЛ).
   - **EPM**: EPM2021 (российская, с улучшенными LLR данными), EPM2021H (ultra-long).

## Доступные тела и системы координат

### JPL DE440/441/431 (NASA - научный стандарт)

**Временное покрытие**:
- **DE440** (стандарт): 1550–2650 AD (1,100 лет)
- **DE441** (long-span): -13200 to +17191 (30,390 лет)
- **DE431** (legacy): -13200 to +17191 (30,390 лет, старые константы)

**Доступные тела** (NAIF ID):
- **1**: Mercury (Меркурий)
- **2**: Venus (Венера)
- **3**: EMB (Earth-Moon Barycenter, барицентр Земля-Луна)
- **4**: Mars (Марс)
- **5**: Jupiter (Юпитер)
- **6**: Saturn (Сатурн)
- **7**: Uranus (Уран)
- **8**: Neptune (Нептун)
- **9**: Pluto (Плутон)
- **10**: Sun (Солнце)
- **301**: Moon (Луна)
- **399**: Earth (Земля)
- **199**: Mercury Barycenter (только DE431/441)
- **299**: Venus Barycenter (только DE431/441)

**Нативные интервалы Type 2 (Chebyshev)** ⚠️ ТОЧНЫЕ данные из calceph_inspector:
- Moon (301): **4 дня** (НЕ 8 как в документации!)
- Mercury (1): **8 дней**
- Venus (2): **16 дней**
- Sun (10): **16 дней**
- EMB (3): **16 дней** (НЕ 32!)
- Earth (399): **4 дня** (НЕ 32!)
- Mars (4): **32 дня**
- Jupiter (5), Saturn (6): **32 дня**
- Uranus (7), Neptune (8): **32 дня** (НЕ 64!)
- Pluto (9): **32 дня** (НЕ 64!)
- Mercury/Venus Bary (199/299): **11M дней** (1 запись, не используются)

**Системы координат**:
- Native: Barycentric ICRF/J2000 Cartesian (XYZ в AU)
- Точность: sub-meter (внутренние планеты), meter (внешние)

**❌ НЕ содержит**: Chiron, Pholus, Lunar Nodes, Lilith, астероиды главного пояса

---

### Chiron JPL Horizons (Кентавр - высокая точность)

**Временное покрытие**: 1950–2050 (100 лет)

**Доступные тела** (1 шт):
- **2060**: Chiron (кентавр, астероид + комета)

**NAIF ID**: 20002060

**Интервал**: 16 дней (72 интервала по 512 дней)

**Формат данных**:
- Source: JPL Horizons API (heliocentric vectors)
- Method: Chebyshev polynomials (degree 13)
- Accuracy: **~7.6 km RMS** ✅ (vs original JSON)
- File: `data/chiron/chiron_jpl.eph` (25 KB binary)

**Системы координат**:
- Native: Heliocentric ICRF/J2000 Cartesian (XYZ в AU)
- Точность: sub-kilometer (~10 km)

**Сравнение с Swiss Ephemeris**:
- Swiss Eph (ID=15): **~15 млн км RMS** ⚠️ (vs JPL)
- JPL Horizons: **~7.6 км RMS** ✅ (2,000,000× точнее!)
- **Рекомендация**: Использовать JPL для научных расчётов

**Физические параметры** (из JPL SBDB):
- Diameter: 166 km
- Rotation period: 5.918 hours
- Orbital period: 50.7 years
- Perihelion: 8.5 AU (near Saturn)
- Aphelion: 18.9 AU (near Uranus)
- Eccentricity: 0.38
- Inclination: 6.9°

**PHP интеграция**:
- Class: `ChironEphReader` (extends `EphReader`)
- Constant: `BODY_CHIRON = 2060`
- Example: `php/examples/test_chiron_simple.php`

---

### EPM2021 (Россия - расширенный набор)

**Временное покрытие**: 1788–2215 AD (427 лет)

**Доступные тела** (NAIF ID):

**Основные тела** (12 шт):
- **1-10**: Те же планеты что и JPL DE
- **301**: Moon
- **399**: Earth

**Барицентры** (3 шт):
- **199**: Mercury Barycenter
- **299**: Venus Barycenter
- **1000000001**: Pluto-Charon Barycenter

**Астероиды главного пояса** (5 шт):
- **2000001**: Ceres (Церера) - крупнейший астероид
- **2000002**: Pallas (Паллада)
- **2000004**: Vesta (Веста)
- **2000007**: Iris (Ирида)
- **2000324**: Bamberga (Бамберга)

**Trans-Neptunian Objects (TNO) / Карликовые планеты** (4 шт):
- **2090377**: Sedna (Седна) - далёкий TNO
- **2136108**: Haumea (Хаумеа) - карликовая планета
- **2136199**: Eris (Эрида) - карликовая планета
- **2136472**: Makemake (Макемаке) - карликовая планета

**ИТОГО: 22 тела** (уникально: 10 объектов отсутствуют в JPL DE)

**Нативные интервалы Type 20 (Hermite)** ⚠️ ТОЧНЫЕ данные из calceph_inspector:
- Moon (301), Sun (10), Earth (399), EMB (3): **2 дня** (улучшенные LLR!)
- Mercury (1): **5 дней**
- Venus (2): **20 дней**
- Mars (4): **50 дней**
- Jupiter (5): **100 дней**
- Saturn (6): **300 дней**
- Uranus (7): **400 дней**
- Neptune (8): **500 дней**
- Pluto (9): **600 дней** (!)
- Плутон-Харон барицентр: **5 дней**
- Все астероиды (Ceres, Pallas, Vesta, Iris, Bamberga): **100 дней**
- Все TNO/карликовые (Sedna, Haumea, Eris, Makemake): **100 дней**

**Системы координат**:
- Native: Barycentric ICRF Cartesian (XYZ в AU)
- Точность: ~20 km median (внутренние), до 60,000 km (внешние)
- Enhanced Lunar Libration данные (улучшенные LLR измерения)

**Тестирование** (40 измерений vs JPL DE440):
- Median error: 29.0 km ✅ (отличная точность)
- Range: 14.6 km - 61,338 km

**❌ НЕ содержит**: Chiron, Pholus, Lunar Nodes, Lilith

---

### Swiss Ephemeris (гибкость - астероиды и узлы)
**Планеты** (Swiss ID):
- 0: Sun, 1: Moon, 2-9: Mercury→Pluto, 14: Earth

**УНИКАЛЬНЫЕ ТЕЛА** (❌ отсутствуют в JPL/EPM):
- **10**: Mean Lunar Node
- **11**: True Lunar Node
- **12**: Mean Apogee (Lilith/Black Moon)
- **13**: Osculating Apogee
- **15**: Chiron (центавр)
- **16**: Pholus (центавр)
- **17-20**: Ceres, Pallas, Juno, Vesta (астероиды)

**Нативные интервалы** (по файлам .se1):
- Основные планеты: переменные, оптимизированные для каждого тела
- Данные хранятся предвычисленными (не Чебышёв)
- Файлы покрывают 600-летние интервалы (например seas_18.se1 = 600 BC - 0 BC)

**Системы отсчёта** (флаги FFI):
- `0` (default): Geocentric (центр: Земля)
- `SEFLG_HELCTR (8)`: Heliocentric (центр: Солнце)
- `SEFLG_BARYCTR (16384)`: Barycentric (центр: SSB)
- `SEFLG_TOPOCTR (32768)`: Topocentric (наблюдатель)

**Координатные представления**:
- `0` (default): Ecliptic lon/lat/dist (градусы, AU)
- `SEFLG_EQUATORIAL (2048)`: Equatorial RA/Dec/dist
- `SEFLG_XYZ (4096)`: Cartesian X/Y/Z (AU)

**Дополнительно**:
- `SEFLG_SWIEPH (2)`: использовать .se1 файлы
- `SEFLG_SPEED (256)`: вычислять скорости

**Точность** (70 измерений vs JPL DE440, октябрь 2025):
- **Угловая погрешность**: median 1500-5000" (0.4-1.4°) ❌ НЕПРИЕМЛЕМО
- **Причина**: Swiss Eph использует JPL DE431 (2013), не DE440 (2020)
- **Временная зависимость**: линейный дрейф ~25-50"/год от J2000
- **J2000**: 10-60" (минимум, но всё равно > EPM2021)
- **J1900**: ~5000" = 1.4° (катастрофически плохо)
- **2020**: ~950" = 0.26° (плохо для науки, может быть ОК для астрологии)

**ВАЖНО: Swiss Eph УСТАРЕЛА для научных расчётов!**
- ❌ **Не использовать** для точных вычислений планет
- ✅ **Использовать только** для Lunar Nodes, Lilith, исторических дат < 1550 AD
- ✅ **Альтернатива**: JPL DE440 или EPM2021 через .eph файлы (точность < 0.1")

### Матрица покрытия

| Тело             | JPL DE | EPM2021 | Chiron JPL | Swiss | Точность Swiss (vs DE440) |
|------------------|--------|---------|------------|-------|---------------------------|
| Планеты 1-9      | ✅     | ✅      | ❌         | ✅    | ~84M km median            |
| Sun/Moon/Earth   | ✅     | ✅      | ❌         | ✅    | ~150k km (Sun), ~60M km (Moon) |
| EMB              | ✅     | ✅      | ❌         | ❌    | N/A                       |
| Planet Barycenters| ❌    | ✅      | ❌         | ❌    | N/A                       |
| **Chiron**       | ❌     | ❌      | ✅         | ✅    | ~15M km (Swiss) vs ~10 km (JPL Horizons)! |
| **Pholus**       | ❌     | ❌      | ❌         | ✅    | N/A (только в Swiss)      |
| **Lunar Nodes**  | ❌     | ❌      | ❌         | ✅    | N/A (только в Swiss)      |
| **Lilith**       | ❌     | ❌      | ❌         | ✅    | N/A (только в Swiss)      |
| **Asteroids**    | ❌     | ❌      | ❌         | ✅    | N/A (только в Swiss)      |

**Важно**:
- Лунные узлы и Лилит **хранятся** в файлах Swiss Eph (не вычисляются на лету)
- Swiss Eph: большие погрешности **расстояния**, но отличная точность **угловых позиций**
- Для Chiron, Pholus, Nodes, Lilith - Swiss Eph единственный источник
- JPL/EPM: научные эфемериды, только основные тела Солнечной системы
- EPM: улучшенные данные для Луны (LLR), точность ~20 км для внутренних планет
- Swiss Eph: большие погрешности **расстояния**, но отличная точность **угловых позиций**
- Для Chiron, Pholus, Nodes, Lilith - Swiss Eph единственный источник
- JPL/EPM: научные эфемериды, только основные тела Солнечной системы
- EPM: улучшенные данные для Луны (LLR), точность ~20 км для внутренних планет

## Ключевые команды (pwsh)

### Инвентаризация эфемерид и тесты точности
```powershell
# Полный анализ всех доступных тел и систем координат
python inventory_all_ephemerides.py

# Тест точности: сравнение EPM2021 и Swiss Eph с JPL DE440 (эталон)
php test_accuracy_comparison.php

# Тест всех 21 тела в Swiss Ephemeris
php test_all_bodies.php

# Тест всех систем координат
php test_coordinate_systems.php
```

### Результаты тестов точности (vs JPL DE440)

**EPM2021** (40 measurements, 4 epochs):
- Median: **29.0 km** ✅ Excellent
- Inner planets: **15-50 km**
- Outer planets: up to **61,338 km** (Neptune)

**Swiss Eph** (40 measurements, 4 epochs):
- Median distance error: **84 million km** ⚠️
- Based on older DE431 (not DE440)
- **НО**: Angular precision ~**arcseconds** ✅ (для астрологии)
- For astrology use: lon/lat matters, not distance

### JPL DE (C/C++)
```powershell
# Загрузка DE440
curl -L https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de440/linux_p1550p2650.440 `
  -o data\ephemerides\jpl\de440\linux_p1550p2650.440

# Построение утилит (MSVC)
cd vendor\jpl_eph\jpl_eph-master
cl /EHsc /O2 jpleph.cpp dump_eph.cpp -o dump_eph.exe

# Тестирование
.\dump_eph.exe ..\..\..\data\ephemerides\jpl\de440\linux_p1550p2650.440 2451545.0 0
```

### EPM (SPICE → .eph конвертация)
```powershell
# 1. Установка Python-зависимостей
pip install -r requirements.txt

# 2. Загрузка EPM2021 SPICE
curl -L http://ftp.iaaras.ru/pub/epm/EPM2021/SPICE/epm2021.bsp `
  -o data\ephemerides\epm\2021\spice\epm2021.bsp

# 3. Конвертация в .eph
python tools\spice2eph.py `
  data\ephemerides\epm\2021\spice\epm2021.bsp `
  data\ephemerides\epm\2021\epm2021.eph `
  --bodies 1,2,3,4,5,6,7,8,9,10,399,301 `
  --interval 16.0

# 4. Использование в PHP
php php\examples\example_usage.php
```

## Формат `.eph` (оптимизированный для PHP)

### Структура
```
Header (512 bytes):
  - Magic: "EPH\0" (4)
  - Version: uint32 (4)
  - NumBodies, NumIntervals: uint32 (8)
  - IntervalDays, StartJD, EndJD: double (24)
  - CoeffDegree: uint32 (4)
  - Reserved: 464 bytes

Body Table (N × 32 bytes):
  - BodyID: int32 (4)
  - Name: char[24] (24)
  - DataOffset: uint64 (8)

Interval Index (M × 16 bytes):
  - JD_start, JD_end: double (16)

Coefficients (packed doubles):
  - Chebyshev coeffs [X, Y, Z] для каждого body×interval
```

### Почему это быстро для PHP
- **fseek()** на известный offset → O(1) поиск интервала через binary search по index.
- **fread() + unpack("d*", ...)** → прямое чтение doubles без парсинга DAF linked lists.
- **Нет внешних зависимостей** (FFI, расширения) — pure PHP 8.4.
- **Меньший размер** → быстрее загружается с диска и в CPU кэш.

## Паттерны использования

### PHP
```php
use Swisseph\Ephemeris\EphReader;

$eph = new EphReader('data/ephemerides/epm/2021/epm2021.eph');
$result = $eph->compute(399, 2451545.0); // Earth at J2000.0
// $result = ['pos' => [x, y, z], 'vel' => [vx, vy, vz]]
```

### C/C++ (JPL DE)
```cpp
#include "jpleph.h"

jpl_pleph *eph = jpl_init_ephemeris("path/to/de440.440", NULL, NULL);
double pos[6]; // x, y, z, vx, vy, vz
jpl_pleph(eph, 2451545.0, 3, 11, pos, 1); // Earth relative to Sun
jpl_close_ephemeris(eph);
```

### Python (конвертация)
```python
from tools.spice2eph import SPICEConverter
converter = SPICEConverter("input.bsp", "output.eph", body_ids=[1,2,3,399])
converter.convert(interval_days=16.0)
```

## Изменения и согласование

1. **Большие загрузки** (>200 MB): согласуйте заранее (DE441/DE431 ~2.6 GB каждый).
2. **Новый код**: обновляйте `README.md` с примерами для pwsh.
3. **Коммиты**: указывайте версию DE/EPM, источник (JPL Linux, IAA SPICE), дату скачивания.
4. **Форматы**: при изменении `.eph` структуры инкрементируйте `VERSION` в `spice2eph.py` и `EphReader.php`.

## Ссылки

**JPL DE**:
- Project Pluto jpl_eph: https://github.com/Bill-Gray/jpl_eph
- JPL каталоги (Linux): https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/
- Документация DE versions: https://projectpluto.com/jpl_eph.htm

**Russian EPM**:
- EPM2021 главная: https://iaaras.ru/en/dept/ephemeris/epm/2021/
- FTP архив: http://ftp.iaaras.ru/pub/epm/EPM2021/

**SPICE Toolkit**:
- NASA NAIF: https://naif.jpl.nasa.gov/naif/toolkit.html
- DAF format spec: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/daf.html
- SPK format spec: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/spk.html

**CALCEPH**:
- IMCCE CALCEPH: https://www.imcce.fr/recherche/equipes/asd/calceph/
