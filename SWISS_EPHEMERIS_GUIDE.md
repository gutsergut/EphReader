# Swiss Ephemeris Integration Guide

## Системы координат

Swiss Ephemeris использует **геоцентрическую систему** (объекты относительно Земли), в то время как JPL DE и EPM используют **барицентрическую систему** (относительно барицентра Солнечной системы).

### Геоцентрическая система (Swiss Eph native)
- **Начало координат**: Центр Земли
- **Тела**: Солнце, Луна, планеты **от Земли**
- **NAIF ID mapping**:
  ```
  Body 10  (Sun)     → ipl=0  (Sun от Земли)
  Body 301 (Moon)    → ipl=1  (Moon от Земли)
  Body 1   (Mercury) → ipl=2  (Mercury от Земли)
  Body 2   (Venus)   → ipl=3  (Venus от Земли)
  Body 4   (Mars)    → ipl=4  (Mars от Земли)
  Body 5   (Jupiter) → ipl=5  (Jupiter от Земли)
  Body 6   (Saturn)  → ipl=6  (Saturn от Земли)
  Body 7   (Uranus)  → ipl=7  (Uranus от Земли)
  Body 8   (Neptune) → ipl=8  (Neptune от Земли)
  Body 9   (Pluto)   → ipl=9  (Pluto от Земли)
  Body 3   (Earth)   → ipl=13 (Earth barycenter)
  ```

### Барицентрическая система (для совместимости с JPL/EPM)
- **Начало координат**: Барицентр Солнечной системы
- **Преобразование**: Инверсия знака для геоцентрических координат
- **Формула**:
  ```
  Pos_barycentric(planet) = Pos_Earth_barycentric - Pos_geocentric(planet)
  Pos_barycentric(Sun) = -Pos_geocentric(Sun)
  ```

## Форматы данных в .eph файлах

### Хранение
**Данные хранятся в native формате источника** (без преобразований):
- Swiss Eph → геоцентрические координаты
- JPL DE → барицентрические координаты
- EPM → барицентрические координаты

### Преобразование в адаптере
Преобразование выполняется **во время чтения** через флаги:

```php
// Геоцентрические (Swiss Eph native)
$result = $reader->compute(10, $jd, frame: 'geocentric');

// Барицентрические (для совместимости с JPL/EPM)
$result = $reader->compute(10, $jd, frame: 'barycentric');
```

## Swiss Ephemeris Flags

### Основные флаги
```c
#define SEFLG_JPLEPH     1   // JPL ephemeris
#define SEFLG_SWIEPH     2   // Swiss Ephemeris
#define SEFLG_MOSEPH     4   // Moshier ephemeris

#define SEFLG_HELCTR     8   // heliocentric position
#define SEFLG_TRUEPOS   16   // true/geometric position
#define SEFLG_J2000     32   // J2000 coordinates
#define SEFLG_NONUT     64   // no nutation
#define SEFLG_SPEED    256   // high speed (daily motion)
#define SEFLG_NOGDEFL  512   // no gravitational deflection
#define SEFLG_NOABERR 1024   // no aberration
#define SEFLG_EQUATORIAL (2*1024)  // equatorial positions
#define SEFLG_XYZ      (4*1024)    // cartesian, not polar, coordinates
#define SEFLG_RADIANS  (8*1024)    // coordinates in radians
#define SEFLG_BARYCTR  (16*1024)   // barycentric positions
#define SEFLG_TOPOCTR  (32*1024)   // topocentric positions
```

### Рекомендуемые комбинации

**Геоцентрические (native)**:
```c
SEFLG_SWIEPH + SEFLG_SPEED = 2 + 256 = 258
```

**Барицентрические**:
```c
SEFLG_SWIEPH + SEFLG_SPEED + SEFLG_BARYCTR = 2 + 256 + 16384 = 16642
```

**Гелиоцентрические**:
```c
SEFLG_SWIEPH + SEFLG_SPEED + SEFLG_HELCTR = 2 + 256 + 8 = 266
```

## Точность Swiss Ephemeris

### Источники данных
- **DE431** (NASA JPL) для планет 1550-2650 AD
- **DE406** для дальних дат
- **JPL Horizons** для астероидов
- **Lunar Laser Ranging** для Луны

### Погрешности (vs JPL DE431)
| Объект  | Погрешность       |
|---------|-------------------|
| Луна    | < 0.001" (3 см)   |
| Солнце  | < 0.001"          |
| Планеты | < 0.001" - 0.01"  |

## Использование

### 1. Прямой FFI доступ (рекомендуется для высокой точности)

```php
require_once 'php/src/SwissEphFFIReader.php';

$reader = new SwissEphFFIReader(
    'vendor/swisseph/swedll64.dll',
    'ephe/'
);

// Геоцентрические (native)
$sun = $reader->compute(10, 2451545.0, frame: 'geocentric');

// Барицентрические
$sun = $reader->compute(10, 2451545.0, frame: 'barycentric');
```

### 2. Конвертированный .eph формат

```php
require_once 'php/src/EphReader.php';

$reader = new EphReader('data/ephemerides/swisseph/swisseph.eph');

// Данные хранятся в геоцентрической системе (native)
$result = $reader->compute(10, 2451545.0);

// Преобразование в барицентрическую систему
$result_bary = $reader->compute(10, 2451545.0, frame: 'barycentric');
```

## Конвертация Swiss Eph → .eph

### Базовая конвертация (геоцентрическая)
```powershell
python tools/swisseph_ffi2eph.py `
  --output data/ephemerides/swisseph/swisseph_geocentric.eph `
  --bodies 1,2,3,4,5,6,7,8,9,10,301 `
  --start-jd 2451545.0 `
  --end-jd 2488070.0 `
  --interval 16.0 `
  --frame geocentric
```

### Барицентрическая конвертация
```powershell
python tools/swisseph_ffi2eph.py `
  --output data/ephemerides/swisseph/swisseph_barycentric.eph `
  --bodies 1,2,3,4,5,6,7,8,9,10,301 `
  --start-jd 2451545.0 `
  --end-jd 2488070.0 `
  --interval 16.0 `
  --frame barycentric
```

## Сравнение с JPL DE440

| Параметр               | Swiss Eph     | JPL DE440     |
|------------------------|---------------|---------------|
| Базовые данные         | DE431 (2013)  | DE440 (2020)  |
| Размер файлов          | 104 MB (.se1) | 97.5 MB       |
| Временной диапазон     | 1800-2400     | 1550-2650     |
| Система координат      | Геоцентр      | Барицентр     |
| Точность (планеты)     | < 0.01"       | < 0.001"      |
| Точность (Луна)        | 3 см (LLR)    | 1 см          |
| Скорость (FFI)         | ~10,000 op/s  | N/A           |
| Скорость (.eph)        | ~20,000 op/s  | ~18,000 op/s  |

## Рекомендации

1. **Для астрологии**: Swiss Ephemeris (геоцентрическая система естественна)
2. **Для астрономии**: JPL DE440 (барицентрическая, новейшие данные)
3. **Для совместимости**: Swiss Eph с барицентрическим флагом
4. **Максимальная точность**: Прямой FFI доступ к Swiss Eph DLL

## Файлы проекта

```
data/ephemerides/swisseph/
  ├── swisseph_geocentric.eph      # Геоцентрические координаты
  └── swisseph_barycentric.eph     # Барицентрические координаты

ephe/
  ├── semo_*.se1     # Луна (104 файла)
  ├── sepl_*.se1     # Планеты (46 файлов)
  └── ...

vendor/swisseph/
  └── swedll64.dll   # Swiss Ephemeris DLL (999 KB)

tools/
  ├── swisseph_standalone.php      # FFI standalone скрипт
  └── swisseph_ffi2eph.py          # Конвертер → .eph

php/src/
  ├── SwissEphFFIReader.php        # FFI reader (прямой доступ к DLL)
  └── EphReader.php                # Binary .eph reader
```

## Примеры

### Сравнение геоцентрических и барицентрических координат
```php
$reader = new SwissEphFFIReader('vendor/swisseph/swedll64.dll', 'ephe/');

$jd = 2451545.0; // J2000.0

// Солнце геоцентрическое (Солнце от Земли)
$sun_geo = $reader->compute(10, $jd, frame: 'geocentric');
// Result: [26476545, -144701405, 584] km

// Солнце барицентрическое (Земля от Солнца, инвертировано)
$sun_bary = $reader->compute(10, $jd, frame: 'barycentric');
// Result: [-26476545, 144701405, -584] km

// Луна всегда геоцентрическая (от Земли)
$moon = $reader->compute(301, $jd);
// Result: [~292k, ~275k, -36k] km
```

### Преобразование координат
```php
// Планета в геоцентрической системе
$mars_geo = $reader->compute(4, $jd, frame: 'geocentric');

// Планета в барицентрической системе
// Mars_bary = Earth_bary - Mars_geo
$earth_bary = getEarthBarycenter($jd); // из JPL DE или вычислить
$mars_bary = [
    $earth_bary['pos'][0] - $mars_geo['pos'][0],
    $earth_bary['pos'][1] - $mars_geo['pos'][1],
    $earth_bary['pos'][2] - $mars_geo['pos'][2],
];
```

## Дополнительные ресурсы

- **Документация**: https://www.astro.com/swisseph/swephprg.htm
- **Теория**: https://www.astro.com/swisseph/swisseph.htm
- **GitHub**: https://github.com/aloistr/swisseph
- **Точность**: https://www.astro.com/swisseph/swephprg.htm#_Toc19111262
