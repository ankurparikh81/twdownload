"""Terminal UI helpers for twdownload.

Implements clean numbered menu selection for video resolutions and informational output formatting.
"""

import sys
from typing import List, Optional

from twdownload.models import VideoVariant


def prompt_resolution_selection(
    variants: List[VideoVariant],
    auto_best: bool = False,
    auto_worst: bool = False,
    target_resolution: Optional[str] = None,
    stream=sys.stdout,
) -> VideoVariant:
    """Prompts user to select a resolution from a numbered list of VideoVariants.

    Args:
        variants: List of VideoVariants sorted descending by resolution.
        auto_best: If True, automatically selects highest quality without prompting.
        auto_worst: If True, automatically selects lowest quality without prompting.
        target_resolution: Specific requested resolution (e.g. '720p', '1280x720').
        stream: Output stream for printing menu.

    Returns:
        Selected VideoVariant.
    """
    if not variants:
        raise ValueError("Cannot select resolution from empty variants list.")

    # Only 1 option available: return immediately
    if len(variants) == 1:
        stream.write(f"  Only 1 resolution available: {variants[0].resolution_label}. Proceeding.\n")
        stream.flush()
        return variants[0]

    # Automated flag: --best
    if auto_best:
        stream.write(f"  Auto-selected highest resolution: {variants[0].resolution_label}\n")
        stream.flush()
        return variants[0]

    # Automated flag: --worst
    if auto_worst:
        stream.write(f"  Auto-selected lowest resolution: {variants[-1].resolution_label}\n")
        stream.flush()
        return variants[-1]

    # Automated flag: -r / --resolution
    if target_resolution:
        target_norm = target_resolution.strip().lower().rstrip("p")
        for v in variants:
            # Check '720', '720p', '1280x720'
            if (
                target_norm == v.standard_label.lower().rstrip("p")
                or target_norm == v.resolution_label.lower()
                or target_resolution.strip().lower() == v.standard_label.lower()
            ):
                stream.write(f"  Matched requested resolution: {v.resolution_label}\n")
                stream.flush()
                return v

        stream.write(
            f"  Requested resolution '{target_resolution}' not available. Available: "
            f"{', '.join(v.standard_label for v in variants)}.\n"
        )
        stream.flush()

    # Display numbered menu
    stream.write("\nMultiple resolutions available:\n")
    for i, v in enumerate(variants):
        is_highest = (i == 0)
        is_lowest = (i == len(variants) - 1)
        menu_line = v.format_menu_item(is_highest=is_highest, is_lowest=is_lowest)
        stream.write(f"  [{i + 1}] {menu_line}\n")
    stream.flush()

    # Prompt user
    num_options = len(variants)
    prompt_msg = f"Select resolution [1-{num_options}] (default: 1): "

    while True:
        try:
            choice_str = input(prompt_msg).strip()
        except EOFError:
            # Piped EOF: default gracefully to option 1
            stream.write(f"\n  Defaulting to highest quality ({variants[0].resolution_label}).\n")
            stream.flush()
            return variants[0]
        except KeyboardInterrupt:
            stream.write("\n")
            sys.exit(130)

        # Default to 1 on empty Enter
        if not choice_str:
            return variants[0]

        if choice_str.isdigit():
            choice_idx = int(choice_str)
            if 1 <= choice_idx <= num_options:
                return variants[choice_idx - 1]

        stream.write(f"  Invalid choice. Please enter a number between 1 and {num_options}.\n")
        stream.flush()
