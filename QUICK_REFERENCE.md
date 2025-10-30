# 🌌 Quick Reference: Ephemeris Comparison Cheat Sheet

> Быстрый справочник для выбора эфемериды под задачу

---

## 🎯 Выбор эфемериды: Decision Tree

```
                           [Какая задача?]
                                 |
            ┌────────────────────┼────────────────────┬─────────────────────┐
            ▼                    ▼                    ▼                     ▼
     Научная точность      Астрология          Скорость           Долгосрочные (30k лет)
            |                    |                    |                     |
            ▼                    ▼                    ▼                     ▼
    EPM2021 (inner)      Swiss Ephemeris      Swiss Ephemeris         JPL DE431
    JPL DE440 (outer)    + EPM2021 (TNO)      + EPM2021 .eph       + Swiss (nodes)

    ✅ 29 km median      ✅ 0.001" angles      ✅ 99 MB size        ✅ 30,390 years
    ✅ Pure PHP          ✅ Nodes/Chiron       ✅ 28× compress      ✅ Uniform 32d
```

---

## 📊 Сводная таблица (1 взгляд)

| Формат         | Размер   | Точность   | Интервал (Луна) | Уник. тела | PHP Pure | Алгоритм      |
|----------------|----------|------------|-----------------|------------|----------|---------------|
| **JPL DE440**  | 97.5 MB  | Эталон ✅  | 4 дня           | 0          | ❌       | Chebyshev     |
| **JPL DE431**  | 2.6 GB   | Эталон ✅  | 4 дня           | 0          | ❌       | Chebyshev     |
| **EPM2021**    | 147 MB   | 29 км ✅   | **2 дня** 🏆    | 10 🌟      | ✅       | Hermite       |
| **Swiss Eph**  | 99 MB 🏆 | 0.001" ✅  | ~27.5 дн (var)  | 6 🌟       | ❌       | **Kammeyer** 🏆|

**Легенда**: 🏆 = лучший, 🌟 = уникальные объекты

---

## 🥇 Победители по категориям

| Категория                  | Победитель       | Почему?                                    |
|----------------------------|------------------|--------------------------------------------|
| **Сжатие**                 | Swiss Eph 🏆     | 28× (2.8 GB → 99 MB)                       |
| **Луна (плотность)**       | EPM2021 🏆       | 2 дня vs 4 (JPL) - в 2× плотнее!          |
| **Солнце (плотность)**     | EPM2021 🏆       | 2 дня vs 16 (JPL) - в 8× плотнее!         |
| **Внешние планеты**        | JPL DE440 🏆     | Uniform 32 дня, эталонная точность         |
| **Угловая точность**       | Swiss Eph 🏆     | 0.001" (1 milli-arcsec)                    |
| **Уникальные тела**        | Swiss + EPM 🏆   | Nodes, Chiron, TNO, астероиды              |
| **PHP интеграция**         | EPM2021 🏆       | Pure PHP (EphReader.php) - NO FFI!         |
| **Долгосрочное покрытие**  | JPL DE431 🏆     | 30,390 лет                                 |

---

## 🔬 Алгоритмы (упрощённо)

### JPL DE440/431 (NASA)
```
Хранит: Полные позиции XYZ (барицентрические)
Метод:  Чебышёв полиномы (Type 2)
Интервалы: Фиксированные (4-32 дня)
Размер: 97 MB (DE440) / 2.6 GB (DE431)
```

### EPM2021 (Russia)
```
Хранит: Полные позиции XYZ (барицентрические)
Метод:  Эрмит интерполяция (Type 20)
Интервалы: Переменные (2-600 дней)
Размер: 147 MB (BSP) / 27 MB (.eph)
Особенность: LLR-улучшенная Луна!
```

### Swiss Ephemeris (Astrodienst)
```
Хранит: Δ-позиции (JPL - VSOP87)
Метод:  Чебышёв для Δ + rotation (Kammeyer 1987)
Интервалы: Адаптивные (аномалистический цикл / 4000 дней)
Размер: 99 MB (compressed 28×!)
Особенность: Революционное сжатие!
```

---

## 🌟 Уникальные тела

| Тело                  | JPL | EPM | Swiss | Применение          |
|-----------------------|-----|-----|-------|---------------------|
| Ceres, Pallas, Vesta  | ❌  | ✅  | ✅    | Астрология/наука    |
| Sedna, Eris, Makemake | ❌  | ✅  | ❌    | Астрология (TNO)    |
| Chiron, Pholus        | ❌  | ❌  | ✅    | Астрология (центавры)|
| Lunar Nodes           | ❌  | ❌  | ✅    | Астрология          |
| Lilith (Black Moon)   | ❌  | ❌  | ✅    | Астрология          |

**ИТОГО**:
- EPM: 10 уникальных объектов
- Swiss: 6 уникальных точек

---

## ⚡ Скорость (теоретическая)

```
🏆 FASTEST:  Swiss Eph          (предвычисленные коэфф., 99 MB, FFI)
✅ FAST:     EPM2021 .eph        (прямой fseek/unpack, Pure PHP)
⚠️ MEDIUM:   JPL DE440/431      (SPICE DAF traversal, FFI)
⚠️ MEDIUM:   EPM2021 BSP        (SPICE DAF traversal, FFI)
```

**Примечание**: Эмпирические бенчмарки заблокированы (calceph Python bindings issue)

---

## 🎯 Гибридная стратегия (оптимально)

### Для PHP проекта с максимальным покрытием:

```php
class HybridEphemeris {
    // 1. Pure PHP (NO FFI overhead!)
    private EphReader $epm;              // EPM2021 .eph - inner planets + TNO

    // 2. FFI для уникальных тел
    private FFI $swiss;                  // Swiss Eph - nodes, Chiron, Pholus
    private FFI $jpl;                    // JPL DE440 - outer planets (reference)

    public function compute(int $body, float $jd) {
        // Внутренние планеты + TNO → Pure PHP
        if ($body <= 4 || $body > 2000000) {
            return $this->epm->compute($body, $jd);  // NO FFI! ✅
        }

        // Nodes, Chiron, Pholus → Swiss FFI
        if ($body >= 10 && $body <= 16) {
            return $this->swiss->calc($body, $jd);
        }

        // Внешние планеты → JPL (reference)
        return $this->jpl->pleph($jd, $body);
    }
}
```

**Преимущества**:
- ✅ **Большинство запросов** через Pure PHP (без FFI overhead)
- ✅ **Максимальное покрытие** (22 тела EPM + 6 Swiss = 28 объектов)
- ✅ **Оптимальная точность** (EPM для Луны/Sun, JPL для внешних)

---

## 📐 Интервалы (победители по телам)

| Тело      | Лучший интервал | Источник   | Комментарий                    |
|-----------|-----------------|------------|--------------------------------|
| **Moon**  | **2 дня** 🏆    | EPM2021    | В 2× плотнее JPL (4 дня)       |
| **Sun**   | **2 дня** 🏆    | EPM2021    | В 8× плотнее JPL (16 дней)     |
| **Earth** | **2 дня** 🏆    | EPM2021    | В 2× плотнее JPL (4 дня)       |
| Mercury   | **5 дней** 🏆   | EPM2021    | JPL: 8 дней                    |
| Venus     | **16 дней** 🏆  | JPL DE431  | EPM: 20 дней                   |
| Mars      | **32 дня** 🏆   | JPL DE431  | EPM: 50 дней (слишком редко)   |
| Jupiter   | **32 дня** 🏆   | JPL DE431  | EPM: 100 дней                  |
| Saturn    | **32 дня** 🏆   | JPL DE431  | EPM: 300 дней                  |
| Uranus    | **32 дня** 🏆   | JPL DE431  | EPM: 400 дней                  |
| Neptune   | **32 дня** 🏆   | JPL DE431  | EPM: 500 дней                  |
| Pluto     | **32 дня** 🏆   | JPL DE431  | EPM: 600 дней (слишком редко!) |

**Вывод**:
- 🏆 **EPM2021** для внутренних объектов + Луны + Солнца
- 🏆 **JPL DE431** для внешних планет (uniform 32 дня)

---

## ⚠️ Важные находки

### 1️⃣ JPL документация содержит ошибки!
```
Документировано:    Earth = 32 дня     Moon = 8 дней      Pluto = 64 дня
Реальность:         Earth = 4 дня      Moon = 4 дня       Pluto = 32 дня
Ошибка:             -87.5%             -50%               -50%
```
**Источник истины**: `calceph_inspector` (единственный надёжный метод!)

### 2️⃣ Swiss Eph = 28× сжатие (Kammeyer algorithm)
```
JPL DE431 original:  2.8 GB
Swiss Eph compressed: 99 MB
Метод: Хранение Δ-позиций (JPL - VSOP87) вместо полных координат
Точность: 0.001" (1 milli-arcsecond) - лучше чем нужно!
```

### 3️⃣ EPM2021 превосходит JPL для Луны
```
EPM интервал: 2 дня (78,000 записей за 427 лет)
JPL интервал: 4 дня
Причина: Improved LLR (Lunar Laser Ranging) data
Точность: ~29 км median vs JPL DE440
```

---

## 📚 Документы для деталей

| Документ                                | Содержание                          |
|-----------------------------------------|-------------------------------------|
| `EPHEMERIS_COMPARISON_SUMMARY.md`       | Полные ответы на все вопросы        |
| `EPHEMERIS_FORMATS_AND_COMPARISON.md`   | Детальное сравнение форматов        |
| `NATIVE_INTERVALS_EXACT.md`             | Точные интервалы (calceph_inspector)|
| `SWISS_EPHEMERIS_GUIDE.md`              | Swiss Eph интеграция + FFI          |
| `.github/copilot-instructions.md`       | Архитектура проекта (правила AI)    |

---

## 🚀 Быстрый старт

### Для научных расчётов:
```bash
# 1. Установить EPM2021 (чистый PHP!)
composer require swisseph/ephemeris
php test_eph.php  # Тест EphReader.php

# 2. Луна, Солнце, внутренние → EPM2021
# 3. Внешние планеты → JPL DE440 (FFI)
```

### Для астрологии:
```bash
# 1. Swiss Eph для основных + узлов/Chiron
php test_swisseph_ffi.php

# 2. EPM2021 для TNO (Sedna, Eris, etc)
php test_eph.php
```

### Для долгосрочных исследований:
```bash
# Скачать JPL DE431 (30,390 лет)
curl -L https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de431/lnxm13000p17000.431 -o data/ephemerides/jpl/de431/
```

---

**Версия**: 1.0
**Дата**: 2025-01-XX
**Статус**: ✅ COMPLETE
