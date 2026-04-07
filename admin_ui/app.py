import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="QueryMind Admin", page_icon="🧠", layout="wide")
st.title("🧠 QueryMind — Admin Panel")

# ── Session state ─────────────────────────────────────────────────────
if "token" not in st.session_state:
    st.session_state.token = None

# ── Login ─────────────────────────────────────────────────────────────
def login(username, password):
    r = requests.post(
        f"{API_URL}/admin/token",
        data={"username": username, "password": password},
    )
    if r.status_code == 200:
        st.session_state.token = r.json()["access_token"]
        return True
    return False

def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

if not st.session_state.token:
    st.subheader("Login")
    with st.form("login_form"):
        username = st.text_input("Username", value="admin")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if login(username, password):
                st.success("Logged in!")
                st.rerun()
            else:
                st.error("Invalid credentials")
    st.stop()

# ── Sidebar nav ───────────────────────────────────────────────────────
page = st.sidebar.radio(
    "Navigation",
    ["LLM Configuration", "Database Configuration", "Upload Files", "Test Chat"],
)
if st.sidebar.button("Logout"):
    st.session_state.token = None
    st.rerun()

# ══════════════════════════════════════════════════════════════════════
# PAGE 1: LLM Configuration
# ══════════════════════════════════════════════════════════════════════
if page == "LLM Configuration":
    st.header("LLM Provider Configuration")
    st.info("Choose between a local Ollama model (free, private) or a cloud API key.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Local — Ollama phi3-mini")
        st.write("Runs entirely on your machine. No data sent externally.")
        if st.button("Use Ollama (phi3-mini)", use_container_width=True, type="primary"):
            r = requests.post(
                f"{API_URL}/admin/llm-config",
                json={"provider": "ollama"},
                headers=auth_headers(),
            )
            if r.status_code == 200:
                st.success("Switched to Ollama phi3-mini")
            else:
                st.error(r.text)

    with col2:
        st.subheader("Cloud — API Key")
        provider = st.selectbox("Provider", ["openai", "anthropic"])
        api_key = st.text_input("API Key", type="password")
        model_map = {
            "openai": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
            "anthropic": ["claude-3-haiku-20240307", "claude-3-5-sonnet-20241022"],
        }
        model = st.selectbox("Model", model_map[provider])
        if st.button("Save Cloud Config", use_container_width=True):
            if not api_key:
                st.error("API key is required")
            else:
                r = requests.post(
                    f"{API_URL}/admin/llm-config",
                    json={"provider": provider, "api_key": api_key, "model": model},
                    headers=auth_headers(),
                )
                if r.status_code == 200:
                    st.success(f"Switched to {provider} / {model}")
                else:
                    st.error(r.text)

    st.divider()
    st.subheader("Current config")
    r = requests.get(f"{API_URL}/admin/llm-config", headers=auth_headers())
    if r.status_code == 200:
        st.json(r.json())

# ══════════════════════════════════════════════════════════════════════
# PAGE 2: Database Configuration
# ══════════════════════════════════════════════════════════════════════
elif page == "Database Configuration":
    st.header("SQL Database Configuration")
    st.write("Connect your database. The chatbot will query it directly using Metadata RAG for high accuracy.")

    with st.form("db_form"):
        db_type = st.selectbox("Database type", ["mysql", "postgresql", "sqlite"])
        col1, col2 = st.columns(2)
        with col1:
            host = st.text_input("Host", value="localhost")
            database = st.text_input("Database name")
            username = st.text_input("Username")
        with col2:
            port = st.number_input("Port", value=3306 if db_type == "mysql" else 5432, step=1)
            password = st.text_input("Password", type="password")
            fetch_schema = st.checkbox("Auto-fetch & Index Schema (Recommended)", value=True)

        st.info("💡 Indexing the schema allows the AI to 'know' your tables and columns before generating SQL.")
        submitted = st.form_submit_button("Connect & Sync Metadata", type="primary")

    if submitted:
        payload = {
            "host": host, "port": port, "database": database,
            "username": username, "password": password, "db_type": db_type,
        }
        with st.spinner("Connecting and Indexing Metadata..."):
            r = requests.post(
                f"{API_URL}/admin/db-config?fetch_schema={str(fetch_schema).lower()}",
                json=payload,
                headers=auth_headers(),
            )
        if r.status_code == 200:
            data = r.json()
            st.success(data["message"])
            st.write(f"**Indexed Tables:** {', '.join(data.get('tables', []))}")
        else:
            st.error(f"Failed: {r.json().get('detail', r.text)}")

    st.divider()
    st.subheader("Current connection")
    r = requests.get(f"{API_URL}/admin/db-config", headers=auth_headers())
    if r.status_code == 200:
        cfg = r.json()
        if cfg.get("configured"):
            st.success(f"Connected to `{cfg.get('database')}` on `{cfg.get('host')}`")
        else:
            st.warning("No database configured yet")

# ══════════════════════════════════════════════════════════════════════
# PAGE 3: Upload Files
# ══════════════════════════════════════════════════════════════════════
elif page == "Upload Files":
    st.header("Upload Context Files")
    st.write("Upload files that the chatbot should know about. Re-uploading replaces the old version.")

    file_type = st.selectbox(
        "File type",
        ["document", "data_dict", "schema"],
        help="data_dict = data dictionary, schema = DB schema docs, document = general context",
    )

    uploaded = st.file_uploader(
        "Choose file",
        type=["pdf", "docx", "txt", "csv"],
        help="Supported: PDF, Word, plain text, CSV",
    )

    if uploaded and st.button("Upload & Embed", type="primary"):
        with st.spinner(f"Processing {uploaded.name}..."):
            r = requests.post(
                f"{API_URL}/admin/upload",
                files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                data={"file_type": file_type, "tenant_id": "default"},
                headers=auth_headers(),
            )
        if r.status_code == 200:
            result = r.json()
            if result.get("status") == "done":
                st.success(f"Indexed {result['chunks']} chunks from {uploaded.name}")
            else:
                st.error(f"Error: {result.get('message')}")
        else:
            st.error(r.text)

# ══════════════════════════════════════════════════════════════════════
# PAGE 4: Test Chat
# ══════════════════════════════════════════════════════════════════════
elif page == "Test Chat":
    st.header("Test Chat Interface")
    st.info("Test the chatbot directly here before embedding it in your app.")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("sql"):
                with st.expander("View Generated SQL"):
                    st.code(msg["sql"], language="sql")
            if msg.get("data"):
                import pandas as pd
                df = pd.DataFrame(msg["data"])
                st.dataframe(df, use_container_width=True)
                # Show simple chart if data is numeric
                if len(df.columns) >= 2 and any(pd.api.types.is_numeric_dtype(df[c]) for c in df.columns):
                    st.caption("Auto-generated Chart Visualization")
                    st.bar_chart(df, x=df.columns[0], y=df.columns[1])
            if msg.get("source"):
                st.caption(f"Source: {msg['source']}")

    if prompt := st.chat_input("Ask anything about your data..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                r = requests.post(
                    f"{API_URL}/chat",
                    json={"message": prompt, "session_id": st.session_state.session_id},
                )
            if r.status_code == 200:
                data = r.json()
                st.write(data["answer"])
                
                # Render SQL and Data if present
                if data.get("sql"):
                    with st.expander("View Generated SQL"):
                        st.code(data["sql"], language="sql")
                if data.get("data"):
                    import pandas as pd
                    df = pd.DataFrame(data["data"])
                    st.dataframe(df, use_container_width=True)
                    if len(df.columns) >= 2 and any(pd.api.types.is_numeric_dtype(df[c]) for c in df.columns):
                        st.bar_chart(df, x=df.columns[0], y=df.columns[1])

                st.caption(f"Source: {data['source']}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": data["answer"],
                    "sql": data.get("sql"),
                    "data": data.get("data"),
                    "source": data["source"],
                })
            else:
                st.error(f"Error: {r.text}")

    if st.button("Clear conversation"):
        st.session_state.messages = []
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()
