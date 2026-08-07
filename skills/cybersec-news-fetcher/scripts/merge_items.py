import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main():
    parser = argparse.ArgumentParser(
        description="Merge RSS-feed and topic-page news items."
    )
    parser.add_argument("--feeds", required=True, help="RSS JSON input")
    parser.add_argument("--topics", required=True, help="Topic-pages JSON input")
    parser.add_argument("--output", required=True, help="Merged JSON output")
    args = parser.parse_args()

    feeds = load_json(args.feeds)
    topics = load_json(args.topics)

    feed_items = feeds.get("items", [])
    topic_items = topics.get("items", [])
    merged_items = feed_items + topic_items

    failed_sources = (
        feeds.get("sources_failed", []) +
        topics.get("sources_failed", [])
    )

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": feeds.get("window_hours"),
        "sources_polled": (
            feeds.get("sources_polled", 0) +
            topics.get("sources_polled", 0)
        ),
        "sources_failed": failed_sources,
        "items_raw": len(merged_items),
        "items_after_time_filter": len(merged_items),
        "items": merged_items,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)

    print(
        f"[merge_items] RSS items: {len(feed_items)} | "
        f"topic-page items: {len(topic_items)} | "
        f"merged: {len(merged_items)}"
    )
    print(f"[merge_items] Wrote: {output_path}")


if __name__ == "__main__":
    main()