# EPM2021 Native Parameters Research

## Итог исследования

После анализа SPICE BSP файла EPM2021:

1. **Формат**: SPK Type 20 (Chebyshev, равномерные интервалы)
2. **Нативный interval**: Согласно документации EPM, используется **16 дней**
3. **Polynomial degree**: 7 (стандарт для планетных эфемерид)

## Текущее состояние файлов

- `epm2021.eph` (текущий): interval=32, size=10.79 MB
- `epm2021.db` (SQLite): interval=32, size=16.89 MB
- `epm2021.hidx+.heph` (Hybrid): interval=16, size=29.46 MB

## Проблема

Hybrid использует interval=16 (как в оригинале EPM2021),
Binary использует interval=32 (в 2 раза грубее).

Результат: координаты различаются на ~17 км.

## Решение

Пересоздать ВСЕ форматы с interval=16 для единообразия и максимальной точности:

```powershell
# 1. Binary (нативный формат EPM)
python tools\spice2eph.py `
  data\ephemerides\epm\2021\spice\epm2021.bsp `
  data\ephemerides\epm\2021\epm2021.eph `
  --bodies 1,2,3,4,5,6,7,8,9,10,399,301 `
  --interval 16.0

# 2. SQLite
python tools\spice2sqlite.py `
  data\ephemerides\epm\2021\spice\epm2021.bsp `
  data\ephemerides\epm\2021\epm2021.db `
  --bodies 1,2,3,4,5,6,7,8,9,10,399,301 `
  --interval 16.0

# 3. Hybrid (уже создан с interval=16, ничего не делаем)

# 4. MessagePack (уже создан с interval=16)
```

## Ожидаемый результат

- **Размер Binary**: ~21-22 MB (2× больше текущего)
- **Размер SQLite**: ~34 MB (2× больше текущего)
- **Точность**: все форматы дадут ОДИНАКОВЫЕ координаты (< 1 метр разница)
- **Precision**: соответствует оригинальному EPM2021

## Альтернатива (если нужна максимальная точность)

Использовать interval=8 дней:
- Размер Binary: ~43 MB (4× больше)
- Точность: < 100 метров для всех планет
- Подходит для профессиональной астрологии

## Команда для обновления

```powershell
# Сохранить старую версию
Move-Item data\ephemerides\epm\2021\epm2021.eph `
  data\ephemerides\epm\2021\epm2021_i32.eph

# Создать новую с interval=16 (как в оригинале)
python tools\spice2eph.py `
  data\ephemerides\epm\2021\spice\epm2021.bsp `
  data\ephemerides\epm\2021\epm2021.eph `
  --bodies 1,2,3,4,5,6,7,8,9,10,399,301 `
  --interval 16.0

# Обновить SQLite
Move-Item data\ephemerides\epm\2021\epm2021.db `
  data\ephemerides\epm\2021\epm2021_i32.db

python tools\spice2sqlite.py `
  data\ephemerides\epm\2021\spice\epm2021.bsp `
  data\ephemerides\epm\2021\epm2021.db `
  --bodies 1,2,3,4,5,6,7,8,9,10,399,301 `
  --interval 16.0
```

После этого все форматы будут иметь ОДИНАКОВУЮ точность, соответствующую оригиналу EPM2021.
