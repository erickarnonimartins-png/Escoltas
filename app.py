import pandas as pd
import streamlit as st
from datetime import date
from db import get_connection, init_db
from auth import exigir_login, menu_lateral, is_admin

st.set_page_config(page_title="Controle de Escoltas", page_icon="🚚", layout="wide")
init_db()
exigir_login()
menu_lateral()

st.title("🚚 Controle de Escoltas")
st.caption("Dashboard geral do sistema")


def buscar_resumo_geral(competencia):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        """
        SELECT
            COUNT(*) AS total_escoltas,
            COALESCE(SUM(total_receber), 0) AS total_receber,
            COALESCE(SUM(CASE WHEN status_pagamento = 'pago' THEN total_pagar ELSE 0 END), 0) AS total_pago,
            COALESCE(SUM(CASE WHEN status_pagamento = 'pendente' THEN total_pagar ELSE 0 END), 0) AS total_pendente,
            COALESCE(SUM(lucro), 0) AS lucro_total
        FROM servicos
        WHERE substr(data_servico, 1, 7) = ?
        """,
        (competencia,),
    ).fetchone()
    conn.close()
    return {
        "total_escoltas": int(row["total_escoltas"] or 0),
        "total_receber": float(row["total_receber"] or 0),
        "total_pago": float(row["total_pago"] or 0),
        "total_pendente": float(row["total_pendente"] or 0),
        "lucro_total": float(row["lucro_total"] or 0),
    }


def buscar_qtd_agentes():
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT COUNT(*) AS total FROM agentes WHERE ativo = 1").fetchone()
    conn.close()
    return int(row["total"] or 0)


def buscar_qtd_rotas():
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT COUNT(*) AS total FROM rotas WHERE ativa = 1").fetchone()
    conn.close()
    return int(row["total"] or 0)


def buscar_escoltas_por_dia(competencia):
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT data_servico, COUNT(*) AS quantidade
        FROM servicos
        WHERE substr(data_servico, 1, 7) = ?
        GROUP BY data_servico
        ORDER BY data_servico
        """,
        (competencia,),
    ).fetchall()
    conn.close()
    return pd.DataFrame([{"Data": row["data_servico"], "Escoltas": int(row["quantidade"] or 0)} for row in rows])


def buscar_ranking_agentes_pagamento(competencia):
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT a.nome AS agente,
               COUNT(*) AS quantidade_escoltas,
               COALESCE(SUM(s.total_pagar), 0) AS total_pagar
        FROM servicos s
        INNER JOIN agentes a ON s.agente_id = a.id
        WHERE substr(s.data_servico, 1, 7) = ?
        GROUP BY a.nome
        ORDER BY quantidade_escoltas DESC, a.nome
        """,
        (competencia,),
    ).fetchall()
    conn.close()
    return pd.DataFrame([{
        "Agente": row["agente"],
        "Qtd. Escoltas": int(row["quantidade_escoltas"] or 0),
        "Total a Pagar": round(float(row["total_pagar"] or 0), 2),
    } for row in rows])


def buscar_ranking_rotas_admin(competencia):
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT r.nome_rota AS rota,
               COUNT(*) AS quantidade_servicos,
               COALESCE(SUM(s.total_receber), 0) AS total_faturado,
               COALESCE(SUM(s.lucro), 0) AS lucro_total
        FROM servicos s
        INNER JOIN rotas r ON s.rota_id = r.id
        WHERE substr(s.data_servico, 1, 7) = ?
        GROUP BY r.nome_rota
        ORDER BY quantidade_servicos DESC, r.nome_rota
        """,
        (competencia,),
    ).fetchall()
    conn.close()
    return pd.DataFrame([{
        "Rota": row["rota"],
        "Qtd. Serviços": int(row["quantidade_servicos"] or 0),
        "Total Faturado": round(float(row["total_faturado"] or 0), 2),
        "Lucro Total": round(float(row["lucro_total"] or 0), 2),
    } for row in rows])


def buscar_pagamentos_pendentes(competencia):
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT a.nome AS agente,
               COUNT(*) AS quantidade_pendencias,
               COALESCE(SUM(s.total_pagar), 0) AS valor_pendente
        FROM servicos s
        INNER JOIN agentes a ON s.agente_id = a.id
        WHERE substr(s.data_servico, 1, 7) = ?
          AND s.status_pagamento = 'pendente'
        GROUP BY a.nome
        ORDER BY valor_pendente DESC, a.nome
        """,
        (competencia,),
    ).fetchall()
    conn.close()
    return pd.DataFrame([{
        "Agente": row["agente"],
        "Qtd. Pendências": int(row["quantidade_pendencias"] or 0),
        "Valor Pendente": round(float(row["valor_pendente"] or 0), 2),
    } for row in rows])


hoje = date.today()

c1, c2 = st.columns(2)
with c1:
    mes = st.selectbox("Mês", options=list(range(1, 13)), index=hoje.month - 1, format_func=lambda x: f"{x:02d}")
with c2:
    ano = st.number_input("Ano", min_value=2020, max_value=2100, value=hoje.year, step=1)

competencia = f"{ano}-{mes:02d}"
qtd_agentes = buscar_qtd_agentes()
qtd_rotas = buscar_qtd_rotas()
df_dia = buscar_escoltas_por_dia(competencia)

if is_admin():
    resumo = buscar_resumo_geral(competencia)
    st.subheader(f"Visão financeira - {competencia}")

    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
    m1.metric("Escoltas", resumo["total_escoltas"])
    m2.metric("A receber", f'R$ {resumo["total_receber"]:.2f}')
    m3.metric("Pago", f'R$ {resumo["total_pago"]:.2f}')
    m4.metric("Pendente", f'R$ {resumo["total_pendente"]:.2f}')
    m5.metric("Lucro", f'R$ {resumo["lucro_total"]:.2f}')
    m6.metric("Agentes ativos", qtd_agentes)
    m7.metric("Rotas ativas", qtd_rotas)

    st.divider()
    st.subheader("Escoltas por dia")
    if not df_dia.empty:
        st.bar_chart(df_dia.set_index("Data"))

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Ranking de agentes")
        df_agentes = buscar_ranking_agentes_pagamento(competencia)
        if not df_agentes.empty:
            st.dataframe(df_agentes, use_container_width=True, hide_index=True)
    with col_b:
        st.subheader("Ranking de rotas")
        df_rotas = buscar_ranking_rotas_admin(competencia)
        if not df_rotas.empty:
            st.dataframe(df_rotas, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Pagamentos pendentes")
    df_pendentes = buscar_pagamentos_pendentes(competencia)
    if not df_pendentes.empty:
        st.dataframe(df_pendentes, use_container_width=True, hide_index=True)
else:
    total_escoltas = int(df_dia["Escoltas"].sum()) if not df_dia.empty else 0
    st.subheader(f"Visão operacional - {competencia}")
    m1, m2, m3 = st.columns(3)
    m1.metric("Escoltas no mês", total_escoltas)
    m2.metric("Agentes ativos", qtd_agentes)
    m3.metric("Rotas ativas", qtd_rotas)

    st.divider()
    st.subheader("Escoltas por dia")
    if not df_dia.empty:
        st.bar_chart(df_dia.set_index("Data"))

    st.divider()
    st.subheader("Pagamentos por agente")
    df_pagto = buscar_ranking_agentes_pagamento(competencia)
    if not df_pagto.empty:
        st.dataframe(df_pagto, use_container_width=True, hide_index=True)

st.divider()
st.caption("Sistema desenvolvido em Python + Streamlit")