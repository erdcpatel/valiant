"""
Maven pom.xml and build output parsing utilities.
"""
import re
from pathlib import Path
from typing import Optional, Dict, Any, Union


class MavenHelper:
    """Helper methods for Maven POM updates and console build output analytics."""

    @staticmethod
    def get_parent_bom_version(pom_path: Union[str, Path]) -> Optional[str]:
        """Extract the version string inside the <parent> element of a pom.xml."""
        path = Path(pom_path)
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8")
        parent_match = re.search(r"<parent>([\s\S]*?)</parent>", content)
        if not parent_match:
            return None
        parent_block = parent_match.group(1)
        version_match = re.search(r"<version>\s*([^<\s]+)\s*</version>", parent_block)
        return version_match.group(1) if version_match else None

    @staticmethod
    def update_parent_bom_version(pom_path: Union[str, Path], new_version: str) -> bool:
        """
        Update the parent BOM version in pom.xml while strictly preserving formatting,
        indentation, XML namespaces, and comments.
        """
        path = Path(pom_path)
        if not path.exists():
            return False

        content = path.read_text(encoding="utf-8")
        parent_match = re.search(r"(<parent>[\s\S]*?)(<version>)([\s\S]*?)(</version>)([\s\S]*?</parent>)", content)
        if not parent_match:
            return False

        # Replace only the version inside the parent tag
        prefix = parent_match.group(1)
        start_tag = parent_match.group(2)
        end_tag = parent_match.group(4)
        suffix = parent_match.group(5)

        new_parent_block = f"{prefix}{start_tag}{new_version.strip()}{end_tag}{suffix}"
        updated_content = content[:parent_match.start()] + new_parent_block + content[parent_match.end():]
        path.write_text(updated_content, encoding="utf-8")
        return True

    @staticmethod
    def parse_maven_summary(output: str) -> Dict[str, Any]:
        """
        Parse raw Maven build console stdout into structured KPIs
        (status, total_time, tests_run, failures, errors, skipped).
        """
        summary = {
            "status": "UNKNOWN",
            "total_time_seconds": 0.0,
            "tests_run": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "passed": 0
        }

        if "BUILD SUCCESS" in output:
            summary["status"] = "SUCCESS"
        elif "BUILD FAILURE" in output:
            summary["status"] = "FAILURE"

        # Parse Total time: e.g. [INFO] Total time:  12.345 s or 01:23 min
        time_match = re.search(r"Total time:\s+([\d\.]+)\s*s", output)
        if time_match:
            summary["total_time_seconds"] = float(time_match.group(1))
        else:
            min_match = re.search(r"Total time:\s+(\d+):(\d+)\s*min", output)
            if min_match:
                mins = int(min_match.group(1))
                secs = int(min_match.group(2))
                summary["total_time_seconds"] = float(mins * 60 + secs)

        # Parse Surefire/Failsafe test results
        # Pattern: Tests run: 45, Failures: 0, Errors: 0, Skipped: 0
        test_matches = re.findall(
            r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)",
            output
        )

        total_tests = 0
        total_fail = 0
        total_err = 0
        total_skip = 0

        for match in test_matches:
            total_tests += int(match[0])
            total_fail += int(match[1])
            total_err += int(match[2])
            total_skip += int(match[3])

        summary["tests_run"] = total_tests
        summary["failures"] = total_fail
        summary["errors"] = total_err
        summary["skipped"] = total_skip
        summary["passed"] = max(0, total_tests - (total_fail + total_err + total_skip))

        return summary
