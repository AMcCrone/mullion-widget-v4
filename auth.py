import streamlit as st

def authenticate_user():
    """Authenticate the user using a password from Streamlit secrets."""
    PASSWORD = st.secrets["password"]
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    def check_password():
        if st.session_state.get("password_input") == PASSWORD:
            st.session_state["authenticated"] = True
        else:
            st.error("Incorrect password.")

    if not st.session_state["authenticated"]:
        st.text_input("Enter Password:", type="password", key="password_input", on_change=check_password)
        st.stop()
