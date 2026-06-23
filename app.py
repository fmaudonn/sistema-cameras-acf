import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

st.set_page_config(
    page_title="ACF Command | Security Camera Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATABASE_URL = st.secrets["DATABASE_URL"]
engine = create_engine(DATABASE_URL)


def executar_sql(sql, params=None):
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})


def consultar_df(sql, params=None):
    with engine.begin() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def carregar_cameras():
    return consultar_df("""
        SELECT 
            id, numero, operacao, nome_camera, canal, ip_camera, modelo, marca,
            dias_gravacao, nvr, ip_nvr, rack, status, qualidade_gravacao,
            observacao, acao_necessaria, serie_number, ativo, criado_em, atualizado_em
        FROM cameras
        ORDER BY id DESC
    """)


def imagem_para_bytes(uploaded_file):
    if uploaded_file is None:
        return None, None
    return uploaded_file.read(), uploaded_file.name


def cadastrar_camera(dados, foto, foto_nome):
    dados["foto_camera"] = foto
    dados["foto_nome"] = foto_nome

    executar_sql("""
        INSERT INTO cameras (
            numero, operacao, nome_camera, canal, ip_camera, login_camera, senha_camera,
            modelo, marca, inicio_gravacao, termino_gravacao, dias_gravacao,
            nvr, ip_nvr, login_nvr, senha_nvr, rack, status, qualidade_gravacao,
            observacao, horario, acao_necessaria, serie_number, foto_camera, foto_nome,
            ativo, atualizado_em
        )
        VALUES (
            :numero, :operacao, :nome_camera, :canal, :ip_camera, :login_camera, :senha_camera,
            :modelo, :marca, :inicio_gravacao, :termino_gravacao, :dias_gravacao,
            :nvr, :ip_nvr, :login_nvr, :senha_nvr, :rack, :status, :qualidade_gravacao,
            :observacao, :horario, :acao_necessaria, :serie_number, :foto_camera, :foto_nome,
            TRUE, CURRENT_TIMESTAMP
        )
    """, dados)


def atualizar_status(camera_id, status, qualidade, observacao, acao):
    executar_sql("""
        UPDATE cameras
        SET status = :status,
            qualidade_gravacao = :qualidade,
            observacao = :observacao,
            acao_necessaria = :acao,
            atualizado_em = CURRENT_TIMESTAMP
        WHERE id = :id
    """, {
        "id": camera_id,
        "status": status,
        "qualidade": qualidade,
        "observacao": observacao,
        "acao": acao
    })


def desativar_camera(camera_id):
    executar_sql("""
        UPDATE cameras
        SET ativo = FALSE,
            status = 'INATIVA',
            atualizado_em = CURRENT_TIMESTAMP
        WHERE id = :id
    """, {"id": camera_id})


def reativar_camera(camera_id):
    executar_sql("""
        UPDATE cameras
        SET ativo = TRUE,
            status = 'ATIVA',
            atualizado_em = CURRENT_TIMESTAMP
        WHERE id = :id
    """, {"id": camera_id})


def excluir_camera(camera_id):
    executar_sql("DELETE FROM cameras WHERE id = :id", {"id": camera_id})


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&display=swap');

html, body, [class*="css"] {
    font-family: 'Rajdhani', sans-serif !important;
}

.stApp {
    background:
        linear-gradient(rgba(0, 8, 12, .88), rgba(0, 8, 12, .95)),
        repeating-linear-gradient(
            0deg,
            rgba(0,255,180,.025) 0px,
            rgba(0,255,180,.025) 1px,
            transparent 1px,
            transparent 4px
        ),
        radial-gradient(circle at 20% 0%, rgba(255, 204, 0, .12), transparent 25%),
        radial-gradient(circle at 90% 10%, rgba(0, 229, 255, .14), transparent 30%),
        linear-gradient(135deg, #020506 0%, #071115 45%, #010203 100%);
    color: #d7faff;
}

.block-container {
    padding-top: 1.2rem;
    padding-left: 1.4rem;
    padding-right: 1.4rem;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #05090b 0%, #071215 60%, #020304 100%);
    border-right: 1px solid rgba(255, 204, 0, .45);
    box-shadow: 8px 0 30px rgba(0,0,0,.55);
}

section[data-testid="stSidebar"] * {
    color: #d7faff !important;
}

h1, h2, h3 {
    font-family: 'Rajdhani', sans-serif !important;
    text-transform: uppercase;
    letter-spacing: .06em;
    color: #f4fbff !important;
}

.command-header {
    border: 1px solid rgba(255, 204, 0, .6);
    background: linear-gradient(135deg, rgba(255,204,0,.13), rgba(0,229,255,.04));
    padding: 20px 26px;
    margin-bottom: 18px;
    position: relative;
    box-shadow: 0 0 35px rgba(255,204,0,.13), inset 0 0 35px rgba(0,229,255,.04);
}

.command-header:before,
.command-header:after {
    content: "";
    position: absolute;
    width: 42px;
    height: 42px;
    border-color: #ffcc00;
    border-style: solid;
}

.command-header:before {
    top: -1px;
    left: -1px;
    border-width: 2px 0 0 2px;
}

.command-header:after {
    right: -1px;
    bottom: -1px;
    border-width: 0 2px 2px 0;
}

.command-title {
    font-size: 34px;
    font-weight: 800;
    color: #ffcc00;
    line-height: 1;
}

.command-subtitle {
    color: #9fb7bd;
    font-family: 'Share Tech Mono', monospace;
    margin-top: 6px;
    font-size: 14px;
}

.system-online {
    color: #24ff6d;
    font-family: 'Share Tech Mono', monospace;
    text-align: right;
    font-size: 15px;
}

.kpi-card {
    min-height: 118px;
    padding: 18px;
    border: 1px solid rgba(100, 255, 230, .25);
    background:
        linear-gradient(135deg, rgba(255,255,255,.06), rgba(255,255,255,.015)),
        radial-gradient(circle at top right, rgba(0,229,255,.10), transparent 38%);
    box-shadow:
        0 0 24px rgba(0, 229, 255, .08),
        inset 0 0 22px rgba(0, 229, 255, .025);
    position: relative;
}

.kpi-card:before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 38px;
    height: 3px;
    background: #ffcc00;
}

.kpi-label {
    color: #a8bec4;
    font-size: 13px;
    font-family: 'Share Tech Mono', monospace;
    text-transform: uppercase;
}

.kpi-value {
    font-size: 40px;
    font-weight: 800;
    color: #24ff6d;
    line-height: 1.1;
}

.kpi-value-yellow { color: #ffcc00; }
.kpi-value-red { color: #ff3b30; }
.kpi-value-cyan { color: #00e5ff; }

.kpi-caption {
    font-family: 'Share Tech Mono', monospace;
    color: #7f9298;
    font-size: 12px;
}

.hud-panel {
    border: 1px solid rgba(100,255,230,.25);
    background: rgba(3, 12, 15, .78);
    box-shadow:
        0 0 28px rgba(0,229,255,.07),
        inset 0 0 35px rgba(0,229,255,.025);
    padding: 16px;
    margin-bottom: 14px;
}

.hud-title {
    font-family: 'Share Tech Mono', monospace;
    text-transform: uppercase;
    color: #f4fbff;
    font-size: 15px;
    margin-bottom: 10px;
    border-left: 3px solid #ffcc00;
    padding-left: 10px;
}

.alert-box {
    border-left: 3px solid #ff3b30;
    background: rgba(255,59,48,.08);
    padding: 10px 12px;
    margin-bottom: 8px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 12px;
}

.ok-dot {
    height: 9px;
    width: 9px;
    background: #24ff6d;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 10px #24ff6d;
}

.bad-dot {
    height: 9px;
    width: 9px;
    background: #ff3b30;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 10px #ff3b30;
}

.warn-dot {
    height: 9px;
    width: 9px;
    background: #ffcc00;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 10px #ffcc00;
}

.stButton button, .stDownloadButton button {
    background: linear-gradient(90deg, #ffcc00, #d99b00) !important;
    color: #020506 !important;
    border: 1px solid rgba(255,204,0,.9) !important;
    border-radius: 0 !important;
    font-weight: 800 !important;
    text-transform: uppercase;
    letter-spacing: .06em;
}

[data-testid="stDataFrame"] {
    border: 1px solid rgba(100,255,230,.25);
    box-shadow: 0 0 25px rgba(0,229,255,.07);
}

input, textarea, select {
    background-color: rgba(0,0,0,.35) !important;
    color: #d7faff !important;
    border: 1px solid rgba(100,255,230,.30) !important;
    border-radius: 0 !important;
}

div[data-baseweb="select"] > div {
    background-color: rgba(0,0,0,.35) !important;
    border: 1px solid rgba(100,255,230,.30) !important;
    border-radius: 0 !important;
}

hr {
    border-color: rgba(100,255,230,.18);
}
</style>
""", unsafe_allow_html=True)


df = carregar_cameras()

total = len(df)
ativas = len(df[(df["ativo"] == True) & (df["status"].fillna("").str.upper() == "ATIVA")]) if not df.empty else 0
inativas = len(df[df["ativo"] == False]) if not df.empty else 0
manutencao = len(df[df["acao_necessaria"].fillna("").str.len() > 0]) if not df.empty else 0
nvrs = df["nvr"].nunique() if not df.empty else 0
disponibilidade = round((ativas / total) * 100, 1) if total > 0 else 0

colh1, colh2 = st.columns([3, 1])
with colh1:
    st.markdown("""
    <div class="command-header">
        <div class="command-title">ACF COMMAND | SECURITY CAMERA CENTER</div>
        <div class="command-subtitle">SISTEMA DE GESTÃO DE CÂMERAS • ACF EXTREMA • MONITORAMENTO OPERACIONAL</div>
    </div>
    """, unsafe_allow_html=True)

with colh2:
    st.markdown("""
    <div class="command-header">
        <div class="system-online">● SISTEMA ONLINE<br>STATUS: OPERACIONAL</div>
    </div>
    """, unsafe_allow_html=True)

menu = st.sidebar.radio(
    "NAVEGAÇÃO",
    [
        "Dashboard",
        "Inventário",
        "Cadastrar Câmera",
        "Atualizar Status",
        "Desativar / Excluir"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### OPERAÇÕES")
if not df.empty:
    ops = df.groupby("operacao", dropna=False).size().reset_index(name="total")
    for _, row in ops.iterrows():
        st.sidebar.markdown(f"<span class='ok-dot'></span> {row['operacao']} — {row['total']} câmeras", unsafe_allow_html=True)
else:
    st.sidebar.info("Sem operações cadastradas.")

st.sidebar.markdown("---")
st.sidebar.markdown("### ALERTAS CRÍTICOS")
if manutencao > 0:
    st.sidebar.markdown(f"<div class='alert-box'>▲ {manutencao} câmera(s) com ação necessária</div>", unsafe_allow_html=True)
else:
    st.sidebar.markdown("<span class='ok-dot'></span> Sem alertas críticos", unsafe_allow_html=True)


if menu == "Dashboard":
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Total Câmeras</div>
        <div class="kpi-value kpi-value-yellow">{total}</div>
        <div class="kpi-caption">100% do parque</div>
    </div>
    """, unsafe_allow_html=True)

    c2.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Ativas</div>
        <div class="kpi-value">{ativas}</div>
        <div class="kpi-caption">em operação</div>
    </div>
    """, unsafe_allow_html=True)

    c3.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Inativas</div>
        <div class="kpi-value kpi-value-red">{inativas}</div>
        <div class="kpi-caption">fora de operação</div>
    </div>
    """, unsafe_allow_html=True)

    c4.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Manutenção</div>
        <div class="kpi-value kpi-value-yellow">{manutencao}</div>
        <div class="kpi-caption">ação necessária</div>
    </div>
    """, unsafe_allow_html=True)

    c5.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">NVRs</div>
        <div class="kpi-value kpi-value-cyan">{nvrs}</div>
        <div class="kpi-caption">gravadores</div>
    </div>
    """, unsafe_allow_html=True)

    c6.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Disponibilidade</div>
        <div class="kpi-value">{disponibilidade}%</div>
        <div class="kpi-caption">base operacional</div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    if df.empty:
        st.info("Nenhuma câmera cadastrada ainda.")
    else:
        col1, col2, col3 = st.columns([1, 1.15, 1])

        template = "plotly_dark"

        with col1:
            st.markdown("<div class='hud-panel'><div class='hud-title'>Distribuição por Status</div>", unsafe_allow_html=True)
            fig = px.pie(
                df,
                names="status",
                hole=0.62,
                template=template
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#d7faff",
                margin=dict(l=10, r=10, t=10, b=10),
                height=360
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='hud-panel'><div class='hud-title'>Câmeras por Operação</div>", unsafe_allow_html=True)
            operacao_df = df.groupby("operacao", dropna=False).size().reset_index(name="total")
            fig2 = px.bar(
                operacao_df,
                x="total",
                y="operacao",
                orientation="h",
                text="total",
                template=template
            )
            fig2.update_traces(textposition="outside")
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,20,24,.25)",
                font_color="#d7faff",
                margin=dict(l=10, r=10, t=10, b=10),
                height=360
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            st.markdown("<div class='hud-panel'><div class='hud-title'>Carga por NVR</div>", unsafe_allow_html=True)
            nvr_df = df.groupby("nvr", dropna=False).size().reset_index(name="total")
            fig3 = px.bar(
                nvr_df,
                x="total",
                y="nvr",
                orientation="h",
                text="total",
                template=template
            )
            fig3.update_traces(textposition="outside")
            fig3.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,20,24,.25)",
                font_color="#d7faff",
                margin=dict(l=10, r=10, t=10, b=10),
                height=360
            )
            st.plotly_chart(fig3, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        col4, col5 = st.columns([1.25, 1])

        with col4:
            st.markdown("<div class='hud-panel'><div class='hud-title'>Inventário Operacional</div>", unsafe_allow_html=True)
            st.dataframe(
                df[["id", "operacao", "nome_camera", "ip_camera", "nvr", "status", "qualidade_gravacao", "ativo"]],
                use_container_width=True,
                hide_index=True
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with col5:
            st.markdown("<div class='hud-panel'><div class='hud-title'>Qualidade de Gravação</div>", unsafe_allow_html=True)
            qualidade_df = df.groupby("qualidade_gravacao", dropna=False).size().reset_index(name="total")
            fig4 = px.pie(
                qualidade_df,
                names="qualidade_gravacao",
                values="total",
                hole=0.62,
                template=template
            )
            fig4.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#d7faff",
                margin=dict(l=10, r=10, t=10, b=10),
                height=360
            )
            st.plotly_chart(fig4, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)


elif menu == "Inventário":
    st.markdown("<div class='hud-panel'><div class='hud-title'>Inventário de Câmeras</div>", unsafe_allow_html=True)

    if df.empty:
        st.warning("Nenhuma câmera cadastrada.")
    else:
        col1, col2, col3 = st.columns(3)
        filtro_operacao = col1.text_input("Operação")
        filtro_status = col2.selectbox("Status", ["Todos"] + sorted(df["status"].dropna().unique().tolist()))
        filtro_ativo = col3.selectbox("Situação", ["Todas", "Ativas", "Inativas"])

        df_filtro = df.copy()

        if filtro_operacao:
            df_filtro = df_filtro[df_filtro["operacao"].fillna("").str.contains(filtro_operacao, case=False)]

        if filtro_status != "Todos":
            df_filtro = df_filtro[df_filtro["status"] == filtro_status]

        if filtro_ativo == "Ativas":
            df_filtro = df_filtro[df_filtro["ativo"] == True]
        elif filtro_ativo == "Inativas":
            df_filtro = df_filtro[df_filtro["ativo"] == False]

        st.dataframe(df_filtro, use_container_width=True, hide_index=True)

        df_filtro.to_excel("inventario_cameras.xlsx", index=False)
        with open("inventario_cameras.xlsx", "rb") as file:
            st.download_button("Baixar inventário em Excel", file, file_name="inventario_cameras.xlsx")

    st.markdown("</div>", unsafe_allow_html=True)


elif menu == "Cadastrar Câmera":
    st.markdown("<div class='hud-panel'><div class='hud-title'>Cadastrar Nova Câmera</div>", unsafe_allow_html=True)

    with st.form("cadastro"):
        col1, col2, col3 = st.columns(3)
        numero = col1.number_input("Nº", min_value=0, step=1)
        operacao = col2.text_input("Operação")
        nome_camera = col3.text_input("Nome da câmera")

        col4, col5, col6 = st.columns(3)
        canal = col4.text_input("Canal")
        ip_camera = col5.text_input("IP da câmera")
        rack = col6.text_input("Rack")

        col7, col8, col9 = st.columns(3)
        login_camera = col7.text_input("Login câmera")
        senha_camera = col8.text_input("Senha câmera", type="password")
        serie_number = col9.text_input("Série Number")

        col10, col11, col12 = st.columns(3)
        modelo = col10.text_input("Modelo")
        marca = col11.text_input("Marca")
        dias_gravacao = col12.number_input("Dias de gravação", min_value=0, step=1)

        col13, col14, col15 = st.columns(3)
        inicio_gravacao = col13.date_input("Início gravação")
        termino_gravacao = col14.date_input("Término gravação")
        horario = col15.text_input("Horário")

        col16, col17, col18 = st.columns(3)
        nvr = col16.text_input("NVR")
        ip_nvr = col17.text_input("IP NVR")
        login_nvr = col18.text_input("Login NVR")

        col19, col20 = st.columns(2)
        senha_nvr = col19.text_input("Senha NVR", type="password")
        status = col20.selectbox("Status", ["ATIVA", "INATIVA", "MANUTENÇÃO", "FALHA", "SEM GRAVAÇÃO"])

        qualidade_gravacao = st.selectbox(
            "Qualidade da gravação",
            ["BOA", "REGULAR", "RUIM", "SEM IMAGEM", "SEM GRAVAÇÃO"]
        )

        observacao = st.text_area("Observação")
        acao_necessaria = st.text_area("Ação necessária")
        foto_upload = st.file_uploader("Foto / imagem da câmera", type=["png", "jpg", "jpeg"])

        salvar = st.form_submit_button("Cadastrar câmera")

        if salvar:
            if not nome_camera:
                st.error("Informe o nome da câmera.")
            else:
                foto_bytes, foto_nome = imagem_para_bytes(foto_upload)

                dados = {
                    "numero": numero,
                    "operacao": operacao,
                    "nome_camera": nome_camera,
                    "canal": canal,
                    "ip_camera": ip_camera,
                    "login_camera": login_camera,
                    "senha_camera": senha_camera,
                    "modelo": modelo,
                    "marca": marca,
                    "inicio_gravacao": inicio_gravacao,
                    "termino_gravacao": termino_gravacao,
                    "dias_gravacao": dias_gravacao,
                    "nvr": nvr,
                    "ip_nvr": ip_nvr,
                    "login_nvr": login_nvr,
                    "senha_nvr": senha_nvr,
                    "rack": rack,
                    "status": status,
                    "qualidade_gravacao": qualidade_gravacao,
                    "observacao": observacao,
                    "horario": horario,
                    "acao_necessaria": acao_necessaria,
                    "serie_number": serie_number
                }

                cadastrar_camera(dados, foto_bytes, foto_nome)
                st.success("Câmera cadastrada com sucesso.")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


elif menu == "Atualizar Status":
    st.markdown("<div class='hud-panel'><div class='hud-title'>Atualizar Status Operacional</div>", unsafe_allow_html=True)

    if df.empty:
        st.warning("Nenhuma câmera cadastrada.")
    else:
        camera_id = st.selectbox(
            "Selecione a câmera",
            df["id"].tolist(),
            format_func=lambda x: f'{x} - {df[df["id"] == x]["nome_camera"].iloc[0]}'
        )

        status = st.selectbox("Novo status", ["ATIVA", "INATIVA", "MANUTENÇÃO", "FALHA", "SEM GRAVAÇÃO"])
        qualidade = st.selectbox("Qualidade", ["BOA", "REGULAR", "RUIM", "SEM IMAGEM", "SEM GRAVAÇÃO"])
        observacao = st.text_area("Observação")
        acao = st.text_area("Ação necessária")

        if st.button("Atualizar"):
            atualizar_status(camera_id, status, qualidade, observacao, acao)
            st.success("Status atualizado.")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


elif menu == "Desativar / Excluir":
    st.markdown("<div class='hud-panel'><div class='hud-title'>Desativar ou Excluir Câmera</div>", unsafe_allow_html=True)

    if df.empty:
        st.warning("Nenhuma câmera cadastrada.")
    else:
        camera_id = st.selectbox(
            "Selecione a câmera",
            df["id"].tolist(),
            format_func=lambda x: f'{x} - {df[df["id"] == x]["nome_camera"].iloc[0]}'
        )

        col1, col2, col3 = st.columns(3)

        if col1.button("Desativar mantendo histórico"):
            desativar_camera(camera_id)
            st.success("Câmera desativada.")
            st.rerun()

        if col2.button("Reativar câmera"):
            reativar_camera(camera_id)
            st.success("Câmera reativada.")
            st.rerun()

        if col3.button("Excluir definitivamente"):
            excluir_camera(camera_id)
            st.error("Câmera excluída definitivamente.")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
