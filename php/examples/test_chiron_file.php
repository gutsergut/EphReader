<?php

$file = __DIR__ . '/../../data/chiron/chiron_jpl.eph';
$fp = fopen($file, 'rb');

// Read header
$data = fread($fp, 512);
$header = unpack(
    'a4magic/Vversion/VnumBodies/VnumIntervals/' .
    'dintervalDays/dstartJD/dendJD/VcoeffDegree',
    $data
);

echo "HEADER:\n";
echo "  startJD: {$header['startJD']}, endJD: {$header['endJD']}\n";
echo "  numBodies: {$header['numBodies']}, numIntervals: {$header['numIntervals']}\n\n";

// Read body (int32 + char[24] + 2×uint32 for uint64)
fseek($fp, 512);
$data = fread($fp, 36);
$entry = unpack('lbodyId/a24name/Voffset_low/Voffset_high', $data);
$dataOffset = $entry['offset_low'] + ($entry['offset_high'] * (2**32));

echo "BODY:\n";
echo "  ID: {$entry['bodyId']}, name: {$entry['name']}\n";
echo "  Offset (parsed): $dataOffset\n\n";

// Read intervals (as floats!)
$intervalsOffset = 512 + 36 * $header['numBodies'];
fseek($fp, $intervalsOffset);

echo "INTERVALS (first 5, trying different formats):\n";
for ($i = 0; $i < min(5, $header['numIntervals']); $i++) {
    $pos = ftell($fp);
    $data = fread($fp, 16);  // Read 16 bytes to try doubles

    $as_doubles = unpack('djd_start/djd_end', $data);
    $as_floats_pairs = unpack('f1/f2/f3/f4', $data);

    echo "  [$i] (offset " . ($pos) . "):\n";
    echo "    As 2×double: {$as_doubles['jd_start']} - {$as_doubles['jd_end']}\n";
    echo "    As 4×float: {$as_floats_pairs[1]}, {$as_floats_pairs[2]}, {$as_floats_pairs[3]}, {$as_floats_pairs[4]}\n";
    echo "    Raw hex: " . bin2hex($data) . "\n";

    // Rewind for next interval (assume 8 bytes per interval for now)
    fseek($fp, $pos + 8);
}

fclose($fp);
