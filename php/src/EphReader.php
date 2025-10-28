<?php
declare(strict_types=1);

namespace Swisseph\Ephemeris;

/**
 * Optimized ephemeris reader for custom .eph binary format
 *
 * Format spec:
 * - Header: 512 bytes (magic, version, metadata)
 * - Body table: N × 32 bytes (body IDs, names, offsets)
 * - Interval index: M × 16 bytes (JD ranges)
 * - Coefficients: packed doubles (Chebyshev coefficients)
 */
class EphReader
{
    private const MAGIC = "EPH\0";
    private const HEADER_SIZE = 512;
    private const BODY_ENTRY_SIZE = 36;  // int32(4) + char[24](24) + uint64(8)
    private const INTERVAL_ENTRY_SIZE = 16;

    private $fp;
    private array $header;
    private array $bodies = [];
    private array $intervals = [];

    public function __construct(string $filepath)
    {
        if (!file_exists($filepath)) {
            throw new \RuntimeException("Ephemeris file not found: {$filepath}");
        }

        $this->fp = fopen($filepath, 'rb');
        if (!$this->fp) {
            throw new \RuntimeException("Cannot open ephemeris file: {$filepath}");
        }

        $this->readHeader();
        $this->readBodyTable();
        $this->readIntervalIndex();
    }

    public function __destruct()
    {
        if ($this->fp) {
            fclose($this->fp);
        }
    }

    private function readHeader(): void
    {
        fseek($this->fp, 0);
        $data = fread($this->fp, self::HEADER_SIZE);

        $unpacked = unpack(
            'a4magic/Vversion/VnumBodies/VnumIntervals/' .
            'dintervalDays/dstartJD/dendJD/VcoeffDegree',
            $data
        );

        if ($unpacked['magic'] !== self::MAGIC) {
            throw new \RuntimeException("Invalid magic: expected EPH, got {$unpacked['magic']}");
        }

        $this->header = $unpacked;
    }

    private function readBodyTable(): void
    {
        $offset = self::HEADER_SIZE;
        fseek($this->fp, $offset);

        for ($i = 0; $i < $this->header['numBodies']; $i++) {
            $data = fread($this->fp, self::BODY_ENTRY_SIZE);
            $entry = unpack('lbodyId/a24name/QdataOffset', $data);

            $this->bodies[$entry['bodyId']] = [
                'name' => rtrim($entry['name'], "\0"),
                'offset' => $entry['dataOffset']
            ];
        }
    }

    private function readIntervalIndex(): void
    {
        $offset = self::HEADER_SIZE +
                  $this->header['numBodies'] * self::BODY_ENTRY_SIZE;
        fseek($this->fp, $offset);

        for ($i = 0; $i < $this->header['numIntervals']; $i++) {
            $data = fread($this->fp, self::INTERVAL_ENTRY_SIZE);
            $interval = unpack('djdStart/djdEnd', $data);
            $this->intervals[] = $interval;
        }
    }

    /**
     * Find interval index for given Julian Date
     */
    private function findInterval(float $jd): int
    {
        // Binary search
        $left = 0;
        $right = count($this->intervals) - 1;

        while ($left <= $right) {
            $mid = (int)(($left + $right) / 2);
            $interval = $this->intervals[$mid];

            if ($jd < $interval['jdStart']) {
                $right = $mid - 1;
            } elseif ($jd > $interval['jdEnd']) {
                $left = $mid + 1;
            } else {
                return $mid;
            }
        }

        throw new \OutOfRangeException(
            "JD {$jd} outside ephemeris range [{$this->header['startJD']}, {$this->header['endJD']}]"
        );
    }

    /**
     * Read Chebyshev coefficients for given body and interval
     */
    private function readCoefficients(int $bodyId, int $intervalIdx): array
    {
        if (!isset($this->bodies[$bodyId])) {
            throw new \InvalidArgumentException("Unknown body ID: {$bodyId}");
        }

        $numCoeffs = $this->header['coeffDegree'] + 1; // degree 13 → 14 coeffs
        $coeffsPerComponent = $numCoeffs;
        $componentsPerBody = 3; // X, Y, Z
        $totalCoeffs = $coeffsPerComponent * $componentsPerBody;

        $bodyOffset = $this->bodies[$bodyId]['offset'];
        $intervalOffset = $intervalIdx * $totalCoeffs * 8; // 8 bytes per double

        $offset = $bodyOffset + $intervalOffset;
        fseek($this->fp, $offset);

        $data = fread($this->fp, $totalCoeffs * 8);
        $coeffs = unpack("d{$totalCoeffs}", $data);

        // unpack() returns 1-indexed array, convert to 0-indexed
        $coeffs = array_values($coeffs);

        return [
            'x' => array_slice($coeffs, 0, $coeffsPerComponent),
            'y' => array_slice($coeffs, $coeffsPerComponent, $coeffsPerComponent),
            'z' => array_slice($coeffs, 2 * $coeffsPerComponent, $coeffsPerComponent)
        ];
    }

    /**
     * Evaluate Chebyshev polynomial T_n(x)
     */
    private function chebyshev(array $coeffs, float $x): float
    {
        $n = count($coeffs);
        if ($n === 0) return 0.0;
        if ($n === 1) return $coeffs[0];

        // Clenshaw's recurrence algorithm
        $b_k1 = 0.0;
        $b_k2 = 0.0;

        for ($k = $n - 1; $k >= 1; $k--) {
            $b_k = 2.0 * $x * $b_k1 - $b_k2 + $coeffs[$k];
            $b_k2 = $b_k1;
            $b_k1 = $b_k;
        }

        return $x * $b_k1 - $b_k2 + $coeffs[0];
    }

    /**
     * Compute position (and velocity) for given body at Julian Date
     *
     * @param int $bodyId NAIF body ID (e.g., 399 = Earth)
     * @param float $jd Julian Date (TDB)
     * @param bool $computeVelocity Whether to compute velocity (default: true)
     * @return array ['pos' => [x, y, z], 'vel' => [vx, vy, vz]] in AU and AU/day
     */
    public function compute(int $bodyId, float $jd, bool $computeVelocity = true): array
    {
        $intervalIdx = $this->findInterval($jd);
        $interval = $this->intervals[$intervalIdx];
        $coeffs = $this->readCoefficients($bodyId, $intervalIdx);

        // Normalize time to [-1, 1] within interval
        $t_norm = 2.0 * ($jd - $interval['jdStart']) /
                  ($interval['jdEnd'] - $interval['jdStart']) - 1.0;

        // Evaluate position
        $pos = [
            $this->chebyshev($coeffs['x'], $t_norm),
            $this->chebyshev($coeffs['y'], $t_norm),
            $this->chebyshev($coeffs['z'], $t_norm)
        ];

        $result = ['pos' => $pos];

        if ($computeVelocity) {
            // Velocity = derivative of Chebyshev
            // dT/dt = (2 / interval_length) × dT/dx
            $dt = ($interval['jdEnd'] - $interval['jdStart']) / 2.0;

            $vel = [
                $this->chebyshevDerivative($coeffs['x'], $t_norm) / $dt,
                $this->chebyshevDerivative($coeffs['y'], $t_norm) / $dt,
                $this->chebyshevDerivative($coeffs['z'], $t_norm) / $dt
            ];

            $result['vel'] = $vel;
        }

        return $result;
    }

    /**
     * Evaluate derivative of Chebyshev polynomial
     */
    private function chebyshevDerivative(array $coeffs, float $x): float
    {
        $n = count($coeffs);
        if ($n === 0) return 0.0;
        if ($n === 1) return 0.0;

        // Derivative coefficients using Chebyshev differentiation formula
        $deriv = array_fill(0, $n - 1, 0.0);

        if ($n >= 2) {
            $deriv[$n - 2] = 2.0 * ($n - 1) * ($coeffs[$n - 1] ?? 0.0);
        }

        for ($k = $n - 3; $k >= 0; $k--) {
            $deriv[$k] = ($deriv[$k + 2] ?? 0.0) + 2.0 * ($k + 1) * ($coeffs[$k + 1] ?? 0.0);
        }

        return $this->chebyshev($deriv, $x);
    }

    /**
     * Get available bodies
     */
    public function getBodies(): array
    {
        return $this->bodies;
    }

    /**
     * Get ephemeris metadata
     */
    public function getMetadata(): array
    {
        return [
            'version' => $this->header['version'],
            'numBodies' => $this->header['numBodies'],
            'numIntervals' => $this->header['numIntervals'],
            'intervalDays' => $this->header['intervalDays'],
            'startJD' => $this->header['startJD'],
            'endJD' => $this->header['endJD'],
            'coeffDegree' => $this->header['coeffDegree']
        ];
    }
}
