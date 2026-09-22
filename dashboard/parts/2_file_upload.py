# ============================================
# TASK 2: File Upload + Validation (Suhash)
# ============================================

import pandas as pd
import streamlit as st

# Columns the framework needs to process the logs
REQUIRED_COLUMNS = [
    "timestamp",
    "session_id",
    "log_id",
    "behavior_type",
    "total_actions",
    "unsafe_executions",
]

uploaded = False
df = None

uploaded_file = st.file_uploader(
    "📁 Upload your agent log CSV file",
    type=["csv"],
    help="Only CSV files are accepted. Required columns: "
    + ", ".join(REQUIRED_COLUMNS),
)

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)

    except Exception as error:
        st.error(f"❌ Could not read the file. Please upload a valid CSV file. ({error})")

    else:
        missing_columns = [
            column for column in REQUIRED_COLUMNS if column not in df.columns
        ]

        if missing_columns:
            st.error(
                "❌ The uploaded CSV is missing the following required column(s): "
                + ", ".join(missing_columns)
            )
            st.info(
                "Make sure your file contains all of these columns: "
                + ", ".join(REQUIRED_COLUMNS)
            )
            df = None

        elif df.empty:
            st.error("❌ The uploaded CSV file is empty. Please upload a file with log data.")

        else:
            uploaded = True
            st.success(f"✅ {len(df):,} logs uploaded successfully!")
