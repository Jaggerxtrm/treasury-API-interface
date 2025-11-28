#!/usr/bin/env python3
"""
Compare two pipeline runs to validate consistency
"""

import re
from pathlib import Path

def extract_metrics(filepath):
    """Extract key metrics from pipeline report"""
    with open(filepath, 'r') as f:
        content = f.read()

    metrics = {}

    # Extract execution summary
    if match := re.search(r'\*\*Status:\*\* (\d+)/(\d+) scripts completed successfully', content):
        metrics['success_count'] = int(match.group(1))
        metrics['total_scripts'] = int(match.group(2))

    if match := re.search(r'\*\*Total Duration:\*\* ([\d.]+) seconds', content):
        metrics['total_duration'] = float(match.group(1))

    # Extract individual script durations
    script_durations = {}
    for match in re.finditer(r'### \d+\. (python .+?)\n\n\*\*Status:\*\* (✅|❌) .+?\n\*\*Duration:\*\* ([\d.]+) seconds', content, re.DOTALL):
        script = match.group(1)
        status = match.group(2)
        duration = float(match.group(3))
        script_durations[script] = {'status': status, 'duration': duration}

    metrics['scripts'] = script_durations

    return metrics

def compare_runs(reference_file, current_file):
    """Compare two pipeline runs"""

    print("=" * 80)
    print("PIPELINE RUN COMPARISON")
    print("=" * 80)

    print(f"\nReference: {reference_file}")
    print(f"Current:   {current_file}")

    ref_metrics = extract_metrics(reference_file)
    cur_metrics = extract_metrics(current_file)

    print("\n" + "-" * 80)
    print("EXECUTION SUMMARY")
    print("-" * 80)

    print(f"\nSuccess Rate:")
    print(f"  Reference: {ref_metrics['success_count']}/{ref_metrics['total_scripts']}")
    print(f"  Current:   {cur_metrics['success_count']}/{cur_metrics['total_scripts']}")

    if ref_metrics['success_count'] == cur_metrics['success_count']:
        print(f"  ✅ Both runs: {cur_metrics['success_count']}/{cur_metrics['total_scripts']} scripts succeeded")
    else:
        print(f"  ⚠️  Success count differs!")

    print(f"\nTotal Duration:")
    print(f"  Reference: {ref_metrics['total_duration']:.1f}s")
    print(f"  Current:   {cur_metrics['total_duration']:.1f}s")
    duration_diff = cur_metrics['total_duration'] - ref_metrics['total_duration']
    duration_pct = (duration_diff / ref_metrics['total_duration']) * 100
    print(f"  Δ: {duration_diff:+.1f}s ({duration_pct:+.1f}%)")

    print("\n" + "-" * 80)
    print("SCRIPT-BY-SCRIPT COMPARISON")
    print("-" * 80)

    all_scripts = set(ref_metrics['scripts'].keys()) | set(cur_metrics['scripts'].keys())

    print(f"\n{'Script':<50} {'Ref (s)':<10} {'Cur (s)':<10} {'Δ (s)':<10} {'Status'}")
    print("-" * 100)

    for script in sorted(all_scripts):
        ref_data = ref_metrics['scripts'].get(script, {})
        cur_data = cur_metrics['scripts'].get(script, {})

        ref_dur = ref_data.get('duration', 0)
        cur_dur = cur_data.get('duration', 0)
        diff = cur_dur - ref_dur

        ref_status = ref_data.get('status', '❌')
        cur_status = cur_data.get('status', '❌')

        status_match = "✅" if ref_status == cur_status == "✅" else "⚠️"

        print(f"{script:<50} {ref_dur:>8.1f}  {cur_dur:>8.1f}  {diff:>+8.1f}  {status_match}")

    print("\n" + "=" * 80)
    print("VALIDATION RESULT")
    print("=" * 80)

    all_passed = (
        ref_metrics['success_count'] == cur_metrics['success_count'] and
        ref_metrics['success_count'] == ref_metrics['total_scripts'] and
        all(cur_metrics['scripts'].get(s, {}).get('status') == '✅' for s in ref_metrics['scripts'])
    )

    if all_passed:
        print("\n✅ VALIDATION PASSED")
        print("   - All scripts executed successfully")
        print("   - Success rate matches reference")
        print("   - No regressions detected")
    else:
        print("\n⚠️  VALIDATION WARNINGS")
        if ref_metrics['success_count'] != cur_metrics['success_count']:
            print("   - Success count differs from reference")
        failed_scripts = [s for s, d in cur_metrics['scripts'].items() if d.get('status') != '✅']
        if failed_scripts:
            print(f"   - Failed scripts: {', '.join(failed_scripts)}")

    print("=" * 80)

    return all_passed

if __name__ == '__main__':
    reference = Path('outputs/pipeline_raw-2025-11-27_02-12-50.md')
    current = Path('outputs/pipeline_raw-2025-11-27_13-02-22.md')

    if not reference.exists():
        print(f"❌ Reference file not found: {reference}")
        exit(1)

    if not current.exists():
        print(f"❌ Current file not found: {current}")
        exit(1)

    success = compare_runs(reference, current)
    exit(0 if success else 1)
