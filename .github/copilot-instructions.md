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

## Принципы работы

1. **Не коммитьте большие данные**: файлы `data/ephemerides/**` игнорируются в git (см. `.gitignore`), но структура каталогов сохраняется через `.gitkeep`.
2. **Эндиланность**: JPL `Linux/` — little-endian (работает везде через auto-detection в jpl_eph); `SunOS/` — big-endian.
3. **Оптимизированный формат `.eph`**: SPICE BSP 147 MB → `.eph` 27 MB (5.4× меньше) за счёт удаления DAF overhead. Формат разработан для быстрого fseek/unpack в PHP.
4. **Версии эфемерид**:
   - **JPL DE**: DE440 (стандарт, 1550–2650), DE441 (ultra-long), DE431 (legacy).
   - **EPM**: EPM2021 (российская, с улучшенными LLR данными), EPM2021H (ultra-long).

## Ключевые команды (pwsh)

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
- Документация DE versions: https://projectpluto.com/jpl_eph.htm#getting_de

**Russian EPM**:
- EPM2021 главная: https://iaaras.ru/en/dept/ephemeris/epm/2021/
- FTP архив: http://ftp.iaaras.ru/pub/epm/EPM2021/

**SPICE Toolkit**:
- NASA NAIF: https://naif.jpl.nasa.gov/naif/toolkit.html
- DAF format spec: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/daf.html
- SPK format spec: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/spk.html

**CALCEPH**:
- IMCCE CALCEPH: https://www.imcce.fr/recherche/equipes/asd/calceph/
