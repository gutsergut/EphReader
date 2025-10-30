# Гибридный Интегратор - Краткая Инструкция

## Что это?

**Hybrid RK4 Integrator** - инструмент для интеграции орбит кентавров и TNO из орбитальных элементов с использованием:
- ✅ RK4 integrator (4-го порядка)
- ✅ Релятивистские поправки (Schwarzschild)
- ✅ 8 планетных возмущений (Mercury-Neptune)
- ✅ Опционально: DE440 precise planet positions

**Точность**: ~1.4° (simplified planets) → **0.1-0.5° (with DE440)**

---

## Быстрый старт

### 1. Установка зависимостей

```powershell
# Python packages
pip install numpy scipy

# Optional: calceph for DE440 planets (much better accuracy)
pip install calceph
```

### 2. Подготовка данных

Нужны орбитальные элементы в JSON формате:

```json
{
  "epoch_jd": 2461001.5,
  "elements": {
    "e": 0.3789792,
    "a": 13.69,
    "i": 6.926,
    "om": 209.29854,
    "w": 339.25364,
    "ma": 212.83973,
    "per": 50.67
  }
}
```

**Источники элементов**:
- Minor Planet Center MPCORB.DAT (используйте `parse_mpcorb_chiron.py`)
- JPL Small-Body Database (используйте `fetch_sbdb_elements.py`)
- Ручной ввод из каталогов

### 3. Запуск интеграции

#### Без DE440 (simplified planets):
```powershell
python tools/integrate_chiron_hybrid.py `
  data/chiron/chiron_mpc.json `
  dummy.eph `
  2451545.0 2466154.5 16.0 `
  data/chiron/chiron_hybrid.json
```

**Результат**: ~1.4° точность (приемлемо для астрологии)

#### С DE440 (best accuracy):
```powershell
# Сначала убедитесь что calceph установлен
pip install calceph

# Запустите с DE440
python tools/integrate_chiron_hybrid.py `
  data/chiron/chiron_mpc.json `
  data/ephemerides/jpl/de440/linux_p1550p2650.440 `
  2451545.0 2466154.5 16.0 `
  data/chiron/chiron_hybrid_de440.json
```

**Ожидаемый результат**: ~0.1-0.5° точность ✅

---

## Параметры командной строки

```
integrate_chiron_hybrid.py <elements.json> <de440.eph> <start_jd> <end_jd> <step_days> [output.json]
```

| Параметр | Описание | Пример |
|----------|----------|--------|
| `elements.json` | Файл с орбитальными элементами | `chiron_mpc.json` |
| `de440.eph` | DE440 файл (или dummy если нет calceph) | `linux_p1550p2650.440` |
| `start_jd` | Начальная дата (Julian Day) | `2451545.0` (J2000.0) |
| `end_jd` | Конечная дата (Julian Day) | `2466154.5` (J2040.0) |
| `step_days` | Шаг интеграции в днях | `16.0` (рекомендуется) |
| `output.json` | Выходной файл (опционально) | `chiron_hybrid.json` |

---

## Интерпретация результатов

### Выходной JSON формат:

```json
{
  "source": "Hybrid integrator: MPC elements + DE440/simplified planets + RK4 + relativistic corrections",
  "method": "DE440",
  "integration": {
    "start_jd": 2451545.0,
    "end_jd": 2466154.5,
    "step_days": 16.0,
    "n_points": 1804
  },
  "positions": [
    {
      "jd": 2451545.0,
      "lon": 250.27,
      "lat": 4.55,
      "dist": 9.972
    },
    ...
  ]
}
```

### Поля:
- `jd`: Julian Day (TDB time scale)
- `lon`: Ecliptic longitude (degrees, 0-360)
- `lat`: Ecliptic latitude (degrees, -90 to +90)
- `dist`: Heliocentric distance (AU)

---

## Сравнение с JPL HORIZONS

Используйте `compare_chiron_4way.php` для проверки точности:

```powershell
php php/examples/compare_chiron_4way.php
```

**Ожидаемые результаты**:
- **Simplified planets**: ~1.4° angular error
- **DE440 planets**: ~0.1-0.5° angular error
- **JPL HORIZONS**: ~0.0001° (baseline)

---

## Когда использовать?

### ✅ Используйте Hybrid RK4:
- Образовательные цели (демонстрация численных методов)
- Когда JPL HORIZONS данные недоступны
- Астрологические расчеты (если 0.1-0.5° достаточно)
- Тестирование различных элементов

### ❌ НЕ используйте Hybrid RK4:
- Научные публикации (только JPL HORIZONS!)
- Высокоточная астрометрия
- Когда есть доступ к JPL HORIZONS (всегда лучше)

---

## Ограничения

### Текущая версия:
1. **RK4 fixed-step** (не адаптивный шаг)
2. **Simplified planets** если нет calceph
3. **Не учитывает**:
   - Asteroid perturbations (Ceres, Pallas, Vesta)
   - Planetary oblateness (J2, J4 terms)
   - Tidal effects
   - Solar radiation pressure
4. **Точность деградирует** при длительной пропагации (>50 лет от эпохи)

### Планы улучшения:
- [ ] RK45 adaptive integrator (Dormand-Prince)
- [ ] Asteroid perturbations (top 3)
- [ ] Error estimation and uncertainty propagation
- [ ] Output в .eph формат для `ChironEphReader.php`

---

## Troubleshooting

### Q: "calceph not available" warning
**A**: Интегратор работает с simplified planets (~1.4° error). Для лучшей точности:
```powershell
pip install calceph
```

### Q: "Semi-major axis 'a' is None"
**A**: Добавьте поле `"per"` (period in years) в elements JSON. Формула: `a = T^(2/3)`

### Q: Ошибка "Failed to get planet position"
**A**: Проверьте что DE440 файл существует и доступен. Или используйте simplified mode (любой dummy путь).

### Q: Интеграция очень медленная
**A**: Увеличьте `step_days` (рекомендуется 16.0). Меньше = точнее, но медленнее.

### Q: Результаты отличаются от JPL на >5°
**A**: Нормально! Это элементный метод, не full N-body. Для science используйте JPL HORIZONS.

---

## Примеры использования

### 1. Chiron 1950-2050
```powershell
python tools/integrate_chiron_hybrid.py `
  data/chiron/chiron_mpc.json `
  data/ephemerides/jpl/de440/linux_p1550p2650.440 `
  2433282.5 2469807.5 16.0 `
  data/chiron/chiron_1950_2050.json
```

### 2. Single epoch test
```powershell
python tools/integrate_chiron_hybrid.py `
  data/chiron/chiron_mpc.json `
  data/ephemerides/jpl/de440/linux_p1550p2650.440 `
  2451545.0 2451545.0 1.0 `
  data/chiron/chiron_j2000_test.json
```

### 3. Другой кентавр (если есть элементы)
```powershell
# 1. Получите элементы из MPCORB или SBDB
# 2. Сохраните в JSON формате
# 3. Запустите интеграцию
python tools/integrate_chiron_hybrid.py `
  data/centaurs/pholus_mpc.json `
  data/ephemerides/jpl/de440/linux_p1550p2650.440 `
  2451545.0 2466154.5 16.0 `
  data/centaurs/pholus_hybrid.json
```

---

## См. также

- `CHIRON_INTEGRATION_FINAL_REPORT.md` - полный отчет о тестировании
- `FINAL_ACCURACY_REPORT.md` - сравнение точности всех методов
- `tools/integrate_chiron_orbit.py` - простой Euler интегратор (для сравнения)
- `php/examples/compare_chiron_4way.php` - скрипт сравнения

---

**Версия**: 1.0
**Дата**: 30 октября 2025
**Статус**: ✅ Production-ready (с simplified planets), ⏳ Testing (с DE440)
