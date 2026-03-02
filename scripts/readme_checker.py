#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-language README quality checker.
Checks version sync, link validity, and structural consistency.
"""

import json
import os
import re

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class READMEQualityChecker:
    def __init__(self):
        self.readme_files = ['README.md', 'README-zh.md', 'README-ja.md']
        self.results = {
            'structure_consistency': [],
            'link_validation': [],
            'translation_sync': [],
            'overall_score': 0
        }

    def check_structure_consistency(self):
        """Check structural consistency across README files."""
        print("Checking structure consistency...")

        structures = {}
        for file in self.readme_files:
            if os.path.exists(file):
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
                    structures[file] = len(headers)

        line_counts = [structures.get(f, 0) for f in self.readme_files if f in structures]
        if line_counts:
            max_diff = max(line_counts) - min(line_counts)
            consistency_score = max(0, 100 - (max_diff * 5))

            self.results['structure_consistency'] = {
                'score': consistency_score,
                'details': structures,
                'status': 'PASS' if consistency_score >= 90 else 'WARN'
            }

            print(f"  Structure consistency: {consistency_score}/100")
            for file, count in structures.items():
                print(f"    {file}: {count} headers")

    def check_link_validation(self):
        """Check link validity across README files."""
        print("Checking link validity...")

        all_links = {}
        broken_links = []

        for file in self.readme_files:
            if os.path.exists(file):
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()

                links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
                all_links[file] = []

                for text, url in links:
                    link_info = {'text': text, 'url': url, 'status': 'unknown'}

                    if not url.startswith(('http://', 'https://', '#')):
                        if os.path.exists(url):
                            link_info['status'] = 'valid'
                        else:
                            link_info['status'] = 'broken'
                            broken_links.append(f"{file}: {url}")
                    elif url.startswith(('http://', 'https://')) and HAS_REQUESTS:
                        # Only check key domains to avoid excessive requests
                        if any(domain in url for domain in ['github.com', 'pypi.org', 'npmjs.com']):
                            try:
                                response = requests.head(url, timeout=10, allow_redirects=True)
                                link_info['status'] = 'valid' if response.status_code < 400 else 'broken'
                            except requests.RequestException:
                                link_info['status'] = 'error'
                        else:
                            link_info['status'] = 'skipped'
                    else:
                        link_info['status'] = 'anchor'

                    all_links[file].append(link_info)

        total_links = sum(len(links) for links in all_links.values())
        broken_count = len(broken_links)
        link_score = max(0, 100 - (broken_count * 10)) if total_links > 0 else 100

        self.results['link_validation'] = {
            'score': link_score,
            'total_links': total_links,
            'broken_links': broken_count,
            'broken_list': broken_links[:10],
            'status': 'PASS' if link_score >= 80 else 'FAIL'
        }

        print(f"  Link validity: {link_score}/100")
        print(f"    Total links: {total_links}")
        print(f"    Broken links: {broken_count}")

    def check_translation_sync(self):
        """Check translation synchronization across README files."""
        print("Checking translation sync...")

        if not all(os.path.exists(f) for f in self.readme_files):
            missing = [f for f in self.readme_files if not os.path.exists(f)]
            print(f"  Warning: missing README files: {missing}")
            self.results['translation_sync'] = {
                'score': 60,
                'status': 'WARN',
                'message': f'Missing files: {missing}'
            }
            return

        mod_times = {}
        for file in self.readme_files:
            mod_times[file] = os.path.getmtime(file)

        times = list(mod_times.values())
        time_diff = max(times) - min(times)

        # Score based on time difference (within 7 days = synchronized)
        sync_score = max(0, 100 - (time_diff / (7 * 24 * 3600) * 20))

        self.results['translation_sync'] = {
            'score': int(sync_score),
            'time_diff_days': round(time_diff / (24 * 3600), 2),
            'status': 'PASS' if sync_score >= 80 else 'WARN',
            'mod_times': {f: f"{os.path.getmtime(f):.0f}" for f in self.readme_files}
        }

        print(f"  Translation sync: {int(sync_score)}/100")
        print(f"    Max time diff: {round(time_diff / (24 * 3600), 1)} days")

    def generate_report(self):
        """Generate quality report."""
        print("\nGenerating quality report...")

        scores = [
            self.results['structure_consistency'].get('score', 0),
            self.results['link_validation'].get('score', 0),
            self.results['translation_sync'].get('score', 0)
        ]
        overall_score = sum(scores) // len(scores)
        self.results['overall_score'] = overall_score

        struct = self.results['structure_consistency']
        links = self.results['link_validation']
        trans = self.results['translation_sync']

        summary_lines = [
            "## README Quality Check Report",
            "",
            f"### Overall Score: {overall_score}/100",
            "",
            "| Check | Score | Status | Details |",
            "|-------|-------|--------|---------|",
            f"| Structure Consistency | {struct.get('score', 0)}/100 | {struct.get('status', 'N/A')} | {len(struct.get('details', {}))} files |",
            f"| Link Validity | {links.get('score', 0)}/100 | {links.get('status', 'N/A')} | {links.get('broken_links', 0)} broken links |",
            f"| Translation Sync | {trans.get('score', 0)}/100 | {trans.get('status', 'N/A')} | {trans.get('time_diff_days', 0)} days diff |",
            "",
            "### Details",
            "",
            "**Structure consistency:**",
        ]

        for file, count in struct.get('details', {}).items():
            summary_lines.append(f"- `{file}`: {count} headers")

        if links.get('broken_list'):
            summary_lines.append("")
            summary_lines.append("**Broken links:**")
            for link in links['broken_list']:
                summary_lines.append(f"- {link}")

        summary_lines.append("")
        summary_lines.append("### Recommendation")

        if overall_score >= 90:
            summary_lines.append("Quality is excellent! Keep it up.")
        elif overall_score >= 70:
            summary_lines.append("Quality is good, with room for improvement.")
        else:
            summary_lines.append("Needs improvement! Please review the issues above.")

        summary = "\n".join(summary_lines)

        # Write to GitHub Actions step summary if available
        github_step_summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if github_step_summary:
            with open(github_step_summary, 'w', encoding='utf-8') as f:
                f.write(summary)

        # Save detailed results
        with open('readme-quality-report.json', 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print("Report generated")

        return 0 if overall_score >= 70 else 1

    def run_all_checks(self):
        """Run all quality checks."""
        print("Starting README quality checks...\n")

        self.check_structure_consistency()
        self.check_link_validation()
        self.check_translation_sync()

        exit_code = self.generate_report()

        print(f"\nDone! Overall score: {self.results['overall_score']}/100")
        return exit_code


if __name__ == "__main__":
    checker = READMEQualityChecker()
    exit_code = checker.run_all_checks()
    raise SystemExit(exit_code)
