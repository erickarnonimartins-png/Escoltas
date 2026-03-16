import streamlit as st
import pandas as pd
from io import BytesIO
from db import get_connection, init_db
from datetime import datetime, timedelta, date
from auth import exigir_login, menu_lateral, is_admin

st.set_page_config(page_title="Lançamentos", page_icon="📝")
init_db()
exigir_login()
menu_lateral()
st.title("📝 Lançamento de Serviços")


def gerar_excel_lancamentos(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Lancamentos Filtrados", index=False)
    output.seek(0)
    return output.getvalue()


def texto_status(status):
    return "🟢 Pago" if status == "pago" else "🔴 Pendente"


def calcular_total_horas(data_servico, hora_inicial, hora_final):
    inicio_dt = datetime.combine(data_servico, hora_inicial)
    fim_dt = datetime.combine(data_servico, hora_final)
    if fim_dt < inicio_dt:
        fim_dt += timedelta(days=1)
    return round((fim_dt - inicio_dt).total_seconds() / 3600, 2)


def parse_date(valor):
    if not valor:
        return date.today()
    return datetime.strptime(str(valor), "%Y-%m-%d").date()


def parse_time(valor):
    if not valor:
        return datetime.strptime("00:00", "%H:%M").time()

    texto = str(valor).strip()

    if len(texto) == 8:
        return datetime.strptime(texto, "%H:%M:%S").time()

    return datetime.strptime(texto, "%H:%M").time()


def parse_time_flexivel(valor):
    if valor is None:
        raise ValueError("Horário inválido.")

    texto = str(valor).strip()

    if not texto:
        raise ValueError("Horário inválido.")

    formatos = ["%H:%M", "%H%M", "%H"]
    for formato in formatos:
        try:
            hora = datetime.strptime(texto, formato).time()
            return hora.replace(second=0, microsecond=0)
        except ValueError:
            continue

    raise ValueError("Use o formato HH:MM. Ex.: 07:03 ou 18:47")


def formatar_hora_para_campo(valor):
    try:
        return parse_time(valor).strftime("%H:%M")
    except Exception:
        return "00:00"


def campo_horario_manual(label, valor_inicial="00:00", key=None):
    texto = st.text_input(
        label,
        value=valor_inicial,
        placeholder="HH:MM",
        max_chars=5,
        key=key,
    )

    try:
        hora = parse_time_flexivel(texto)
        return hora, True
    except ValueError:
        return None, False


def marcar_lancamento_como_pago(servico_id, data_pagamento, forma_pagamento):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE servicos
        SET status_pagamento = 'pago',
            data_pagamento = ?,
            forma_pagamento = ?
        WHERE id = ?
        """,
        (str(data_pagamento), forma_pagamento, servico_id),
    )
    conn.commit()
    conn.close()


def carregar_agentes():
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute("SELECT id, nome, ativo FROM agentes ORDER BY nome").fetchall()
    conn.close()
    return [{"id": row["id"], "nome": row["nome"], "ativo": row["ativo"]} for row in rows]


def carregar_rotas():
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT id, nome_rota, origem, destino, valor_fixo_receber, valor_fixo_pagar, ativa
        FROM rotas
        ORDER BY nome_rota
        """
    ).fetchall()
    conn.close()
    return [{
        "id": row["id"],
        "nome_rota": row["nome_rota"],
        "origem": row["origem"],
        "destino": row["destino"],
        "valor_fixo_receber": float(row["valor_fixo_receber"] or 0),
        "valor_fixo_pagar": float(row["valor_fixo_pagar"] or 0),
        "ativa": row["ativa"],
    } for row in rows]


def carregar_servicos():
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT
            s.id, s.data_servico, s.rota_id, s.agente_id, s.placa_caminhao,
            s.hora_inicial, s.hora_final, s.total_horas, s.valor_fixo_receber,
            s.valor_fixo_pagar, s.valor_extra_recebido, s.pedagio_km_extra,
            s.total_receber, s.total_pagar, s.lucro, s.observacao,
            s.status_pagamento, s.data_pagamento, s.forma_pagamento,
            r.nome_rota, a.nome AS nome_agente
        FROM servicos s
        INNER JOIN rotas r ON s.rota_id = r.id
        INNER JOIN agentes a ON s.agente_id = a.id
        ORDER BY s.data_servico DESC, s.id DESC
        """
    ).fetchall()
    conn.close()
    return [{
        "id": row["id"],
        "data_servico": row["data_servico"],
        "rota_id": row["rota_id"],
        "agente_id": row["agente_id"],
        "placa_caminhao": row["placa_caminhao"],
        "hora_inicial": row["hora_inicial"],
        "hora_final": row["hora_final"],
        "total_horas": float(row["total_horas"] or 0),
        "valor_fixo_receber": float(row["valor_fixo_receber"] or 0),
        "valor_fixo_pagar": float(row["valor_fixo_pagar"] or 0),
        "valor_extra_recebido": float(row["valor_extra_recebido"] or 0),
        "pedagio_km_extra": float(row["pedagio_km_extra"] or 0),
        "total_receber": float(row["total_receber"] or 0),
        "total_pagar": float(row["total_pagar"] or 0),
        "lucro": float(row["lucro"] or 0),
        "observacao": row["observacao"],
        "status_pagamento": row["status_pagamento"],
        "data_pagamento": row["data_pagamento"],
        "forma_pagamento": row["forma_pagamento"],
        "nome_rota": row["nome_rota"],
        "nome_agente": row["nome_agente"],
    } for row in rows]


def buscar_servicos_filtrados(mes, ano, agente_id=None, rota_id=None, status_pagamento=None, placa=None):
    conn = get_connection()
    cur = conn.cursor()
    competencia = f"{ano}-{mes:02d}"
    sql = """
        SELECT
            s.id, s.data_servico, s.rota_id, s.agente_id, s.placa_caminhao,
            s.hora_inicial, s.hora_final, s.total_horas, s.valor_fixo_receber,
            s.valor_fixo_pagar, s.valor_extra_recebido, s.pedagio_km_extra,
            s.total_receber, s.total_pagar, s.lucro, s.observacao,
            s.status_pagamento, s.data_pagamento, s.forma_pagamento,
            r.nome_rota, a.nome AS nome_agente
        FROM servicos s
        INNER JOIN rotas r ON s.rota_id = r.id
        INNER JOIN agentes a ON s.agente_id = a.id
        WHERE substr(s.data_servico, 1, 7) = ?
    """
    params = [competencia]

    if agente_id:
        sql += " AND s.agente_id = ?"
        params.append(agente_id)

    if rota_id:
        sql += " AND s.rota_id = ?"
        params.append(rota_id)

    if status_pagamento and status_pagamento != "todos":
        sql += " AND s.status_pagamento = ?"
        params.append(status_pagamento)

    if placa and placa.strip():
        sql += " AND UPPER(COALESCE(s.placa_caminhao, '')) LIKE ?"
        params.append(f"%{placa.strip().upper()}%")

    sql += " ORDER BY s.data_servico DESC, s.id DESC"

    rows = cur.execute(sql, params).fetchall()
    conn.close()

    return [{
        "id": row["id"],
        "data_servico": row["data_servico"],
        "rota_id": row["rota_id"],
        "agente_id": row["agente_id"],
        "placa_caminhao": row["placa_caminhao"],
        "hora_inicial": row["hora_inicial"],
        "hora_final": row["hora_final"],
        "total_horas": float(row["total_horas"] or 0),
        "valor_fixo_receber": float(row["valor_fixo_receber"] or 0),
        "valor_fixo_pagar": float(row["valor_fixo_pagar"] or 0),
        "valor_extra_recebido": float(row["valor_extra_recebido"] or 0),
        "pedagio_km_extra": float(row["pedagio_km_extra"] or 0),
        "total_receber": float(row["total_receber"] or 0),
        "total_pagar": float(row["total_pagar"] or 0),
        "lucro": float(row["lucro"] or 0),
        "observacao": row["observacao"],
        "status_pagamento": row["status_pagamento"],
        "data_pagamento": row["data_pagamento"],
        "forma_pagamento": row["forma_pagamento"],
        "nome_rota": row["nome_rota"],
        "nome_agente": row["nome_agente"],
    } for row in rows]


agentes = carregar_agentes()
rotas = carregar_rotas()
servicos = carregar_servicos()

agentes_ativos = [a for a in agentes if a["ativo"] == 1]
rotas_ativas = [r for r in rotas if r["ativa"] == 1]

if not agentes_ativos:
    st.warning("Cadastre pelo menos 1 agente ativo antes de lançar serviços.")
    st.stop()

if not rotas_ativas:
    st.warning("Cadastre pelo menos 1 rota ativa antes de lançar serviços.")
    st.stop()

mapa_agentes = {a["id"]: a for a in agentes}
mapa_rotas = {r["id"]: r for r in rotas}
mapa_servicos = {s["id"]: s for s in servicos}

st.subheader("Novo lançamento")
ids_rotas_ativas = [r["id"] for r in rotas_ativas]
ids_agentes_ativos = [a["id"] for a in agentes_ativos]

with st.form("form_novo_lancamento", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        data_servico = st.date_input("Data do serviço", value=date.today())
        if is_admin():
            texto_rota = lambda rid: f'{mapa_rotas[rid]["nome_rota"]} | Recebo: R$ {mapa_rotas[rid]["valor_fixo_receber"]:.2f} | Pago: R$ {mapa_rotas[rid]["valor_fixo_pagar"]:.2f}'
        else:
            texto_rota = lambda rid: f'{mapa_rotas[rid]["nome_rota"]} | Pago: R$ {mapa_rotas[rid]["valor_fixo_pagar"]:.2f}'

        rota_id = st.selectbox("Rota", options=ids_rotas_ativas, format_func=texto_rota)
        agente_id = st.selectbox("Agente", options=ids_agentes_ativos, format_func=lambda aid: mapa_agentes[aid]["nome"])
        placa_caminhao = st.text_input("Placa do caminhão")

    with col2:
        hora_inicial, hora_inicial_ok = campo_horario_manual(
            "Hora inicial",
            valor_inicial="00:00",
            key="hora_inicial_novo"
        )
        hora_final, hora_final_ok = campo_horario_manual(
            "Hora final",
            valor_inicial="00:00",
            key="hora_final_novo"
        )

        if is_admin():
            valor_extra_recebido = st.number_input("Valor extra recebido", min_value=0.0, step=10.0, format="%.2f")
            pedagio_km_extra = st.number_input("Pedágio/KM extra", min_value=0.0, step=10.0, format="%.2f")
        else:
            valor_extra_recebido = 0.0
            pedagio_km_extra = 0.0

    observacao = st.text_area("Observação")

    col3, col4, col5 = st.columns(3)
    with col3:
        status_pagamento = st.selectbox("Status do pagamento", ["pendente", "pago"])
    with col4:
        data_pagamento = st.date_input("Data do pagamento", value=date.today())
    with col5:
        forma_pagamento = st.selectbox("Forma de pagamento", ["", "pix", "dinheiro", "transferência", "outro"])

    horarios_validos = (
        hora_inicial_ok and hora_final_ok and
        hora_inicial is not None and hora_final is not None
    )

    rota = mapa_rotas[rota_id]
    total_horas = calcular_total_horas(data_servico, hora_inicial, hora_final) if horarios_validos else 0.0
    valor_fixo_receber = float(rota["valor_fixo_receber"])
    valor_fixo_pagar = float(rota["valor_fixo_pagar"])
    total_receber = valor_fixo_receber + float(valor_extra_recebido) + float(pedagio_km_extra)
    total_pagar = valor_fixo_pagar
    lucro = total_receber - total_pagar

    st.subheader("Resumo do lançamento")
    if is_admin():
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Total de horas", f"{total_horas:.2f} h")
        r2.metric("Total a receber", f"R$ {total_receber:.2f}")
        r3.metric("Total a pagar", f"R$ {total_pagar:.2f}")
        r4.metric("Lucro", f"R$ {lucro:.2f}")
    else:
        r1, r2 = st.columns(2)
        r1.metric("Total de horas", f"{total_horas:.2f} h")
        r2.metric("Total a pagar", f"R$ {total_pagar:.2f}")

    salvar = st.form_submit_button("Salvar lançamento")

    if salvar:
        if not horarios_validos:
            st.error("Corrija os horários antes de salvar. Use o formato HH:MM.")
        else:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO servicos (
                    data_servico, rota_id, agente_id, placa_caminhao, hora_inicial, hora_final,
                    total_horas, valor_fixo_receber, valor_fixo_pagar, valor_extra_recebido,
                    pedagio_km_extra, total_receber, total_pagar, lucro, observacao,
                    status_pagamento, data_pagamento, forma_pagamento
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(data_servico),
                    rota_id,
                    agente_id,
                    placa_caminhao.strip(),
                    hora_inicial.strftime("%H:%M"),
                    hora_final.strftime("%H:%M"),
                    total_horas,
                    valor_fixo_receber,
                    valor_fixo_pagar,
                    float(valor_extra_recebido),
                    float(pedagio_km_extra),
                    total_receber,
                    total_pagar,
                    lucro,
                    observacao.strip(),
                    status_pagamento,
                    str(data_pagamento) if status_pagamento == "pago" else None,
                    forma_pagamento if status_pagamento == "pago" else None,
                ),
            )
            conn.commit()
            conn.close()
            st.success("Lançamento salvo com sucesso.")
            st.rerun()

st.divider()
st.subheader("Gerenciar lançamento existente")

if servicos:
    ids_servicos = [s["id"] for s in servicos]

    servico_id = st.selectbox(
        "Escolha um lançamento",
        options=ids_servicos,
        format_func=lambda sid: f'#{mapa_servicos[sid]["id"]} | {mapa_servicos[sid]["data_servico"]} | {mapa_servicos[sid]["nome_rota"]} | {mapa_servicos[sid]["nome_agente"]} | {mapa_servicos[sid]["placa_caminhao"] or "-"} | {texto_status(mapa_servicos[sid]["status_pagamento"])}'
    )

    servico_sel = mapa_servicos[servico_id]

    aba1, aba2, aba3, aba4 = st.tabs(["✏️ Editar", "📄 Duplicar", "🗑️ Excluir", "💰 Marcar como pago"])

    with aba1:
        ids_rotas = [r["id"] for r in rotas]
        ids_agentes = [a["id"] for a in agentes]
        idx_rota = ids_rotas.index(servico_sel["rota_id"]) if servico_sel["rota_id"] in ids_rotas else 0
        idx_agente = ids_agentes.index(servico_sel["agente_id"]) if servico_sel["agente_id"] in ids_agentes else 0

        with st.form(f"form_editar_{servico_sel['id']}"):
            c1, c2 = st.columns(2)

            with c1:
                data_edit = st.date_input("Data do serviço", value=parse_date(servico_sel["data_servico"]))

                if is_admin():
                    texto_rota_edit = lambda rid: f'{mapa_rotas[rid]["nome_rota"]} | Recebo: R$ {mapa_rotas[rid]["valor_fixo_receber"]:.2f} | Pago: R$ {mapa_rotas[rid]["valor_fixo_pagar"]:.2f}'
                else:
                    texto_rota_edit = lambda rid: f'{mapa_rotas[rid]["nome_rota"]} | Pago: R$ {mapa_rotas[rid]["valor_fixo_pagar"]:.2f}'

                rota_edit_id = st.selectbox(
                    "Rota",
                    options=ids_rotas,
                    index=idx_rota,
                    format_func=texto_rota_edit,
                    key=f"rota_edit_{servico_sel['id']}"
                )
                agente_edit_id = st.selectbox(
                    "Agente",
                    options=ids_agentes,
                    index=idx_agente,
                    format_func=lambda aid: mapa_agentes[aid]["nome"],
                    key=f"agente_edit_{servico_sel['id']}"
                )
                placa_edit = st.text_input("Placa do caminhão", value=servico_sel["placa_caminhao"] or "")

            with c2:
                hora_inicial_edit, hora_inicial_edit_ok = campo_horario_manual(
                    "Hora inicial",
                    valor_inicial=formatar_hora_para_campo(servico_sel["hora_inicial"]),
                    key=f"hora_inicial_edit_{servico_sel['id']}"
                )
                hora_final_edit, hora_final_edit_ok = campo_horario_manual(
                    "Hora final",
                    valor_inicial=formatar_hora_para_campo(servico_sel["hora_final"]),
                    key=f"hora_final_edit_{servico_sel['id']}"
                )

                if is_admin():
                    valor_extra_edit = st.number_input(
                        "Valor extra recebido",
                        min_value=0.0,
                        step=10.0,
                        format="%.2f",
                        value=float(servico_sel["valor_extra_recebido"] or 0)
                    )
                    pedagio_edit = st.number_input(
                        "Pedágio/KM extra",
                        min_value=0.0,
                        step=10.0,
                        format="%.2f",
                        value=float(servico_sel["pedagio_km_extra"] or 0)
                    )
                else:
                    valor_extra_edit = float(servico_sel["valor_extra_recebido"] or 0)
                    pedagio_edit = float(servico_sel["pedagio_km_extra"] or 0)

            observacao_edit = st.text_area("Observação", value=servico_sel["observacao"] or "")

            c3, c4, c5 = st.columns(3)
            with c3:
                status_edit = st.selectbox(
                    "Status do pagamento",
                    ["pendente", "pago"],
                    index=0 if servico_sel["status_pagamento"] == "pendente" else 1
                )
            with c4:
                data_pagamento_padrao = parse_date(servico_sel["data_pagamento"]) if servico_sel["data_pagamento"] else date.today()
                data_pagamento_edit = st.date_input("Data do pagamento", value=data_pagamento_padrao)
            with c5:
                formas = ["", "pix", "dinheiro", "transferência", "outro"]
                forma_atual = servico_sel["forma_pagamento"] if servico_sel["forma_pagamento"] in formas else ""
                forma_pagamento_edit = st.selectbox("Forma de pagamento", formas, index=formas.index(forma_atual))

            horarios_edit_validos = (
                hora_inicial_edit_ok and hora_final_edit_ok and
                hora_inicial_edit is not None and hora_final_edit is not None
            )

            rota_edit = mapa_rotas[rota_edit_id]
            total_horas_edit = calcular_total_horas(data_edit, hora_inicial_edit, hora_final_edit) if horarios_edit_validos else 0.0
            valor_fixo_receber_edit = float(rota_edit["valor_fixo_receber"])
            valor_fixo_pagar_edit = float(rota_edit["valor_fixo_pagar"])
            total_receber_edit = valor_fixo_receber_edit + float(valor_extra_edit) + float(pedagio_edit)
            total_pagar_edit = valor_fixo_pagar_edit
            lucro_edit = total_receber_edit - total_pagar_edit

            st.subheader("Resumo da edição")
            if is_admin():
                e1, e2, e3, e4 = st.columns(4)
                e1.metric("Total de horas", f"{total_horas_edit:.2f} h")
                e2.metric("Total a receber", f"R$ {total_receber_edit:.2f}")
                e3.metric("Total a pagar", f"R$ {total_pagar_edit:.2f}")
                e4.metric("Lucro", f"R$ {lucro_edit:.2f}")
            else:
                e1, e2 = st.columns(2)
                e1.metric("Total de horas", f"{total_horas_edit:.2f} h")
                e2.metric("Total a pagar", f"R$ {total_pagar_edit:.2f}")

            salvar_edicao = st.form_submit_button("Salvar alterações")

            if salvar_edicao:
                if not horarios_edit_validos:
                    st.error("Corrija os horários antes de salvar. Use o formato HH:MM.")
                else:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute(
                        """
                        UPDATE servicos
                        SET data_servico = ?, rota_id = ?, agente_id = ?, placa_caminhao = ?,
                            hora_inicial = ?, hora_final = ?, total_horas = ?, valor_fixo_receber = ?,
                            valor_fixo_pagar = ?, valor_extra_recebido = ?, pedagio_km_extra = ?,
                            total_receber = ?, total_pagar = ?, lucro = ?, observacao = ?,
                            status_pagamento = ?, data_pagamento = ?, forma_pagamento = ?
                        WHERE id = ?
                        """,
                        (
                            str(data_edit),
                            rota_edit_id,
                            agente_edit_id,
                            placa_edit.strip(),
                            hora_inicial_edit.strftime("%H:%M"),
                            hora_final_edit.strftime("%H:%M"),
                            total_horas_edit,
                            valor_fixo_receber_edit,
                            valor_fixo_pagar_edit,
                            float(valor_extra_edit),
                            float(pedagio_edit),
                            total_receber_edit,
                            total_pagar_edit,
                            lucro_edit,
                            observacao_edit.strip(),
                            status_edit,
                            str(data_pagamento_edit) if status_edit == "pago" else None,
                            forma_pagamento_edit if status_edit == "pago" else None,
                            servico_sel["id"],
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.success("Lançamento atualizado com sucesso.")
                    st.rerun()

    with aba2:
        st.write("Esse botão cria um novo lançamento igual ao selecionado.")
        st.write("O novo lançamento sai com status de pagamento pendente.")

        with st.form(f"form_duplicar_{servico_sel['id']}"):
            nova_data = st.date_input("Nova data do lançamento duplicado", value=date.today())
            manter_observacao = st.checkbox("Manter observação original", value=True)
            duplicar = st.form_submit_button("Duplicar lançamento")

            if duplicar:
                rota_dup = mapa_rotas[servico_sel["rota_id"]]
                hora_inicial_dup = parse_time(servico_sel["hora_inicial"])
                hora_final_dup = parse_time(servico_sel["hora_final"])
                total_horas_dup = calcular_total_horas(nova_data, hora_inicial_dup, hora_final_dup)
                valor_fixo_receber_dup = float(rota_dup["valor_fixo_receber"])
                valor_fixo_pagar_dup = float(rota_dup["valor_fixo_pagar"])
                valor_extra_dup = float(servico_sel["valor_extra_recebido"] or 0)
                pedagio_dup = float(servico_sel["pedagio_km_extra"] or 0)
                total_receber_dup = valor_fixo_receber_dup + valor_extra_dup + pedagio_dup
                total_pagar_dup = valor_fixo_pagar_dup
                lucro_dup = total_receber_dup - total_pagar_dup
                obs_dup = servico_sel["observacao"] if manter_observacao else ""

                conn = get_connection()
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO servicos (
                        data_servico, rota_id, agente_id, placa_caminhao, hora_inicial, hora_final,
                        total_horas, valor_fixo_receber, valor_fixo_pagar, valor_extra_recebido,
                        pedagio_km_extra, total_receber, total_pagar, lucro, observacao,
                        status_pagamento, data_pagamento, forma_pagamento
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(nova_data),
                        servico_sel["rota_id"],
                        servico_sel["agente_id"],
                        (servico_sel["placa_caminhao"] or "").strip(),
                        hora_inicial_dup.strftime("%H:%M"),
                        hora_final_dup.strftime("%H:%M"),
                        total_horas_dup,
                        valor_fixo_receber_dup,
                        valor_fixo_pagar_dup,
                        valor_extra_dup,
                        pedagio_dup,
                        total_receber_dup,
                        total_pagar_dup,
                        lucro_dup,
                        (obs_dup or "").strip(),
                        "pendente",
                        None,
                        None,
                    ),
                )
                conn.commit()
                conn.close()
                st.success("Lançamento duplicado com sucesso.")
                st.rerun()

    with aba3:
        st.warning("A exclusão apaga esse lançamento do banco.")

        with st.form(f"form_excluir_{servico_sel['id']}"):
            confirmar = st.checkbox(f'Confirmo excluir o lançamento #{servico_sel["id"]}')
            excluir = st.form_submit_button("Excluir lançamento")

            if excluir:
                if not confirmar:
                    st.error("Marque a confirmação antes de excluir.")
                else:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM servicos WHERE id = ?", (servico_sel["id"],))
                    conn.commit()
                    conn.close()
                    st.success("Lançamento excluído com sucesso.")
                    st.rerun()

    with aba4:
        if servico_sel["status_pagamento"] == "pago":
            st.success("Esse lançamento já está pago.")
            st.write(f'Data do pagamento: {servico_sel["data_pagamento"] or "-"}')
            st.write(f'Forma de pagamento: {servico_sel["forma_pagamento"] or "-"}')
        else:
            st.warning("Esse lançamento está pendente.")
            with st.form(f"form_pagar_{servico_sel['id']}"):
                data_pagamento_ind = st.date_input("Data do pagamento", value=date.today())
                forma_pagamento_ind = st.selectbox("Forma de pagamento", ["pix", "dinheiro", "transferência", "outro"])
                confirmar_pagamento_ind = st.form_submit_button("Marcar lançamento como pago")

                if confirmar_pagamento_ind:
                    marcar_lancamento_como_pago(servico_sel["id"], data_pagamento_ind, forma_pagamento_ind)
                    st.success("Lançamento marcado como pago com sucesso.")
                    st.rerun()
else:
    st.info("Nenhum lançamento salvo ainda.")

st.divider()
st.subheader("Filtros de consulta")

hoje = date.today()
for key, value in {
    "mes_filtro": hoje.month,
    "ano_filtro": hoje.year,
    "status_filtro": "todos",
    "agente_filtro": 0,
    "rota_filtro": 0,
    "placa_filtro": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

if st.button("🧹 Limpar filtros", use_container_width=True):
    st.session_state["mes_filtro"] = hoje.month
    st.session_state["ano_filtro"] = hoje.year
    st.session_state["status_filtro"] = "todos"
    st.session_state["agente_filtro"] = 0
    st.session_state["rota_filtro"] = 0
    st.session_state["placa_filtro"] = ""
    st.rerun()

f1, f2, f3 = st.columns(3)
with f1:
    mes_filtro = st.selectbox("Mês", options=list(range(1, 13)), format_func=lambda x: f"{x:02d}", key="mes_filtro")
with f2:
    ano_filtro = st.number_input("Ano", min_value=2020, max_value=2100, step=1, key="ano_filtro")
with f3:
    status_filtro = st.selectbox("Status do pagamento", options=["todos", "pendente", "pago"], key="status_filtro")

f4, f5, f6 = st.columns(3)
with f4:
    opcoes_agentes = [0] + [a["id"] for a in agentes]
    agente_filtro = st.selectbox("Filtrar por agente", options=opcoes_agentes, format_func=lambda aid: "Todos" if aid == 0 else mapa_agentes[aid]["nome"], key="agente_filtro")
with f5:
    opcoes_rotas = [0] + [r["id"] for r in rotas]
    rota_filtro = st.selectbox("Filtrar por rota", options=opcoes_rotas, format_func=lambda rid: "Todas" if rid == 0 else mapa_rotas[rid]["nome_rota"], key="rota_filtro")
with f6:
    placa_filtro = st.text_input("Buscar por placa", key="placa_filtro")

servicos_filtrados = buscar_servicos_filtrados(
    mes_filtro,
    ano_filtro,
    None if agente_filtro == 0 else agente_filtro,
    None if rota_filtro == 0 else rota_filtro,
    status_filtro,
    placa_filtro
)

st.divider()
st.subheader("Resultados da consulta")

if servicos_filtrados:
    total_registros = len(servicos_filtrados)
    total_pagar_filtro = sum(s["total_pagar"] for s in servicos_filtrados)

    if is_admin():
        total_receber_filtro = sum(s["total_receber"] for s in servicos_filtrados)
        lucro_filtro = sum(s["lucro"] for s in servicos_filtrados)
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Registros", total_registros)
        k2.metric("Total a receber", f"R$ {total_receber_filtro:.2f}")
        k3.metric("Total a pagar", f"R$ {total_pagar_filtro:.2f}")
        k4.metric("Lucro", f"R$ {lucro_filtro:.2f}")
    else:
        k1, k2 = st.columns(2)
        k1.metric("Registros", total_registros)
        k2.metric("Total a pagar", f"R$ {total_pagar_filtro:.2f}")

    dados = []
    for s in servicos_filtrados:
        base = {
            "ID": s["id"],
            "Data": s["data_servico"],
            "Rota": s["nome_rota"],
            "Agente": s["nome_agente"],
            "Placa": s["placa_caminhao"],
            "Hora Inicial": s["hora_inicial"],
            "Hora Final": s["hora_final"],
            "Horas": s["total_horas"],
            "Pago Fixo": f'R$ {s["valor_fixo_pagar"]:.2f}',
            "Total Pagar": f'R$ {s["total_pagar"]:.2f}',
            "Pagamento": texto_status(s["status_pagamento"]),
            "Data Pagamento": s["data_pagamento"],
            "Forma Pagamento": s["forma_pagamento"],
            "Observação": s["observacao"],
        }
        if is_admin():
            base.update({
                "Recebo Fixo": f'R$ {s["valor_fixo_receber"]:.2f}',
                "Extra Recebido": f'R$ {s["valor_extra_recebido"]:.2f}',
                "Pedágio/KM": f'R$ {s["pedagio_km_extra"]:.2f}',
                "Total Receber": f'R$ {s["total_receber"]:.2f}',
                "Lucro": f'R$ {s["lucro"]:.2f}',
            })
        dados.append(base)

    st.dataframe(dados, use_container_width=True, hide_index=True)
    df_exportacao = pd.DataFrame(dados)
    arquivo_excel = gerar_excel_lancamentos(df_exportacao)

    st.download_button(
        label="📥 Baixar consulta filtrada em Excel",
        data=arquivo_excel,
        file_name=f"lancamentos_filtrados_{ano_filtro}_{mes_filtro:02d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
else:
    st.info("Nenhum lançamento encontrado com esses filtros.")
