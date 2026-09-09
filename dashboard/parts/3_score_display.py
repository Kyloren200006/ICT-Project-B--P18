import pandas as pd
import streamlit as st


def render_score_display(data: pd.DataFrame) -> None:
    if data is None or data.empty:
        st.info("Upload a valid CSV file to view trust scores.")
        return

    overall_score = data["overall_trust_score"].mean()

    if overall_score >= 0.95:
        trust_level = "Trusted"
    elif overall_score >= 0.80:
        trust_level = "Low Risk"
    elif overall_score >= 0.50:
        trust_level = "Moderate Risk"
    else:
        trust_level = "High Risk"

    st.subheader("Trust Score")

    st.metric(
        label="Overall Trust Score",
        value=f"{overall_score:.3f}"
    )

    if trust_level == "Trusted":
        st.success(trust_level)
    elif trust_level == "Low Risk":
        st.warning(trust_level)
    elif trust_level == "Moderate Risk":
        st.markdown(
            f"""
            <div style="
                background-color: #ff9800;
                color: white;
                padding: 14px;
                border-radius: 8px;
                font-weight: 600;
            ">
                {trust_level}
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.error(trust_level)

    metric_columns = [
    "DM_001_score",
    "PIR_001_score",
    "UAE_001_score",
    "SIL_001_score",
    "MI_001_score",
    "EA_001_score",
    "ETL_001_score"
    ]

    metric_averages = data[metric_columns].mean().reset_index()
    metric_averages.columns = ["Metric", "Average Score"]

    st.subheader("Average Metric Scores")
    st.dataframe(metric_averages, use_container_width=True)
