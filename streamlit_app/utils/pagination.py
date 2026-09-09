# utils/pagination.py
"""
Pagination simple et fixe : 10 éléments par page.
"""

import streamlit as st
import pandas as pd

PAGE_SIZE = 10  # Taille fixe


def paginate_list(items: list, key_prefix: str, default_page_size: int = PAGE_SIZE) -> tuple:
    """
    Pagination fixe à 10 éléments par page.
    Returns: (items_page, page_num, total_pages)
    """
    total = len(items)
    if total == 0:
        return [], 1, 1

    page_size = PAGE_SIZE
    page_key = f"page_num_{key_prefix}"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    total_pages = max(1, (total + page_size - 1) // page_size)

    if st.session_state[page_key] > total_pages:
        st.session_state[page_key] = total_pages

    current_page = st.session_state[page_key]

    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:
        if st.button("◀ Précédent", key=f"prev_{key_prefix}", disabled=(current_page <= 1), use_container_width=True):
            st.session_state[page_key] = max(1, current_page - 1)
            st.rerun()

    with col2:
        st.markdown(
            f"<div style='text-align:center;padding-top:0.45rem;color:#374151;font-size:0.85rem;'>"
            f"Page <strong>{current_page}</strong> / {total_pages}"
            f" &nbsp;·&nbsp; "
            f"<span style='color:#6B7280;'>{total} lot(s)</span>"
            f" &nbsp;·&nbsp; "
            f"<span style='color:#9CA3AF;'>10 / page</span>"
            f"</div>",
            unsafe_allow_html=True
        )

    with col3:
        if st.button("Suivant ▶", key=f"next_{key_prefix}", disabled=(current_page >= total_pages), use_container_width=True):
            st.session_state[page_key] = min(total_pages, current_page + 1)
            st.rerun()

    start = (current_page - 1) * page_size
    end = min(start + page_size, total)
    return items[start:end], current_page, total_pages


def render_lots_table_fixed(df: pd.DataFrame, key: str, height: int = 380):
    """Dataframe avec hauteur fixe (scroll interne)."""
    st.dataframe(df, use_container_width=True, hide_index=True, height=height, key=key)