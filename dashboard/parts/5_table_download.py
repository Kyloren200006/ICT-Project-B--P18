"""Scrollable log table and CSV download component for the dashboard."""

import pandas as pd
import streamlit as st


def render_table_download(data: pd.DataFrame) -> None:
    """Display all log data and provide a CSV download button."""
    st.subheader("📋 Log Data")

    if data is None or data.empty:
        st.info("Upload a valid CSV file to view and download the log data.")
        return

    st.caption(f"Showing {len(data):,} uploaded logs")

    st.dataframe(
        data,
        width="stretch",
        height=450,
        hide_index=True,
    )

    csv_data = data.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇️ Download results as CSV",
        data=csv_data,
        file_name="trust_evaluation_results.csv",
        mime="text/csv",
        type="primary",
        width="stretch",
    )