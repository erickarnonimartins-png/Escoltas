import streamlit as st
from db import get_connection


def _init_state():
    defaults = {
        "auth_ok": False,
        "auth_user": "",
        "auth_nome": "",
        "auth_role": "",
        "auth_user_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def aplicar_estilo():
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] {display: none;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def buscar_usuario_login(usuario: str):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, nome, usuario, senha, perfil, ativo FROM usuarios WHERE LOWER(usuario) = LOWER(?)",
        (usuario.strip(),),
    ).fetchone()
    conn.close()
    return row


def tela_login():
    aplicar_estilo()
    st.title("🔐 Acesso ao Sistema")
    st.caption("Entre com seu usuário e senha")

    with st.form("form_login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar")

        if entrar:
            user = buscar_usuario_login(usuario)
            if not user or str(user["senha"]) != senha or int(user["ativo"] or 0) != 1:
                st.error("Usuário ou senha inválidos.")
            else:
                st.session_state.auth_ok = True
                st.session_state.auth_user = str(user["usuario"])
                st.session_state.auth_nome = str(user["nome"])
                st.session_state.auth_role = str(user["perfil"])
                st.session_state.auth_user_id = user["id"]
                st.rerun()

    st.stop()


def exigir_login():
    _init_state()
    aplicar_estilo()
    if not st.session_state.auth_ok:
        tela_login()


def sair():
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        st.session_state.auth_ok = False
        st.session_state.auth_user = ""
        st.session_state.auth_nome = ""
        st.session_state.auth_role = ""
        st.session_state.auth_user_id = None
        st.rerun()


def usuario_nome():
    _init_state()
    return st.session_state.auth_nome or "Usuário"


def perfil_atual():
    _init_state()
    return st.session_state.auth_role or ""


def is_admin():
    return perfil_atual() == "admin"


def is_operador():
    return perfil_atual() == "operador"


def exigir_admin():
    if not is_admin():
        st.error("Acesso restrito ao administrador.")
        st.stop()


def menu_lateral():
    st.sidebar.title("🚚 Controle de Escoltas")
    st.sidebar.caption(f"{usuario_nome()} • {perfil_atual()}")
    st.sidebar.divider()
    st.sidebar.page_link("app.py", label="Início", icon="🏠")
    st.sidebar.page_link("pages/1_Agentes.py", label="Agentes", icon="👮")
    st.sidebar.page_link("pages/2_Rotas.py", label="Rotas", icon="🛣️")
    st.sidebar.page_link("pages/3_Lancamentos.py", label="Lançamentos", icon="📝")

    if is_admin():
        st.sidebar.page_link("pages/4_Fechamento.py", label="Fechamento", icon="📊")
        st.sidebar.page_link("pages/5_Backup.py", label="Backup", icon="💾")
        st.sidebar.page_link("pages/6_Usuarios.py", label="Usuários", icon="👤")

    st.sidebar.divider()
    sair()