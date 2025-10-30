<?php
declare(strict_types=1);

namespace Swisseph\Ephemeris;

use FFI;

/**
 * Swiss Ephemeris Reader using FFI to call native swetest.dll
 *
 * This reader uses PHP FFI to directly call Swiss Ephemeris C library
 * without requiring compilation or format conversion.
 *
 * Download swetest.dll from: https://www.astro.com/ftp/swisseph/
 * Place in vendor/swisseph/ directory
 *
 * Advantages:
 * - No compilation needed
 * - Access to full Swiss Ephemeris features
 * - Well-tested native library
 * - Supports 10,000+ asteroids and fixed stars
 */
class SwissEphFFIReader extends AbstractEphemeris
{
    private FFI $ffi;
    private string $ephePath;
    private bool $initialized = false;

    // Swiss Ephemeris planet constants
    private const SE_SUN = 0;
    private const SE_MOON = 1;
    private const SE_MERCURY = 2;
    private const SE_VENUS = 3;
    private const SE_MARS = 4;
    private const SE_JUPITER = 5;
    private const SE_SATURN = 6;
    private const SE_URANUS = 7;
    private const SE_NEPTUNE = 8;
    private const SE_PLUTO = 9;
    private const SE_EARTH = 14;

    // Flags
    private const SEFLG_SWIEPH = 2;     // Use Swiss Ephemeris
    private const SEFLG_HELCTR = 8;     // Heliocentric positions
    private const SEFLG_SPEED = 256;    // Calculate velocity
    private const SEFLG_XYZ = 2048;     // Cartesian coordinates

    // NAIF to Swiss Ephemeris mapping
    private const NAIF_TO_SWEPH = [
        1 => self::SE_MERCURY,
        2 => self::SE_VENUS,
        3 => 14, // Earth-Moon Barycenter → Earth
        4 => self::SE_MARS,
        5 => self::SE_JUPITER,
        6 => self::SE_SATURN,
        7 => self::SE_URANUS,
        8 => self::SE_NEPTUNE,
        9 => self::SE_PLUTO,
        10 => self::SE_SUN,
        301 => self::SE_MOON,
        399 => self::SE_EARTH,
    ];

    public function __construct(string $dllPath, string $ephePath)
    {
        if (!extension_loaded('ffi')) {
            throw new \RuntimeException("FFI extension not enabled. Enable in php.ini: extension=ffi");
        }

        if (!file_exists($dllPath)) {
            throw new \RuntimeException("Swiss Ephemeris DLL not found: {$dllPath}");
        }

        if (!is_dir($ephePath)) {
            throw new \RuntimeException("Ephemeris directory not found: {$ephePath}");
        }

        $this->ephePath = $ephePath;

        // Load FFI interface
        $this->ffi = FFI::cdef("
            void swe_set_ephe_path(char *path);
            int swe_calc_ut(double tjd_ut, int ipl, int iflag, double *xx, char *serr);
            void swe_close(void);
            char *swe_version(char *svers);
        ", $dllPath);

        $this->initialize();
    }

    private function initialize(): void
    {
        // Set ephemeris path
        $this->ffi->swe_set_ephe_path($this->ephePath);

        // Get version
        $version = FFI::new("char[256]");
        $this->ffi->swe_version($version);
        $versionStr = FFI::string($version);

        // Setup metadata
        $this->metadata = [
            'format' => 'swiss_ephemeris_ffi',
            'source' => 'Swiss Ephemeris ' . $versionStr,
            'ephe_path' => $this->ephePath,
            'start_jd' => 2305424.5,  // ~1600 AD (typical Swiss Eph coverage)
            'end_jd' => 2524624.5,     // ~2100 AD
            'interval_days' => 'variable', // Swiss Eph uses adaptive intervals
            'degree' => 'variable'
        ];

        // Setup bodies
        $this->bodies = [
            1 => 'Mercury',
            2 => 'Venus',
            3 => 'EMB',
            4 => 'Mars',
            5 => 'Jupiter',
            6 => 'Saturn',
            7 => 'Uranus',
            8 => 'Neptune',
            9 => 'Pluto',
            10 => 'Sun',
            301 => 'Moon',
            399 => 'Earth'
        ];

        $this->initialized = true;
    }

    public function __destruct()
    {
        if ($this->initialized) {
            $this->ffi->swe_close();
        }
    }

    /**
     * {@inheritDoc}
     */
    public function compute(int $bodyId, float $jd, bool $computeVelocity = true): array
    {
        if (!$this->initialized) {
            throw new \RuntimeException("Swiss Ephemeris not initialized");
        }

        // Map NAIF ID to Swiss Ephemeris planet number
        if (!isset(self::NAIF_TO_SWEPH[$bodyId])) {
            throw new \InvalidArgumentException("Body ID {$bodyId} not supported");
        }

        $planet = self::NAIF_TO_SWEPH[$bodyId];

        // Setup flags
        $flags = self::SEFLG_SWIEPH | self::SEFLG_HELCTR | self::SEFLG_XYZ;
        if ($computeVelocity) {
            $flags |= self::SEFLG_SPEED;
        }

        // Allocate result array (6 doubles: x, y, z, vx, vy, vz)
        $result = FFI::new("double[6]");
        $error = FFI::new("char[256]");

        // Call Swiss Ephemeris
        $ret = $this->ffi->swe_calc_ut($jd, $planet, $flags, $result, $error);

        if ($ret < 0) {
            $errMsg = FFI::string($error);
            throw new \RuntimeException("Swiss Ephemeris error: {$errMsg}");
        }

        // Extract results
        $pos = [$result[0], $result[1], $result[2]];
        $vel = $computeVelocity ? [$result[3], $result[4], $result[5]] : [0.0, 0.0, 0.0];

        return [
            'pos' => $pos,
            'vel' => $vel
        ];
    }
}
