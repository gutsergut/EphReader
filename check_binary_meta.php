<?php
require 'vendor/autoload.php';

$binary = new Swisseph\Ephemeris\EphReader('data/ephemerides/epm/2021/epm2021.eph');
$meta = $binary->getMetadata();

echo "Binary .eph metadata:\n";
print_r($meta);
