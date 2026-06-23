import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from sqlalchemy import create_engine, text
from datetime import datetime

st.set_page_config(
    page_title="ACF Command HUD v3",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DATABASE_URL = st.secrets["DATABASE_URL"]
engine = create_engine(DATABASE_URL)


def consultar_df(sql, params=None):
    with engine.begin() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def executar_sql(sql, params=None):
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})


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
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@400;600;700&family=Share+Tech+Mono&display=swap');

:root {
    --bg: #010509;
    --panel: rgba(3, 13, 18, .86);
    --cyan: #00f6ff;
    --green: #23ff6d;
    --yellow: #ffd000;
    --red: #ff3131;
    --muted: #8faab0;
}

html, body, [class*="css"] {
    font-family: 'Rajdhani', sans-serif !important;
}

.stApp {
    background:
        linear-gradient(rgba(0,0,0,.68), rgba(0,0,0,.92)),
        radial-gradient(circle at 20% 5%, rgba(0,246,255,.20), transparent 28%),
        radial-gradient(circle at 80% 0%, rgba(255,208,0,.14), transparent 22%),
        radial-gradient(circle at 50% 100%, rgba(35,255,109,.09), transparent 35%),
        repeating-linear-gradient(0deg, rgba(0,246,255,.035) 0px, rgba(0,246,255,.035) 1px, transparent 1px, transparent 5px),
        #010509;
    color: #e6fdff;
}

.stApp:before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 9999;
    background: linear-gradient(
        to bottom,
        transparent 0%,
        rgba(0,246,255,.10) 50%,
        transparent 100%
    );
    height: 120px;
    animation: globalScan 5s linear infinite;
    mix-blend-mode: screen;
}

.stApp:after {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 9998;
    background-image:
        linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px);
    background-size: 42px 42px;
    opacity: .45;
}

#MainMenu, footer, header {
    visibility: hidden;
}

.block-container {
    padding: .6rem 1rem 1rem 1rem;
    max-width: 100% !important;
}

.topbar {
    display: grid;
    grid-template-columns: 1fr 370px 210px;
    gap: 12px;
    margin-bottom: 12px;
}

.panel,
.title-panel,
.status-panel,
.clock-panel,
.kpi-card,
.forms-panel {
    position: relative;
    border: 1px solid rgba(0,246,255,.35);
    background: linear-gradient(135deg, rgba(4,17,22,.92), rgba(1,7,10,.88));
    box-shadow:
        0 0 28px rgba(0,246,255,.08),
        inset 0 0 24px rgba(0,246,255,.035);
    overflow: hidden;
}

.panel:before,
.title-panel:before,
.status-panel:before,
.clock-panel:before,
.kpi-card:before,
.forms-panel:before {
    content: "";
    position: absolute;
    top: 0;
    left: -40%;
    width: 40%;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--cyan), transparent);
    animation: borderRun 3.5s linear infinite;
}

.panel:after,
.title-panel:after,
.status-panel:after,
.clock-panel:after,
.kpi-card:after,
.forms-panel:after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(120deg, transparent 30%, rgba(255,255,255,.045), transparent 70%);
    transform: translateX(-120%);
    animation: lightSweep 7s infinite;
    pointer-events: none;
}

.title-panel {
    padding: 16px 22px;
    clip-path: polygon(0 0, 96% 0, 100% 28%, 100% 100%, 0 100%);
}

.status-panel,
.clock-panel {
    padding: 15px 20px;
}

.big-title {
    font-family: 'Orbitron', sans-serif;
    color: var(--yellow);
    font-size: 28px;
    font-weight: 900;
    letter-spacing: .04em;
    text-shadow: 0 0 18px rgba(255,208,0,.24);
    animation: titlePulse 2.8s infinite alternate;
}

.subtitle {
    font-family: 'Share Tech Mono', monospace;
    color: #9eb9bf;
    font-size: 12px;
    margin-top: 4px;
}

.online {
    font-family: 'Share Tech Mono', monospace;
    color: var(--green);
    font-size: 14px;
    text-shadow: 0 0 14px rgba(35,255,109,.45);
}

.heartbeat {
    height: 34px;
    margin-top: 8px;
    background:
        linear-gradient(90deg, transparent, rgba(35,255,109,.10), transparent),
        repeating-linear-gradient(90deg, transparent 0 18px, rgba(35,255,109,.18) 19px);
    position: relative;
}

.heartbeat:after {
    content: "";
    position: absolute;
    left: 0;
    top: 16px;
    width: 100%;
    height: 2px;
    background: var(--green);
    clip-path: polygon(0 50%, 10% 50%, 14% 10%, 19% 90%, 23% 50%, 35% 50%, 39% 20%, 43% 78%, 47% 50%, 100% 50%);
    animation: beat 1.4s infinite linear;
}

.clock-main {
    font-family: 'Share Tech Mono', monospace;
    color: #fff;
    font-size: 18px;
}

.clock-sub {
    font-family: 'Share Tech Mono', monospace;
    color: #91a9ae;
    font-size: 12px;
}

.nav-grid {
    display: grid;
    grid-template-columns: 240px 1fr;
    gap: 12px;
}

.left-rail {
    border: 1px solid rgba(0,246,255,.35);
    background: rgba(1,8,11,.88);
    padding: 13px;
    min-height: 86vh;
    box-shadow: 0 0 28px rgba(0,246,255,.08);
}

.logo-main {
    font-family: 'Orbitron', sans-serif;
    font-size: 25px;
    font-weight: 900;
    color: var(--yellow);
}

.logo-sub {
    font-family: 'Share Tech Mono', monospace;
    font-size: 12px;
    color: #dffcff;
}

.side-title {
    font-family: 'Share Tech Mono', monospace;
    color: #9ec8ce;
    font-size: 12px;
    margin-top: 18px;
    margin-bottom: 8px;
}

.side-row {
    font-family: 'Share Tech Mono', monospace;
    font-size: 12px;
    padding: 7px 0;
    border-bottom: 1px solid rgba(255,255,255,.06);
    display: flex;
    justify-content: space-between;
}

.dot-green,
.dot-red,
.dot-yellow,
.dot-cyan {
    width: 9px;
    height: 9px;
    display: inline-block;
    border-radius: 50%;
    margin-right: 6px;
}

.dot-green { background: var(--green); box-shadow: 0 0 12px var(--green); }
.dot-red { background: var(--red); box-shadow: 0 0 12px var(--red); }
.dot-yellow { background: var(--yellow); box-shadow: 0 0 12px var(--yellow); }
.dot-cyan { background: var(--cyan); box-shadow: 0 0 12px var(--cyan); }

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 12px;
    margin-bottom: 12px;
}

.kpi-card {
    min-height: 110px;
    padding: 14px;
}

.kpi-label {
    font-family: 'Share Tech Mono', monospace;
    color: #9db5bb;
    font-size: 11px;
    text-transform: uppercase;
}

.kpi-value {
    font-family: 'Orbitron', sans-serif;
    font-size: 30px;
    font-weight: 900;
    color: var(--green);
    margin-top: 6px;
}

.kpi-yellow { color: var(--yellow); }
.kpi-red { color: var(--red); }
.kpi-cyan { color: var(--cyan); }

.kpi-mini {
    font-family: 'Share Tech Mono', monospace;
    color: #788f94;
    font-size: 11px;
}

.dashboard-row {
    display: grid;
    grid-template-columns: 1fr 1.15fr .9fr 1fr;
    gap: 12px;
    margin-bottom: 12px;
}

.dashboard-row-2 {
    display: grid;
    grid-template-columns: 1.1fr 1.9fr;
    gap: 12px;
    margin-bottom: 12px;
}

.dashboard-row-3 {
    display: grid;
    grid-template-columns: 1.2fr 1fr .9fr;
    gap: 12px;
}

.panel {
    padding: 13px;
    min-height: 285px;
}

.panel-title {
    font-family: 'Share Tech Mono', monospace;
    color: #e6fdff;
    font-size: 14px;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.fake-map {
    height: 300px;
    border: 1px solid rgba(0,246,255,.25);
    background:
        radial-gradient(circle at 25% 52%, rgba(35,255,109,.42), transparent 5%),
        radial-gradient(circle at 48% 42%, rgba(255,208,0,.40), transparent 5%),
        radial-gradient(circle at 73% 58%, rgba(35,255,109,.35), transparent 5%),
        radial-gradient(circle at 80% 28%, rgba(0,246,255,.30), transparent 4%),
        repeating-linear-gradient(35deg, transparent 0 18px, rgba(0,246,255,.08) 19px),
        linear-gradient(135deg, #041116, #010609);
    position: relative;
    overflow: hidden;
}

.fake-map:before {
    content: "";
    position: absolute;
    inset: -40%;
    background:
        linear-gradient(90deg, transparent 48%, rgba(0,246,255,.25) 50%, transparent 52%),
        linear-gradient(0deg, transparent 48%, rgba(0,246,255,.22) 50%, transparent 52%);
    animation: mapGridMove 8s linear infinite;
}

.fake-map:after {
    content: "";
    position: absolute;
    left: -30%;
    top: -20%;
    width: 160%;
    height: 2px;
    background: linear-gradient(90deg, transparent, rgba(0,246,255,.65), transparent);
    animation: mapSweep 3.5s linear infinite;
}

.node {
    position: absolute;
    z-index: 2;
    border: 1px solid rgba(35,255,109,.8);
    background: rgba(0,0,0,.66);
    color: #caffd8;
    font-family: 'Share Tech Mono', monospace;
    font-size: 12px;
    padding: 7px 9px;
    box-shadow: 0 0 20px rgba(35,255,109,.28);
    animation: nodePulse 2.2s infinite alternate;
}

.radar {
    width: 210px;
    height: 210px;
    margin: 20px auto;
    border-radius: 50%;
    border: 1px solid rgba(0,246,255,.42);
    background:
        radial-gradient(circle, rgba(0,246,255,.08) 0 8%, transparent 9% 24%, rgba(0,246,255,.07) 25% 26%, transparent 27% 48%, rgba(0,246,255,.07) 49% 50%, transparent 51%),
        conic-gradient(from 0deg, rgba(0,246,255,.48), transparent 48deg, transparent 360deg);
    position: relative;
    animation: radarSpin 3s linear infinite;
    box-shadow: 0 0 30px rgba(0,246,255,.18);
}

.radar:after {
    content: "";
    position: absolute;
    inset: 48%;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 18px var(--green);
}

.feed-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 9px;
}

.camera-feed {
    height: 118px;
    border: 1px solid rgba(0,246,255,.28);
    background:
        linear-gradient(rgba(0,0,0,.10), rgba(0,0,0,.72)),
        repeating-linear-gradient(90deg, rgba(255,255,255,.055) 0px, rgba(255,255,255,.055) 1px, transparent 1px, transparent 7px),
        radial-gradient(circle at center, rgba(180,205,215,.25), transparent 72%),
        #121c22;
    position: relative;
    overflow: hidden;
}

.camera-feed:before {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(120deg, transparent, rgba(255,255,255,.20), transparent);
    transform: translateX(-130%);
    animation: cameraSweep 4s infinite;
}

.camera-feed:after {
    content: "LIVE";
    position: absolute;
    top: 6px;
    right: 7px;
    font-family: 'Share Tech Mono', monospace;
    color: var(--green);
    font-size: 10px;
}

.feed-label {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 5px 7px;
    background: rgba(0,0,0,.78);
    color: #e6fdff;
    font-family: 'Share Tech Mono', monospace;
    font-size: 10px;
}

.log-line {
    font-family: 'Share Tech Mono', monospace;
    font-size: 12px;
    padding: 5px 0;
    border-bottom: 1px solid rgba(255,255,255,.06);
}

.progress-bar {
    height: 9px;
    background: rgba(255,255,255,.10);
    margin-top: 8px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--green), var(--cyan));
    box-shadow: 0 0 14px rgba(0,246,255,.55);
    animation: progressGlow 1.5s infinite alternate;
}

.forms-panel {
    padding: 18px;
}

.stButton button,
.stDownloadButton button {
    background: linear-gradient(90deg, var(--yellow), #b88a00) !important;
    color: #010509 !important;
    border: 0 !important;
    border-radius: 0 !important;
    font-family: 'Share Tech Mono', monospace !important;
    text-transform: uppercase;
    font-weight: 900 !important;
}

input,
textarea {
    background: rgba(0,0,0,.48) !important;
    color: #e6fdff !important;
    border: 1px solid rgba(0,246,255,.36) !important;
    border-radius: 0 !important;
}

div[data-baseweb="select"] > div {
    background: rgba(0,0,0,.48) !important;
    color: #e6fdff !important;
    border: 1px solid rgba(0,246,255,.36) !important;
    border-radius: 0 !important;
}

@keyframes globalScan {
    0% { transform: translateY(-140px); opacity: .15; }
    50% { opacity: .55; }
    100% { transform: translateY(110vh); opacity: .10; }
}

@keyframes borderRun {
    0% { left: -40%; opacity: .2; }
    50% { opacity: 1; }
    100% { left: 120%; opacity: .2; }
}

@keyframes lightSweep {
    0% { transform: translateX(-130%); }
    40% { transform: translateX(130%); }
    100% { transform: translateX(130%); }
}

@keyframes titlePulse {
    from { text-shadow: 0 0 12px rgba(255,208,0,.20); }
    to { text-shadow: 0 0 26px rgba(255,208,0,.45); }
}

@keyframes beat {
    0% { transform: translateX(-18%); opacity: .45; }
    50% { opacity: 1; }
    100% { transform: translateX(18%); opacity: .55; }
}

@keyframes mapSweep {
    from { transform: translateY(-80px); }
    to { transform: translateY(440px); }
}

@keyframes mapGridMove {
    from { transform: translate(0,0); }
    to { transform: translate(80px,80px); }
}

@keyframes nodePulse {
    from { transform: scale(1); }
    to { transform: scale(1.04); }
}

@keyframes radarSpin {
    to { transform: rotate(360deg); }
}

@keyframes cameraSweep {
    0% { transform: translateX(-130%); }
    45% { transform: translateX(130%); }
    100% { transform: translateX(130%); }
}

@keyframes progressGlow {
    from { filter: brightness(1); }
    to { filter: brightness(1.45); }
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

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


def nav(label):
    if st.sidebar.button(label, use_container_width=True):
        st.session_state.page = label
        st.rerun()


with st.sidebar:
    st.markdown("<div class='logo-main'>ACF COMMAND</div><div class='logo-sub'>CONTROL SYSTEM</div>", unsafe_allow_html=True)
    st.markdown("<div class='side-title'>NAVEGAÇÃO</div>", unsafe_allow_html=True)
    nav("Dashboard")
    nav("Inventário")
    nav("Cadastrar Câmera")
    nav("Atualizar Status")
    nav("Desativar / Excluir")

    st.markdown("<div class='side-title'>OPERAÇÕES</div>", unsafe_allow_html=True)
    if not df.empty:
        ops = df.groupby("operacao", dropna=False).size().reset_index(name="total")
        for _, row in ops.iterrows():
            st.markdown(f"<div class='side-row'><span><span class='dot-green'></span>{row['operacao']}</span><span>{row['total']}</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='side-row'>SEM DADOS</div>", unsafe_allow_html=True)

    st.markdown("<div class='side-title'>ALERTAS</div>", unsafe_allow_html=True)
    if manutencao:
        st.markdown(f"<div class='side-row'><span><span class='dot-red'></span>AÇÕES PENDENTES</span><span>{manutencao}</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='side-row'><span><span class='dot-green'></span>SEM ALERTAS</span><span>OK</span></div>", unsafe_allow_html=True)


hora = datetime.now().strftime("%H:%M:%S")
data = datetime.now().strftime("%d/%m/%Y")

st.markdown(f"""
<div class="topbar">
    <div class="title-panel">
        <div class="big-title">ACF COMMAND | SECURITY CAMERA CENTER</div>
        <div class="subtitle">SISTEMA DE GESTÃO DE CÂMERAS • ACF EXTREMA • MONITORAMENTO CINEMÁTICO</div>
    </div>
    <div class="status-panel">
        <div class="online">● SISTEMA ONLINE</div>
        <div class="online">STATUS: OPERACIONAL</div>
        <div class="heartbeat"></div>
    </div>
    <div class="clock-panel">
        <div class="clock-main">{hora}</div>
        <div class="clock-sub">{data}</div>
        <div class="clock-sub">ACF EXTREMA</div>
    </div>
</div>
""", unsafe_allow_html=True)


def donut(labels, values):
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.70,
        textinfo="none",
        marker=dict(colors=["#23ff6d", "#ff3131", "#ffd000", "#00f6ff", "#8faab0"])
    )])
    fig.update_layout(
        height=245,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e6fdff")
    )
    return fig


def bar(df_bar, x, y):
    fig = px.bar(
        df_bar,
        x=x,
        y=y,
        orientation="h",
        text=x,
        color_discrete_sequence=["#00c9bd"]
    )
    fig.update_layout(
        height=245,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,246,255,.035)",
        font=dict(color="#e6fdff"),
        xaxis=dict(gridcolor="rgba(0,246,255,.08)"),
        yaxis=dict(gridcolor="rgba(0,246,255,.04)")
    )
    return fig


if st.session_state.page == "Dashboard":
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card"><div class="kpi-label">Total Câmeras</div><div class="kpi-value kpi-yellow">{total}</div><div class="kpi-mini">100% do parque</div></div>
        <div class="kpi-card"><div class="kpi-label">Ativas</div><div class="kpi-value">{ativas}</div><div class="kpi-mini">em operação</div></div>
        <div class="kpi-card"><div class="kpi-label">Inativas</div><div class="kpi-value kpi-red">{inativas}</div><div class="kpi-mini">fora de operação</div></div>
        <div class="kpi-card"><div class="kpi-label">Manutenção</div><div class="kpi-value kpi-yellow">{manutencao}</div><div class="kpi-mini">ação necessária</div></div>
        <div class="kpi-card"><div class="kpi-label">NVRs Online</div><div class="kpi-value kpi-cyan">{nvrs}</div><div class="kpi-mini">gravadores</div></div>
        <div class="kpi-card"><div class="kpi-label">Disponibilidade</div><div class="kpi-value">{disponibilidade}%</div><div class="kpi-mini">sistema</div></div>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.warning("Nenhuma câmera cadastrada.")
    else:
        c1, c2, c3, c4 = st.columns([1, 1.15, .9, 1])

        with c1:
            st.markdown("<div class='panel'><div class='panel-title'>Distribuição por Status</div>", unsafe_allow_html=True)
            status_df = df.groupby("status", dropna=False).size().reset_index(name="total")
            st.plotly_chart(donut(status_df["status"], status_df["total"]), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='panel'><div class='panel-title'>Câmeras por Operação</div>", unsafe_allow_html=True)
            op_df = df.groupby("operacao", dropna=False).size().reset_index(name="total").sort_values("total")
            st.plotly_chart(bar(op_df, "total", "operacao"), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c3:
            st.markdown("<div class='panel'><div class='panel-title'>Radar Operacional</div><div class='radar'></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c4:
            st.markdown("<div class='panel'><div class='panel-title'>Qualidade de Gravação</div>", unsafe_allow_html=True)
            q_df = df.groupby("qualidade_gravacao", dropna=False).size().reset_index(name="total")
            st.plotly_chart(donut(q_df["qualidade_gravacao"], q_df["total"]), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        c5, c6 = st.columns([1.15, 1.85])

        with c5:
            st.markdown("""
            <div class="panel">
                <div class="panel-title">Mapa Operacional Animado</div>
                <div class="fake-map">
                    <div class="node" style="left:18%; top:52%;">ABBVIE<br>342 CÂMERAS</div>
                    <div class="node" style="left:42%; top:38%;">CHIESI<br>128 CÂMERAS</div>
                    <div class="node" style="left:67%; top:58%;">PHILIPS<br>96 CÂMERAS</div>
                    <div class="node" style="left:72%; top:25%;">SANOFI<br>72 CÂMERAS</div>
                    <div class="node" style="left:30%; top:72%;">ADIUM<br>186 CÂMERAS</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c6:
            feeds = ""
            for _, r in df.head(8).iterrows():
                dot = "dot-green" if str(r["status"]).upper() == "ATIVA" else "dot-red"
                feeds += f"""
                <div class="camera-feed">
                    <div class="feed-label"><span class="{dot}"></span>{r['nome_camera']} - {r['operacao']}<br>{r['status']}</div>
                </div>
                """
            st.markdown(f"""
            <div class="panel">
                <div class="panel-title">Feed de Câmeras - Simulação Visual</div>
                <div class="feed-grid">{feeds}</div>
            </div>
            """, unsafe_allow_html=True)

        c7, c8, c9 = st.columns([1.2, 1, .9])

        with c7:
            st.markdown("""
            <div class="panel" style="min-height:205px;">
                <div class="panel-title">Log de Atividades</div>
                <div class="log-line"><span class="dot-green"></span>15:42:10 Câmera voltou ao ar</div>
                <div class="log-line"><span class="dot-red"></span>15:41:22 NVR com carga elevada</div>
                <div class="log-line"><span class="dot-yellow"></span>15:40:05 Atualização realizada</div>
                <div class="log-line"><span class="dot-cyan"></span>15:38:42 Varredura operacional concluída</div>
            </div>
            """, unsafe_allow_html=True)

        with c8:
            carga = min(100, int((total / max(nvrs, 1)) * 4)) if total else 0
            st.markdown(f"""
            <div class="panel" style="min-height:205px;">
                <div class="panel-title">Status dos NVRs</div>
                <div class="log-line">NVRs cadastrados: {nvrs}</div>
                <div class="log-line">Câmeras totais: {total}</div>
                <div class="log-line">Carga média estimada</div>
                <div class="progress-bar"><div class="progress-fill" style="width:{carga}%"></div></div>
                <div class="log-line"><span class="dot-green"></span>Sistema operacional</div>
            </div>
            """, unsafe_allow_html=True)

        with c9:
            meta = 1300
            progresso = round((total / meta) * 100, 1) if total else 0
            st.markdown(f"""
            <div class="panel" style="min-height:205px;">
                <div class="panel-title">Expansão do Parque</div>
                <div class="kpi-value kpi-yellow">{progresso}%</div>
                <div class="log-line">Meta: {meta} câmeras</div>
                <div class="log-line">Atual: {total} câmeras</div>
                <div class="log-line">Faltando: {max(meta-total,0)}</div>
            </div>
            """, unsafe_allow_html=True)


elif st.session_state.page == "Inventário":
    st.markdown("<div class='forms-panel'><h3>Inventário de Câmeras</h3>", unsafe_allow_html=True)

    if df.empty:
        st.warning("Nenhuma câmera cadastrada.")
    else:
        c1, c2, c3 = st.columns(3)
        filtro_operacao = c1.text_input("Operação")
        filtro_status = c2.selectbox("Status", ["Todos"] + sorted(df["status"].dropna().unique().tolist()))
        filtro_ativo = c3.selectbox("Situação", ["Todas", "Ativas", "Inativas"])

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
            st.download_button("Baixar Inventário em Excel", file, file_name="inventario_cameras.xlsx")

    st.markdown("</div>", unsafe_allow_html=True)


elif st.session_state.page == "Cadastrar Câmera":
    st.markdown("<div class='forms-panel'><h3>Cadastrar Nova Câmera</h3>", unsafe_allow_html=True)

    with st.form("cadastro"):
        c1, c2, c3 = st.columns(3)
        numero = c1.number_input("Nº", min_value=0, step=1)
        operacao = c2.text_input("Operação")
        nome_camera = c3.text_input("Nome da câmera")

        c4, c5, c6 = st.columns(3)
        canal = c4.text_input("Canal")
        ip_camera = c5.text_input("IP da câmera")
        rack = c6.text_input("Rack")

        c7, c8, c9 = st.columns(3)
        login_camera = c7.text_input("Login câmera")
        senha_camera = c8.text_input("Senha câmera", type="password")
        serie_number = c9.text_input("Série Number")

        c10, c11, c12 = st.columns(3)
        modelo = c10.text_input("Modelo")
        marca = c11.text_input("Marca")
        dias_gravacao = c12.number_input("Dias de gravação", min_value=0, step=1)

        c13, c14, c15 = st.columns(3)
        inicio_gravacao = c13.date_input("Início gravação")
        termino_gravacao = c14.date_input("Término gravação")
        horario = c15.text_input("Horário")

        c16, c17, c18 = st.columns(3)
        nvr = c16.text_input("NVR")
        ip_nvr = c17.text_input("IP NVR")
        login_nvr = c18.text_input("Login NVR")

        c19, c20 = st.columns(2)
        senha_nvr = c19.text_input("Senha NVR", type="password")
        status = c20.selectbox("Status", ["ATIVA", "INATIVA", "MANUTENÇÃO", "FALHA", "SEM GRAVAÇÃO"])

        qualidade_gravacao = st.selectbox("Qualidade da gravação", ["BOA", "REGULAR", "RUIM", "SEM IMAGEM", "SEM GRAVAÇÃO"])
        observacao = st.text_area("Observação")
        acao_necessaria = st.text_area("Ação necessária")
        foto_upload = st.file_uploader("Foto / imagem da câmera", type=["png", "jpg", "jpeg"])

        salvar = st.form_submit_button("Cadastrar câmera")

        if salvar:
            if not nome_camera:
                st.error("Informe o nome da câmera.")
            else:
                foto_bytes, foto_nome = imagem_para_bytes(foto_upload)
                cadastrar_camera({
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
                }, foto_bytes, foto_nome)

                st.success("Câmera cadastrada com sucesso.")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


elif st.session_state.page == "Atualizar Status":
    st.markdown("<div class='forms-panel'><h3>Atualizar Status Operacional</h3>", unsafe_allow_html=True)

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


elif st.session_state.page == "Desativar / Excluir":
    st.markdown("<div class='forms-panel'><h3>Desativar ou Excluir Câmera</h3>", unsafe_allow_html=True)

    if df.empty:
        st.warning("Nenhuma câmera cadastrada.")
    else:
        camera_id = st.selectbox(
            "Selecione a câmera",
            df["id"].tolist(),
            format_func=lambda x: f'{x} - {df[df["id"] == x]["nome_camera"].iloc[0]}'
        )

        c1, c2, c3 = st.columns(3)

        if c1.button("Desativar mantendo histórico"):
            desativar_camera(camera_id)
            st.success("Câmera desativada.")
            st.rerun()

        if c2.button("Reativar câmera"):
            reativar_camera(camera_id)
            st.success("Câmera reativada.")
            st.rerun()

        if c3.button("Excluir definitivamente"):
            excluir_camera(camera_id)
            st.error("Câmera excluída definitivamente.")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
