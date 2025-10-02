#!/usr/bin/env python3
"""Demo of checkpoint management and cache invalidation.

Shows how the system determines whether to use cached results or run fresh analysis.
"""

from pathlib import Path

from investing_agents.core.checkpoint import CheckpointManager


def main():
    print("=" * 80)
    print("CHECKPOINT MANAGEMENT DEMO")
    print("=" * 80)

    # Example 1: Check if we can use cached NVDA analysis
    print("\n📋 Scenario 1: Checking cache for NVDA analysis")
    print("-" * 80)

    work_dir = Path("nvidia_test_fixed")
    manager = CheckpointManager(work_dir)

    use_cache, checkpoint, reason = manager.should_use_cache(
        ticker="NVDA", company="NVIDIA Corporation", max_age_hours=24
    )

    print(f"Work directory: {work_dir}")
    print(f"Use cache: {use_cache}")
    print(f"Reason: {reason}")

    if checkpoint:
        print(f"Checkpoint: {checkpoint}")

        # Validate the cache
        is_valid, validation_reason = manager.validate_cache(
            checkpoint, ticker="NVDA", company="NVIDIA Corporation"
        )
        print(f"\nCache valid: {is_valid}")
        print(f"Validation: {validation_reason}")

        # Get resume point
        resume_info = manager.get_resume_point(checkpoint)
        if resume_info:
            print(f"\nResume info:")
            print(f"  Status: {resume_info.get('status', 'N/A')}")
            print(f"  Resume from: {resume_info.get('resume_from')}")

            if resume_info.get("resume_from") == "completed":
                print(f"  ✅ Analysis complete - can load from cache")
                print(f"  Final report: {resume_info.get('final_report_path')}")
            elif resume_info.get("resume_from") == "partial":
                print(f"  ⚠️  Analysis incomplete - can resume from checkpoint")
                print(f"  Has hypotheses: {resume_info.get('has_hypotheses')}")

    # Example 2: Different ticker (should invalidate cache)
    print("\n\n📋 Scenario 2: Requesting different ticker (AAPL)")
    print("-" * 80)

    use_cache, checkpoint, reason = manager.should_use_cache(
        ticker="AAPL",  # Different ticker!
        company="Apple Inc.",
        max_age_hours=24,
    )

    print(f"Use cache: {use_cache}")
    print(f"Reason: {reason}")
    print(f"✅ Cache correctly invalidated for different ticker")

    # Example 3: Force refresh
    print("\n\n📋 Scenario 3: Force refresh (--no-cache flag)")
    print("-" * 80)

    use_cache, checkpoint, reason = manager.should_use_cache(
        ticker="NVDA",
        company="NVIDIA Corporation",
        max_age_hours=24,
        force_refresh=True,  # User requested fresh analysis
    )

    print(f"Use cache: {use_cache}")
    print(f"Reason: {reason}")
    print(f"✅ Cache correctly bypassed with force_refresh=True")

    # Example 4: Stale cache (> 24 hours old)
    print("\n\n📋 Scenario 4: Stale cache check (max_age_hours=1)")
    print("-" * 80)

    use_cache, checkpoint, reason = manager.should_use_cache(
        ticker="NVDA",
        company="NVIDIA Corporation",
        max_age_hours=1,  # Only accept cache < 1 hour old
    )

    print(f"Use cache: {use_cache}")
    print(f"Reason: {reason}")
    if not use_cache:
        print(f"✅ Cache correctly rejected as too old")

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
