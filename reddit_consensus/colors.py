"""Clean, elegant console UI for Reddit Consensus Agent"""

import json
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import (
    DEFAULT_UI_COMMENT_PREVIEW_LENGTH,
    DEFAULT_UI_TITLE_PREVIEW_LENGTH,
    DEFAULT_UI_TREE_DISPLAY_DEPTH,
)

# Global console instance
console = Console()

# Elegant color theme
THEME = {
    "primary": "cyan",
    "accent": "yellow",
    "success": "green",
    "header": "blue",
    "neutral": "white",
    "muted": "dim white",
}

# Tool display names
TOOL_NAMES = {
    "reddit_search_for_posts": "Search Reddit Posts",
    "reddit_get_post_comments": "Fetch Comments",
}


def get_tool_name(tool_name: str) -> str:
    """Get clean display name for tool"""
    return TOOL_NAMES.get(tool_name, tool_name)


def get_friendly_tool_name(tool_name: str) -> str:
    """Get friendly display name for tool - alias for backward compatibility"""
    return get_tool_name(tool_name)


def _format_time_ago(created_utc: float) -> str:
    """Format timestamp as human-readable time ago"""
    try:
        created_time = datetime.fromtimestamp(created_utc)
        now = datetime.now()
        diff = now - created_time

        if diff.days > 365:
            years = diff.days // 365
            return f"{years}y ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months}mo ago"
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        else:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
    except Exception:
        return "unknown"


def create_header(title: str, subtitle: str = "") -> Panel:
    """Create clean header panel"""
    content = title
    if subtitle:
        content += f"\n{subtitle}"
    return Panel(content, style=f"bold {THEME['header']}", padding=(0, 1))


def create_tool_table(tool_results: list[dict[str, Any]]) -> Table:
    """Create compact tool execution table"""
    table = Table(
        title="Tool Execution",
        style=THEME["primary"],
        show_header=True,
        header_style="bold",
    )
    table.add_column("Tool", style="bold", min_width=12, max_width=20)
    table.add_column("Status", justify="center", min_width=6, max_width=8)
    table.add_column("Details", min_width=10, max_width=25)

    for result in tool_results:
        tool_name = get_tool_name(result.get("tool_name", "Unknown"))
        status = f"[{THEME['success']}]✓ Done[/{THEME['success']}]"
        details = _extract_details(result)
        table.add_row(tool_name, status, details)

    return table


def _extract_details(result: dict[str, Any]) -> str:
    """Extract concise details from tool result"""
    tool_name = result.get("tool_name")
    result_data = result.get("result", "")

    if not result_data:
        return "Completed"

    try:
        data = json.loads(result_data)

        if tool_name == "reddit_search_for_posts" and "results" in data:
            posts = data["results"]
            subreddits = set()
            for post in posts:
                url = post.get("url", "")
                if "/r/" in url:
                    sub = url.split("/r/")[1].split("/")[0]
                    subreddits.add(sub)
            return f"{len(posts)} posts\n{len(subreddits)} subs"

        elif tool_name == "reddit_get_post_comments":
            if "comments" in data:
                comments = data["comments"]
                title = data.get("post_title", "")[:15] + "..."
                return f'{len(comments)} comments\nfrom "{title}"'
            elif "comment_tree" in data:
                comment_tree = data["comment_tree"]
                title = data.get("post_title", "")[:15] + "..."
                total_replies = sum(_count_replies(comment) for comment in comment_tree)
                return f'{len(comment_tree)} comments\n+{total_replies} replies\nfrom "{title}"'

        return "Completed"
    except Exception:
        return "Completed"


def _count_replies(comment: dict[str, Any]) -> int:
    """Count total replies in a comment tree"""
    count = len(comment.get("replies", []))
    for reply in comment.get("replies", []):
        count += _count_replies(reply)
    return count


def _format_comment_tree(
    comment: dict[str, Any], max_display_depth: int = DEFAULT_UI_TREE_DISPLAY_DEPTH
) -> list[str]:
    """Format a comment tree with proper indentation"""
    lines = []

    def format_comment_recursive(comment_data: dict[str, Any], depth: int = 0):
        # Create indentation based on depth
        indent = "  " * depth
        tree_prefix = ""

        if depth > 0:
            tree_prefix = "├─ " if depth == 1 else "└─ "

        # Format comment text
        text = comment_data.get("text", "").replace("\n", " ").strip()
        if len(text) > DEFAULT_UI_COMMENT_PREVIEW_LENGTH:
            text = text[: DEFAULT_UI_COMMENT_PREVIEW_LENGTH - 3] + "..."

        author = comment_data.get("author", "unknown")
        score = comment_data.get("score", 0)
        reply_count = comment_data.get("reply_count", 0)

        # Add timestamp if available
        time_info = ""
        if comment_data.get("created_utc"):
            time_ago = _format_time_ago(comment_data["created_utc"])
            time_info = f" {time_ago}"

        # Build comment line
        comment_line = f'{indent}{tree_prefix}"{text}" - {author} (↑{score}){time_info}'
        if reply_count > 0 and depth < max_display_depth:
            comment_line += f" [{reply_count} replies]"
        elif reply_count > 0:
            comment_line += f" [+{reply_count} more]"

        lines.append(comment_line)

        # Add replies if within display depth
        if depth < max_display_depth:
            for reply in comment_data.get("replies", []):
                format_comment_recursive(reply, depth + 1)

    format_comment_recursive(comment)
    return lines


def create_result_panels(tool_results: list[dict[str, Any]]) -> list[Panel]:
    """Create result panels for tool outputs"""
    panels = []

    for result in tool_results:
        tool_name = result.get("tool_name")
        result_data = result.get("result", "")

        if tool_name == "reddit_search_for_posts" and result_data:
            panel = _create_search_panel(result_data)
            if panel:
                panels.append(panel)

        elif tool_name == "reddit_get_post_comments" and result_data:
            # Try hierarchical first, then fall back to flat
            panel = _create_hierarchical_comments_panel(result_data)
            if not panel:
                panel = _create_comments_panel(result_data)
            if panel:
                panels.append(panel)

    return panels


def _create_search_panel(result_json: str) -> Panel | None:
    """Create search results panel"""
    try:
        data = json.loads(result_json)
        if not data.get("results"):
            return None

        query = data.get("query", "search")
        results = data["results"]

        # Extract subreddits
        subreddits = set()
        for post in results:
            url = post.get("url", "")
            if "/r/" in url:
                sub = url.split("/r/")[1].split("/")[0]
                subreddits.add(sub)

        # Build content
        lines = [f"Found {len(results)} posts across {len(subreddits)} subreddits", ""]
        lines.append("Top Results:")

        for post in results[:3]:
            title = post.get("title", "No title")
            if len(title) > DEFAULT_UI_TITLE_PREVIEW_LENGTH:
                title = title[: DEFAULT_UI_TITLE_PREVIEW_LENGTH - 3] + "..."
            score = post.get("score", 0)
            author = post.get("author", "unknown")

            # Add timestamp if available
            time_info = ""
            if post.get("created_utc"):
                time_ago = _format_time_ago(post["created_utc"])
                time_info = f" ({time_ago})"

            lines.append(f'• "{title}" - {author} (↑{score}){time_info}')

        content = "\n".join(lines)
        return Panel(content, title=f'Reddit Search: "{query}"', style=THEME["primary"])

    except Exception:
        return None


def _create_hierarchical_comments_panel(result_json: str) -> Panel | None:
    """Create hierarchical comments panel with tree structure"""
    try:
        data = json.loads(result_json)
        if not data.get("comment_tree"):
            return None

        post_title = data.get("post_title", "Unknown Post")
        if len(post_title) > DEFAULT_UI_TITLE_PREVIEW_LENGTH - 5:
            post_title = post_title[: DEFAULT_UI_TITLE_PREVIEW_LENGTH - 8] + "..."

        comment_tree = data["comment_tree"]
        max_depth = data.get("max_depth", 3)
        total_comments = len(comment_tree)

        # Count total replies
        total_replies = sum(_count_replies(comment) for comment in comment_tree)

        # Add post timing info
        post_info = ""
        if data.get("post_created_utc"):
            post_time_ago = _format_time_ago(data["post_created_utc"])
            post_author = data.get("post_author", "unknown")
            post_info = f" by {post_author} ({post_time_ago})"

        # Build content
        lines = [
            f"{total_comments} comments with {total_replies} replies (depth: {max_depth})",
            "",
        ]
        if post_info:
            lines.append(f"Post{post_info}")
            lines.append("")
        lines.append("Comment Tree:")

        # Format each top-level comment and its replies
        for comment in comment_tree[:3]:  # Show first 3 comment trees
            comment_lines = _format_comment_tree(comment)
            lines.extend(comment_lines)
            lines.append("")  # Add spacing between comment trees

        if len(comment_tree) > 3:
            lines.append(f"... and {len(comment_tree) - 3} more comment threads")

        content = "\n".join(lines)
        return Panel(
            content, title=f'Comment Tree: "{post_title}"', style=THEME["accent"]
        )

    except Exception:
        return None


def _create_comments_panel(result_json: str) -> Panel | None:
    """Create comments panel"""
    try:
        data = json.loads(result_json)
        if not data.get("comments"):
            return None

        post_title = data.get("post_title", "Unknown Post")
        if len(post_title) > DEFAULT_UI_TITLE_PREVIEW_LENGTH - 5:
            post_title = post_title[: DEFAULT_UI_TITLE_PREVIEW_LENGTH - 8] + "..."

        comments = data["comments"]

        # Add post timing info
        post_info = ""
        if data.get("post_created_utc"):
            post_time_ago = _format_time_ago(data["post_created_utc"])
            post_author = data.get("post_author", "unknown")
            post_info = f" by {post_author} ({post_time_ago})"

        # Build content
        lines = [f"{len(comments)} top comments from Reddit discussion", ""]
        if post_info:
            lines.append(f"Post{post_info}")
            lines.append("")
        lines.append("Top Comments:")

        for comment in comments[:3]:
            text = comment.get("text", "").replace("\n", " ").strip()
            if len(text) > DEFAULT_UI_COMMENT_PREVIEW_LENGTH - 15:
                text = text[: DEFAULT_UI_COMMENT_PREVIEW_LENGTH - 18] + "..."
            score = comment.get("score", 0)
            author = comment.get("author", "unknown")

            # Add timestamp if available
            time_info = ""
            if comment.get("created_utc"):
                time_ago = _format_time_ago(comment["created_utc"])
                time_info = f" ({time_ago})"

            lines.append(f'• "{text}" - {author} (↑{score}){time_info}')

        content = "\n".join(lines)
        return Panel(content, title=f'Comments: "{post_title}"', style=THEME["accent"])

    except Exception:
        return None


def render_dashboard(tool_results: list[dict[str, Any]]) -> None:
    """Render elegant dashboard with tool results"""
    if not tool_results:
        return

    # Create panels
    tool_table = create_tool_table(tool_results)
    result_panels = create_result_panels(tool_results)

    # Display tool table
    console.print(tool_table)

    # Display result panels
    for panel in result_panels:
        console.print(panel)


def print_colored(label: str, message: str, color: str = None) -> None:
    """Print colored message with label"""
    if color is None:
        color = THEME.get(label.lower(), THEME["neutral"])
    console.print(f"[{color}][{label}][/{color}] {message}")


def print_phase_header(title: str, subtitle: str = "") -> None:
    """Print phase header with elegant formatting"""
    header = create_header(title, subtitle)
    console.print(header)


def print_additional_notes(additional_notes: str) -> None:
    """Print additional notes section elegantly"""
    if not additional_notes or not additional_notes.strip():
        return

    console.print()  # Add spacing

    # Create panel for additional notes
    panel = Panel(
        additional_notes.strip(),
        title="Additional Notes",
        style=THEME["muted"],
        border_style="dim",
    )
    console.print(panel)


def print_recommendations_table(recommendations: list[dict[str, Any]]) -> None:
    """Print recommendations in table format - alias for backward compatibility"""
    print_recommendations(recommendations)


def print_recommendations(recommendations: list[dict[str, Any]]) -> None:
    """Print final recommendations elegantly"""
    if not recommendations:
        return

    for i, rec in enumerate(recommendations, 1):
        title = f"{i}. {rec.get('name', 'Recommendation')}"

        lines = []
        if rec.get("description"):
            lines.append(rec["description"])

        if rec.get("pros"):
            lines.append(
                f"\n[{THEME['success']}]✓ Pros:[/{THEME['success']}] {rec['pros']}"
            )

        if rec.get("cons"):
            lines.append(
                f"[{THEME['accent']}]! Cons:[/{THEME['accent']}] {rec['cons']}"
            )

        if rec.get("reasoning"):
            lines.append(
                f"\n[{THEME['neutral']}]• Reasoning:[/{THEME['neutral']}] {rec['reasoning']}"
            )

        if rec.get("reddit_sources"):
            sources = ", ".join(rec["reddit_sources"])
            lines.append(
                f"\n[{THEME['primary']}]• Sources:[/{THEME['primary']}] {sources}"
            )

        content = "\n".join(lines)
        panel = Panel(content, title=title, style=THEME["neutral"])
        console.print(panel)


def print_tools_with_results(
    tool_results: list[dict[str, Any]], title: str = ""
) -> None:
    """Legacy function - use render_dashboard instead"""
    render_dashboard(tool_results)


# Unused legacy functions - keeping for compatibility
def print_tool_table(tool_results: list, title: str = "Tool Execution") -> None:
    console.print(create_tool_table(tool_results))


def print_post_search_results(result_json: str) -> None:
    panel = _create_search_panel(result_json)
    if panel:
        console.print(panel)


def print_comment_search_results(result_json: str) -> None:
    panel = _create_comments_panel(result_json)
    if panel:
        console.print(panel)
