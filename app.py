import uuid
from datetime import datetime, timezone

import streamlit as st

from qdrant_store import init_collection, upsert_item, search, get_all, delete_item
from embeddings import embed_text
from extraction_agent import extract_from_transcript
from rag_agent import answer_query

st.set_page_config(page_title="AI Chief of Staff", layout="wide")
init_collection()

st.title("AI Chief of Staff — Meeting Command Center")
st.caption("Decisions and Tasks as distinct entities. Human-verified. Self-correcting memory.")

tab1, tab2, tab3 = st.tabs(["1. Ingest & Extract", "2. Review (HITL)", "3. Ask (RAG Chat)"])

with tab1:
    st.subheader("Paste a meeting transcript")
    meeting_name = st.text_input("Meeting name", value="Standup 21 Jul")
    default_access = st.selectbox("Default access level for items from this meeting", ["general", "leadership"])
    transcript = st.text_area("Transcript", height=250, placeholder="Paste the raw meeting transcript here...")

    if st.button("Extract decisions & tasks", type="primary"):
        if not transcript.strip():
            st.warning("Paste a transcript first.")
        else:
            with st.spinner("Extraction Agent (Lyzr) is reading the transcript..."):
                meeting_id = str(uuid.uuid4())[:8]
                data = extract_from_transcript(transcript, meeting_id)

            st.session_state["pending_meeting_id"] = meeting_id
            st.session_state["pending_meeting_name"] = meeting_name
            st.session_state["pending_access_level"] = default_access
            st.session_state["pending_decisions"] = data.get("decisions", [])
            st.session_state["pending_tasks"] = data.get("tasks", [])

            st.success(
                f"Extracted {len(data.get('decisions', []))} decisions and "
                f"{len(data.get('tasks', []))} tasks. Go to the Review tab."
            )
            if data.get("_raw_error"):
                st.error("Model did not return clean JSON. Raw output below, fix the prompt in Lyzr Studio if this repeats:")
                st.code(data["_raw_error"])

with tab2:
    st.subheader("Human-in-the-loop review")
    st.caption(
        "Approving embeds the item into Qdrant as organizational memory. "
        "Editing an already-committed item below re-embeds it — that's the correction feedback loop."
    )

    decisions = st.session_state.get("pending_decisions", [])
    tasks = st.session_state.get("pending_tasks", [])
    meeting_id = st.session_state.get("pending_meeting_id")
    meeting_name = st.session_state.get("pending_meeting_name")
    default_access = st.session_state.get("pending_access_level", "general")

    if not decisions and not tasks:
        st.info("Nothing pending review. Extract a transcript in tab 1 first.")
    else:
        st.markdown("### Pending decisions")
        for i, d in enumerate(decisions):
            with st.expander(f"Decision {i + 1}: {d.get('content', '')[:70]}"):
                content = st.text_area("Content", value=d.get("content", ""), key=f"dec_content_{i}")
                access = st.selectbox(
                    "Access level", ["general", "leadership"],
                    index=0 if d.get("access_level", default_access) == "general" else 1,
                    key=f"dec_access_{i}",
                )
                if st.button("Approve & commit", key=f"dec_approve_{i}"):
                    vec = embed_text(content)
                    payload = {
                        "type": "decision",
                        "content": content,
                        "meeting_id": meeting_id,
                        "meeting_name": meeting_name,
                        "access_level": access,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "verified": True,
                    }
                    upsert_item(vec, payload)
                    st.success("Committed to organizational memory.")

        st.markdown("### Pending tasks")
        for i, t in enumerate(tasks):
            with st.expander(f"Task {i + 1}: {t.get('description', '')[:70]}"):
                desc = st.text_area("Description", value=t.get("description", ""), key=f"task_desc_{i}")
                owner = st.text_input("Owner", value=t.get("owner", ""), key=f"task_owner_{i}")
                deadline = st.text_input("Deadline", value=t.get("deadline", ""), key=f"task_deadline_{i}")
                access = st.selectbox(
                    "Access level", ["general", "leadership"],
                    index=0 if t.get("access_level", default_access) == "general" else 1,
                    key=f"task_access_{i}",
                )
                if st.button("Approve & commit", key=f"task_approve_{i}"):
                    content = f"Task: {desc}. Owner: {owner}. Deadline: {deadline}."
                    vec = embed_text(content)
                    payload = {
                        "type": "task",
                        "content": content,
                        "description": desc,
                        "owner": owner,
                        "deadline": deadline,
                        "status": "open",
                        "meeting_id": meeting_id,
                        "meeting_name": meeting_name,
                        "access_level": access,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "verified": True,
                    }
                    upsert_item(vec, payload)
                    st.success("Committed to organizational memory.")

    st.markdown("---")
    st.markdown("### Committed items — edit to trigger the correction feedback loop")
    points = get_all()
    if not points:
        st.caption("No committed items yet.")
    for p in points:
        payload = p.payload
        with st.expander(f"[{payload.get('type')}] {payload.get('content', '')[:70]}"):
            new_content = st.text_area("Content", value=payload.get("content", ""), key=f"edit_{p.id}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save correction (re-embed)", key=f"save_{p.id}"):
                    vec = embed_text(new_content)
                    payload["content"] = new_content
                    payload["corrected"] = True
                    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
                    upsert_item(vec, payload, point_id=p.id)
                    st.success("Re-embedded and updated in Qdrant.")
            with col2:
                if st.button("Delete", key=f"del_{p.id}"):
                    delete_item(p.id)
                    st.rerun()

with tab3:
    st.subheader("Ask your organizational memory")
    role = st.selectbox("Your role (demo of RBAC filtering)", ["employee", "leadership"])
    query = st.text_input("Ask a question about past meetings")

    if st.button("Ask", type="primary") and query.strip():
        with st.spinner("Searching Qdrant and asking the RAG Chat Agent..."):
            qvec = embed_text(query)
            access_filter = None if role == "leadership" else "general"
            results = search(qvec, access_level=access_filter, limit=5)
            context = "\n".join(
                f"- ({r.payload.get('meeting_name', 'unknown meeting')}) {r.payload.get('content')}"
                for r in results
            )
            answer = answer_query(query, context) if results else "No relevant organizational memory found for your access level."

        st.markdown("**Answer:**")
        st.write(answer)
        with st.expander("Retrieved context (what RBAC allowed through)"):
            if not results:
                st.caption("Nothing matched, or it was filtered out by your role.")
            for r in results:
                st.write(f"[{r.payload.get('type')}] {r.payload.get('content')}  (score {r.score:.2f})")
