#!/usr/bin/env python3
"""
Performance Analysis: find_duplicates optimization
Author: Performance Engineer (SuperClaude)

This module demonstrates performance optimization techniques for
finding duplicates in a list.
"""

import random
import time
from collections import Counter
from typing import Any, List

# ============================================================================
# ORIGINAL IMPLEMENTATION - O(n³) worst case
# ============================================================================


def find_duplicates_original(lst: List[Any]) -> List[Any]:
    """
    Original implementation with nested loops.

    Time Complexity: O(n³) worst case
        - O(n²) from nested loops
        - O(n) from `in` check on list for each comparison
    Space Complexity: O(d) where d = number of duplicates
    """
    duplicates = []
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            if lst[i] == lst[j] and lst[i] not in duplicates:
                duplicates.append(lst[i])
    return duplicates


# ============================================================================
# OPTIMIZED IMPLEMENTATION #1 - O(n) using set + Counter
# ============================================================================


def find_duplicates_counter(lst: List[Any]) -> List[Any]:
    """
    Optimized using Counter from collections.

    Time Complexity: O(n)
        - O(n) to build Counter
        - O(n) to filter (single pass)
    Space Complexity: O(n) for Counter storage
    """
    counts = Counter(lst)
    return [item for item, count in counts.items() if count > 1]


# ============================================================================
# OPTIMIZED IMPLEMENTATION #2 - O(n) using two sets (memory efficient)
# ============================================================================


def find_duplicates_two_sets(lst: List[Any]) -> List[Any]:
    """
    Optimized using two sets for seen and duplicates tracking.

    Time Complexity: O(n) - single pass through list
    Space Complexity: O(n) for sets

    This is often the fastest for typical use cases.
    """
    seen = set()
    duplicates = set()

    for item in lst:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)

    return list(duplicates)


# ============================================================================
# OPTIMIZED IMPLEMENTATION #3 - O(n) preserving order
# ============================================================================


def find_duplicates_ordered(lst: List[Any]) -> List[Any]:
    """
    Optimized version that preserves the order of first duplicate occurrence.

    Time Complexity: O(n)
    Space Complexity: O(n)
    """
    seen = set()
    duplicates = []
    duplicates_set = set()  # For O(1) membership check

    for item in lst:
        if item in seen and item not in duplicates_set:
            duplicates.append(item)
            duplicates_set.add(item)
        seen.add(item)

    return duplicates


# ============================================================================
# OPTIMIZED IMPLEMENTATION #4 - Using set intersection (elegant)
# ============================================================================


def find_duplicates_set_trick(lst: List[Any]) -> List[Any]:
    """
    Elegant one-liner using set comprehension.

    Time Complexity: O(n)
    Space Complexity: O(n)
    """
    seen = set()
    # Item is duplicate if seen.add() returns None (item was already there)
    # set.add() returns None always, so we use the walrus operator
    return list(
        {x for x in lst if x in seen or seen.add(x) is None and False}
        if False
        else {x for x in lst if x in seen or not seen.add(x)} - seen.union(set())
    )


# Cleaner version of the set trick:
def find_duplicates_clean(lst: List[Any]) -> List[Any]:
    """Clean set-based approach."""
    seen = set()
    return list({x for x in lst if x in seen or seen.add(x)})


# ============================================================================
# BENCHMARKING SUITE
# ============================================================================


def benchmark(func, data: List[Any], name: str, iterations: int = 3) -> float:
    """Run benchmark and return average time in milliseconds."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func(data)  # Execute function, result not needed for timing
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    avg_time = sum(times) / len(times)
    return avg_time


def run_benchmarks():
    """Run comprehensive benchmarks across different data sizes."""
    print("=" * 70)
    print("PERFORMANCE BENCHMARK: find_duplicates implementations")
    print("=" * 70)

    # Test configurations
    sizes = [100, 500, 1000, 2000, 5000]
    duplicate_ratios = [0.1, 0.5]  # 10% and 50% duplicates

    implementations = [
        ("Original O(n³)", find_duplicates_original),
        ("Counter O(n)", find_duplicates_counter),
        ("Two Sets O(n)", find_duplicates_two_sets),
        ("Ordered O(n)", find_duplicates_ordered),
        ("Clean Set O(n)", find_duplicates_clean),
    ]

    for ratio in duplicate_ratios:
        print(f"\n{'=' * 70}")
        print(f"Duplicate Ratio: {ratio * 100:.0f}%")
        print("=" * 70)

        print(f"\n{'Size':<10}", end="")
        for name, _ in implementations:
            print(f"{name:<18}", end="")
        print()
        print("-" * 100)

        for size in sizes:
            # Generate test data with controlled duplicate ratio
            unique_count = int(size * (1 - ratio))
            unique_items = list(range(unique_count))
            duplicated_items = random.choices(range(unique_count), k=size - unique_count)
            test_data = unique_items + duplicated_items
            random.shuffle(test_data)

            print(f"{size:<10}", end="")

            for name, func in implementations:
                # Skip original for large sizes (too slow)
                if "Original" in name and size > 2000:
                    print(f"{'SKIP':<18}", end="")
                    continue

                try:
                    avg_time = benchmark(func, test_data, name)
                    print(f"{avg_time:>8.3f} ms       ", end="")
                except Exception:
                    print(f"{'ERROR':<18}", end="")
            print()

    # Verify correctness
    print("\n" + "=" * 70)
    print("CORRECTNESS VERIFICATION")
    print("=" * 70)

    test_cases = [
        [1, 2, 3, 2, 1, 4, 5, 4],
        [1, 1, 1, 1],
        [1, 2, 3, 4, 5],
        [],
        ["a", "b", "a", "c", "b"],
    ]

    for test in test_cases:
        print(f"\nInput: {test}")
        original_result = sorted(find_duplicates_original(test))

        for name, func in implementations[1:]:  # Skip original
            result = sorted(func(test))
            status = "✓" if result == original_result else "✗"
            print(f"  {name}: {result} {status}")


def demonstrate_complexity():
    """Demonstrate the time complexity difference."""
    print("\n" + "=" * 70)
    print("COMPLEXITY DEMONSTRATION")
    print("=" * 70)
    print("\nScaling behavior as input size doubles:\n")

    sizes = [500, 1000, 2000, 4000]
    prev_original = None
    prev_optimized = None

    print(f"{'Size':<10}{'Original':<15}{'Ratio':<10}{'Optimized':<15}{'Ratio':<10}{'Speedup':<10}")
    print("-" * 70)

    for size in sizes:
        # Generate data with 50% duplicates
        unique = list(range(size // 2))
        data = unique + random.choices(unique, k=size // 2)
        random.shuffle(data)

        # Benchmark original (skip if too slow)
        if size <= 2000:
            t_original = benchmark(find_duplicates_original, data, "original", 2)
            ratio_orig = f"{t_original / prev_original:.2f}x" if prev_original else "-"
            prev_original = t_original
        else:
            t_original = float("inf")
            ratio_orig = "SKIP"

        # Benchmark optimized
        t_optimized = benchmark(find_duplicates_two_sets, data, "optimized", 2)
        ratio_opt = f"{t_optimized / prev_optimized:.2f}x" if prev_optimized else "-"
        prev_optimized = t_optimized

        # Calculate speedup
        speedup = f"{t_original / t_optimized:.0f}x" if t_original != float("inf") else ">>100x"

        orig_str = f"{t_original:.3f} ms" if t_original != float("inf") else "SKIP"
        print(
            f"{size:<10}{orig_str:<15}{ratio_orig:<10}{t_optimized:.3f} ms      {ratio_opt:<10}{speedup:<10}"
        )

    print("\nExpected ratios when doubling input:")
    print("  - O(n³): ~8x (2³ = 8)")
    print("  - O(n²): ~4x (2² = 4)")
    print("  - O(n):  ~2x (2¹ = 2)")


if __name__ == "__main__":
    run_benchmarks()
    demonstrate_complexity()
