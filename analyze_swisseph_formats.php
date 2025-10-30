<?php
/**
 * Анализ форматов и систем координат Swiss Ephemeris
 * Проверяет все доступные флаги и опции
 */

$dllPath = __DIR__ . '/vendor/swisseph/swedll64.dll';
$ephePath = __DIR__ . '/ephe';

if (!extension_loaded('ffi')) {
    die("FFI extension not loaded\n");
}

$ffi = FFI::cdef("
    void swe_set_ephe_path(char *path);
    int swe_calc_ut(double tjd_ut, int ipl, int iflag, double *xx, char *serr);
    char *swe_version(char *version);
    void swe_close(void);
", $dllPath);

$version = FFI::new("char[256]");
$ffi->swe_version($version);
echo "Swiss Ephemeris Version: " . FFI::string($version) . "\n\n";

$ffi->swe_set_ephe_path($ephePath);

// Флаги Swiss Ephemeris
$flags = [
    'SEFLG_JPLEPH' => 1,       // JPL ephemeris
    'SEFLG_SWIEPH' => 2,       // Swiss Ephemeris
    'SEFLG_MOSEPH' => 4,       // Moshier ephemeris
    'SEFLG_HELCTR' => 8,       // Heliocentric position
    'SEFLG_TRUEPOS' => 16,     // True position (not apparent)
    'SEFLG_J2000' => 32,       // No precession (J2000 coordinates)
    'SEFLG_NONUT' => 64,       // No nutation
    'SEFLG_SPEED3' => 128,     // Speed from 3 positions
    'SEFLG_SPEED' => 256,      // Speed (velocity)
    'SEFLG_NOGDEFL' => 512,    // No gravitational deflection
    'SEFLG_NOABERR' => 1024,   // No aberration
    'SEFLG_ASTROMETRIC' => (16|32|64|512|1024), // Astrometric position
    'SEFLG_EQUATORIAL' => 2048, // Equatorial coordinates (not ecliptic)
    'SEFLG_XYZ' => 4096,       // Cartesian coordinates
    'SEFLG_RADIANS' => 8192,   // Radians (not degrees)
    'SEFLG_BARYCTR' => 16384,  // Barycentric position
    'SEFLG_TOPOCTR' => 32768,  // Topocentric position
    'SEFLG_ORBEL' => 65536,    // Orbital elements
    'SEFLG_SIDEREAL' => 131072, // Sidereal position
];

echo "=== Swiss Ephemeris Coordinate Flags ===\n\n";
foreach ($flags as $name => $value) {
    printf("%-25s = %6d (0x%04X)\n", $name, $value, $value);
}

echo "\n=== Testing Different Coordinate Systems for Sun at J2000.0 ===\n\n";

$jd = 2451545.0;
$ipl = 0; // Sun
$xx = FFI::new("double[6]");
$serr = FFI::new("char[256]");

$tests = [
    'Geocentric Ecliptic (default)' => 2 + 256, // SEFLG_SWIEPH + SEFLG_SPEED
    'Geocentric Equatorial' => 2 + 256 + 2048, // + SEFLG_EQUATORIAL
    'Geocentric Cartesian (XYZ)' => 2 + 256 + 4096, // + SEFLG_XYZ
    'Heliocentric Ecliptic' => 2 + 256 + 8, // + SEFLG_HELCTR
    'Heliocentric Cartesian' => 2 + 256 + 8 + 4096,
    'Barycentric Ecliptic' => 2 + 256 + 16384, // + SEFLG_BARYCTR
    'Barycentric Cartesian' => 2 + 256 + 16384 + 4096,
    'J2000 (no precession)' => 2 + 256 + 32, // + SEFLG_J2000
    'Astrometric' => 2 + 256 + (16|32|64|512|1024),
];

foreach ($tests as $name => $iflag) {
    $result = $ffi->swe_calc_ut($jd, $ipl, $iflag, $xx, $serr);

    if ($result < 0) {
        echo "❌ $name: " . FFI::string($serr) . "\n";
        continue;
    }

    echo "✅ $name:\n";

    // Определяем формат вывода
    if ($iflag & 4096) { // XYZ
        printf("   X: %18.9f AU\n", $xx[0]);
        printf("   Y: %18.9f AU\n", $xx[1]);
        printf("   Z: %18.9f AU\n", $xx[2]);
        printf("   VX: %17.9f AU/day\n", $xx[3]);
        printf("   VY: %17.9f AU/day\n", $xx[4]);
        printf("   VZ: %17.9f AU/day\n", $xx[5]);
    } else {
        printf("   Longitude: %15.9f°\n", $xx[0]);
        printf("   Latitude:  %15.9f°\n", $xx[1]);
        printf("   Distance:  %15.9f AU\n", $xx[2]);
        printf("   Speed Lon: %15.9f°/day\n", $xx[3]);
        printf("   Speed Lat: %15.9f°/day\n", $xx[4]);
        printf("   Speed Dist:%15.9f AU/day\n", $xx[5]);
    }
    echo "\n";
}

echo "=== Testing Earth-Moon Barycenter (body 13) ===\n\n";

$bodies = [
    0 => 'Sun',
    1 => 'Moon',
    2 => 'Mercury',
    3 => 'Earth (returns Sun geocentric)',
    13 => 'Earth-Moon Barycenter',
];

foreach ($bodies as $id => $name) {
    $iflag = 2 + 256 + 4096; // Cartesian
    $result = $ffi->swe_calc_ut($jd, $id, $iflag, $xx, $serr);

    if ($result < 0) {
        echo "❌ Body $id ($name): " . FFI::string($serr) . "\n";
        continue;
    }

    echo "✅ Body $id ($name):\n";
    printf("   Position: [%.3f, %.3f, %.3f] AU\n", $xx[0], $xx[1], $xx[2]);
    printf("   Distance: %.9f AU\n", sqrt($xx[0]**2 + $xx[1]**2 + $xx[2]**2));
    echo "\n";
}

echo "=== Swiss Ephemeris .se1 File Format Analysis ===\n\n";

$seFile = $ephePath . '/semo_00.se1';
if (file_exists($seFile)) {
    $fp = fopen($seFile, 'rb');
    $header = fread($fp, 256);
    fclose($fp);

    echo "File: $seFile\n";
    echo "Size: " . filesize($seFile) . " bytes\n";
    echo "First 64 bytes (hex):\n";
    echo chunk_split(bin2hex(substr($header, 0, 64)), 32, "\n");
    echo "\n";

    // Попытка распознать формат
    $magic = substr($header, 0, 4);
    echo "Magic bytes: " . bin2hex($magic) . " ('" . addcslashes($magic, "\0..\37") . "')\n";

    // Swiss Eph обычно начинается с номера версии
    $values = unpack('V*', substr($header, 0, 16));
    echo "First 4 int32 values: ";
    print_r($values);
}

echo "\n=== Coordinate System Summary ===\n\n";
echo "Swiss Ephemeris native storage format:\n";
echo "  • Files (.se1): Chebyshev polynomials in ecliptic coordinates\n";
echo "  • Default output: Geocentric ecliptic (lon/lat/dist)\n";
echo "  • Can convert to: Equatorial, Cartesian (XYZ), various reference frames\n\n";

echo "Available reference frames:\n";
echo "  1. GEOCENTRIC: Center = Earth, default for planets\n";
echo "  2. HELIOCENTRIC: Center = Sun (SEFLG_HELCTR)\n";
echo "  3. BARYCENTRIC: Center = Solar System Barycenter (SEFLG_BARYCTR)\n";
echo "     Note: For Earth, returns Earth-Moon barycenter position\n";
echo "  4. TOPOCENTRIC: Center = Observer on Earth (SEFLG_TOPOCTR)\n\n";

echo "Available coordinate systems:\n";
echo "  1. ECLIPTIC: Longitude, Latitude, Distance (default)\n";
echo "  2. EQUATORIAL: RA, Dec, Distance (SEFLG_EQUATORIAL)\n";
echo "  3. CARTESIAN: X, Y, Z (SEFLG_XYZ)\n\n";

echo "Recommended storage for .eph files:\n";
echo "  • Geocentric Cartesian (XYZ) - most universal\n";
echo "  • Include SEFLG_SPEED for velocities\n";
echo "  • Store as is, convert in adapter on-demand\n";

$ffi->swe_close();
