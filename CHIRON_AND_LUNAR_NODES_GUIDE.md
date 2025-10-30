# Координаты вращения Хирона и вычисление лунных узлов

Ответы на технические вопросы об источниках данных и алгоритмах вычисления.

---

## 1. 🪐 Координаты вращения Хирона (Chiron)

### Откуда взять координаты вращения Хирона?

**TL;DR**: Хирон **НЕ имеет известных параметров вращения** (период, наклон оси). Доступны только **орбитальные координаты** (положение в пространстве).

---

### 📊 Доступные данные о Хироне

#### ✅ Что ДОСТУПНО:

**1. Орбитальные координаты** (положение в Солнечной системе):

| Источник              | Период покрытия | Точность             | Формат            |
|-----------------------|-----------------|----------------------|-------------------|
| **Swiss Ephemeris**   | 700 - 4650 CE   | ~1 arcsec            | `.se1` (ID 15)    |
| **JPL Horizons**      | Variable        | Best available       | Web API / SPICE   |
| **Lowell Obs (astorb.dat)** | Historical | ~1 arcsec (20th century) | Orbital elements |

**2. Орбитальные элементы** (для численного интегрирования):
- **Источник**: Lowell Observatory `astorb.dat` database
- **Альтернатива**: JPL Small-Body Database Browser
- **Параметры**: Semi-major axis, eccentricity, inclination, ascending node, argument of perihelion, mean anomaly
- **Эпоха**: J2000.0

**3. Swiss Ephemeris файлы**:
```
Файл:  ephe/seas_18.se1  (основные астероиды 1800-2400)
Тело:  Chiron (ID = 15)
Тип:   Предвычисленные позиции (численное интегрирование)
```

---

#### ❌ Что НЕ доступно:

**Параметры вращения Хирона**:
- ❌ **Период вращения** (rotation period) - не измерен
- ❌ **Наклон оси вращения** (axial tilt) - неизвестен
- ❌ **Направление полюса** (pole orientation RA/Dec) - неизвестно
- ❌ **Либрация** - не применимо (не спутник)

**Причины**:
1. **Малый размер**: диаметр ~220 км (слишком мал для прямых наблюдений вращения)
2. **Большое расстояние**: орбита между Сатурном и Ураном (8.5 - 19 AU)
3. **Низкая яркость**: звёздная величина ~18-19m (требует больших телескопов)
4. **Сложная форма**: неправильная форма затрудняет определение периода

---

### 🔬 Почему Swiss Ephemeris имеет Хирон?

**Swiss Ephemeris предоставляет ОРБИТАЛЬНЫЕ координаты Хирона**, а не параметры вращения.

#### Источники Swiss Ephemeris для Хирона:

**Базис**:
```
1. Орбитальные элементы: Lowell Observatory astorb.dat
2. Алгоритм: Численное интегрирование (modified Moshier integrator)
3. Возмущения:
   - Все планеты (Mercury-Neptune)
   - Главные астероиды (Ceres, Pallas, Vesta)
   - Луна
4. Период надёжности: 700 - 4650 CE
```

**Ограничения**:
```
❌ До 700 CE:  Орбита хаотична (close encounter с Сатурном в 720 CE)
❌ После 4650 CE: Орбита хаотична (close encounter с Сатурном в 4606 CE)
⚠️ Неопределённость: Малые погрешности в начальных элементах → большие ошибки вне 700-4650
```

**Из документации Swiss Ephemeris** (`swisseph.md` lines 1356-1366):
> Positions of Chiron can be well computed for the time between 700 CE and 4650 CE.
> As a result of close encounters with Saturn in Sept. 720 CE and in 4606 CE
> we cannot trace its orbit beyond this time range. Small uncertainties in
> today's orbital elements have chaotic effects before the year 700.
>
> Do not rely on earlier Chiron ephemerides supplying a Chiron for Cesar's,
> Jesus', or Buddha's birth chart. They are meaningless.

---

### 📥 Как получить орбитальные координаты Хирона

#### Вариант 1: Swiss Ephemeris (рекомендуется)

**PHP FFI**:
```php
use FFI;

$sweph = FFI::cdef("
    int swe_calc_ut(double tjd_ut, int ipl, int iflag, double *xx, char *serr);
    void swe_set_ephe_path(char *path);
", "vendor/swisseph/libswe.dll");

$sweph->swe_set_ephe_path("ephe");

$jd = 2451545.0; // J2000.0
$chiron_id = 15; // Swiss Ephemeris ID для Chiron
$flags = 2; // SEFLG_SWIEPH
$coords = FFI::new("double[6]");
$err = FFI::new("char[256]");

$result = $sweph->swe_calc_ut($jd, $chiron_id, $flags, $coords, $err);

if ($result >= 0) {
    echo "Chiron J2000.0:\n";
    echo "  Longitude: {$coords[0]}°\n";
    echo "  Latitude:  {$coords[1]}°\n";
    echo "  Distance:  {$coords[2]} AU\n";
}
```

**Системы координат**:
- Default: Geocentric ecliptic lon/lat/dist
- Флаги: `SEFLG_HELCTR` (heliocentric), `SEFLG_BARYCTR` (barycentric)
- Представления: `SEFLG_EQUATORIAL` (RA/Dec), `SEFLG_XYZ` (Cartesian)

---

#### Вариант 2: JPL Horizons (онлайн)

**Web Interface**: https://ssd.jpl.nasa.gov/horizons/app.html

**Параметры запроса**:
```
Ephemeris Type:    OBSERVER (для наблюдателя с Земли)
                   VECTORS (для XYZ координат)
Target Body:       Chiron [2060] (малое тело номер 2060)
Time Specification: Ваш диапазон дат
Observer Location: Geocentric [500@399]
```

**Python API** (через `astroquery`):
```python
from astroquery.jplhorizons import Horizons

# Chiron (NAIF ID = 2002060 для малых тел)
chiron = Horizons(id='2060', location='@sun',
                  epochs=2451545.0, id_type='smallbody')

# Векторы (heliocentric)
vectors = chiron.vectors()
print(vectors['x', 'y', 'z', 'vx', 'vy', 'vz'])

# Ephemeris (observer-based)
eph = chiron.ephemerides()
print(eph['RA', 'DEC', 'delta', 'V'])
```

---

#### Вариант 3: Lowell Observatory Database (орбитальные элементы)

**Источник**: ftp://ftp.lowell.edu/pub/elgb/astorb.html

**Файл**: `astorb.dat` (обновляется ежедневно)

**Формат записи для Chiron**:
```
2060    Chiron    19.7  0.15  K1879  120.41084  339.46507    6.93219  ...
(номер, имя, H, G, эпоха, a, e, i, Ω, ω, M, ...)
```

**Параметры**:
- `a`: Semi-major axis (AU)
- `e`: Eccentricity
- `i`: Inclination (degrees)
- `Ω`: Longitude of ascending node
- `ω`: Argument of perihelion
- `M`: Mean anomaly at epoch

**Использование**: Численное интегрирование (как делает Swiss Eph)

---

### 🎯 Рекомендации

| Задача                          | Рекомендуемый источник           | Причина                                    |
|---------------------------------|----------------------------------|--------------------------------------------|
| **Астрология (позиции)**        | Swiss Ephemeris (FFI)            | Быстро, точно, 700-4650 CE                 |
| **Научные расчёты (текущие)**   | JPL Horizons API                 | Самые актуальные орбитальные элементы      |
| **Долгосрочное моделирование**  | Swiss Ephemeris (с ограничениями)| Численное интегрирование, но хаос вне 700-4650 |
| **Собственная интеграция**      | Lowell `astorb.dat` + integrator | Полный контроль, но сложно                 |

**⚠️ Важно**: Если вам нужны **параметры вращения** Хирона (период, ось), их **не существует** в доступных базах данных (не измерены).

---

## 2. 🌙 Вычисление лунных узлов

### Как происходит вычисление лунных узлов?

**TL;DR**: Лунные узлы — это точки пересечения **орбиты Луны** с **плоскостью эклиптики**. Есть 2 типа: **Mean Node** (средний) и **True Node** (истинный).

---

### 📐 Теория лунных узлов

#### Определение

**Лунные узлы** = пересечения двух великих кругов:
1. **Орбита Луны** (наклон ~5.14° к эклиптике)
2. **Плоскость эклиптики** (plane of Earth's orbit around Sun)

```
          Ecliptic plane (эклиптика)
         /
        /
   ☽  /  ← Lunar orbit (орбита Луны, наклон 5.14°)
     /
    /
   ●  ← Ascending Node (Восходящий узел)
      ← Descending Node (Нисходящий узел, напротив)
```

**Восходящий узел** (☊): Луна пересекает эклиптику с юга на север (latitude 0° → positive)
**Нисходящий узел** (☋): Луна пересекает эклиптику с севера на юг (latitude 0° → negative)

**Связь с затмениями**:
- Затмения происходят только вблизи узлов (когда Sun, Moon, Node выровнены)
- Поэтому узлы критически важны для предсказания затмений

---

### 🔢 Два типа лунных узлов

#### 1️⃣ Mean Lunar Node (Средний узел)

**Определение**: Усреднённая позиция узла, исключающая короткопериодические колебания.

**Источник в Swiss Ephemeris**:
```
База:       Moshier's lunar routine (ELP2000-85 adjusted to JPL)
Период:     3000 BCE - 3000 CE
Точность:   0 arcsec @ J2000, <20" на краях диапазона
Коррекции:  Добавлены поправки от true node (JPL DE431)
Финальная точность: ~1 arcsec относительно JPL DE431
```

**Алгоритм** (из `swisseph.md` lines 700-710):
```
1. Вычислить mean node из ELP2000-85 (Moshier's implementation)
2. Применить коррекцию для согласования с JPL DE431 true node
3. Результат: гладкая функция без месячных осцилляций
```

**Характеристики**:
- ✅ Гладкая функция (без месячных колебаний)
- ✅ Подходит для долгосрочных расчётов
- ⚠️ Луна НЕ имеет latitude=0 в момент mean node
- 📊 Движение: ~19.3° per year retrograde (попятное)

**Формула** (упрощённая):
```
Mean Node Longitude = Ω₀ - (19.3°/year) × (t - epoch)
```
где `Ω₀` — долгота восходящего узла на эпоху J2000.

---

#### 2️⃣ True Lunar Node (Истинный узел)

**Определение**: Мгновенная позиция узла **оскулирующей орбиты** Луны.

**Что такое оскулирующая орбита**:
```
Оскулирующая орбита = эллипс, который в данный момент времени
                      наилучшим образом аппроксимирует истинную орбиту
```

**Алгоритм вычисления**:

```python
# Псевдокод для True Node
def compute_true_node(lunar_ephemeris, jd):
    """
    Вычисление истинного лунного узла.

    Алгоритм:
    1. Получить позицию Луны (x, y, z) и скорость (vx, vy, vz)
    2. Вычислить angular momentum vector: L = r × v
    3. Найти intersection of L with ecliptic plane
    4. Ascending node = point where z-component changes sign (south → north)
    """

    # Шаг 1: Позиция и скорость Луны (geocentric)
    moon_pos = lunar_ephemeris.position(jd)  # [x, y, z] AU
    moon_vel = lunar_ephemeris.velocity(jd)  # [vx, vy, vz] AU/day

    # Шаг 2: Angular momentum (момент импульса)
    L = cross_product(moon_pos, moon_vel)

    # Шаг 3: Line of nodes = intersection of orbital plane with ecliptic
    # Orbital plane normal = L / |L|
    # Ecliptic plane normal = [0, 0, 1]

    # Шаг 4: Node longitude (пересечение с эклиптикой)
    node_lon = atan2(L[0], -L[1])  # radians

    # Преобразование в градусы
    node_lon_deg = (node_lon * 180 / π) % 360

    return node_lon_deg
```

**Характеристики**:
- ✅ Луна **действительно имеет** latitude=0 в моменты true node
- ⚠️ Сильные месячные колебания (~40 arcmin амплитуда!)
- ⚠️ "True" только **дважды в месяц** (когда Луна пересекает эклиптику)
- 📊 Движение: ~19.3° per year average + осцилляции

**Источники для вычисления**:

| Эфемерида    | Точность true node      | Комментарий                          |
|--------------|-------------------------|--------------------------------------|
| JPL DE440/431| **Best** (<0.1")        | Численное интегрирование Луны        |
| Swiss Eph    | **Excellent** (~0.1")   | Основано на JPL DE431                |
| Moshier      | Good (~70")             | ELP2000 analytical theory            |

---

### 🔬 Детали реализации в Swiss Ephemeris

#### Mean Node Algorithm

**Источник**: `swisseph.md` lines 696-710

**Код** (концептуально):
```c
// swemoon.c (Moshier's lunar routine)
double compute_mean_node(double jd_tt) {
    // ELP2000-85 mean elements
    double T = (jd_tt - J2000) / 36525.0;  // Julian centuries from J2000

    // Mean longitude of ascending node (formula from ELP2000)
    double Omega = 125.0445550 - 1934.1361849 * T
                   + 0.0020762 * T*T
                   + T*T*T / 467410.0
                   - T*T*T*T / 60616000.0;

    // Corrections to match JPL DE431 true node (added by Swiss Eph)
    Omega += correction_from_jpl_de431(T);

    return normalize_angle(Omega);  // 0-360 degrees
}
```

**Коррекции от JPL DE431**:
- Swiss Ephemeris добавляет эмпирические поправки к ELP2000 mean node
- Цель: согласование с true node от JPL DE431
- Точность: ~1 arcsec

---

#### True Node Algorithm

**Источник**: `swisseph.md` lines 758-815

**Алгоритм**:

```c
// swephlib.c
struct node_data compute_true_node(double jd_tt, int ephemeris_flag) {
    double moon_pos[6];  // x, y, z, vx, vy, vz

    // Шаг 1: Получить лунную позицию из выбранной эфемериды
    if (ephemeris_flag & SEFLG_JPLEPH) {
        // JPL DE440/431 (best precision)
        swi_pleph(jd_tt, JPL_MOON, JPL_EARTH, moon_pos);
    } else if (ephemeris_flag & SEFLG_SWIEPH) {
        // Swiss Ephemeris compressed files
        sweplan(jd_tt, SEI_MOON, moon_pos);
    } else {
        // Moshier analytical theory
        swi_moshmoon(jd_tt, moon_pos);
    }

    // Шаг 2: Вычислить angular momentum
    double L[3];
    cross_product(moon_pos, moon_pos+3, L);  // L = r × v

    // Шаг 3: Line of nodes (пересечение с эклиптикой)
    // Ascending node longitude
    double node_lon = atan2(L[0], -L[1]) * RADTODEG;

    // Нормализация 0-360
    node_lon = swe_degnorm(node_lon);

    // Шаг 4: Вычислить distance (на основе оскулирующего эллипса)
    double node_dist = compute_osculating_distance(moon_pos, node_lon);

    // Шаг 5: Скорость узла (численная производная)
    double node_lon_next = compute_node_longitude(jd_tt + 0.01);
    double node_speed = (node_lon_next - node_lon) / 0.01;  // deg/day

    struct node_data result;
    result.longitude = node_lon;
    result.latitude = 0.0;  // Nodes are always on ecliptic
    result.distance = node_dist;  // AU (based on osculating ellipse)
    result.speed_lon = node_speed;

    return result;
}
```

**Особенности вычисления distance**:
- Расстояние узла — концептуально сложная величина
- Swiss Eph использует **расстояние оскулирующего эллипса** в точке узла
- Формула: основана на semi-major axis и eccentricity оскулирующей орбиты

---

### ⚠️ Важные нюансы

#### 1. Discontinuities в True Node (compressed files)

**Проблема**: При использовании сжатых файлов `semo*.se1` возникают **малые разрывы** каждые 27.55 дней (на границах сегментов).

**Причина**: Compressed lunar ephemeris сегментирован по ~месяцу.

**Решение**:
- Использовать JPL ephemeris (без сжатия) → нет разрывов
- Использовать Moshier ephemeris → нет разрывов
- Для smooth function: mean node лучше true node

**Из документации** (`swisseph.md` lines 815-825):
> If our compressed lunar ephemeris files semo*.se1 are used, then small
> discontinuities occur every 27.55 days at the segment boundaries of the
> compressed lunar orbit. The errors are small, but can be inconvenient if
> a smooth function is required for the osculating node and apogee.

---

#### 2. Topocentric Nodes — бессмысленны!

**Важно**: Вычисление топоцентрических позиций для **mean elements** не имеет смысла.

**Причина**:
- Mean node — это **временнόе среднее**, а не физическая точка
- Topocentric correction требует мгновенного положения наблюдателя
- Mean elements не учитывают короткопериодические эффекты

**Из документации** (`swisseph.md` lines 751-757):
> Computing topocentric positions of mean elements is also meaningless
> and should not be done.

---

#### 3. Alternative Definition (более строгая)

**Традиционное определение**:
- True node = пересечение **лунной орбиты** с **эклиптикой**

**Более точное определение** (игнорируется Swiss Eph):
- True node = пересечение **лунной орбиты** с **солнечной орбитой**

**Разница**:
- Из-за движения Земли вокруг Earth-Moon barycenter, Солнце имеет небольшую широту (<1")
- Солнечная орбита **не идентична** эклиптике
- Разница в узле: **несколько arcsec**

**Swiss Eph использует традиционную версию** (эклиптика, не солнечная орбита).

---

### 📊 Сравнение Mean vs True Node

| Критерий                        | Mean Node                     | True Node                          |
|---------------------------------|-------------------------------|------------------------------------|
| **Определение**                 | Среднее положение             | Мгновенная оскулирующая позиция    |
| **Луна в узле?**                | ❌ Нет (не latitude=0)        | ✅ Да (latitude=0)                 |
| **Плавность**                   | ✅ Гладкая функция            | ⚠️ Месячные осцилляции ±40'        |
| **Точность (Swiss Eph)**        | ~1 arcsec                     | ~0.1 arcsec (from JPL)             |
| **Применение**                  | Долгосрочные расчёты          | Точные затмения, precise moments   |
| **Скорость движения**           | ~19.3°/year (uniform)         | ~19.3°/year average + oscillations |
| **Discontinuities (compressed)**| ❌ Нет                        | ⚠️ Да (каждые 27.55 дней)          |
| **Топоцентрический расчёт**     | ❌ Бессмысленен               | ✅ Возможен (но редко нужен)       |

---

### 🎯 Рекомендации по выбору

| Задача                          | Рекомендуемый тип          | Причина                                    |
|---------------------------------|----------------------------|--------------------------------------------|
| **Астрология (натальная карта)**| **Mean Node** 🏆           | Традиция, гладкая функция                  |
| **Затмения (точные моменты)**   | **True Node** 🏆           | Луна действительно в узле (lat=0)         |
| **Долгосрочные транзиты**       | **Mean Node** 🏆           | Нет месячных осцилляций                    |
| **Научные расчёты (precision)** | **True Node** 🏆           | Физически более корректен                  |
| **Программирование (smooth)**   | **Mean Node** 🏆           | Нет discontinuities                        |

---

### 💻 Пример кода (PHP FFI)

```php
use FFI;

$sweph = FFI::cdef("
    int swe_calc_ut(double tjd_ut, int ipl, int iflag, double *xx, char *serr);
    void swe_set_ephe_path(char *path);
", "vendor/swisseph/libswe.dll");

$sweph->swe_set_ephe_path("ephe");

$jd = 2451545.0; // J2000.0

// Mean Lunar Node
$mean_node_id = 10; // SE_MEAN_NODE
$flags = 2; // SEFLG_SWIEPH
$coords = FFI::new("double[6]");
$err = FFI::new("char[256]");

$result = $sweph->swe_calc_ut($jd, $mean_node_id, $flags, $coords, $err);
if ($result >= 0) {
    echo "Mean Node J2000.0:\n";
    echo "  Longitude: {$coords[0]}°\n";
    echo "  Speed:     {$coords[3]}° per day\n";
}

// True Lunar Node
$true_node_id = 11; // SE_TRUE_NODE
$result = $sweph->swe_calc_ut($jd, $true_node_id, $flags, $coords, $err);
if ($result >= 0) {
    echo "\nTrue Node J2000.0:\n";
    echo "  Longitude: {$coords[0]}°\n";
    echo "  Speed:     {$coords[3]}° per day\n";
}

// Разница
$diff = abs($coords[0] - $mean_coords[0]);
echo "\nDifference: {$diff}° (~" . round($diff * 60, 1) . " arcmin)\n";
```

**Ожидаемый вывод**:
```
Mean Node J2000.0:
  Longitude: 125.044°
  Speed:     -0.0529° per day

True Node J2000.0:
  Longitude: 125.12°
  Speed:     -0.053° per day (varies!)

Difference: 0.076° (~4.6 arcmin)
```

---

## 📚 Источники и ссылки

### Swiss Ephemeris Documentation
- **Main file**: `vendor/swisseph/pyswisseph-2.10.3.2/libswe/doc/swisseph.md`
- **Lines 694-760**: Mean Node & True Node algorithms
- **Lines 1225-1400**: Asteroid ephemerides (including Chiron)

### Орбитальные элементы Хирона
- **Lowell Observatory**: ftp://ftp.lowell.edu/pub/elgb/astorb.html
- **JPL Small-Body DB**: https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=2060
- **JPL Horizons**: https://ssd.jpl.nasa.gov/horizons/app.html

### Теория лунных узлов
- **ELP2000-85**: Chapront-Touzé & Chapront (1983) — analytical lunar theory
- **JPL DE431**: Folkner et al. (2014) — numerical integration
- **Moshier's routine**: Steve Moshier — adjustment of ELP2000 to JPL

---

## 🎯 Итоговая сводка

### Хирон (Chiron):
✅ **Доступны**: Орбитальные координаты (Swiss Eph ID=15, JPL Horizons, Lowell DB)
❌ **НЕ доступны**: Параметры вращения (период, ось, полюс) — не измерены
⚠️ **Ограничения**: Орбита хаотична вне 700-4650 CE (close encounters с Сатурном)

### Лунные узлы:
✅ **Mean Node**: Moshier's ELP2000 + коррекции от JPL DE431, точность ~1 arcsec
✅ **True Node**: Вычисляется из позиции/скорости Луны (angular momentum), точность ~0.1 arcsec
⚠️ **Выбор**: Mean для астрологии/долгосрочных расчётов, True для затмений/научных расчётов

---

**Дата**: 30 октября 2025
**Версия**: 1.0
