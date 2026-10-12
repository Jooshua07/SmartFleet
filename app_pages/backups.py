import streamlit as st

from services.backup_service import create_database_backup, list_backups, verify_backup


def _format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / 1024:.1f} KB"


st.subheader("Database Backups")

if st.button("Create backup", icon=":material/backup:", type="primary", width="stretch"):
    try:
        with st.status("Creating backup...", expanded=False) as status:
            backup_path = create_database_backup()
            object_count = verify_backup(backup_path)
            status.update(label="Backup verified", state="complete")
        st.success(f"Backup saved: {backup_path.name}", icon=":material/check_circle:")
        st.caption(f"Verified {object_count} archive lines.")
    except Exception as exc:
        st.error(f"Could not create backup: {exc}", icon=":material/error:")

st.subheader("Recent backups")
backups = list_backups(limit=10)
if not backups:
    st.caption("No backups found yet.")
else:
    for backup in backups:
        with st.container(border=True):
            st.markdown(f"**{backup['name']}**")
            st.caption(f"{backup['modified_at']:%d %b %Y %H:%M} | {_format_size(backup['size_bytes'])}")
            st.download_button(
                "Download",
                data=backup["path"].read_bytes(),
                file_name=backup["name"],
                mime="application/octet-stream",
                icon=":material/download:",
                key=f"download_backup_{backup['name']}",
                width="stretch",
            )
