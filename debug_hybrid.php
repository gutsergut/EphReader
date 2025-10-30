<?php
$db = new PDO('sqlite:data/ephemerides/epm/2021/epm2021.hidx');

echo "Hybrid Index Data:\n";
echo "==================\n\n";

// Check metadata
$stmt = $db->query('SELECT * FROM metadata');
$meta = [];
while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    $meta[$row['key']] = $row['value'];
    echo "{$row['key']}: {$row['value']}\n";
}

echo "\n\nSample Intervals (Body 399 - Earth):\n";
echo "=====================================\n";

$stmt = $db->query('SELECT body_id, jd_start, jd_end, data_offset, data_size FROM intervals WHERE body_id = 399 LIMIT 5');
while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    printf("Body=%d JD=%.1f-%.1f offset=%d size=%d (%.1f doubles, %.0f coeffs per axis)\n",
        $row['body_id'], $row['jd_start'], $row['jd_end'],
        $row['data_offset'], $row['data_size'],
        $row['data_size'] / 8.0,
        ($row['data_size'] / 8.0) / 3.0);
}

// Test one interval
echo "\n\nTest Interval at JD 2451545.0:\n";
echo "================================\n";

$stmt = $db->prepare('
    SELECT jd_start, jd_end, data_offset, data_size
    FROM intervals
    WHERE body_id = ? AND jd_start <= ? AND jd_end >= ?
    LIMIT 1
');
$stmt->execute([399, 2451545.0, 2451545.0]);
$row = $stmt->fetch(PDO::FETCH_ASSOC);

if ($row) {
    printf("Interval: JD %.1f to %.1f\n", $row['jd_start'], $row['jd_end']);
    printf("Data: offset=%d size=%d\n", $row['data_offset'], $row['data_size']);

    // Read actual data
    $fp = fopen('data/ephemerides/epm/2021/epm2021.heph', 'rb');
    fseek($fp, $row['data_offset']);
    $data = fread($fp, $row['data_size']);
    fclose($fp);

    $totalDoubles = $row['data_size'] / 8;
    $coeffs = unpack("d{$totalDoubles}", $data);
    $coeffs = array_values($coeffs);

    echo "\nFirst 8 coefficients (X-axis):\n";
    for ($i = 0; $i < 8; $i++) {
        printf("  [%d] = %.15f\n", $i, $coeffs[$i]);
    }
} else {
    echo "No interval found!\n";
}
