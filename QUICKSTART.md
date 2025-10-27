# Quick Start Guide

Быстрый старт для работы с оптимизированным форматом `.eph` в PHP.

## Минимальная установка (только PHP)

Если у вас уже есть готовый `.eph` файл:

```powershell
# 1. Установите PHP 8.4+ (если ещё нет)
php -v  # проверьте версию

# 2. Установите Composer-зависимости (опционально для autoload)
composer install

# 3. Используйте в своём коде
php php/examples/example_usage.php
```

## Полная установка (с конвертацией SPICE)

Для создания `.eph` файлов из SPICE BSP:

### Шаг 1: Установите Python-зависимости

```powershell
# Проверьте Python 3.10+
python --version

# Установите библиотеки
pip install -r requirements.txt
```

### Шаг 2: Скачайте SPICE-файлы

**Вариант A: EPM2021 (российская эфемерида, 1787-2214 AD)**

```powershell
# Создайте директорию
mkdir -p data\ephemerides\epm\2021\spice

# Скачайте SPICE BSP (~147 MB)
curl -L http://ftp.iaaras.ru/pub/epm/EPM2021/SPICE/epm2021.bsp `
  -o data\ephemerides\epm\2021\spice\epm2021.bsp
```

**Вариант B: JPL DE440** (используйте если есть SPICE-версия, либо конвертируйте из `.440`)

*(Для JPL DE обычно используют нативный формат через jpl_eph — см. основной README)*

### Шаг 3: Конвертируйте в .eph

```powershell
python tools\spice2eph.py `
  data\ephemerides\epm\2021\spice\epm2021.bsp `
  data\ephemerides\epm\2021\epm2021.eph `
  --bodies 1,2,3,4,5,6,7,8,9,10,399,301 `
  --interval 16.0
```

**Параметры**:
- `--bodies`: NAIF body IDs (1=Mercury, 2=Venus, 3=EMB, 4=Mars, ..., 399=Earth, 301=Moon)
- `--interval`: Интервал в днях (16 — оптимально для большинства задач)

**Результат**: `epm2021.eph` (~27 MB вместо 147 MB SPICE)

### Шаг 4: Используйте в PHP

```php
<?php
require_once 'vendor/autoload.php'; // или require_once 'php/src/EphReader.php';

use Swisseph\Ephemeris\EphReader;

$eph = new EphReader('data/ephemerides/epm/2021/epm2021.eph');

// Земля на J2000.0
$result = $eph->compute(399, 2451545.0);

printf("Позиция (AU): X=%.6f, Y=%.6f, Z=%.6f\n", ...$result['pos']);
printf("Скорость (AU/день): VX=%.6f, VY=%.6f, VZ=%.6f\n", ...$result['vel']);
```

## Benchmark

Запустите встроенный бенчмарк:

```powershell
php php/examples/example_usage.php
```

Ожидаемые результаты на среднем ПК:
- **Время на вычисление**: 0.5–2 ms
- **Throughput**: 500–2000 вычислений/сек

## NAIF Body IDs (справка)

| ID  | Тело             | ID  | Тело             |
|-----|------------------|-----|------------------|
| 0   | SSB (барицентр)  | 199 | Mercury          |
| 1   | Mercury Bary     | 299 | Venus            |
| 2   | Venus Bary       | 399 | Earth            |
| 3   | EMB              | 499 | Mars             |
| 4   | Mars Bary        | 599 | Jupiter          |
| 5   | Jupiter Bary     | 699 | Saturn           |
| 6   | Saturn Bary      | 799 | Uranus           |
| 7   | Uranus Bary      | 899 | Neptune          |
| 8   | Neptune Bary     | 999 | Pluto            |
| 9   | Pluto Bary       | 301 | Moon             |
| 10  | Sun              |     |                  |

**Примечание**: "Bary" = barycenter (барицентр системы тело+спутники). Используйте 399 для Earth, 301 для Moon.

## Troubleshooting

### Ошибка: "calceph not installed"

```powershell
pip install calceph
```

Если установка не удаётся (нужна компиляция):
- **Windows**: Скачайте wheel с https://www.lfd.uci.edu/~gohlke/pythonlibs/#calceph
- **Linux**: `sudo apt install libcalceph-dev python3-calceph`

### Ошибка: "Ephemeris file not found"

Проверьте путь к `.eph` файлу:
```php
$eph = new EphReader('data/ephemerides/epm/2021/epm2021.eph');
```

Используйте абсолютный путь если нужно:
```php
$eph = new EphReader(__DIR__ . '/../../data/ephemerides/epm/2021/epm2021.eph');
```

### Ошибка: "JD outside ephemeris range"

EPM2021: 1787–2214 AD (JD ~2373484 – 2529200)  
Проверьте:
```php
$meta = $eph->getMetadata();
print_r($meta); // покажет startJD и endJD
```

## Дополнительные ресурсы

- **Основной README**: `README.md` — полная документация
- **Copilot инструкции**: `.github/copilot-instructions.md` — правила для AI-агентов
- **Changelog**: `CHANGELOG.md` — история изменений
- **EPM2021**: https://iaaras.ru/en/dept/ephemeris/epm/2021/
- **SPICE Toolkit**: https://naif.jpl.nasa.gov/naif/toolkit.html
- **CALCEPH**: https://www.imcce.fr/recherche/equipes/asd/calceph/
