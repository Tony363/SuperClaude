#!/usr/bin/env python3
"""Performance benchmark comparing duplicate-finding algorithms."""

import random
import time
from collections import Counter


# Original O(n²×k) implementation
def find_duplicates_original(lst):
    duplicates = []
    for i in range(len(lst)):
        for j in range(i+1, len(lst)):
            if lst[i] == lst[j] and lst[i] not in duplicates:
                duplicates.append(lst[i])
    return duplicates

# Optimized O(n) using Counter
def find_duplicates_counter(lst):
    counts = Counter(lst)
    return [item for item, count in counts.items() if count > 1]

# Optimized O(n) using sets
def find_duplicates_set(lst):
    seen = set()
    duplicates = set()
    for item in lst:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)
    return list(duplicates)

# O(n log n) sorting approach
def find_duplicates_sorted(lst):
    if not lst:
        return []
    sorted_lst = sorted(lst)
    duplicates = []
    prev = sorted_lst[0]
    is_dup = False
    for i in range(1, len(sorted_lst)):
        if sorted_lst[i] == prev:
            if not is_dup:
                duplicates.append(prev)
                is_dup = True
        else:
            prev = sorted_lst[i]
            is_dup = False
    return duplicates


def benchmark(func, data, runs=3):
    """Benchmark a function and return average time."""
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        result = func(data)
        end = time.perf_counter()
        times.append(end - start)
    return sum(times) / len(times), len(result)


def main():
    print("=" * 70)
    print("PERFORMANCE BENCHMARK: find_duplicates implementations")
    print("=" * 70)

    # Test correctness first
    test_data = [1, 2, 3, 2, 4, 5, 3, 6, 1]
    expected = {1, 2, 3}  # Use set for comparison

    print("\n[Correctness Test]")
    for name, func in [
        ("Original", find_duplicates_original),
        ("Counter", find_duplicates_counter),
        ("Set", find_duplicates_set),
        ("Sorted", find_duplicates_sorted),
    ]:
        result = set(func(test_data))
        status = "✓ PASS" if result == expected else f"✗ FAIL (got {result})"
        print(f"  {name}: {status}")

    # Benchmark different sizes
    print("\n[Performance Benchmarks]")

    sizes = [100, 500, 1000, 2000]

    for size in sizes:
        # Create test data with ~30% duplicates
        data = [random.randint(1, int(size * 0.7)) for _ in range(size)]

        print(f"\n  Size: {size:,} elements")
        print(f"  {'-' * 50}")

        results = {}

        # Only run original on smaller sizes (too slow otherwise)
        if size <= 1000:
            try:
                avg_time, dup_count = benchmark(find_duplicates_original, data, runs=1)
                results["Original"] = avg_time
                print(f"  Original (O(n²×k)):  {avg_time*1000:>10.3f} ms  ({dup_count} duplicates)")
            except Exception as e:
                print(f"  Original: Error - {e}")
        else:
            print("  Original (O(n²×k)):  SKIPPED (too slow)")

        # Run optimized versions
        for name, func, complexity in [
            ("Counter", find_duplicates_counter, "O(n)"),
            ("Set", find_duplicates_set, "O(n)"),
            ("Sorted", find_duplicates_sorted, "O(n log n)"),
        ]:
            avg_time, dup_count = benchmark(func, data, runs=3)
            results[name] = avg_time
            print(f"  {name} ({complexity}):  {avg_time*1000:>10.3f} ms")

        # Show speedup
        if "Original" in results and results["Original"] > 0:
            best_optimized = min(results["Counter"], results["Set"])
            speedup = results["Original"] / best_optimized
            print(f"\n  Speedup: {speedup:.1f}x faster with optimized version")

    # Large scale test (optimized only)
    print("\n" + "=" * 70)
    print("LARGE SCALE TEST (optimized versions only)")
    print("=" * 70)

    for size in [10_000, 50_000, 100_000]:
        data = [random.randint(1, int(size * 0.7)) for _ in range(size)]
        print(f"\n  Size: {size:,} elements")

        for name, func in [
            ("Counter", find_duplicates_counter),
            ("Set", find_duplicates_set),
            ("Sorted", find_duplicates_sorted),
        ]:
            avg_time, dup_count = benchmark(func, data, runs=3)
            print(f"    {name}: {avg_time*1000:>10.3f} ms")

    print("\n" + "=" * 70)
    print("CONCLUSION: Use Counter or Set-based approach for O(n) performance")
    print("=" * 70)


if __name__ == "__main__":
    main()
