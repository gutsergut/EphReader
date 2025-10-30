<?php
/**
 * Standalone Swiss Ephemeris FFI Calculator
 * Возвращает JSON с position/velocity для использования в Python
 *
 * Usage: php swisseph_standalone.php <body_id> <jd> [frame]
 *   body_id: NAIF body ID (1-10, 301, 399)
 *   jd: Julian Date
 *   frame: 'geocentric' (default) or 'barycentric'
 */

if ($argc < 3) {
    echo json_encode(['error' => 'Usage: php swisseph_standalone.php <body_id> <jd> [frame=geocentric|barycentric]']);
    exit(1);
}

$bodyId = (int)$argv[1];
$jd = (float)$argv[2];
$frame = $argv[3] ?? 'geocentric'; // Default: геоцентрическая система

$dllPath = __DIR__ . '/../vendor/swisseph/swedll64.dll';
$ephePath = __DIR__ . '/../ephe';

if (!in_array($frame, ['geocentric', 'barycentric'])) {
    echo json_encode(['error' => "Invalid frame: $frame (use 'geocentric' or 'barycentric')"]);
    exit(1);
}

if (!file_exists($dllPath)) {
    echo json_encode(['error' => "DLL not found: $dllPath"]);
    exit(1);
}

if (!extension_loaded('ffi')) {
    echo json_encode(['error' => 'FFI extension not loaded']);
    exit(1);
}

try {
    // Минимальный FFI интерфейс
    $ffi = FFI::cdef("
        void swe_set_ephe_path(char *path);
        int swe_calc_ut(double tjd_ut, int ipl, int iflag, double *xx, char *serr);
        void swe_close(void);
    ", $dllPath);

    $ffi->swe_set_ephe_path($ephePath);

    // NAIF → Swiss Ephemeris mapping
    $naifToSweph = [
        1 => 2,    // Mercury
        2 => 3,    // Venus
        3 => 0,    // Earth (as Sun from geocentric)
        4 => 4,    // Mars
        5 => 5,    // Jupiter
        6 => 6,    // Saturn
        7 => 7,    // Uranus
        8 => 8,    // Neptune
        9 => 9,    // Pluto
        10 => 0,   // Sun
        301 => 1,  // Moon
        399 => 13, // Earth barycenter
    ];

    $swephId = $naifToSweph[$bodyId] ?? null;
    if ($swephId === null) {
        echo json_encode(['error' => "Body ID $bodyId not supported"]);
        exit(1);
    }

    $xx = FFI::new("double[6]");
    $serr = FFI::new("char[256]");

    // Всегда используем геоцентрическую систему (native Swiss Eph)
    // SEFLG_SWIEPH + SEFLG_SPEED
    $iflag = 2 + 256;

    $result = $ffi->swe_calc_ut($jd, $swephId, $iflag, $xx, $serr);    if ($result < 0) {
        $error = FFI::string($serr);
        echo json_encode(['error' => $error]);
        exit(1);
    }

    // Конвертируем в км (прямоугольные координаты)
    // xx[0] = longitude (deg), xx[1] = latitude (deg), xx[2] = distance (AU)
    // xx[3] = speed in long (deg/day), xx[4] = speed in lat (deg/day), xx[5] = speed in dist (AU/day)

    $AU_TO_KM = 149597870.7;

    $lon_rad = $xx[0] * M_PI / 180.0;
    $lat_rad = $xx[1] * M_PI / 180.0;
    $dist_km = $xx[2] * $AU_TO_KM;

    // Сферические → Декартовы
    $pos = [
        $dist_km * cos($lat_rad) * cos($lon_rad),
        $dist_km * cos($lat_rad) * sin($lon_rad),
        $dist_km * sin($lat_rad),
    ];

    // Для скорости нужна численная производная
    // Упрощённо: используем скорость изменения расстояния
    $vel_lon = $xx[3] * M_PI / 180.0; // rad/day
    $vel_lat = $xx[4] * M_PI / 180.0;
    $vel_dist = $xx[5] * $AU_TO_KM; // km/day

    $vel = [
        -$dist_km * cos($lat_rad) * sin($lon_rad) * $vel_lon + cos($lat_rad) * cos($lon_rad) * $vel_dist,
        $dist_km * cos($lat_rad) * cos($lon_rad) * $vel_lon + cos($lat_rad) * sin($lon_rad) * $vel_dist,
        $dist_km * cos($lat_rad) * $vel_lat + sin($lat_rad) * $vel_dist,
    ];

    // Преобразование в барицентрическую систему (если запрошено)
    // Swiss Eph native = геоцентрическая (объекты от Земли)
    // Барицентрическая = инверсия знака (Земля от объектов)
    if ($frame === 'barycentric') {
        $pos = array_map(fn($v) => -$v, $pos);
        $vel = array_map(fn($v) => -$v, $vel);
    }

    echo json_encode([
        'pos' => $pos,
        'vel' => $vel,
        'frame' => $frame,
    ]);

    $ffi->swe_close();} catch (Throwable $e) {
    echo json_encode(['error' => $e->getMessage()]);
    exit(1);
}
