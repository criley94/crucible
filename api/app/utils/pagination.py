"""Shared pagination utilities."""


def paginate_query(query, page, per_page):
    """Apply page-based pagination to a SQLAlchemy query.

    Returns (items, pagination_dict) where pagination_dict contains
    total, page, per_page, and total_pages.
    """
    page = max(1, page)
    per_page = max(1, per_page)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, -(-total // per_page)),  # ceiling division
    }
