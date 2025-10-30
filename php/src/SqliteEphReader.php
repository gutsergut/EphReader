<?php
declare(strict_types=1);

namespace Swisseph\Ephemeris;

use PDO;
use PDOException;

/**
 * SQLite-based ephemeris reader (PHP-native, optimized)
 *
 * Advantages over binary .eph:
 * - Native PDO (no manual binary parsing)
 * - Indexed SQL queries (faster than binary search for random access)
 * - Compressed BLOBs (smaller file size)
 * - Easy debugging with sqlite3 command-line tool
 * - No offset calculations or format version issues
 */
class SqliteEphReader extends AbstractEphemeris implements EphemerisInterface
{
    private PDO $db;
    private bool $compressed = false;

    public function __construct(string $dbPath)
    {
        if (!file_exists($dbPath)) {
            throw new \RuntimeException("Ephemeris database not found: {$dbPath}");
        }

        try {
            $this->db = new PDO("sqlite:{$dbPath}");
            $this->db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

            // Load metadata
            $stmt = $this->db->query('SELECT key, value FROM metadata');
            while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
                $this->metadata[$row['key']] = $row['value'];
            }

            $this->compressed = (bool)($this->metadata['compressed'] ?? false);

            // Load bodies
            $stmt = $this->db->query('SELECT id, name FROM bodies ORDER BY id');
            while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
                $this->bodies[(int)$row['id']] = $row['name'];
            }

        } catch (PDOException $e) {
            throw new \RuntimeException("Failed to open ephemeris database: " . $e->getMessage());
        }
    }

    /**
     * Compute position and velocity for given body at Julian Date
     *
     * @param int $bodyId NAIF body ID (e.g., 399 = Earth)
     * @param float $jd Julian Date (TDB)
     * @param bool $computeVelocity Whether to compute velocity (default: true)
     * @return array ['pos' => [x, y, z], 'vel' => [vx, vy, vz]] in AU and AU/day
     */
    public function compute(int $bodyId, float $jd, bool $computeVelocity = true): array
    {
        // Find interval containing JD (indexed query)
        $stmt = $this->db->prepare('
            SELECT jd_start, jd_end, coeffs_x, coeffs_y, coeffs_z
            FROM intervals
            WHERE body_id = ? AND jd_start <= ? AND jd_end >= ?
            LIMIT 1
        ');
        $stmt->execute([$bodyId, $jd, $jd]);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);

        if (!$row) {
            throw new \OutOfRangeException(
                "JD {$jd} outside ephemeris range for body {$bodyId}"
            );
        }

        // Decompress and unpack coefficients
        $coeffs_x = $this->unpackCoeffs($row['coeffs_x']);
        $coeffs_y = $this->unpackCoeffs($row['coeffs_y']);
        $coeffs_z = $this->unpackCoeffs($row['coeffs_z']);

        // Normalize time to [-1, 1] within interval
        $t_norm = 2.0 * ($jd - $row['jd_start']) /
                  ($row['jd_end'] - $row['jd_start']) - 1.0;

        // Evaluate position
        $pos = [
            $this->chebyshev($coeffs_x, $t_norm),
            $this->chebyshev($coeffs_y, $t_norm),
            $this->chebyshev($coeffs_z, $t_norm)
        ];

        $result = ['pos' => $pos];

        if ($computeVelocity) {
            $dt = ($row['jd_end'] - $row['jd_start']) / 2.0;

            $vel = [
                $this->chebyshevDerivative($coeffs_x, $t_norm) / $dt,
                $this->chebyshevDerivative($coeffs_y, $t_norm) / $dt,
                $this->chebyshevDerivative($coeffs_z, $t_norm) / $dt
            ];

            $result['vel'] = $vel;
        }

        return $result;
    }

    /**
     * Unpack coefficients from BLOB (with optional decompression)
     */
    private function unpackCoeffs(string $blob): array
    {
        if ($this->compressed) {
            $blob = gzuncompress($blob);
            if ($blob === false) {
                throw new \RuntimeException("Failed to decompress coefficients");
            }
        }

        $degree = (int)($this->metadata['chebyshev_degree'] ?? 7);
        $numCoeffs = $degree + 1;

        $unpacked = unpack("d{$numCoeffs}", $blob);
        return $unpacked ? array_values($unpacked) : [];
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
            'format' => 'sqlite',
            'version' => $this->metadata['version'] ?? 'unknown',
            'source' => $this->metadata['source'] ?? 'unknown',
            'num_bodies' => (int)($this->metadata['num_bodies'] ?? 0),
            'num_intervals' => (int)($this->metadata['num_intervals'] ?? 0),
            'interval_days' => (float)($this->metadata['interval_days'] ?? 0),
            'start_jd' => (float)($this->metadata['start_jd'] ?? 0),
            'end_jd' => (float)($this->metadata['end_jd'] ?? 0),
            'degree' => (int)($this->metadata['chebyshev_degree'] ?? 0),
            'compressed' => $this->compressed
        ];
    }

    /**
     * Get database statistics
     */
    public function getStats(): array
    {
        $stats = [];

        // Total intervals
        $stmt = $this->db->query('SELECT COUNT(*) as count FROM intervals');
        $stats['totalIntervals'] = $stmt->fetchColumn();

        // Intervals per body
        $stmt = $this->db->query('
            SELECT b.name, COUNT(i.id) as count
            FROM bodies b
            LEFT JOIN intervals i ON b.id = i.body_id
            GROUP BY b.id, b.name
        ');
        $stats['intervalsPerBody'] = $stmt->fetchAll(PDO::FETCH_KEY_PAIR);

        // Database size
        $stmt = $this->db->query('SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()');
        $stats['databaseSize'] = $stmt->fetchColumn();

        return $stats;
    }
}
