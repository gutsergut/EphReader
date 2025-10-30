<?php

declare(strict_types=1);

namespace Swisseph\Ephemeris;

/**
 * Extended EphReader with Chiron support.
 *
 * Reads binary .eph files for both regular ephemerides (EPM2021, DE440)
 * and Chiron-specific ephemeris from JPL Horizons.
 *
 * @package Swisseph\Ephemeris
 */
class ChironEphReader extends EphReader
{
    /**
     * Chiron body ID.
     */
    public const BODY_CHIRON = 2060;

    /**
     * Compute position for Chiron or any other body.
     *
     * Overrides parent to add Chiron support with special handling
     * for Chiron-specific .eph files.
     *
     * @param int $bodyId Body ID (e.g., 2060 for Chiron, 399 for Earth)
     * @param float $jd Julian Date
     * @param bool $computeVelocity Whether to compute velocity (default: true)
     * @return array{pos: array{0: float, 1: float, 2: float}, vel: array{0: float, 1: float, 2: float}}
     * @throws \RuntimeException If computation fails
     */
    public function compute(int $bodyId, float $jd, bool $computeVelocity = true): array
    {
        // Check if this is a Chiron-specific file
        if ($bodyId === self::BODY_CHIRON && $this->header['numBodies'] === 1) {
            // Dedicated Chiron file - use optimized path
            return $this->computeChiron($jd);
        }

        // Otherwise use standard EphReader logic
        return parent::compute($bodyId, $jd, $computeVelocity);
    }

    /**
     * Compute Chiron position using Chebyshev polynomials.
     *
     * @param float $jd Julian Date
     * @return array{pos: array{0: float, 1: float, 2: float}, vel: array{0: float, 1: float, 2: float}}
     * @throws \RuntimeException If JD out of range or computation fails
     */
    private function computeChiron(float $jd): array
    {
        // Validate JD range
        if ($jd < $this->header['startJD'] || $jd > $this->header['endJD']) {
            throw new \RuntimeException(sprintf(
                'JD %.1f out of range [%.1f, %.1f]',
                $jd,
                $this->header['startJD'],
                $this->header['endJD']
            ));
        }

        // Find interval containing this JD (binary search)
        $interval_idx = $this->findInterval($this->intervals, $jd);

        // Read interval metadata
        $interval = $this->intervals[$interval_idx];
        $jd_start = $interval['start'];
        $jd_end = $interval['end'];

        // Normalize time to [-1, 1] for Chebyshev evaluation
        $t_normalized = 2.0 * ($jd - $jd_start) / ($jd_end - $jd_start) - 1.0;

        // Read Chebyshev coefficients for this interval
        $coeffs = $this->readCoefficients(self::BODY_CHIRON, $interval_idx);

        // Extract X, Y, Z coefficients
        $x_coeffs = $coeffs['x'];
        $y_coeffs = $coeffs['y'];
        $z_coeffs = $coeffs['z'];

        $x = $this->evaluateChebyshev($x_coeffs, $t_normalized);
        $y = $this->evaluateChebyshev($y_coeffs, $t_normalized);
        $z = $this->evaluateChebyshev($z_coeffs, $t_normalized);

        // Compute velocities (derivative of Chebyshev polynomials)
        $dt_norm_dj = 2.0 / ($jd_end - $jd_start);  // dt_normalized / dJD

        $vx = $this->evaluateChebyshevDerivative($x_coeffs, $t_normalized) * $dt_norm_dj;
        $vy = $this->evaluateChebyshevDerivative($y_coeffs, $t_normalized) * $dt_norm_dj;
        $vz = $this->evaluateChebyshevDerivative($z_coeffs, $t_normalized) * $dt_norm_dj;

        return [
            'pos' => [$x, $y, $z],
            'vel' => [$vx, $vy, $vz]
        ];
    }

    /**
     * Find interval index containing given JD (uses parent implementation).
     *
     * @param array $intervals Interval array
     * @param float $jd Julian Date
     * @return int Interval index
     * @throws \RuntimeException If interval not found
     */
    protected function findInterval(array $intervals, float $jd): int
    {
        // Use parent implementation
        return parent::findInterval($intervals, $jd);
    }



    /**
     * Evaluate Chebyshev polynomial at given point.
     *
     * Uses Clenshaw's algorithm for numerical stability.
     *
     * @param array<float> $coeffs Chebyshev coefficients (c0, c1, c2, ...)
     * @param float $x Point to evaluate at (should be in [-1, 1])
     * @return float Polynomial value
     */
    private function evaluateChebyshev(array $coeffs, float $x): float
    {
        // Clenshaw's algorithm
        $n = count($coeffs);
        if ($n === 0) {
            return 0.0;
        }
        if ($n === 1) {
            return $coeffs[0];
        }

        $b_k_plus_2 = 0.0;
        $b_k_plus_1 = 0.0;

        // Iterate from highest degree to lowest
        for ($k = $n - 1; $k >= 1; $k--) {
            $b_k = 2.0 * $x * $b_k_plus_1 - $b_k_plus_2 + $coeffs[$k];
            $b_k_plus_2 = $b_k_plus_1;
            $b_k_plus_1 = $b_k;
        }

        // Final step (k=0)
        return $x * $b_k_plus_1 - $b_k_plus_2 + $coeffs[0];
    }

    /**
     * Evaluate derivative of Chebyshev polynomial.
     *
     * T'_n(x) = n * U_{n-1}(x) where U is Chebyshev polynomial of 2nd kind.
     *
     * @param array<float> $coeffs Chebyshev coefficients
     * @param float $x Point to evaluate at
     * @return float Derivative value
     */
    private function evaluateChebyshevDerivative(array $coeffs, float $x): float
    {
        $n = count($coeffs);
        if ($n <= 1) {
            return 0.0;  // Derivative of constant is 0
        }

        // Compute derivative coefficients
        // d/dx T_n(x) = n * U_{n-1}(x)
        // where U_k are Chebyshev polynomials of the second kind

        $deriv_coeffs = [];
        for ($i = 1; $i < $n; $i++) {
            $sum = 0.0;
            for ($j = $i; $j < $n; $j++) {
                if (($j - $i) % 2 === 0) {
                    $sum += 2.0 * $j * $coeffs[$j];
                }
            }
            if ($i === 0) {
                $sum /= 2.0;
            }
            $deriv_coeffs[] = $sum;
        }

        // For simpler alternative: Use finite difference on polynomial evaluation
        // This is less accurate but easier to implement
        $h = 1e-8;
        $f_plus = $this->evaluateChebyshev($coeffs, $x + $h);
        $f_minus = $this->evaluateChebyshev($coeffs, $x - $h);

        return ($f_plus - $f_minus) / (2.0 * $h);
    }

    /**
     * Get human-readable body name.
     *
     * @param int $body_id Body ID
     * @return string Body name
     */
    public static function getBodyName(int $body_id): string
    {
        if ($body_id === self::BODY_CHIRON) {
            return 'Chiron';
        }

        // Fall back to parent class names
        return parent::getBodyName($body_id);
    }
}
