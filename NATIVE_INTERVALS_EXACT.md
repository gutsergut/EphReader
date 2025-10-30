# ТОЧНЫЕ НАТИВНЫЕ ИНТЕРВАЛЫ ЧЕБЫШЁВА - Финальный отчёт

**Извлечено через calceph_inspector (CALCEPH 4.0.1)**

## JPL DE431 (Type 2 - Chebyshev)

| Body ID | Name                 | Center | Interval (days) | Records  | Notes                    |
|---------|----------------------|--------|-----------------|----------|--------------------------|
| 1       | Mercury              | 0 (SSB)| **8**           | 602,681  | Быстрое движение         |
| 2       | Venus                | 0 (SSB)| **16**          | 301,341  |                          |
| 3       | EMB                  | 0 (SSB)| **16**          | 301,341  |                          |
| 4       | Mars                 | 0 (SSB)| **32**          | 150,671  |                          |
| 5       | Jupiter              | 0 (SSB)| **32**          | 150,671  |                          |
| 6       | Saturn               | 0 (SSB)| **32**          | 150,671  |                          |
| 7       | Uranus               | 0 (SSB)| **32**          | 150,671  |                          |
| 8       | Neptune              | 0 (SSB)| **32**          | 150,671  |                          |
| 9       | Pluto                | 0 (SSB)| **32**          | 150,671  |                          |
| 10      | Sun                  | 0 (SSB)| **16**          | 301,341  |                          |
| 199     | Mercury Barycenter   | 1      | 11,000,000      | 1        | Не используется (тривиальный) |
| 299     | Venus Barycenter     | 2      | 11,000,000      | 1        | Не используется (тривиальный) |
| 301     | Moon                 | 3 (EMB)| **4**           | 1,205,361| Самое быстрое движение   |
| 399     | Earth                | 3 (EMB)| **4**           | 1,205,361|                          |

**Временное покрытие**: JD -3100014.50 to 1721425.50 (BC 13200 to AD 1)
**Формат**: SPICE SPK Type 2 (Chebyshev polynomials)

---

## EPM2021 (Type 20 - Hermite interpolation)

| Body ID    | Name                  | Center     | Interval (days) | Records | Notes                    |
|------------|-----------------------|------------|-----------------|---------|--------------------------|
| 1          | Mercury               | 0 (SSB)    | **5**           | 31,200  | Быстрое движение         |
| 2          | Venus                 | 0 (SSB)    | **20**          | 7,800   |                          |
| 3          | EMB                   | 0 (SSB)    | **2**           | 78,000  |                          |
| 4          | Mars                  | 0 (SSB)    | **50**          | 3,120   |                          |
| 5          | Jupiter               | 0 (SSB)    | **100**         | 1,560   |                          |
| 6          | Saturn                | 0 (SSB)    | **300**         | 520     |                          |
| 7          | Uranus                | 0 (SSB)    | **400**         | 390     |                          |
| 8          | Neptune               | 0 (SSB)    | **500**         | 312     |                          |
| 9          | Pluto                 | 0 (SSB)    | **600**         | 260     | Самое медленное          |
| 10         | Sun                   | 0 (SSB)    | **2**           | 78,000  |                          |
| 301        | Moon                  | 399 (Earth)| **2**           | 78,000  | Самое быстрое            |
| 399        | Earth                 | 0 (SSB)    | **2**           | 78,000  |                          |
| 2000001    | Ceres (asteroid)      | 0 (SSB)    | **100**         | 1,560   |                          |
| 2000002    | Pallas (asteroid)     | 0 (SSB)    | **100**         | 1,560   |                          |
| 2000004    | Vesta (asteroid)      | 0 (SSB)    | **100**         | 1,560   |                          |
| 2000007    | Iris (asteroid)       | 0 (SSB)    | **100**         | 1,560   |                          |
| 2000324    | Bamberga (asteroid)   | 0 (SSB)    | **100**         | 1,560   |                          |
| 2090377    | Sedna (TNO)           | 0 (SSB)    | **100**         | 1,560   | Уникальный TNO           |
| 2136108    | Haumea (dwarf planet) | 0 (SSB)    | **100**         | 1,560   | Уникальная карликовая    |
| 2136199    | Eris (dwarf planet)   | 0 (SSB)    | **100**         | 1,560   | Уникальная карликовая    |
| 2136472    | Makemake (dwarf planet)| 0 (SSB)   | **100**         | 1,560   | Уникальная карликовая    |
| 1000000001 | Pluto-Charon Barycenter| 1000000000| **5**           | 31,200  |                          |

**Временное покрытие**: JD 2374000.50 to 2530000.50 (AD 1788 to 2215)
**Формат**: SPICE SPK Type 20 (Hermite interpolation, NOT Chebyshev!)
**Примечание**: EPM использует Type 20 (интерполяция Эрмита), а не Type 2 (Чебышёв)

---

## Сравнение JPL DE431 vs EPM2021

### Основные планеты

| Body      | DE431 (days) | EPM2021 (days) | Difference | Notes                     |
|-----------|--------------|----------------|------------|---------------------------|
| Mercury   | 8            | 5              | -3         | EPM более детальный       |
| Venus     | 16           | 20             | +4         | DE более детальный        |
| EMB       | 16           | 2              | -14        | EPM ГОРАЗДО детальнее     |
| Mars      | 32           | 50             | +18        | DE более детальный        |
| Jupiter   | 32           | 100            | +68        | DE ГОРАЗДО детальнее      |
| Saturn    | 32           | 300            | +268       | DE ГОРАЗДО детальнее      |
| Uranus    | 32           | 400            | +368       | DE ГОРАЗДО детальнее      |
| Neptune   | 32           | 500            | +468       | DE ГОРАЗДО детальнее      |
| Pluto     | 32           | 600            | +568       | DE ГОРАЗДО детальнее      |
| Sun       | 16           | 2              | -14        | EPM ГОРАЗДО детальнее     |
| Moon      | 4            | 2              | -2         | EPM более детальный       |
| Earth     | 4            | 2              | -2         | EPM более детальный       |

### Выводы

1. **Внутренние объекты** (Sun, Moon, Earth, EMB):
   - EPM2021 использует **очень малые интервалы (2 дня)**
   - Это связано с улучшенными LLR (Lunar Laser Ranging) измерениями
   - Объясняет высокую точность EPM для Луны и Земли

2. **Внешние планеты** (Jupiter-Pluto):
   - DE431 **значительно детальнее** (32 дня vs 100-600 дней)
   - EPM использует большие интервалы для экономии места
   - Для внешних планет рекомендуется использовать JPL DE

3. **Уникальные тела EPM**:
   - Asteroids: 100 дней (достаточно для main-belt)
   - TNO/Dwarf planets: 100 дней (медленное движение)

---

## Рекомендации для конвертера

### Профиль "optimal" - Оптимальные интервалы

```json
"optimal_intervals": {
  "1": 8,      // Mercury (JPL DE)
  "2": 16,     // Venus (JPL DE)
  "3": 2,      // EMB (EPM2021 - улучшенный)
  "4": 32,     // Mars (JPL DE)
  "5": 32,     // Jupiter (JPL DE)
  "6": 32,     // Saturn (JPL DE)
  "7": 32,     // Uranus (JPL DE)
  "8": 32,     // Neptune (JPL DE)
  "9": 32,     // Pluto (JPL DE)
  "10": 2,     // Sun (EPM2021 - улучшенный)
  "301": 2,    // Moon (EPM2021 - улучшенный LLR)
  "399": 2,    // Earth (EPM2021 - улучшенный)
  "2000001": 100,  // Ceres (EPM2021)
  "2000002": 100,  // Pallas (EPM2021)
  "2000004": 100,  // Vesta (EPM2021)
  "2000007": 100,  // Iris (EPM2021)
  "2000324": 100,  // Bamberga (EPM2021)
  "2090377": 100,  // Sedna (EPM2021)
  "2136108": 100,  // Haumea (EPM2021)
  "2136199": 100,  // Eris (EPM2021)
  "2136472": 100   // Makemake (EPM2021)
}
```

### Размер файлов при конвертации

**JPL DE431 (12 bodies, 13,200 years)**:
- Mercury (8d): 602,681 intervals × 12 bytes = 7.2 MB
- Venus (16d): 301,341 intervals × 12 bytes = 3.6 MB
- Moon (4d): 1,205,361 intervals × 12 bytes = 14.5 MB
- **Total estimate**: ~50-60 MB

**EPM2021 (22 bodies, 427 years)**:
- Inner bodies (2d): 78,000 intervals × 22 bytes (type 20) = 1.7 MB each
- Asteroids (100d): 1,560 intervals × 22 bytes = 34 KB each
- **Total estimate**: ~25-30 MB

---

## Инструменты

**calceph_inspector** (CALCEPH 4.0.1):
```bash
vendor/calceph-4.0.1/install/bin/calceph_inspector.exe <spk_file>
```

Выводит точную информацию:
- Interval (Time span per record)
- Number of records
- Data type (2 = Chebyshev, 20 = Hermite)
- Frame reference
- Time scale (TDB)

---

## Заключение

✅ **ТОЧНЫЕ нативные интервалы извлечены** через CALCEPH inspector
✅ **EPM2021 использует Type 20 (Hermite)**, а не Chebyshev
✅ **JPL DE431 использует Type 2 (Chebyshev)** как ожидалось
✅ **EPM2021 более детальный** для внутренних объектов (2 дня vs 4-16 дней)
✅ **JPL DE431 более детальный** для внешних планет (32 дня vs 100-600 дней)

**Рекомендация**: Использовать гибридный подход - EPM для внутренних объектов + unique bodies, JPL DE для внешних планет и научной точности.
