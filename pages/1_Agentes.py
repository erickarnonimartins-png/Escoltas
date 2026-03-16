import streamlit as st
from db import get_connection, init_db
from auth import exigir_login, menu_lateral

st.set_page_config(page_title="Agentes", page_icon="👮")
init_db()
exigir_login()
menu_lateral()
st.title("👮 Cadastro de Agentes")


def carregar_agentes():
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT id, nome, telefone, pix, observacao, ativo
        FROM agentes
        ORDER BY nome
    """).fetchall()
    conn.close()
    return [{
        "id": row["id"],
        "nome": row["nome"],
        "telefone": row["telefone"] or "",
        "pix": row["pix"] or "",
        "observacao": row["observacao"] or "",
        "ativo": row["ativo"],
    } for row in rows]


def contar_servicos_do_agente(agente_id):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT COUNT(*) AS total FROM servicos WHERE agente_id = ?", (agente_id,)).fetchone()
    conn.close()
    return int(row["total"] or 0)


agentes = carregar_agentes()
mapa_agentes = {a["id"]: a for a in agentes}

ativos = sum(1 for a in agentes if a["ativo"] == 1)
inativos = sum(1 for a in agentes if a["ativo"] == 0)

m1, m2, m3 = st.columns(3)
m1.metric("Total de agentes", len(agentes))
m2.metric("Ativos", ativos)
m3.metric("Inativos", inativos)

st.divider()
st.subheader("Novo agente")

with st.form("form_novo_agente", clear_on_submit=True):
    nome = st.text_input("Nome do agente")
    telefone = st.text_input("Telefone")
    pix = st.text_input("Chave PIX")
    observacao = st.text_area("Observação")
    ativo = st.checkbox("Ativo", value=True)

    salvar = st.form_submit_button("Salvar agente")
    if salvar:
        if not nome.strip():
            st.error("Digite o nome do agente.")
        else:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO agentes (nome, telefone, pix, observacao, ativo)
                VALUES (?, ?, ?, ?, ?)
                """,
                (nome.strip(), telefone.strip(), pix.strip(), observacao.strip(), 1 if ativo else 0),
            )
            conn.commit()
            conn.close()
            st.success("Agente salvo com sucesso.")
            st.rerun()

st.divider()
st.subheader("Gerenciar agente")

if agentes:
    ids_agentes = [a["id"] for a in agentes]
    agente_id_sel = st.selectbox(
        "Escolha um agente",
        options=ids_agentes,
        format_func=lambda aid: f'#{mapa_agentes[aid]["id"]} | {mapa_agentes[aid]["nome"]}'
    )
    agente_sel = mapa_agentes[agente_id_sel]
    aba1, aba2 = st.tabs(["✏️ Editar", "🗑️ Excluir"])

    with aba1:
        with st.form(f"form_editar_agente_{agente_sel['id']}"):
            nome_edit = st.text_input("Nome do agente", value=agente_sel["nome"])
            telefone_edit = st.text_input("Telefone", value=agente_sel["telefone"])
            pix_edit = st.text_input("Chave PIX", value=agente_sel["pix"])
            observacao_edit = st.text_area("Observação", value=agente_sel["observacao"])
            ativo_edit = st.checkbox("Ativo", value=(agente_sel["ativo"] == 1))

            salvar_edicao = st.form_submit_button("Salvar alterações")
            if salvar_edicao:
                if not nome_edit.strip():
                    st.error("Digite o nome do agente.")
                else:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute(
                        """
                        UPDATE agentes
                        SET nome = ?, telefone = ?, pix = ?, observacao = ?, ativo = ?
                        WHERE id = ?
                        """,
                        (nome_edit.strip(), telefone_edit.strip(), pix_edit.strip(), observacao_edit.strip(), 1 if ativo_edit else 0, agente_sel["id"]),
                    )
                    conn.commit()
                    conn.close()
                    st.success("Agente atualizado com sucesso.")
                    st.rerun()

    with aba2:
        qtd_servicos = contar_servicos_do_agente(agente_sel["id"])
        if qtd_servicos > 0:
            st.warning(f'Esse agente possui {qtd_servicos} serviço(s) vinculado(s). O ideal é marcar como inativo.')
            if st.button("Marcar como inativo", key=f"inativar_{agente_sel['id']}"):
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("UPDATE agentes SET ativo = 0 WHERE id = ?", (agente_sel["id"],))
                conn.commit()
                conn.close()
                st.success("Agente marcado como inativo.")
                st.rerun()
        else:
            st.warning("A exclusão apaga esse agente do banco.")
            with st.form(f"form_excluir_agente_{agente_sel['id']}"):
                confirmar = st.checkbox(f'Confirmo excluir o agente "{agente_sel["nome"]}"')
                excluir = st.form_submit_button("Excluir agente")
                if excluir:
                    if not confirmar:
                        st.error("Marque a confirmação antes de excluir.")
                    else:
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("DELETE FROM agentes WHERE id = ?", (agente_sel["id"],))
                        conn.commit()
                        conn.close()
                        st.success("Agente excluído com sucesso.")
                        st.rerun()
else:
    st.info("Nenhum agente cadastrado ainda.")

st.divider()
st.subheader("Agentes cadastrados")

agentes = carregar_agentes()
if agentes:
    dados = [{
        "ID": a["id"],
        "Nome": a["nome"],
        "Telefone": a["telefone"],
        "PIX": a["pix"],
        "Observação": a["observacao"],
        "Status": "Ativo" if a["ativo"] == 1 else "Inativo"
    } for a in agentes]
    st.dataframe(dados, use_container_width=True, hide_index=True)
else:
    st.info("Nenhum agente cadastrado ainda.")
