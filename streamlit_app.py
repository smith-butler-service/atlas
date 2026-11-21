"""Smith Research — capacity / status dashboard (Streamlit Community Cloud).

Shows the free compute Smith Research has actually landed. No live pool
connection, no real money, no mining. Static status page.
"""

import streamlit as st

st.set_page_config(page_title="Smith Research — Capacity Status", layout="wide")
st.title("Smith Research — Capacity Status")
st.caption("Smith Project · smith.butler.service@gmail.com · Free compute only, $0 spent")

col1, col2, col3 = st.columns(3)
col1.metric("Local capacity", "4 vCPU / 6 GB RAM / 0 GPU")
col2.metric("GitHub Actions", "Unlimited minutes", "Run #1 OK (13 s)")
col3.metric("Free accounts live", "4", "Repo + Databricks + Deepnote + Actions")

st.subheader("Free accounts live")
st.table(
    {
        "Service": [
            "GitHub (atlas repo)",
            "GitHub Actions",
            "Databricks Free Edition",
            "Deepnote Free",
        ],
        "What it gives": [
            "Public repo, 36 files",
            "Hourly smoke-test run",
            "Serverless Spark notebook",
            "Unlimited Basic machines, 2 vCPU / 5 GB",
        ],
        "Status": ["Live", "Run #1 OK", "Notebook ran (13 s)", "Notebook ran (4 s)"],
    }
)

st.subheader("Still blocked / waiting")
st.table(
    {
        "Service": ["Azure Pipelines", "AppVeyor", "CodeSandbox", "FOSSHost", "Streamlit"],
        "Blocker": [
            "Microsoft blocked account creation; form retired; public projects retired",
            "Account blocked — needs AppVeyor support",
            "Cloudflare check will not clear in browser",
            "Site timed out (ERR_TIMED_OUT) — retry owed",
            "Sign-in policy_denied — needs Streamlit support",
        ],
    }
)

st.caption("Mining is never claimed on any CI / notebook / research-cloud service. Free only, no card.")
