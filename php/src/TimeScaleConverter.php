<?php
/**
 * Time Scale Converter: UT ↔ TDB/TT conversion.
 *
 * Handles conversion between different astronomical time scales:
 * - UT (Universal Time) - civil time, used by Swiss Ephemeris
 * - TT (Terrestrial Time) - uniform atomic time scale
 * - TDB (Barycentric Dynamical Time) - used by JPL ephemerides
 *
 * References:
 * - IERS Bulletins: https://www.iers.org/
 * - USNO Delta T: https://maia.usno.navy.mil/
 * - Espenak & Meeus polynomial approximations
 *
 * @package Swisseph\Ephemeris
 */

namespace Swisseph\Ephemeris;

class TimeScaleConverter
{
    /**
     * TT - TAI offset (constant).
     * TT = TAI + 32.184 seconds
     */
    private const TT_TAI_OFFSET = 32.184;

    /**
     * Leap seconds table (TAI - UTC).
     * Source: IERS Bulletin C
     * Updated: 2025-10
     */
    private const LEAP_SECONDS = [
        2441317.5 => 10,  // 1972-01-01
        2441499.5 => 11,  // 1972-07-01
        2441683.5 => 12,  // 1973-01-01
        2442048.5 => 13,  // 1974-01-01
        2442413.5 => 14,  // 1975-01-01
        2442778.5 => 15,  // 1976-01-01
        2443144.5 => 16,  // 1977-01-01
        2443509.5 => 17,  // 1978-01-01
        2443874.5 => 18,  // 1979-01-01
        2444239.5 => 19,  // 1980-01-01
        2444786.5 => 20,  // 1981-07-01
        2445151.5 => 21,  // 1982-07-01
        2445516.5 => 22,  // 1983-07-01
        2446247.5 => 23,  // 1985-07-01
        2447161.5 => 24,  // 1988-01-01
        2447892.5 => 25,  // 1990-01-01
        2448257.5 => 26,  // 1991-01-01
        2448804.5 => 27,  // 1992-07-01
        2449169.5 => 28,  // 1993-07-01
        2449534.5 => 29,  // 1994-07-01
        2450083.5 => 30,  // 1996-01-01
        2450630.5 => 31,  // 1997-07-01
        2451179.5 => 32,  // 1999-01-01
        2453736.5 => 33,  // 2006-01-01
        2454832.5 => 34,  // 2009-01-01
        2456109.5 => 35,  // 2012-07-01
        2457204.5 => 36,  // 2015-07-01
        2457754.5 => 37,  // 2017-01-01
    ];

    /**
     * Convert Julian Day from UT to TDB.
     *
     * @param float $jd_ut Julian Day in UT time scale
     * @return float Julian Day in TDB time scale
     */
    public static function utToTDB(float $jd_ut): float
    {
        $deltaT = self::getDeltaT($jd_ut);
        return $jd_ut + ($deltaT / 86400.0);
    }

    /**
     * Convert Julian Day from TDB to UT.
     *
     * @param float $jd_tdb Julian Day in TDB time scale
     * @return float Julian Day in UT time scale
     */
    public static function tdbToUT(float $jd_tdb): float
    {
        // Iterative solution (TDB depends on UT, which we're solving for)
        $jd_ut = $jd_tdb;
        for ($i = 0; $i < 3; $i++) {
            $deltaT = self::getDeltaT($jd_ut);
            $jd_ut = $jd_tdb - ($deltaT / 86400.0);
        }
        return $jd_ut;
    }

    /**
     * Convert Julian Day from UT to TT (Terrestrial Time).
     *
     * @param float $jd_ut Julian Day in UT time scale
     * @return float Julian Day in TT time scale
     */
    public static function utToTT(float $jd_ut): float
    {
        $deltaT = self::getDeltaT($jd_ut);
        return $jd_ut + ($deltaT / 86400.0);
    }

    /**
     * Calculate Delta T (TT - UT) in seconds.
     *
     * Uses polynomial approximations from:
     * - Espenak & Meeus (2006) for historical dates
     * - Morrison & Stephenson (2004) for ancient dates
     * - IERS measurements for modern dates
     *
     * @param float $jd_ut Julian Day in UT
     * @return float Delta T in seconds
     */
    public static function getDeltaT(float $jd_ut): float
    {
        // Convert JD to calendar year
        $year = self::jdToDecimalYear($jd_ut);

        // Modern era (1972-2025): use leap seconds + measured UT1-UTC
        if ($year >= 1972.0 && $year <= 2025.0) {
            return self::getDeltaTModern($jd_ut);
        }

        // Near-modern era (1800-1972): polynomial approximations
        if ($year >= 1800.0 && $year < 1972.0) {
            return self::getDeltaTPolynomial($year);
        }

        // Historical era (before 1800): extrapolation
        return self::getDeltaTHistorical($year);
    }

    /**
     * Get Delta T for modern era using leap seconds.
     *
     * @param float $jd_ut Julian Day in UT
     * @return float Delta T in seconds
     */
    private static function getDeltaTModern(float $jd_ut): float
    {
        // Find current leap seconds
        $leapSeconds = 10; // Default before 1972
        foreach (self::LEAP_SECONDS as $jd_leap => $ls) {
            if ($jd_ut >= $jd_leap) {
                $leapSeconds = $ls;
            } else {
                break;
            }
        }

        // TT = TAI + 32.184
        // TAI = UTC + leapSeconds
        // UT1 ≈ UTC (within 0.9 seconds, we approximate UT ≈ UT1 ≈ UTC)
        // Therefore: TT - UT ≈ leapSeconds + 32.184

        // Add small correction for UT1-UTC (measured by IERS)
        // Typical range: -0.9 to +0.9 seconds
        // For simplicity, use average correction based on year
        $year = self::jdToDecimalYear($jd_ut);
        $ut1_utc_correction = self::getUT1MinusUTC($year);

        return $leapSeconds + self::TT_TAI_OFFSET - $ut1_utc_correction;
    }

    /**
     * Estimate UT1-UTC correction (seconds).
     * Source: IERS Earth Orientation Parameters
     *
     * @param float $year Decimal year
     * @return float UT1-UTC in seconds
     */
    private static function getUT1MinusUTC(float $year): float
    {
        // Simplified model: UT1-UTC oscillates with ~7-year period
        // due to variations in Earth's rotation rate
        // Amplitude: ±0.9 seconds (IERS constraint)

        // Recent measurements (approximate):
        if ($year >= 2020.0 && $year <= 2025.0) {
            // Linear interpolation between known values
            // 2020: -0.18 s
            // 2025: +0.15 s (estimated)
            return -0.18 + ($year - 2020.0) * (0.33 / 5.0);
        }

        // Default: assume small correction
        return 0.0;
    }

    /**
     * Get Delta T using polynomial approximations (1800-1972).
     * Source: Espenak & Meeus (2006)
     *
     * @param float $year Decimal year
     * @return float Delta T in seconds
     */
    private static function getDeltaTPolynomial(float $year): float
    {
        if ($year >= 1900.0 && $year < 1920.0) {
            // 1900-1920: Espenak & Meeus formula
            $t = $year - 1900.0;
            return -2.79 + 1.494119 * $t - 0.0598939 * $t**2
                   + 0.0061966 * $t**3 - 0.000197 * $t**4;
        }

        if ($year >= 1920.0 && $year < 1941.0) {
            $t = $year - 1920.0;
            return 21.20 + 0.84493 * $t - 0.076100 * $t**2
                   + 0.0020936 * $t**3;
        }

        if ($year >= 1941.0 && $year < 1961.0) {
            $t = $year - 1950.0;
            return 29.07 + 0.407 * $t - $t**2 / 233.0
                   + $t**3 / 2547.0;
        }

        if ($year >= 1961.0 && $year < 1972.0) {
            $t = $year - 1975.0;
            return 45.45 + 1.067 * $t - $t**2 / 260.0
                   - $t**3 / 718.0;
        }

        if ($year >= 1800.0 && $year < 1900.0) {
            $t = $year - 1800.0;
            return -2.50 + 0.228 * $t + 0.54 * $t**2
                   + 0.033 * $t**3;
        }

        // Fallback
        return 0.0;
    }

    /**
     * Get Delta T for historical dates (extrapolation).
     * Source: Morrison & Stephenson (2004)
     *
     * @param float $year Decimal year
     * @return float Delta T in seconds
     */
    private static function getDeltaTHistorical(float $year): float
    {
        // Parabolic approximation for ancient times
        $t = ($year - 1820.0) / 100.0;
        return -20.0 + 32.0 * $t**2;
    }

    /**
     * Convert Julian Day to decimal year.
     *
     * @param float $jd Julian Day
     * @return float Decimal year (e.g., 2000.5 for mid-2000)
     */
    private static function jdToDecimalYear(float $jd): float
    {
        // J2000.0 = JD 2451545.0 = 2000-01-01 12:00 TT
        // Days per year (average): 365.25
        return 2000.0 + ($jd - 2451545.0) / 365.25;
    }

    /**
     * Get Delta T summary for a given date.
     *
     * @param float $jd_ut Julian Day in UT
     * @return array Summary with breakdown
     */
    public static function getDeltaTBreakdown(float $jd_ut): array
    {
        $year = self::jdToDecimalYear($jd_ut);
        $deltaT = self::getDeltaT($jd_ut);

        $breakdown = [
            'jd_ut' => $jd_ut,
            'year' => $year,
            'delta_t_seconds' => $deltaT,
            'delta_t_days' => $deltaT / 86400.0,
            'jd_tdb' => $jd_ut + ($deltaT / 86400.0),
        ];

        if ($year >= 1972.0 && $year <= 2025.0) {
            $leapSeconds = 37; // Current as of 2025
            $ut1_utc = self::getUT1MinusUTC($year);
            $breakdown['leap_seconds'] = $leapSeconds;
            $breakdown['tt_tai_offset'] = self::TT_TAI_OFFSET;
            $breakdown['ut1_utc_correction'] = $ut1_utc;
            $breakdown['formula'] = "ΔT = {$leapSeconds} (leap) + " .
                                   self::TT_TAI_OFFSET . " (TT-TAI) - " .
                                   number_format($ut1_utc, 3) . " (UT1-UTC)";
        } else {
            $breakdown['method'] = 'polynomial_approximation';
        }

        return $breakdown;
    }
}
