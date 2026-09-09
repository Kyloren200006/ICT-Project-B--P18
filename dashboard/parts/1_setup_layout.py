# ============================================
# TASK 1: Setup + Layout (Sandev)
# ============================================

st.set_page_config(
    page_title="Trust Evaluation Dashboard",
    page_icon="🔐",
    layout="wide"
)

# Main header
st.markdown("# 🔐 Trust Evaluation Dashboard")
st.markdown("Upload your agent logs to evaluate trust, privacy, and security risks in real time.")
st.divider()

with st.sidebar:
    st.header("📋 Instructions")
    st.markdown("""
    1. Upload a CSV file  
    2. Framework processes data  
    3. View results  
    """)
    st.divider()
    st.info("📌 Required columns: timestamp, session_id, log_id, behavior_type, total_actions, unsafe_executions")
    st.caption("⚡ Built with Streamlit · ICT Project B P18")
