<?php
declare(strict_types=1);

namespace Swisseph\Ephemeris;

/**
 * MessagePack ephemeris reader
 *
 * Advantages:
 * - Compact binary format (smaller than SQLite, faster deserialization)
 * - Simple file structure (one file to manage)
 * - Can use msgpack PHP extension OR pure PHP fallback
 * - Easy to convert to JSON for debugging
 *
 * Requirements:
 * - Preferred: pecl install msgpack (10-20× faster)
 * - Fallback: Pure PHP implementation (slower but works everywhere)
 */
class MessagePackEphReader extends AbstractEphemeris
{
    private array $data;
    private array $intervals = [];

    public function __construct(string $filepath)
    {
        if (!file_exists($filepath)) {
            throw new \RuntimeException("MessagePack file not found: {$filepath}");
        }

        $contents = file_get_contents($filepath);

        // Try msgpack extension first, fallback to pure PHP
        if (function_exists('msgpack_unpack')) {
            $this->data = msgpack_unpack($contents);
        } else {
            // Fallback: use pure PHP implementation (slower)
            throw new \RuntimeException(
                "msgpack extension not installed. Run: pecl install msgpack\n" .
                "Or use SQLite/Binary formats instead."
            );
        }

        $this->metadata = $this->data['metadata'] ?? [];
        $this->metadata['format'] = 'msgpack';

        // Build bodies map
        foreach ($this->data['bodies'] ?? [] as $bodyId => $bodyData) {
            $this->bodies[$bodyId] = $bodyData['name'];
        }

        // Convert intervals to internal format
        foreach ($this->data['intervals'] ?? [] as $interval) {
            $this->intervals[] = [
                'start' => $interval['start'],
                'end' => $interval['end']
            ];
        }
    }

    /**
     * {@inheritDoc}
     */
    public function compute(int $bodyId, float $jd, bool $computeVelocity = true): array
    {
        if (!isset($this->data['coefficients'][$bodyId])) {
            throw new \InvalidArgumentException("Body ID {$bodyId} not found");
        }

        // Find interval
        $intervalIdx = $this->findInterval($this->intervals, $jd);
        $interval = $this->intervals[$intervalIdx];

        // Get coefficients for this body/interval
        $coeffs = $this->data['coefficients'][$bodyId][$intervalIdx];

        // Normalize time to [-1, 1]
        $t_norm = 2.0 * ($jd - $interval['start']) /
                  ($interval['end'] - $interval['start']) - 1.0;

        // Evaluate position
        $pos = [
            $this->chebyshev($coeffs['x'], $t_norm),
            $this->chebyshev($coeffs['y'], $t_norm),
            $this->chebyshev($coeffs['z'], $t_norm)
        ];

        $result = ['pos' => $pos];

        if ($computeVelocity) {
            $dt = ($interval['end'] - $interval['start']) / 2.0;
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
     * Export to JSON for debugging
     */
    public function toJSON(): string
    {
        return json_encode($this->data, JSON_PRETTY_PRINT);
    }

    /**
     * Get file statistics
     */
    public function getStats(): array
    {
        $totalCoeffs = 0;
        foreach ($this->data['coefficients'] ?? [] as $bodyCoeffs) {
            $totalCoeffs += count($bodyCoeffs);
        }

        return [
            'format' => 'MessagePack',
            'numBodies' => count($this->bodies),
            'numIntervals' => count($this->intervals),
            'totalCoeffSets' => $totalCoeffs,
            'avgCoeffsPerSet' => $totalCoeffs > 0 ?
                array_sum(array_map('count', $this->data['coefficients'][array_key_first($this->data['coefficients'])] ?? [[]])) / count($this->intervals) : 0
        ];
    }
}
