#!/usr/bin/env python3
"""
SPICE BSP Performance Benchmark
Tests original EPM2021 SPICE file performance
"""

import spiceypy as sp
import time
import numpy as np
import sys
import json

# Configuration
SPICE_FILE = 'data/ephemerides/epm/2021/spice/epm2021.bsp'
BODY_ID = 399  # Earth
ITERATIONS = 1000
J2000_JD = 2451545.0

# Load SPICE kernel
sp.furnsh(SPICE_FILE)

def jd_to_et(jd):
    """Convert Julian Date to Ephemeris Time"""
    return (jd - J2000_JD) * 86400.0

def compute_position(body_id, jd):
    """Compute position at given JD"""
    et = jd_to_et(jd)
    state, _ = sp.spkgps(body_id, et, 'J2000', 0)
    # Convert km to AU
    pos_au = [x / 149597870.7 for x in state[:3]]
    return pos_au

# Generate test data
np.random.seed(42)
start_jd = 2374000.5
end_jd = 2530000.5
random_jds = np.random.uniform(start_jd, end_jd, ITERATIONS)
sequential_jds = np.arange(J2000_JD, J2000_JD + ITERATIONS, 1.0)

results = {
    'format': 'SPICE BSP (Original)',
    'file_size_mb': 147.13,
    'body_id': BODY_ID,
    'iterations': ITERATIONS
}

# Test 1: Initialization (kernel loading)
print("Testing SPICE initialization...", file=sys.stderr)
start = time.time()
sp.kclear()
sp.furnsh(SPICE_FILE)
init_time_ms = (time.time() - start) * 1000
results['init_time_ms'] = init_time_ms

# Test 2: Single computation (J2000.0)
print("Testing single computation...", file=sys.stderr)
start = time.time()
pos = compute_position(BODY_ID, J2000_JD)
single_time_ms = (time.time() - start) * 1000
results['single_time_ms'] = single_time_ms
results['single_pos_x'] = pos[0]

# Test 3: Random access
print(f"Testing random access ({ITERATIONS} iterations)...", file=sys.stderr)
start = time.time()
for jd in random_jds:
    compute_position(BODY_ID, jd)
random_time_ms = (time.time() - start) * 1000
results['random_total_ms'] = random_time_ms
results['random_avg_ms'] = random_time_ms / ITERATIONS
results['random_ops_per_sec'] = int(ITERATIONS / (random_time_ms / 1000))

# Test 4: Sequential access
print(f"Testing sequential access ({ITERATIONS} iterations)...", file=sys.stderr)
start = time.time()
for jd in sequential_jds:
    compute_position(BODY_ID, jd)
seq_time_ms = (time.time() - start) * 1000
results['seq_total_ms'] = seq_time_ms
results['seq_avg_ms'] = seq_time_ms / ITERATIONS
results['seq_ops_per_sec'] = int(ITERATIONS / (seq_time_ms / 1000))

# Output results as JSON
print(json.dumps(results, indent=2))

sp.kclear()
