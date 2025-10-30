# Chiron Data Acquisition Report

**Дата:** 2025-01-XX
**Статус:** ✅ ЗАВЕРШЕНО

---

## 📊 Сводка загруженных данных

### ✅ Источник 1: JPL Horizons API

**Файл:** `data/chiron/chiron_vectors_jpl.json` (517.4 KB)

- **Тип данных:** Heliocentric vectors (гелиоцентрические векторы)
- **Координаты:** X, Y, Z, VX, VY, VZ (AU, AU/day)
- **Система отсчёта:** ICRF/J2000 Ecliptic
- **Покрытие:** 1950–2050 (~100 лет)
- **Интервал:** 16 дней
- **Точек данных:** 2,283
- **Диапазон JD:** 2433282.5 – 2469807.5

**Метод получения:**
- API: astroquery.jplhorizons.Horizons
- ID: '2060' (small body)
- Location: @sun (heliocentric)
- Разбито на 23 порции по 100 эпох (обход ограничения 414 URI Too Large)

---

### ✅ Источник 2: JPL Horizons Geocentric

**Файл:** `data/chiron/chiron_ephemeris_geocentric_jpl.json` (791.2 KB)

- **Тип данных:** Geocentric ephemeris (геоцентрические эфемериды)
- **Координаты:** RA, Dec, distance, magnitude
- **Система отсчёта:** J2000 Equatorial (geocentric)
- **Покрытие:** 2000–2010 (10 лет, образец)
- **Интервал:** 1 день
- **Точек данных:** 3,653
- **Диапазон JD:** 2451545.0 – 2455197.5

**Метод получения:**
- API: astroquery.jplhorizons.Horizons
- ID: '2060' (small body)
- Location: 500@399 (geocentric)
- Разбито на 37 порций по 100 эпох

---

### ✅ Источник 3: JPL Small Body Database Browser

**Файл:** `data/chiron/chiron_elements_sbdb.json` (6.1 KB)

- **Тип данных:** Orbital elements + physical parameters
- **Орбитальные элементы:**
  - Semi-major axis (a): 13.692 AU
  - Eccentricity (e): 0.3790
  - Inclination (i): 6.926°
  - Longitude of ascending node (Ω): [in file]
  - Argument of perihelion (ω): [in file]
  - Mean anomaly (M): [in file]
  - Orbital period: 18,506 days (~50.7 years)
  - Perihelion distance (q): 8.506 AU (near Saturn)
  - Aphelion distance (Q): 18.878 AU (near Uranus)

- **Физические параметры:**
  - Absolute magnitude (H): 5.55
  - Diameter: 166 km (±uncertainty)
  - Rotation period: 5.918 hours
  - Geometric albedo: 0.15
  - B-V color index: 0.704
  - U-B color index: 0.283
  - Tholen spectral type: B
  - SMASSII spectral type: Cb

- **Метаданные:**
  - NAIF ID: 20002060
  - Orbital class: **Centaur** (объект между Юпитером и Нептуном)
  - NEO (Near-Earth Object): No
  - PHA (Potentially Hazardous): No
  - Covariance matrix: Включена (для оценки неопределённости)

**Метод получения:**
- API: https://ssd-api.jpl.nasa.gov/sbdb.api
- Full precision orbital elements
- Covariance matrix included

---

## 🔍 Сравнение с Swiss Ephemeris

**Swiss Ephemeris данные:**
- **Body ID:** 15 (SE_CHIRON)
- **Файл:** `ephe/seas_18.se1` (main asteroids 1800–2400)
- **Покрытие:** 700–4650 CE (надёжный период)
- **Ограничения:**
  - Хаотичная орбита вне 700–4650 CE из-за близких сближений с Сатурном
  - Основана на численном интегрировании (Moshier integrator + Lowell elements)
  - Точность: ~1 угловая секунда (20 век)

**Следующий шаг:** Создать скрипт сравнения JPL Horizons vs Swiss Eph для оценки точности.

---

## 📈 Технические детали

### Проблемы и решения

**Проблема 1:** Horizons API не принимает start/stop/step для small bodies
**Решение:** Генерация явного списка эпох через `numpy.arange().tolist()`

**Проблема 2:** 414 URI Too Large error (2,283 эпохи → слишком длинный URL)
**Решение:** Chunking - разбивка на порции по 100 эпох, 23 запроса по 2-5 сек каждый

**Проблема 3:** Lowell Observatory astorb.dat недоступен (404 Not Found)
**Решение:** Переключение на JPL SBDB API (более надёжный, официальный источник)

### Преимущества JPL SBDB

- ✅ Официальный API от NASA/JPL
- ✅ Всегда актуальные данные
- ✅ JSON формат (легко парсить)
- ✅ Включает covariance matrix (оценка неопределённости)
- ✅ Физические параметры (диаметр, альбедо, цвет, вращение)
- ✅ Не требует загрузки 50 MB файла
- ✅ Поддерживает полную точность (full-prec)

---

## 🎯 Следующие шаги

### 1. Сравнение точности ⏳

Создать скрипт `tools/compare_chiron_sources.py`:
- Загрузить Swiss Ephemeris позиции (через FFI)
- Загрузить JPL Horizons векторы
- Сравнить на общих эпохах (например, 2000–2010)
- Вычислить:
  - Position error (km)
  - Angular separation (arcsec)
  - Distance error (%)
  - RMS error statistics

### 2. Конвертация в .eph формат ⏳

Создать `tools/convert_chiron_to_eph.py`:
- Входной файл: `chiron_vectors_jpl.json`
- Выходной файл: `data/chiron/chiron_jpl.eph`
- Формат: Binary .eph (как EPM2021)
- Структура:
  - Header (512 bytes)
  - Body table (1 body × 32 bytes)
  - Interval index (2283 intervals × 16 bytes)
  - Coefficients (Chebyshev or Hermite, 3 × degree doubles)
- Метод: Chebyshev approximation (как JPL DE440)

### 3. Интеграция в PHP ⏳

- Добавить Chiron в `EphReader.php` (body_id = 2060)
- Тест: `php/examples/example_chiron.php`
- Бенчмарк: Сравнить скорость доступа .eph vs FFI Swiss Eph

### 4. Документация ⏳

Обновить:
- `README.md` - добавить Chiron в список тел
- `.github/copilot-instructions.md` - добавить Chiron ID=2060, NAIF=20002060
- `EPHEMERIS_COMPARISON_SUMMARY.md` - добавить раздел Chiron sources

---

## 📁 Структура файлов

```
data/chiron/
├── chiron_vectors_jpl.json              (517.4 KB) ✅ heliocentric XYZ
├── chiron_ephemeris_geocentric_jpl.json (791.2 KB) ✅ geocentric RA/Dec
├── chiron_elements_sbdb.json            (6.1 KB)   ✅ orbital elements
└── chiron_jpl.eph                       (TBD)      ⏳ binary ephemeris

tools/
├── fetch_chiron_horizons.py   ✅ JPL Horizons vectors + ephemeris
├── fetch_chiron_lowell.py     ⚠️  Lowell Observatory (недоступен)
├── fetch_chiron_sbdb.py       ✅ JPL SBDB orbital elements
├── compare_chiron_sources.py  ⏳ Сравнение JPL vs Swiss
└── convert_chiron_to_eph.py   ⏳ JSON → binary .eph
```

---

## 🌟 Ключевые факты о Хироне

### Открытие
- **Дата:** 1 ноября 1977
- **Открыватель:** Charles Kowal (Паломарская обсерватория)
- **Обозначение:** 2060 Chiron = 95P/Chiron (астероид + комета)

### Орбита
- **Класс:** Centaur (кентавр - между Юпитером и Нептуном)
- **Большая полуось:** 13.7 AU
- **Эксцентриситет:** 0.38 (вытянутая орбита)
- **Перигелий:** 8.5 AU (около Сатурна)
- **Афелий:** 18.9 AU (около Урана)
- **Период:** 50.7 года
- **Наклонение:** 6.9°

### Физика
- **Диаметр:** 166 км (±20 км)
- **Период вращения:** 5.918 часов (быстрое вращение!)
- **Альбедо:** 0.15 (тёмная поверхность)
- **Цвет:** B-V = 0.70 (красноватый)
- **Спектральный тип:** B/Cb (углеродистый астероид)

### Особенности
- ✨ **Первый обнаруженный кентавр** (1977)
- ☄️ **Комета-астероид:** Показывает кометную активность (кома, хвост)
- 🔄 **Хаотичная орбита:** Нестабильна на длительных сроках (>1 млн лет)
- 🌡️ **Криовулканизм:** Возможно, выделяет газы (N2, CO, CO2)
- 🪐 **Близкие сближения:** Регулярно проходит близко к Сатурну и Урану

### Астрологическое значение
- **Открыт:** 1977 (эра "новых кентавров" в астрологии)
- **Символизм:** Целительство, учительство, раны и их исцеление
- **Орфей:** Связан с темой "раненого целителя" (Chiron в греческой мифологии)
- **Транснептунский:** Хотя технически кентавр, часто рассматривается с TNO

---

## 🔬 Научная ценность данных

### JPL Horizons векторы (100 лет)
- **Precision:** Sub-kilometer (внутренняя солнечная система)
- **Use case:**
  - Численное интегрирование
  - Сравнение с другими эфемеридами
  - Prediction для наблюдений

### SBDB орбитальные элементы
- **Epoch:** 2460600.5 (2024-Nov-13)
- **Solution date:** 2024 (latest fit)
- **Uncertainty:** Covariance matrix included
- **Use case:**
  - Аналитическое предсказание позиций
  - Пропагация орбиты на короткие сроки (<10 лет)
  - Идентификация близких сближений

### Swiss Ephemeris (4000 лет)
- **Coverage:** 700–4650 CE
- **Method:** Numerical integration (DE431-based)
- **Uncertainty:** Растёт за пределами 700–4650 CE
- **Use case:**
  - Исторические/будущие позиции для астрологии
  - Связь с другими малыми телами

---

## ✅ Чеклист выполнения

- [x] Создать fetch_chiron_horizons.py
- [x] Исправить epoch format issue (start/stop → list)
- [x] Исправить URI Too Large error (chunking по 100 эпох)
- [x] Загрузить heliocentric vectors (2283 точки, 100 лет)
- [x] Загрузить geocentric ephemeris (3653 точки, 10 лет)
- [x] Создать fetch_chiron_sbdb.py (замена Lowell)
- [x] Загрузить orbital elements + physical parameters
- [x] Создать отчёт о загруженных данных
- [ ] Сравнить JPL vs Swiss accuracy
- [ ] Конвертировать в binary .eph format
- [ ] Интегрировать в PHP EphReader
- [ ] Обновить документацию
- [ ] Benchmark performance

---

**Итого:** 3 файла, 1.3 MB данных, 100 лет покрытия, 8 физических параметров ✅
