import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="European Bank | Churn Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = Path(__file__).parent / "European_Bank P2.csv"

st.markdown(
    """
    <style>
    .main {background-color: #f7f9fc;}
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #e7ebf2;
        padding: 16px 18px;
        border-radius: 12px;
    }
    .page-title {font-size: 2.2rem; font-weight: 750; color: #17365d;}
    .sub-title {color: #5b6575; margin-top: -8px;}
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_data
def load_csv(file_bytes=None):
    if file_bytes is not None:
        from io import BytesIO
        return pd.read_csv(BytesIO(file_bytes))
    return pd.read_csv(DATA_PATH)

def normalize_columns(data):
    data = data.copy()
    expected = [
        "Year", "CustomerId", "Surname", "CreditScore", "Geography", "Gender",
        "Age", "Tenure", "Balance", "NumOfProducts", "HasCrCard",
        "IsActiveMember", "EstimatedSalary", "Exited"
    ]
    missing = [col for col in expected if col not in data.columns]
    if missing:
        raise ValueError("Missing expected columns: " + ", ".join(missing))
    for col in ["CreditScore", "Age", "Tenure", "Balance", "NumOfProducts",
                "HasCrCard", "IsActiveMember", "EstimatedSalary", "Exited"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(subset=["Exited", "Geography", "Age"])
    data["Exited"] = data["Exited"].astype(int)
    data["Activity status"] = data["IsActiveMember"].map({1: "Active", 0: "Inactive"}).fillna("Unknown")
    data["Outcome"] = data["Exited"].map({1: "Exited", 0: "Retained"}).fillna("Unknown")
    return data

st.sidebar.title("📊 Churn Analytics")
st.sidebar.caption("European Bank customer retention")
uploaded = st.sidebar.file_uploader(
    "Use another compatible CSV (optional)",
    type=["csv"],
    help="Upload a CSV with the same columns as the supplied European Bank dataset.",
)

try:
    raw = load_csv(uploaded.getvalue() if uploaded else None)
    df = normalize_columns(raw)
except Exception as exc:
    st.error(f"Could not load the dataset: {exc}")
    st.info("Check that the CSV is in the repository and has the expected column names.")
    st.stop()

st.sidebar.divider()
st.sidebar.subheader("Filter customers")
countries = sorted(df["Geography"].dropna().astype(str).unique().tolist())
selected_countries = st.sidebar.multiselect("Geography", countries, default=countries)
genders = sorted(df["Gender"].dropna().astype(str).unique().tolist())
selected_genders = st.sidebar.multiselect("Gender", genders, default=genders)
min_age = int(df["Age"].min())
max_age = int(df["Age"].max())
age_range = st.sidebar.slider("Age range", min_age, max_age, (min_age, max_age))
activity_options = ["Active", "Inactive", "Unknown"]
selected_activity = st.sidebar.multiselect("Activity status", activity_options, default=activity_options)
outcome_options = ["Retained", "Exited"]
selected_outcomes = st.sidebar.multiselect("Customer outcome", outcome_options, default=outcome_options)

filtered = df[
    df["Geography"].astype(str).isin(selected_countries)
    & df["Gender"].astype(str).isin(selected_genders)
    & df["Age"].between(age_range[0], age_range[1])
    & df["Activity status"].isin(selected_activity)
    & df["Outcome"].isin(selected_outcomes)
].copy()

st.markdown('<div class="page-title">European Bank Customer Churn Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Interactive exploratory data analysis, customer insights, and retention opportunities</div>',
    unsafe_allow_html=True,
)
st.caption("Dataset: supplied European Bank P2 CSV · Filters apply across all tabs · Descriptive analysis, not causal proof")

if filtered.empty:
    st.warning("No customers match the selected filters. Adjust one or more filters in the sidebar.")
    st.stop()

total = len(filtered)
exited = int(filtered["Exited"].sum())
retained = total - exited
exit_rate = exited / total if total else 0
active_df = filtered[filtered["IsActiveMember"] == 1]
inactive_df = filtered[filtered["IsActiveMember"] == 0]
active_rate = active_df["Exited"].mean() if len(active_df) else 0
inactive_rate = inactive_df["Exited"].mean() if len(inactive_df) else 0
avg_age = filtered["Age"].mean()
avg_balance = filtered["Balance"].mean()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Customers in view", f"{total:,}")
k2.metric("Exited customers", f"{exited:,}")
k3.metric("Exit rate", f"{exit_rate:.1%}")
k4.metric("Average age", f"{avg_age:.1f}")
k5.metric("Average balance", f"{avg_balance:,.0f}")

overview, segments, explore, quality = st.tabs(
    ["📌 Overview", "👥 Customer segments", "🔎 Explore the data", "🧹 Data quality"]
)

with overview:
    left, right = st.columns(2)
    with left:
        outcome_counts = filtered["Outcome"].value_counts().rename_axis("Outcome").reset_index(name="Customers")
        fig = px.pie(
            outcome_counts, names="Outcome", values="Customers", hole=0.58,
            title="Customer outcome mix",
            color="Outcome",
            color_discrete_map={"Retained": "#247a69", "Exited": "#d95d5d"},
        )
        fig.update_layout(legend_title_text="", margin=dict(t=60, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        geo = filtered.groupby("Geography", as_index=False).agg(
            Customers=("Exited", "size"), Exit_Rate=("Exited", "mean")
        )
        geo["Exit rate"] = geo["Exit_Rate"] * 100
        fig = px.bar(
            geo, x="Geography", y="Exit rate", text=geo["Exit rate"].map(lambda x: f"{x:.1f}%"),
            title="Exit rate by geography", hover_data=["Customers"],
            labels={"Exit rate": "Exit rate (%)"},
        )
        fig.update_traces(textposition="outside", marker_color="#2f75a5")
        fig.update_layout(yaxis_ticksuffix="%", margin=dict(t=60, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        age_data = filtered.copy()
        bins = [0, 25, 35, 45, 55, 65, 120]
        labels = ["18–25", "26–35", "36–45", "46–55", "56–65", "66+"]
        age_data["Age band"] = pd.cut(age_data["Age"], bins=bins, labels=labels, include_lowest=True)
        age_plot = age_data.groupby("Age band", observed=False, as_index=False).agg(
            Customers=("Exited", "size"), Exit_Rate=("Exited", "mean")
        )
        age_plot["Exit rate (%)"] = age_plot["Exit_Rate"] * 100
        fig = px.bar(age_plot, x="Age band", y="Exit rate (%)", title="Exit rate by age band",
                     hover_data=["Customers"], labels={"Age band": "Age band"})
        fig.update_traces(marker_color="#6d83b5")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        activity_plot = filtered.groupby("Activity status", as_index=False).agg(
            Customers=("Exited", "size"), Exit_Rate=("Exited", "mean")
        )
        activity_plot["Exit rate (%)"] = activity_plot["Exit_Rate"] * 100
        fig = px.bar(activity_plot, x="Activity status", y="Exit rate (%)",
                     title="Exit rate by activity status", hover_data=["Customers"])
        fig.update_traces(marker_color="#e0a24a")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Quick interpretation")
    if len(geo):
        top_geo = geo.sort_values("Exit_Rate", ascending=False).iloc[0]
        st.write(
            f"Within the current filters, **{top_geo['Geography']}** has the highest observed exit rate "
            f"({top_geo['Exit_Rate']:.1%}; {int(top_geo['Customers']):,} customers)."
        )
    if len(active_df) and len(inactive_df):
        st.write(
            f"Inactive customers have an exit rate of **{inactive_rate:.1%}**, compared with "
            f"**{active_rate:.1%}** among active customers. This is an association, not proof that inactivity causes exit."
        )

with segments:
    left, right = st.columns(2)
    with left:
        product_plot = filtered.groupby("NumOfProducts", as_index=False).agg(
            Customers=("Exited", "size"), Exit_Rate=("Exited", "mean")
        )
        product_plot["Exit rate (%)"] = product_plot["Exit_Rate"] * 100
        fig = px.bar(product_plot, x="NumOfProducts", y="Exit rate (%)",
                     title="Exit rate by number of products", hover_data=["Customers"],
                     labels={"NumOfProducts": "Number of products"})
        fig.update_traces(marker_color="#8064a2")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        gender_plot = filtered.groupby("Gender", as_index=False).agg(
            Customers=("Exited", "size"), Exit_Rate=("Exited", "mean")
        )
        gender_plot["Exit rate (%)"] = gender_plot["Exit_Rate"] * 100
        fig = px.bar(gender_plot, x="Gender", y="Exit rate (%)",
                     title="Exit rate by gender", hover_data=["Customers"])
        fig.update_traces(marker_color="#3b9a91")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Segment summary")
    seg_cols = ["Geography", "Gender", "Age", "IsActiveMember", "NumOfProducts", "Balance", "CreditScore", "Exited"]
    segment_data = filtered[seg_cols].copy()
    segment_data["Age band"] = pd.cut(segment_data["Age"], [0,25,35,45,55,65,120],
                                      labels=["18–25","26–35","36–45","46–55","56–65","66+"], include_lowest=True)
    summary = segment_data.groupby(["Geography", "Gender", "Age band"], observed=True).agg(
        Customers=("Exited", "size"),
        Exited=("Exited", "sum"),
        Exit_Rate=("Exited", "mean"),
        Mean_Balance=("Balance", "mean"),
    ).reset_index()
    summary["Exit rate"] = summary["Exit_Rate"].map(lambda x: f"{x:.1%}")
    summary["Mean balance"] = summary["Mean_Balance"].map(lambda x: f"{x:,.2f}")
    st.dataframe(summary[["Geography", "Gender", "Age band", "Customers", "Exited", "Exit rate", "Mean balance"]],
                 use_container_width=True, hide_index=True)
    st.download_button(
        "Download filtered segment summary (CSV)",
        summary.to_csv(index=False).encode("utf-8"),
        file_name="filtered_churn_segment_summary.csv",
        mime="text/csv",
    )
    st.caption("Demographic differences are for auditing and service improvement—not for discriminatory pricing, eligibility, or service restrictions.")

with explore:
    st.subheader("Numeric variable distributions")
    numeric_col = st.selectbox(
        "Choose a variable",
        ["Age", "CreditScore", "Tenure", "Balance", "NumOfProducts", "EstimatedSalary"],
    )
    fig = px.histogram(filtered, x=numeric_col, color="Outcome", barmode="overlay", opacity=0.72,
                       title=f"Distribution of {numeric_col} by customer outcome")
    st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        fig = px.box(filtered, x="Outcome", y="Age", color="Outcome", title="Age by outcome")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.scatter(filtered.sample(min(2500, len(filtered)), random_state=42),
                         x="CreditScore", y="Balance", color="Outcome", hover_data=["Age", "Geography"],
                         title="Credit score vs balance (sampled for display)")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Filtered data preview")
    # Do not display direct identifiers such as customer ID or surname.
    preview_cols = ["Year", "CreditScore", "Geography", "Gender", "Age", "Tenure",
                    "Balance", "NumOfProducts", "HasCrCard", "IsActiveMember",
                    "EstimatedSalary", "Exited"]
    st.dataframe(filtered[preview_cols].head(100), use_container_width=True, hide_index=True)
    st.download_button(
        "Download filtered analysis data (CSV)",
        filtered[preview_cols].to_csv(index=False).encode("utf-8"),
        file_name="filtered_customer_churn_data.csv",
        mime="text/csv",
    )

with quality:
    st.subheader("Dataset profile")
    q1, q2, q3 = st.columns(3)
    q1.metric("Rows loaded", f"{len(raw):,}")
    q2.metric("Columns loaded", f"{raw.shape[1]:,}")
    q3.metric("Missing cells", f"{int(raw.isna().sum().sum()):,}")
    quality_table = pd.DataFrame({
        "Column": raw.columns,
        "Missing values": [int(raw[c].isna().sum()) for c in raw.columns],
        "Unique values": [int(raw[c].nunique(dropna=True)) for c in raw.columns],
        "Data type": [str(raw[c].dtype) for c in raw.columns],
    })
    st.dataframe(quality_table, use_container_width=True, hide_index=True)
    st.write("**Checks and cautions**")
    st.write(f"- Duplicate customer IDs: **{int(raw['CustomerId'].duplicated().sum()) if 'CustomerId' in raw else 'not available'}**")
    if "NumOfProducts" in raw and "Exited" in raw:
        psummary = raw.groupby("NumOfProducts")["Exited"].agg(["count", "mean"]).reset_index()
        psummary["Exit rate"] = psummary["mean"].map(lambda x: f"{x:.1%}")
        st.write("- Product-count outcome rates should be checked against the data dictionary, especially where groups are small.")
        st.dataframe(psummary[["NumOfProducts", "count", "Exit rate"]], hide_index=True, use_container_width=True)
    st.info(
        "This dashboard provides descriptive analytics. The dataset does not establish why customers exited, "
        "and its sample may not represent all European bank customers. Validate data definitions before policy or business decisions."
    )

st.sidebar.divider()
st.sidebar.caption("Built with Streamlit · Use aggregated insights responsibly")
