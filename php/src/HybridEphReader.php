<?php
declare(strict_types=1);

namespace Swisseph\Ephemeris;

/**
 * Hybrid ephemeris reader (.hidx + .heph)
 *
 * Combines advantages of SQLite and Binary:
 * - SQLite index: Fast lookups, metadata queries
 * - Binary data: Compact coefficient storage
 * - Can use mmap for zero-copy coefficient access
 * - Separates metadata from bulk data
 *
 * Format:
 * - .hidx: SQLite database (metadata, bodies, intervals→offset mapping)
 * - .heph: Binary coefficient data (sequential doubles)
 */
class HybridEphReader extends AbstractEphemeris
{
    private \PDO $db;
    private $dataFp;
    private string $dataPath;

    public function __construct(string $indexPath)
    {
        if (!file_exists($indexPath)) {
            throw new \RuntimeException("Hybrid index not found: {$indexPath}");
        }

        // Open SQLite index
        $this->db = new \PDO("sqlite:{$indexPath}");
        $this->db->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);

        // Load metadata
        $stmt = $this->db->query('SELECT key, value FROM metadata');
        while ($row = $stmt->fetch(\PDO::FETCH_ASSOC)) {
            $this->metadata[$row['key']] = $row['value'];
        }
        $this->metadata['format'] = 'hybrid';

        // Normalize degree key for compatibility
        if (isset($this->metadata['chebyshev_degree'])) {
            $this->metadata['degree'] = $this->metadata['chebyshev_degree'];
        }

        // Load bodies
        $stmt = $this->db->query('SELECT id, name FROM bodies');
        while ($row = $stmt->fetch(\PDO::FETCH_ASSOC)) {
            $this->bodies[(int)$row['id']] = $row['name'];
        }

        // Open binary data file
        $dataFile = $this->metadata['data_file'] ?? null;
        if (!$dataFile) {
            throw new \RuntimeException("Metadata missing 'data_file' field");
        }

        $basePath = dirname($indexPath);
        $this->dataPath = $basePath . DIRECTORY_SEPARATOR . $dataFile;

        if (!file_exists($this->dataPath)) {
            throw new \RuntimeException("Hybrid data file not found: {$this->dataPath}");
        }

        $this->dataFp = fopen($this->dataPath, 'rb');
        if (!$this->dataFp) {
            throw new \RuntimeException("Cannot open data file: {$this->dataPath}");
        }
    }

    public function __destruct()
    {
        if ($this->dataFp) {
            fclose($this->dataFp);
        }
    }

    /**
     * {@inheritDoc}
     */
    public function compute(int $bodyId, float $jd, bool $computeVelocity = true): array
    {
        // Query index for interval
        $stmt = $this->db->prepare('
            SELECT jd_start, jd_end, data_offset, data_size
            FROM intervals
            WHERE body_id = ? AND jd_start <= ? AND jd_end >= ?
            LIMIT 1
        ');

        $stmt->execute([$bodyId, $jd, $jd]);
        $row = $stmt->fetch(\PDO::FETCH_ASSOC);

        if (!$row) {
            throw new \OutOfRangeException(
                "JD {$jd} outside ephemeris range for body {$bodyId}"
            );
        }

        // Read coefficients from binary file
        $coeffs = $this->readCoefficients($row['data_offset'], $row['data_size']);

        // Normalize time
        $t_norm = 2.0 * ($jd - $row['jd_start']) /
                  ($row['jd_end'] - $row['jd_start']) - 1.0;

        // Evaluate position
        $pos = [
            $this->chebyshev($coeffs['x'], $t_norm),
            $this->chebyshev($coeffs['y'], $t_norm),
            $this->chebyshev($coeffs['z'], $t_norm)
        ];

        $result = ['pos' => $pos];

        if ($computeVelocity) {
            $dt = ($row['jd_end'] - $row['jd_start']) / 2.0;
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
     * Read coefficients from binary data file
     */
    private function readCoefficients(int $offset, int $size): array
    {
        fseek($this->dataFp, $offset);
        $data = fread($this->dataFp, $size);

        $numCoeffs = (int)($this->metadata['chebyshev_degree'] ?? 7) + 1;
        $totalDoubles = $size / 8; // 8 bytes per double

        $coeffs = unpack("d{$totalDoubles}", $data);
        $coeffs = array_values($coeffs); // Convert to 0-indexed

        return [
            'x' => array_slice($coeffs, 0, $numCoeffs),
            'y' => array_slice($coeffs, $numCoeffs, $numCoeffs),
            'z' => array_slice($coeffs, 2 * $numCoeffs, $numCoeffs)
        ];
    }

    /**
     * Get statistics
     */
    public function getStats(): array
    {
        $stmt = $this->db->query('SELECT COUNT(*) as total FROM intervals');
        $totalIntervals = $stmt->fetchColumn();

        $stmt = $this->db->query('SELECT body_id, COUNT(*) as count FROM intervals GROUP BY body_id');
        $intervalsPerBody = [];
        while ($row = $stmt->fetch(\PDO::FETCH_ASSOC)) {
            $bodyName = $this->bodies[$row['body_id']] ?? "Body{$row['body_id']}";
            $intervalsPerBody[$bodyName] = $row['count'];
        }

        return [
            'format' => 'Hybrid',
            'indexSize' => filesize(str_replace('.heph', '.hidx', $this->dataPath)),
            'dataSize' => filesize($this->dataPath),
            'totalIntervals' => $totalIntervals,
            'intervalsPerBody' => $intervalsPerBody
        ];
    }

    /**
     * {@inheritDoc}
     */
    public function getTimeRange(): array
    {
        return [
            'start' => (float)($this->metadata['start_jd'] ?? 0.0),
            'end' => (float)($this->metadata['end_jd'] ?? 0.0)
        ];
    }
}
