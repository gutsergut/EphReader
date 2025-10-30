<?php
// Проверка систем координат Swiss Ephemeris

$ffi = FFI::cdef('
    void swe_set_ephe_path(char *path);
    int swe_calc(double tjd, int ipl, int iflag, double *xx, char *serr);
', 'vendor/swisseph/swedll64.dll');

$ffi->swe_set_ephe_path('ephe');
$jd = 2451545.0;
$body = 5; // Jupiter
$AU_TO_KM = 149597870.7;

echo "Swiss Ephemeris Coordinate Systems Test\n";
echo "=========================================\n\n";
echo "Body: Jupiter\n";
echo "JD: $jd (J2000.0)\n\n";

// Geocentric XYZ
$xx_geo = FFI::new('double[6]');
$serr = FFI::new('char[256]');
$ffi->swe_calc($jd, $body, 2|256|4096, $xx_geo, $serr); // default = geocentric

echo "Geocentric XYZ:\n";
printf("  X: %12.6f AU = %15.0f km\n", $xx_geo[0], $xx_geo[0] * $AU_TO_KM);
printf("  Y: %12.6f AU = %15.0f km\n", $xx_geo[1], $xx_geo[1] * $AU_TO_KM);
printf("  Z: %12.6f AU = %15.0f km\n", $xx_geo[2], $xx_geo[2] * $AU_TO_KM);
$dist_geo = sqrt($xx_geo[0]**2 + $xx_geo[1]**2 + $xx_geo[2]**2);
printf("  Distance: %12.6f AU = %15.0f km\n\n", $dist_geo, $dist_geo * $AU_TO_KM);

// Heliocentric XYZ
$xx_helio = FFI::new('double[6]');
$ffi->swe_calc($jd, $body, 2|256|4096|8, $xx_helio, $serr); // HELCTR

echo "Heliocentric XYZ:\n";
printf("  X: %12.6f AU = %15.0f km\n", $xx_helio[0], $xx_helio[0] * $AU_TO_KM);
printf("  Y: %12.6f AU = %15.0f km\n", $xx_helio[1], $xx_helio[1] * $AU_TO_KM);
printf("  Z: %12.6f AU = %15.0f km\n", $xx_helio[2], $xx_helio[2] * $AU_TO_KM);
$dist_helio = sqrt($xx_helio[0]**2 + $xx_helio[1]**2 + $xx_helio[2]**2);
printf("  Distance: %12.6f AU = %15.0f km\n\n", $dist_helio, $dist_helio * $AU_TO_KM);

// Barycentric XYZ
$xx_bary = FFI::new('double[6]');
$ffi->swe_calc($jd, $body, 2|256|4096|16384, $xx_bary, $serr); // BARYCTR

echo "Barycentric XYZ:\n";
printf("  X: %12.6f AU = %15.0f km\n", $xx_bary[0], $xx_bary[0] * $AU_TO_KM);
printf("  Y: %12.6f AU = %15.0f km\n", $xx_bary[1], $xx_bary[1] * $AU_TO_KM);
printf("  Z: %12.6f AU = %15.0f km\n", $xx_bary[2], $xx_bary[2] * $AU_TO_KM);
$dist_bary = sqrt($xx_bary[0]**2 + $xx_bary[1]**2 + $xx_bary[2]**2);
printf("  Distance: %12.6f AU = %15.0f km\n\n", $dist_bary, $dist_bary * $AU_TO_KM);

echo "Expected (JPL DE440 Jupiter @ J2000):\n";
echo "  Heliocentric: ~5.2 AU (~778 million km)\n";
echo "  Barycentric: slightly different due to Solar System barycenter offset\n";
