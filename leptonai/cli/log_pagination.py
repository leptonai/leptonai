"""Keep timestamp-only log pagination from skipping a partial timestamp group."""

from typing import Optional, Sequence, Tuple

import click


MAX_LOG_PAGE_LIMIT = 10_000


def complete_log_page(
    timestamps: Sequence[Optional[int]], request_limit: int
) -> Tuple[int, int]:
    """Return the safe output prefix length and the next request's page size.

    Timestamps must be sorted in retrieval order (ascending or descending).
    A full page may truncate its final timestamp group: leave that whole group
    unprinted and query it again inclusively. This preserves repeated identical
    lines without needing to deduplicate records that were already printed.
    If the entire page shares a timestamp, enlarge the query until it can make
    progress, or fail at the API limit rather than silently skip unseen rows.
    """
    if any(timestamp is None for timestamp in timestamps):
        raise click.ClickException("Cannot paginate log entries without timestamps.")
    if len(timestamps) < request_limit:
        return len(timestamps), request_limit

    boundary = timestamps[-1]
    complete = len(timestamps)
    while complete and timestamps[complete - 1] == boundary:
        complete -= 1
    if complete:
        return complete, request_limit
    if request_limit >= MAX_LOG_PAGE_LIMIT:
        raise click.ClickException(
            f"Log page is full at timestamp {boundary}; cannot paginate this "
            "timestamp completely. Narrow the query with workload, replica, node, "
            "or text filters."
        )
    return 0, min(request_limit * 2, MAX_LOG_PAGE_LIMIT)
