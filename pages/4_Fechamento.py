import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import date
from db import get_connection, init_db
from auth import exigir_login, menu_lateral, exigir_admin

st.set_page_config(page_title="Fechamento Mensal", page_icon="📊")
init_db()
exigir_login()
menu_lateral()
exigir_admin()
st.title("📊 Fechamento Mensal")


def gerar_excel_fechamento(df_resumo, df_agentes, df_rotas, df_detalhes):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_resumo.to_excel(writer, sheet_name="Resumo", index=False)
        df_agentes.to_excel(writer, sheet_name="Por Agente", index=False)
        df_rotas.to_excel(writer, sheet_name="Por Rota", index=False)
        df_detalhes.to_excel(writer, sheet_name="Lancamentos", index=False)
    output.seek(0)
    return output.getvalue()


def texto_status(status):
    return "🟢 Pago" if status == "pago" else "🔴 Pendente"


def carregar_agentes_pendentes(competencia):
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT DISTINCT a.id, a.nome
        FROM servicos s
        INNER JOIN agentes a ON s.agente_id = a.id
        WHERE substr(s.data_servico, 1, 7) = ?
          AND s.status_pagamento = 'pendente'
        ORDER BY a.nome
        """,
        (competencia,),
    ).fetchall()
    conn.close()
    return [{"id": row["id"], "nome": row["nome"]} for row in rows]


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


def buscar_resumo_agentes(competencia):
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT
            a.nome AS agente,
            COUNT(*) AS quantidade_escoltas,
            COALESCE(SUM(s.total_horas), 0) AS total_horas,
            COALESCE(SUM(s.total_pagar), 0) AS total_a_receber_agente,
            COALESCE(SUM(CASE WHEN s.status_pagamento = 'pago' THEN s.total_pagar ELSE 0 END), 0) AS valor_pago,
            COALESCE(SUM(CASE WHEN s.status_pagamento = 'pendente' THEN s.total_pagar ELSE 0 END), 0) AS valor_pendente
        FROM servicos s
        INNER JOIN agentes a ON s.agente_id = a.id
        WHERE substr(s.data_servico, 1, 7) = ?
        GROUP BY a.nome
        ORDER BY quantidade_escoltas DESC, a.nome
        """,
        (competencia,),
    ).fetchall()
    conn.close()
    dados = []
    for row in rows:
        vp = round(float(row["valor_pendente"] or 0), 2)
        dados.append({
            "Agente": row["agente"],
            "Qtd. Escoltas": int(row["quantidade_escoltas"] or 0),
            "Total Horas": round(float(row["total_horas"] or 0), 2),
            "Total a Receber": round(float(row["total_a_receber_agente"] or 0), 2),
            "Valor Pago": round(float(row["valor_pago"] or 0), 2),
            "Valor Pendente": vp,
            "Status": "🔴 Pendente" if vp > 0 else "🟢 Pago"
        })
    return pd.DataFrame(dados)


def buscar_resumo_rotas(competencia):
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT
            r.nome_rota AS rota,
            COUNT(*) AS quantidade_servicos,
            COALESCE(SUM(s.total_receber), 0) AS total_faturado,
            COALESCE(SUM(s.total_pagar), 0) AS total_pago,
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
        "Total Pago": round(float(row["total_pago"] or 0), 2),
        "Lucro Total": round(float(row["lucro_total"] or 0), 2),
    } for row in rows])


def buscar_detalhes(competencia):
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT
            s.data_servico, r.nome_rota, a.nome AS agente, s.placa_caminhao,
            s.hora_inicial, s.hora_final, s.total_horas, s.valor_fixo_receber,
            s.valor_fixo_pagar, s.valor_extra_recebido, s.pedagio_km_extra,
            s.total_receber, s.total_pagar, s.lucro, s.status_pagamento,
            s.data_pagamento, s.forma_pagamento, s.observacao
        FROM servicos s
        INNER JOIN rotas r ON s.rota_id = r.id
        INNER JOIN agentes a ON s.agente_id = a.id
        WHERE substr(s.data_servico, 1, 7) = ?
        ORDER BY s.data_servico DESC, s.id DESC
        """,
        (competencia,),
    ).fetchall()
    conn.close()
    return pd.DataFrame([{
        "Data": row["data_servico"],
        "Rota": row["nome_rota"],
        "Agente": row["agente"],
        "Placa": row["placa_caminhao"],
        "Hora Inicial": row["hora_inicial"],
        "Hora Final": row["hora_final"],
        "Horas": round(float(row["total_horas"] or 0), 2),
        "Recebo Fixo": round(float(row["valor_fixo_receber"] or 0), 2),
        "Pago Fixo": round(float(row["valor_fixo_pagar"] or 0), 2),
        "Extra": round(float(row["valor_extra_recebido"] or 0), 2),
        "Pedágio/KM": round(float(row["pedagio_km_extra"] or 0), 2),
        "Total Receber": round(float(row["total_receber"] or 0), 2),
        "Total Pagar": round(float(row["total_pagar"] or 0), 2),
        "Lucro": round(float(row["lucro"] or 0), 2),
        "Pagamento": texto_status(row["status_pagamento"]),
        "Data Pagamento": row["data_pagamento"],
        "Forma Pagamento": row["forma_pagamento"],
        "Observação": row["observacao"],
    } for row in rows])


def marcar_pendencias_como_pagas(agente_id, competencia, data_pagamento, forma_pagamento):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE servicos
        SET status_pagamento = 'pago',
            data_pagamento = ?,
            forma_pagamento = ?
        WHERE agente_id = ?
          AND substr(data_servico, 1, 7) = ?
          AND status_pagamento = 'pendente'
        """,
        (str(data_pagamento), forma_pagamento, agente_id, competencia),
    )
    conn.commit()
    conn.close()


hoje = date.today()
col1, col2 = st.columns(2)
with col1:
    mes = st.selectbox("Mês", options=list(range(1, 13)), index=hoje.month - 1, format_func=lambda x: f"{x:02d}")
with col2:
    ano = st.number_input("Ano", min_value=2020, max_value=2100, value=hoje.year, step=1)

competencia = f"{ano}-{mes:02d}"
agentes_pendentes = carregar_agentes_pendentes(competencia)
mapa = {a["id"]: a for a in agentes_pendentes}

if agentes_pendentes:
    st.subheader("Baixar pagamento de agente")
    ids = [a["id"] for a in agentes_pendentes]
    with st.form("form_pagamento_agente"):
        agente_id_sel = st.selectbox("Agente com pendências", options=ids, format_func=lambda aid: mapa[aid]["nome"])
        data_pagamento = st.date_input("Data do pagamento", value=hoje)
        forma_pagamento = st.selectbox("Forma de pagamento", ["pix", "dinheiro", "transferência", "outro"])
        confirmar = st.form_submit_button("Marcar pendências do agente como pagas")
        if confirmar:
            marcar_pendencias_como_pagas(agente_id_sel, competencia, data_pagamento, forma_pagamento)
            st.success(f'Pendências de {mapa[agente_id_sel]["nome"]} marcadas como pagas.')
            st.rerun()
else:
    st.info("Não há pagamentos pendentes para este mês.")

st.divider()
resumo = buscar_resumo_geral(competencia)
st.subheader(f"Resumo geral - {competencia}")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total de escoltas", resumo["total_escoltas"])
m2.metric("Total a receber", f'R$ {resumo["total_receber"]:.2f}')
m3.metric("Total pago", f'R$ {resumo["total_pago"]:.2f}')
m4.metric("Total pendente", f'R$ {resumo["total_pendente"]:.2f}')
m5.metric("Lucro total", f'R$ {resumo["lucro_total"]:.2f}')

st.divider()
st.subheader("Resumo por agente")
df_agentes = buscar_resumo_agentes(competencia)
if not df_agentes.empty:
    st.dataframe(df_agentes, use_container_width=True, hide_index=True)
else:
    st.info("Nenhum lançamento encontrado para este mês.")

st.divider()
st.subheader("Resumo por rota")
df_rotas = buscar_resumo_rotas(competencia)
if not df_rotas.empty:
    st.dataframe(df_rotas, use_container_width=True, hide_index=True)
else:
    st.info("Nenhuma rota encontrada para este mês.")

st.divider()
st.subheader("Lançamentos do mês")
df_detalhes = buscar_detalhes(competencia)
if not df_detalhes.empty:
    st.dataframe(df_detalhes, use_container_width=True, hide_index=True)
else:
    st.info("Nenhum lançamento detalhado para este mês.")

st.divider()
st.subheader("Exportação")
df_resumo = pd.DataFrame([{
    "Competência": competencia,
    "Total de Escoltas": resumo["total_escoltas"],
    "Total a Receber": round(resumo["total_receber"], 2),
    "Total Pago": round(resumo["total_pago"], 2),
    "Total Pendente": round(resumo["total_pendente"], 2),
    "Lucro Total": round(resumo["lucro_total"], 2),
}])

arquivo_excel = gerar_excel_fechamento(df_resumo=df_resumo, df_agentes=df_agentes, df_rotas=df_rotas, df_detalhes=df_detalhes)
st.download_button(
    label="📥 Baixar fechamento em Excel",
    data=arquivo_excel,
    file_name=f"fechamento_{competencia}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
