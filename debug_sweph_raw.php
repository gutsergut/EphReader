<?php
$ffi = FFI::cdef("
    void swe_set_ephe_path(char *path);
    int swe_calc_ut(double tjd_ut, int ipl, int iflag, double *xx, char *serr);
", 'vendor/swisseph/swedll64.dll');

$ffi->swe_set_ephe_path('ephe');
$xx = FFI::new('double[6]');
$serr = FFI::new('char[256]');

// Test Sun at J2000.0, с флагом скорости
$iflag = 2 + 256; // SEFLG_SWIEPH + SEFLG_SPEED
$result = $ffi->swe_calc_ut(2451545.0, 0, $iflag, $xx, $serr);

echo "Result: $result\n";
for ($i = 0; $i < 6; $i++) {
    echo "xx[$i] = " . $xx[$i] . "\n";
}
