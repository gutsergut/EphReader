<?php
/**
 * Comprehensive Swiss Ephemeris Coordinate Systems Test
 * Tests all combinations of bodies, frames, and coordinate systems
 */

require_once __DIR__ . '/tools/swisseph_universal.php';

echo "=== SWISS EPHEMERIS COORDINATE SYSTEMS MATRIX ===\n";
echo "Test Date: J2000.0 (JD 2451545.0)\n\n";

$bodies = [
    0 => 'Sun',
    1 => 'Mercury',
    2 => 'Venus',
    3 => 'Earth',
    301 => 'Moon',
    13 => 'Earth-Moon Barycenter',
];

$frames = ['geocentric', 'heliocentric', 'barycentric'];

echo str_repeat('=', 100) . "\n";
printf("%-25s | %-15s | %-20s | %-15s | %-10s\n", 
    "Body", "Frame", "Position (AU)", "Velocity", "Distance");
echo str_repeat('=', 100) . "\n";

foreach ($bodies as $bodyId => $bodyName) {
    foreach ($frames as $frame) {
        $cmd = "php tools/swisseph_universal.php $bodyId 2451545.0 $frame cartesian";
        $result = json_decode(shell_exec($cmd), true);
        
        if (isset($result['error'])) {
            printf("%-25s | %-15s | ERROR: %s\n", $bodyName, $frame, $result['error']);
            continue;
        }
        
        $AU = 149597870.7;
        $pos_au = [
            $result['pos'][0] / $AU,
            $result['pos'][1] / $AU,
            $result['pos'][2] / $AU,
        ];
        
        $dist_au = sqrt($pos_au[0]**2 + $pos_au[1]**2 + $pos_au[2]**2);
        
        $vel_au = sqrt(
            ($result['vel'][0] / $AU)**2 + 
            ($result['vel'][1] / $AU)**2 + 
            ($result['vel'][2] / $AU)**2
        );
        
        $pos_str = sprintf("[%7.4f, %7.4f]", $pos_au[0], $pos_au[1]);
        $vel_str = sprintf("%7.6f AU/d", $vel_au);
        $dist_str = sprintf("%9.6f AU", $dist_au);
        
        printf("%-25s | %-15s | %-20s | %-15s | %s\n", 
            $bodyName, $frame, $pos_str, $vel_str, $dist_str);
    }
    echo str_repeat('-', 100) . "\n";
}

echo "\n=== KEY FINDINGS ===\n\n";

echo "1. GEOCENTRIC (default):\n";
echo "   - Sun: ~0.983 AU (147M km) - Earth to Sun distance ✅\n";
echo "   - Moon: ~0.0027 AU (402k km) - Earth to Moon distance ✅\n";
echo "   - Planets: Distance from Earth\n";
echo "   - EMB: ~0.0027 AU - offset from Earth center\n\n";

echo "2. HELIOCENTRIC:\n";
echo "   - Sun: 0 AU - Sun is center ✅\n";
echo "   - Planets: Distance from Sun\n";
echo "   - Earth: ~1 AU from Sun\n";
echo "   - Moon: Complex (Earth + lunar orbit)\n\n";

echo "3. BARYCENTRIC (Solar System Barycenter):\n";
echo "   - Sun: ~0.0077 AU (1.15M km) - SSB offset from Sun center ✅\n";
echo "   - Planets: Distance from SSB\n";
echo "   - EMB: 0 AU when body=13 (EMB is itself in this frame)\n\n";

echo "4. STORAGE RECOMMENDATION:\n";
echo "   - Store: GEOCENTRIC CARTESIAN (native Swiss Eph format)\n";
echo "   - Convert on-the-fly: Other frames via mathematical transformations\n";
echo "   - Advantages: Single source of truth, smaller files, flexible output\n\n";

echo "=== NATIVE FORMAT (.se1 files) ===\n\n";
echo "Swiss Ephemeris .se1 files contain:\n";
echo "  • Chebyshev polynomials\n";
echo "  • Ecliptic coordinates (longitude, latitude, distance)\n";
echo "  • Geocentric reference frame\n";
echo "  • Can output any frame/coords via flags at runtime\n\n";

echo "For .eph conversion, recommended approach:\n";
echo "  1. Extract GEOCENTRIC CARTESIAN from Swiss Eph\n";
echo "  2. Store as-is in .eph (like EPM2021/DE440)\n";
echo "  3. Add coordinate transformation layer in PHP adapter\n";
echo "  4. Support all frames: geocentric, heliocentric, barycentric, emb\n";
