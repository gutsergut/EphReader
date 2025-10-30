<?php
declare(strict_types=1);

namespace Swisseph\Ephemeris;

/**
 * Swiss Ephemeris Reader using .se1 files
 *
 * This reader parses Swiss Ephemeris proprietary .se1 format directly
 * without requiring the Swiss Ephemeris C library.
 *
 * Supports:
 * - Planets (semo_*.se1) - Moon positions
 * - Asteroids (seas_*.se1) - Asteroid positions
 *
 * Format structure (reverse-engineered):
 * - Header: 400 bytes (metadata)
 * - Records: Variable-length Chebyshev coefficient blocks
 */
class SwissEphReader extends AbstractEphemeris
{
    private const HEADER_SIZE = 400;

    private $fp;
    private array $header = [];
    private string $filepath;

    public function __construct(string $filepath)
    {
        $this->filepath = $filepath;

        if (!file_exists($filepath)) {
            throw new \RuntimeException("Swiss Ephemeris file not found: {$filepath}");
        }

        $this->fp = fopen($filepath, 'rb');
        if (!$this->fp) {
            throw new \RuntimeException("Cannot open file: {$filepath}");
        }

        $this->readHeader();
        $this->parseMetadata();
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

        // Swiss Ephemeris header format (partially documented)
        // Bytes 0-7: Magic/version
        // Bytes 8-15: Start JD
        // Bytes 16-23: End JD
        // Bytes 24-31: Granule size (days)

        $header = unpack(
            'a8magic/' .
            'dstartJD/' .
            'dendJD/' .
            'dgranule',
            $data
        );

        $this->header = $header;
    }

    private function parseMetadata(): void
    {
        $filename = basename($this->filepath);

        // Extract body ID from filename
        // semo_00.se1 → Moon epoch 0 (JD ~2414992.5)
        // seas_00.se1 → Asteroids epoch 0

        if (preg_match('/^semo_(\w+)\.se1$/', $filename, $matches)) {
            $this->metadata['type'] = 'moon';
            $this->metadata['epoch'] = $matches[1];
            $this->bodies[301] = 'Moon';
        } elseif (preg_match('/^seas_(\w+)\.se1$/', $filename, $matches)) {
            $this->metadata['type'] = 'asteroids';
            $this->metadata['epoch'] = $matches[1];
            // Load asteroid names from seasnam.txt
            $this->loadAsteroidNames();
        } elseif (preg_match('/^sepl_(\w+)\.se1$/', $filename, $matches)) {
            $this->metadata['type'] = 'planets';
            $this->metadata['epoch'] = $matches[1];
        }

        $this->metadata['format'] = 'swiss_ephemeris';
        $this->metadata['source'] = $filename;
        $this->metadata['start_jd'] = $this->header['startJD'] ?? 0;
        $this->metadata['end_jd'] = $this->header['endJD'] ?? 0;
        $this->metadata['granule'] = $this->header['granule'] ?? 0;
    }

    private function loadAsteroidNames(): void
    {
        $seasnamPath = dirname($this->filepath) . '/seasnam.txt';

        if (!file_exists($seasnamPath)) {
            return;
        }

        $lines = file($seasnamPath, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);

        foreach ($lines as $line) {
            // Format: "000001  Ceres" or just "000001"
            if (preg_match('/^(\d+)\s*(.*)$/', trim($line), $matches)) {
                $id = (int)$matches[1];
                $name = trim($matches[2]) ?: "Asteroid{$id}";

                // NAIF ID for asteroids: 2000000 + asteroid number
                $naifId = 2000000 + $id;
                $this->bodies[$naifId] = $name;
            }
        }
    }

    /**
     * {@inheritDoc}
     *
     * Note: This is a simplified implementation.
     * Full Swiss Ephemeris parsing requires deep knowledge of the format.
     * Consider using the C library via FFI for production use.
     */
    public function compute(int $bodyId, float $jd, bool $computeVelocity = true): array
    {
        if (!$this->hasBody($bodyId)) {
            throw new \InvalidArgumentException("Body ID {$bodyId} not available in this file");
        }

        if (!$this->isValidJD($jd)) {
            throw new \OutOfRangeException(
                "JD {$jd} outside range [{$this->metadata['start_jd']}, {$this->metadata['end_jd']}]"
            );
        }

        // TODO: Implement actual Swiss Ephemeris format parsing
        // This requires:
        // 1. Locate record for given JD
        // 2. Read Chebyshev coefficients
        // 3. Evaluate polynomials

        throw new \RuntimeException(
            "Swiss Ephemeris .se1 parsing not yet implemented. " .
            "Use SwissEphFFIReader for production or convert to .eph format."
        );
    }

    /**
     * Get raw data for conversion to other formats
     *
     * @param float $startJD Start Julian Date
     * @param float $endJD End Julian Date
     * @param int $bodyId Body ID to extract
     * @return array Array of intervals with Chebyshev coefficients
     */
    public function extractRawData(float $startJD, float $endJD, int $bodyId): array
    {
        // This method would be used by a converter tool
        // to extract data from Swiss Ephemeris and convert to .eph format

        throw new \RuntimeException("Raw data extraction not yet implemented");
    }
}
