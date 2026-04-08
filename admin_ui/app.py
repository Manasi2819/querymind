import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="QueryMind Admin", page_icon="🧠", layout="wide")

# ── Inject Custom CSS ──────────────────────────────────────────────────
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown('<h1 class="premium-header">🧠 QueryMind — Admin Panel</h1>', unsafe_allow_html=True)

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

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "LLM Configuration", "Database Configuration", "Knowledge Base", "Test Chat"],
)
if st.sidebar.button("Logout"):
    st.session_state.token = None
    st.rerun()

# ══════════════════════════════════════════════════════════════════════
# PAGE 0: Dashboard
# ══════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    st.header("System Overview")
    
    try:
        r = requests.get(f"{API_URL}/admin/stats", headers=auth_headers())
        if r.status_code == 200:
            stats = r.json()
            
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            col1.metric("Indexed Tables", stats.get("tables", 0))
            col2.metric("Knowledge Particles", stats.get("files", 0))
            col3.metric("LLM Provider", stats.get("llm", "N/A"))
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.divider()
            
            # DB Status Card
            st.subheader("Active Connections")
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            if stats.get("db_connected"):
                st.success("Database is connected and synced.")
                if st.button("Disconnect Database", type="secondary"):
                    requests.delete(f"{API_URL}/admin/db-config", headers=auth_headers())
                    st.rerun()
            else:
                st.warning("No database connected. Go to 'Database Configuration' to get started.")
            st.markdown('</div>', unsafe_allow_html=True)

        else:
            st.error("Failed to load dashboard stats")
    except:
        st.error("Could not connect to backend service")

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

    db_type = st.selectbox("Database type", ["mysql", "postgresql", "sqlite"])
    method = st.radio("Connection Method", ["Detailed Fields", "Direct URL"], horizontal=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    with st.form("db_form"):
        
        url = None
        host = "localhost"
        port = 3306
        database = ""
        username = ""
        password = ""
        
        if method == "Direct URL":
            url = st.text_input("Connection URL", placeholder="mysql+pymysql://user:pass@host:port/db")
            st.caption("💡 Supported formats: mysql+pymysql://, postgresql://, sqlite:///")
        else:
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
    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        payload = {
            "url": url,
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
# PAGE 3: Knowledge Base
# ══════════════════════════════════════════════════════════════════════
elif page == "Knowledge Base":
    st.header("Knowledge Management")
    st.write("Manage the documents and metadata that power your chatbot's intelligence.")

    if "upload_success" in st.session_state:
        st.success(st.session_state.upload_success)
        del st.session_state.upload_success

    tab1, tab2 = st.tabs(["Upload New", "Managed Particles"])
    
    with tab1:
        st.subheader("Ingest Data")
        col_a, col_b = st.columns([2, 1])
        
        with col_a:
            file_category = st.radio(
                "Knowledge Category",
                ["document", "knowledge_base"],
                format_func=lambda x: "📖 General Document" if x == "document" else "🧠 DB Knowledge Base (SQL, JSON, MD)",
                help="Knowledge Base files are prioritized for schema-related questions."
            )
            
            allowed = ["pdf", "docx", "txt"] if file_category == "document" else ["sql", "json", "md", "csv"]
            uploaded = st.file_uploader(f"Upload {file_category} files", type=allowed)
            
        with col_b:
            st.info("""**Support:**  
- **Docs:** PDF, Word, TXT  
- **KB:** SQL, JSON, MD, CSV""")
            if uploaded and st.button("Upload & Index", type="primary", use_container_width=True):
                with st.spinner("Processing..."):
                    r = requests.post(
                        f"{API_URL}/admin/upload",
                        files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                        data={"file_type": file_category},
                        headers=auth_headers(),
                    )
                if r.status_code == 200:
                    data = r.json()
                    chunks = data.get("chunks", 0)
                    st.session_state.upload_success = f"✅ Success: File **{uploaded.name}** has been indexed and chunked into {chunks} parts. It is now available in **Managed Particles**."
                    st.rerun()
                else:
                    try:
                        err_detail = r.json().get("detail", r.text)
                    except:
                        err_detail = r.text
                    st.error(f"❌ Indexing Failed: {err_detail}")

    with tab2:
        st.subheader("Your Knowledge Store")
        try:
            r = requests.get(f"{API_URL}/admin/files", headers=auth_headers())
            if r.status_code == 200:
                files = r.json()
                if files:
                    import pandas as pd
                    df = pd.DataFrame(files)
                    df = df[["filename", "file_type", "upload_date", "chunk_count"]]
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    st.divider()
                    to_delete = st.selectbox("Select particle to remove", df["filename"].tolist())
                    if st.button(f"Delete {to_delete}", type="secondary"):
                        requests.delete(f"{API_URL}/admin/files/{to_delete}", headers=auth_headers())
                        st.success("Deleted!")
                        st.rerun()
                else:
                    st.info("No knowledge particles indexed yet.")
        except:
            st.error("Could not fetch file list")

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
