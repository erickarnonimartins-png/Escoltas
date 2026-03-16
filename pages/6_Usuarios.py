import streamlit as st
from db import get_connection, init_db
from auth import exigir_login, menu_lateral, exigir_admin

st.set_page_config(page_title="Usuários", page_icon="👤")
init_db()
exigir_login()
menu_lateral()
exigir_admin()
st.title("👤 Usuários do Sistema")


def carregar_usuarios():
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, nome, usuario, senha, perfil, ativo FROM usuarios ORDER BY nome, usuario"
    ).fetchall()
    conn.close()
    return [{
        "id": row["id"],
        "nome": row["nome"],
        "usuario": row["usuario"],
        "senha": row["senha"],
        "perfil": row["perfil"],
        "ativo": row["ativo"],
    } for row in rows]


usuarios = carregar_usuarios()
mapa = {u["id"]: u for u in usuarios}

m1, m2 = st.columns(2)
m1.metric("Total de usuários", len(usuarios))
m2.metric("Ativos", sum(1 for u in usuarios if u["ativo"] == 1))

st.divider()
st.subheader("Novo usuário")
with st.form("form_novo_usuario", clear_on_submit=True):
    nome = st.text_input("Nome")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha")
    perfil = st.selectbox("Perfil", ["admin", "operador"])
    ativo = st.checkbox("Ativo", value=True)
    salvar = st.form_submit_button("Salvar usuário")
    if salvar:
        if not nome.strip() or not usuario.strip() or not senha.strip():
            st.error("Preencha nome, usuário e senha.")
        else:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO usuarios (nome, usuario, senha, perfil, ativo) VALUES (?, ?, ?, ?, ?)",
                    (nome.strip(), usuario.strip().lower(), senha.strip(), perfil, 1 if ativo else 0),
                )
                conn.commit()
                conn.close()
                st.success("Usuário salvo com sucesso.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar usuário: {e}")

st.divider()
st.subheader("Gerenciar usuário")

if usuarios:
    ids = [u["id"] for u in usuarios]
    usuario_id_sel = st.selectbox("Escolha um usuário", options=ids, format_func=lambda uid: f'#{mapa[uid]["id"]} | {mapa[uid]["nome"]} | {mapa[uid]["usuario"]} | {mapa[uid]["perfil"]}')
    usuario_sel = mapa[usuario_id_sel]
    aba1, aba2 = st.tabs(["✏️ Editar", "🗑️ Excluir"])

    with aba1:
        with st.form(f"form_editar_usuario_{usuario_sel['id']}"):
            nome_edit = st.text_input("Nome", value=usuario_sel["nome"])
            usuario_edit = st.text_input("Usuário", value=usuario_sel["usuario"])
            senha_edit = st.text_input("Senha", value=usuario_sel["senha"])
            perfil_edit = st.selectbox("Perfil", ["admin", "operador"], index=0 if usuario_sel["perfil"] == "admin" else 1)
            ativo_edit = st.checkbox("Ativo", value=(usuario_sel["ativo"] == 1))
            salvar_edicao = st.form_submit_button("Salvar alterações")
            if salvar_edicao:
                if not nome_edit.strip() or not usuario_edit.strip() or not senha_edit.strip():
                    st.error("Preencha nome, usuário e senha.")
                else:
                    try:
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute(
                            "UPDATE usuarios SET nome = ?, usuario = ?, senha = ?, perfil = ?, ativo = ? WHERE id = ?",
                            (nome_edit.strip(), usuario_edit.strip().lower(), senha_edit.strip(), perfil_edit, 1 if ativo_edit else 0, usuario_sel["id"]),
                        )
                        conn.commit()
                        conn.close()
                        st.success("Usuário atualizado com sucesso.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar usuário: {e}")

    with aba2:
        st.warning("A exclusão apaga esse usuário do sistema.")
        with st.form(f"form_excluir_usuario_{usuario_sel['id']}"):
            confirmar = st.checkbox(f'Confirmo excluir o usuário "{usuario_sel["usuario"]}"')
            excluir = st.form_submit_button("Excluir usuário")
            if excluir:
                if not confirmar:
                    st.error("Marque a confirmação antes de excluir.")
                else:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM usuarios WHERE id = ?", (usuario_sel["id"],))
                    conn.commit()
                    conn.close()
                    st.success("Usuário excluído com sucesso.")
                    st.rerun()
else:
    st.info("Nenhum usuário cadastrado ainda.")

st.divider()
st.subheader("Usuários cadastrados")
usuarios = carregar_usuarios()
if usuarios:
    dados = [{
        "ID": u["id"],
        "Nome": u["nome"],
        "Usuário": u["usuario"],
        "Senha": u["senha"],
        "Perfil": u["perfil"],
        "Status": "Ativo" if u["ativo"] == 1 else "Inativo",
    } for u in usuarios]
    st.dataframe(dados, use_container_width=True, hide_index=True)
