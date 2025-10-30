<?php
declare(strict_types=1);

namespace Swisseph\Ephemeris;

/**
 * Factory for creating ephemeris readers
 *
 * Automatically detects format and returns appropriate reader:
 * - .eph → Binary format (EphReader)
 * - .db → SQLite format (SqliteEphReader)
 * - .msgpack → MessagePack format (MessagePackEphReader)
 * - .hidx → Hybrid format (HybridEphReader)
 * - .se1 → Swiss Ephemeris format (SwissEphReader) [TODO]
 * - .440/.441/.431 → JPL DE format (JPLReader) [TODO]
 */
class EphemerisFactory
{
    /**
     * Create ephemeris reader from file path
     *
     * @param string $filepath Path to ephemeris file
     * @return EphemerisInterface
     * @throws \RuntimeException if format not recognized
     */
    public static function create(string $filepath): EphemerisInterface
    {
        if (!file_exists($filepath)) {
            throw new \RuntimeException("Ephemeris file not found: {$filepath}");
        }

        $ext = strtolower(pathinfo($filepath, PATHINFO_EXTENSION));

        return match ($ext) {
            'eph' => new EphReader($filepath),
            'db' => new SqliteEphReader($filepath),
            'msgpack' => new MessagePackEphReader($filepath),
            'hidx' => new HybridEphReader($filepath),
            // TODO: Add Swiss Ephemeris and JPL readers
            // 'se1' => new SwissEphReader($filepath),
            // '440', '441', '431' => new JPLReader($filepath),
            default => throw new \RuntimeException("Unknown ephemeris format: .{$ext}")
        };
    }

    /**
     * Create reader with explicit format type
     *
     * @param string $filepath Path to file
     * @param string $format Format type: 'binary', 'sqlite', 'msgpack', 'hybrid'
     * @return EphemerisInterface
     */
    public static function createWithFormat(string $filepath, string $format): EphemerisInterface
    {
        return match (strtolower($format)) {
            'binary', 'eph' => new EphReader($filepath),
            'sqlite', 'db' => new SqliteEphReader($filepath),
            'msgpack', 'messagepack' => new MessagePackEphReader($filepath),
            'hybrid', 'hidx' => new HybridEphReader($filepath),
            default => throw new \RuntimeException("Unknown format: {$format}")
        };
    }

    /**
     * Get best format for use case
     *
     * @param string $useCase 'speed', 'size', 'debug', 'balanced'
     * @return string Recommended format
     */
    public static function getRecommendedFormat(string $useCase): string
    {
        return match (strtolower($useCase)) {
            'speed', 'performance', 'fast' => 'binary',
            'size', 'compact', 'small' => 'binary',
            'debug', 'development', 'inspect' => 'sqlite',
            'balanced', 'hybrid' => 'hybrid',
            'portable', 'msgpack' => 'msgpack',
            default => 'binary' // Default to fastest
        };
    }

    /**
     * Compare formats with statistics
     *
     * @param array $files ['binary' => 'path.eph', 'sqlite' => 'path.db', ...]
     * @return array Statistics comparison
     */
    public static function compareFormats(array $files): array
    {
        $comparison = [];

        foreach ($files as $format => $filepath) {
            if (!file_exists($filepath)) {
                continue;
            }

            try {
                $reader = self::create($filepath);
                $metadata = $reader->getMetadata();

                $comparison[$format] = [
                    'file_size' => filesize($filepath),
                    'num_bodies' => count($reader->getBodies()),
                    'time_range' => $reader->getTimeRange(),
                    'format_info' => $metadata['format'] ?? 'unknown'
                ];
            } catch (\Exception $e) {
                $comparison[$format] = ['error' => $e->getMessage()];
            }
        }

        return $comparison;
    }

    /**
     * Auto-discover ephemeris files in directory
     *
     * @param string $directory Directory to search
     * @return array ['format' => ['filepath1', 'filepath2'], ...]
     */
    public static function discover(string $directory): array
    {
        $found = [
            'binary' => [],
            'sqlite' => [],
            'msgpack' => [],
            'hybrid' => [],
            'swisseph' => [],
            'jpl' => []
        ];

        if (!is_dir($directory)) {
            return $found;
        }

        $iterator = new \RecursiveIteratorIterator(
            new \RecursiveDirectoryIterator($directory)
        );

        foreach ($iterator as $file) {
            if (!$file->isFile()) {
                continue;
            }

            $ext = strtolower($file->getExtension());
            $path = $file->getPathname();

            match ($ext) {
                'eph' => $found['binary'][] = $path,
                'db' => $found['sqlite'][] = $path,
                'msgpack' => $found['msgpack'][] = $path,
                'hidx' => $found['hybrid'][] = $path,
                'se1' => $found['swisseph'][] = $path,
                '440', '441', '431' => $found['jpl'][] = $path,
                default => null
            };
        }

        return $found;
    }
}
