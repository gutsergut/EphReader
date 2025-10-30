<?php
declare(strict_types=1);

namespace Swisseph\Ephemeris;

/**
 * Common interface for all ephemeris readers
 *
 * Provides unified API regardless of underlying format:
 * - Binary .eph
 * - SQLite .db
 * - JSON/MessagePack .msgpack
 * - Hybrid .heph
 * - Swiss Ephemeris .se1
 * - JPL DE .440/.441/.431
 */
interface EphemerisInterface
{
    /**
     * Compute position and velocity for given body at Julian Date
     *
     * @param int $bodyId NAIF body ID (1-10, 199-999, 301, 399)
     * @param float $jd Julian Date (TDB)
     * @param bool $computeVelocity Whether to compute velocity (default: true)
     * @return array ['pos' => [x, y, z], 'vel' => [vx, vy, vz]] in AU and AU/day
     * @throws \OutOfRangeException if JD outside ephemeris range
     * @throws \InvalidArgumentException if body ID not available
     */
    public function compute(int $bodyId, float $jd, bool $computeVelocity = true): array;

    /**
     * Batch compute positions for multiple bodies at same JD
     *
     * @param array $bodyIds Array of NAIF body IDs
     * @param float $jd Julian Date (TDB)
     * @param bool $computeVelocity Whether to compute velocities
     * @return array Associative array [bodyId => ['pos' => [...], 'vel' => [...]]]
     */
    public function computeBatch(array $bodyIds, float $jd, bool $computeVelocity = true): array;

    /**
     * Get available bodies in this ephemeris
     *
     * @return array Associative array [bodyId => name]
     */
    public function getBodies(): array;

    /**
     * Get ephemeris metadata
     *
     * @return array [
     *   'format' => string,
     *   'version' => string,
     *   'startJD' => float,
     *   'endJD' => float,
     *   'numBodies' => int,
     *   'source' => string
     * ]
     */
    public function getMetadata(): array;

    /**
     * Check if body is available
     *
     * @param int $bodyId NAIF body ID
     * @return bool
     */
    public function hasBody(int $bodyId): bool;

    /**
     * Check if JD is within ephemeris range
     *
     * @param float $jd Julian Date
     * @return bool
     */
    public function isValidJD(float $jd): bool;

    /**
     * Get ephemeris time range
     *
     * @return array ['start' => float, 'end' => float]
     */
    public function getTimeRange(): array;
}
