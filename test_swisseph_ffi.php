<?php
/**
 * Test Swiss Ephemeris DLL via FFI
 * Проверяет работоспособность скомпилированной DLL
 */

declare(strict_types=1);

$dllPath = __DIR__ . '/vendor/swisseph/swedll64.dll';

if (!file_exists($dllPath)) {
    echo "❌ DLL not found: $dllPath\n";
    echo "Please compile first: .\build_swisseph.ps1\n";
    exit(1);
}

if (!extension_loaded('ffi')) {
    echo "❌ PHP FFI extension not available\n";
    echo "Enable in php.ini: extension=ffi\n";
    exit(1);
}

try {
    echo "🔧 Loading Swiss Ephemeris DLL...\n";
    echo "   Path: $dllPath\n";
    echo "   Size: " . round(filesize($dllPath) / 1024 / 1024, 2) . " MB\n\n";

    // Минимальный FFI интерфейс для тестирования
    $ffi = FFI::cdef("
        void swe_set_ephe_path(char *path);
        char *swe_version(char *version);
        int swe_calc_ut(double tjd_ut, int ipl, int iflag, double *xx, char *serr);
        void swe_close(void);
    ", $dllPath);

    // Получить версию Swiss Ephemeris
    $version = FFI::new("char[256]");
    $ffi->swe_version($version);
    $versionStr = FFI::string($version);

    echo "✅ Swiss Ephemeris DLL loaded successfully!\n";
    echo "   Version: $versionStr\n\n";

    // Установить путь к эфемеридам
    $ephePath = __DIR__ . '/ephe';
    if (!is_dir($ephePath)) {
        echo "⚠️  Warning: Ephemeris directory not found: $ephePath\n";
        echo "   DLL works, but calculations need .se1 files\n";
    } else {
        $ffi->swe_set_ephe_path($ephePath);
        echo "📂 Ephemeris path set: $ephePath\n\n";

        // Тест: вычислить положение Солнца на J2000.0
        $jd = 2451545.0;  // J2000.0
        $ipl = 0;         // Sun
        $iflag = 2;       // SEFLG_SWIEPH
        $xx = FFI::new("double[6]");
        $serr = FFI::new("char[256]");

        echo "🌞 Testing Sun position calculation...\n";
        echo "   Date: JD $jd (J2000.0)\n";

        $result = $ffi->swe_calc_ut($jd, $ipl, $iflag, $xx, $serr);

        if ($result < 0) {
            $error = FFI::string($serr);
            echo "❌ Calculation error: $error\n";
        } else {
            echo "✅ Calculation successful!\n";
            echo "   Longitude: " . number_format($xx[0], 6) . "°\n";
            echo "   Latitude:  " . number_format($xx[1], 6) . "°\n";
            echo "   Distance:  " . number_format($xx[2], 9) . " AU\n";

            // Проверка разумности результата
            // Солнце на J2000.0: долгота ~280°, расстояние ~0.983 AU
            if ($xx[0] > 270 && $xx[0] < 290 && $xx[2] > 0.98 && $xx[2] < 1.02) {
                echo "\n🎯 Results look correct!\n";
            } else {
                echo "\n⚠️  Results might be incorrect (check ephemeris files)\n";
            }
        }
    }

    // Закрыть библиотеку
    $ffi->swe_close();
    echo "\n✅ Test complete!\n";

} catch (FFI\Exception $e) {
    echo "❌ FFI Error: " . $e->getMessage() . "\n";
    echo "\nPossible causes:\n";
    echo "  1. DLL is corrupted\n";
    echo "  2. DLL is 32-bit (need 64-bit for PHP x64)\n";
    echo "  3. Missing dependencies (MSVC runtime)\n";
    exit(1);
} catch (Throwable $e) {
    echo "❌ Error: " . $e->getMessage() . "\n";
    exit(1);
}
