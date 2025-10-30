<?php
/**
 * Universal Swiss Ephemeris FFI Calculator
 * Поддерживает все системы отсчёта и координат
 *
 * Usage: php swisseph_universal.php <body_id> <jd> [frame] [coords]
 *   body_id: NAIF body ID (0-9, 1, 301, 13, 399)
 *   jd: Julian Date
 *   frame: geocentric | heliocentric | barycentric | emb (default: geocentric)
 *   coords: cartesian | ecliptic | equatorial (default: cartesian)
 */

if ($argc < 3) {
    echo json_encode([
        'error' => 'Usage: php swisseph_universal.php <body_id> <jd> [frame] [coords]',
        'frames' => ['geocentric', 'heliocentric', 'barycentric', 'emb'],
        'coords' => ['cartesian', 'ecliptic', 'equatorial'],
    ]);
    exit(1);
}

$bodyId = (int)$argv[1];
$jd = (float)$argv[2];
$frame = $argv[3] ?? 'geocentric';
$coords = $argv[4] ?? 'cartesian';

$dllPath = __DIR__ . '/../vendor/swisseph/swedll64.dll';
$ephePath = __DIR__ . '/../ephe';

// Validate inputs
$validFrames = ['geocentric', 'heliocentric', 'barycentric', 'emb'];
$validCoords = ['cartesian', 'ecliptic', 'equatorial'];

if (!in_array($frame, $validFrames)) {
    echo json_encode(['error' => "Invalid frame: $frame (use: " . implode(', ', $validFrames) . ")"]);
    exit(1);
}

if (!in_array($coords, $validCoords)) {
    echo json_encode(['error' => "Invalid coords: $coords (use: " . implode(', ', $validCoords) . ")"]);
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
    $ffi = FFI::cdef("
        void swe_set_ephe_path(char *path);
        int swe_calc_ut(double tjd_ut, int ipl, int iflag, double *xx, char *serr);
        void swe_close(void);
    ", $dllPath);

    $ffi->swe_set_ephe_path($ephePath);

    // NAIF → Swiss Ephemeris mapping
    $naifToSweph = [
        0 => 0,    // Sun
        1 => 2,    // Mercury
        2 => 3,    // Venus
        3 => 0,    // Earth (returns Sun geocentric)
        4 => 4,    // Mars
        5 => 5,    // Jupiter
        6 => 6,    // Saturn
        7 => 7,    // Uranus
        8 => 8,    // Neptune
        9 => 9,    // Pluto
        10 => 0,   // Sun (same as 0)
        301 => 1,  // Moon
        13 => 13,  // Earth-Moon Barycenter
        399 => 13, // Earth barycenter (alias for 13)
    ];

    $swephId = $naifToSweph[$bodyId] ?? null;
    if ($swephId === null) {
        echo json_encode(['error' => "Body ID $bodyId not supported"]);
        exit(1);
    }

    // Build iflag
    $iflag = 2; // SEFLG_SWIEPH
    $iflag |= 256; // SEFLG_SPEED

    // Frame flags
    switch ($frame) {
        case 'heliocentric':
            $iflag |= 8; // SEFLG_HELCTR
            break;
        case 'barycentric':
            $iflag |= 16384; // SEFLG_BARYCTR
            break;
        case 'emb':
            // Earth-Moon Barycenter: use body 13
            if ($bodyId === 3 || $bodyId === 399) {
                $swephId = 13;
            }
            break;
        // geocentric: default, no flag needed
    }

    // Coordinate flags
    switch ($coords) {
        case 'cartesian':
            $iflag |= 4096; // SEFLG_XYZ
            break;
        case 'equatorial':
            $iflag |= 2048; // SEFLG_EQUATORIAL
            break;
        // ecliptic: default, no flag needed
    }

    $xx = FFI::new("double[6]");
    $serr = FFI::new("char[256]");

    $result = $ffi->swe_calc_ut($jd, $swephId, $iflag, $xx, $serr);

    if ($result < 0) {
        $error = FFI::string($serr);
        echo json_encode(['error' => $error]);
        exit(1);
    }

    // Parse results based on coordinate system
    if ($coords === 'cartesian') {
        // Already in AU, convert to km
        $AU_TO_KM = 149597870.7;

        $pos = [
            $xx[0] * $AU_TO_KM,
            $xx[1] * $AU_TO_KM,
            $xx[2] * $AU_TO_KM,
        ];

        $vel = [
            $xx[3] * $AU_TO_KM, // AU/day → km/day
            $xx[4] * $AU_TO_KM,
            $xx[5] * $AU_TO_KM,
        ];
    } else {
        // Spherical (ecliptic or equatorial)
        // Need to convert to Cartesian for consistency
        $AU_TO_KM = 149597870.7;

        $lon_rad = $xx[0] * M_PI / 180.0;
        $lat_rad = $xx[1] * M_PI / 180.0;
        $dist_km = $xx[2] * $AU_TO_KM;

        // Spherical → Cartesian
        $pos = [
            $dist_km * cos($lat_rad) * cos($lon_rad),
            $dist_km * cos($lat_rad) * sin($lon_rad),
            $dist_km * sin($lat_rad),
        ];

        // Velocity (simplified - proper conversion needs numerical derivative)
        $vel_lon = $xx[3] * M_PI / 180.0; // rad/day
        $vel_lat = $xx[4] * M_PI / 180.0;
        $vel_dist = $xx[5] * $AU_TO_KM; // km/day

        $vel = [
            -$dist_km * cos($lat_rad) * sin($lon_rad) * $vel_lon + cos($lat_rad) * cos($lon_rad) * $vel_dist,
            $dist_km * cos($lat_rad) * cos($lon_rad) * $vel_lon + cos($lat_rad) * sin($lon_rad) * $vel_dist,
            $dist_km * cos($lat_rad) * $vel_lat + sin($lat_rad) * $vel_dist,
        ];

        // Store original spherical coordinates too
        $spherical = [
            'lon' => $xx[0],
            'lat' => $xx[1],
            'dist' => $xx[2],
            'lon_speed' => $xx[3],
            'lat_speed' => $xx[4],
            'dist_speed' => $xx[5],
        ];
    }

    $output = [
        'pos' => $pos,
        'vel' => $vel,
        'frame' => $frame,
        'coords' => $coords,
        'body_id' => $bodyId,
        'sweph_id' => $swephId,
        'jd' => $jd,
    ];

    if (isset($spherical)) {
        $output['spherical'] = $spherical;
    }

    echo json_encode($output);

    $ffi->swe_close();

} catch (Throwable $e) {
    echo json_encode(['error' => $e->getMessage()]);
    exit(1);
}
