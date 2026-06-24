import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from sqlalchemy import create_engine, text
from datetime import datetime

st.set_page_config(
    page_title="ACF Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
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

:root{
    --bg:#02070a;
    --panel:#061114;
    --cyan:#00f5ff;
    --green:#24ff6d;
    --yellow:#ffd000;
    --red:#ff2f2f;
    --muted:#8fa8ad;
}

html, body, [class*="css"] {
    font-family: 'Rajdhani', sans-serif !important;
}

.stApp {
    background:
        radial-gradient(circle at 25% 10%, rgba(0, 245, 255, .14), transparent 26%),
        radial-gradient(circle at 80% 5%, rgba(255, 208, 0, .10), transparent 22%),
        linear-gradient(rgba(0,0,0,.72), rgba(0,0,0,.88)),
        repeating-linear-gradient(0deg, rgba(0,255,255,.035) 0px, rgba(0,255,255,.035) 1px, transparent 1px, transparent 5px),
        #02070a;
    color:#dffcff;
}

.block-container {
    padding: 0.8rem 1rem 1rem 1rem;
    max-width: 100% !important;
}

#MainMenu, footer, header {
    visibility: hidden;
}

.command-grid {
    display: grid;
    grid-template-columns: 250px 1fr;
    gap: 14px;
}

.left-rail {
    border: 1px solid rgba(0,245,255,.32);
    background: rgba(2,10,12,.84);
    min-height: 92vh;
    padding: 14px;
    box-shadow: 0 0 35px rgba(0,245,255,.08);
    position: relative;
    overflow: hidden;
}

.left-rail:before {
    content:"";
    position:absolute;
    top:-80px;
    left:-80px;
    width:180px;
    height:180px;
    background: radial-gradient(circle, rgba(255,208,0,.22), transparent 65%);
    animation: pulse 3s infinite alternate;
}

.logo-box {
    border-bottom: 1px solid rgba(0,245,255,.28);
    padding-bottom: 16px;
    margin-bottom: 18px;
}

.logo-main {
    font-family:'Orbitron', sans-serif;
    color:var(--yellow);
    font-size:26px;
    font-weight:900;
    line-height:1;
}

.logo-sub {
    font-family:'Share Tech Mono', monospace;
    color:#dffcff;
    font-size:13px;
    margin-top:4px;
}

.menu-title {
    color:#9fd7de;
    font-family:'Share Tech Mono', monospace;
    font-size:13px;
    margin: 16px 0 8px;
}

.menu-item {
    border: 1px solid rgba(0,245,255,.18);
    padding: 10px 12px;
    margin-bottom: 8px;
    background: rgba(255,255,255,.025);
    font-family:'Share Tech Mono', monospace;
    color:#dffcff;
    font-size:13px;
}

.menu-active {
    border-color: var(--yellow);
    color: var(--yellow);
    box-shadow: inset 4px 0 0 var(--yellow), 0 0 18px rgba(255,208,0,.18);
}

.ops-row {
    display:flex;
    justify-content:space-between;
    border-bottom:1px solid rgba(255,255,255,.06);
    padding: 7px 0;
    font-family:'Share Tech Mono', monospace;
    font-size:12px;
}

.dot-green, .dot-red, .dot-yellow {
    width:9px;
    height:9px;
    border-radius:50%;
    display:inline-block;
    margin-right:7px;
}

.dot-green {background:var(--green); box-shadow:0 0 10px var(--green);}
.dot-red {background:var(--red); box-shadow:0 0 10px var(--red);}
.dot-yellow {background:var(--yellow); box-shadow:0 0 10px var(--yellow);}

.main-screen {
    min-height: 92vh;
}

.topbar {
    display:grid;
    grid-template-columns: 1fr 380px 190px;
    gap:12px;
    margin-bottom: 12px;
}

.title-panel, .status-panel, .map-panel {
    border:1px solid rgba(0,245,255,.32);
    background: rgba(2,12,15,.80);
    padding:16px 20px;
    position:relative;
    overflow:hidden;
    box-shadow: 0 0 24px rgba(0,245,255,.07);
}

.title-panel:before, .status-panel:before, .map-panel:before, .hud-card:before, .panel:before {
    content:"";
    position:absolute;
    top:0;
    left:0;
    width:48px;
    height:3px;
    background:var(--cyan);
    animation: scan 2.5s infinite;
}

.big-title {
    font-family:'Orbitron', sans-serif;
    color:var(--yellow);
    font-size:30px;
    font-weight:900;
    letter-spacing:.03em;
}

.subtitle {
    font-family:'Share Tech Mono', monospace;
    color:#8fb2b8;
    font-size:13px;
    margin-top:5px;
}

.online {
    font-family:'Share Tech Mono', monospace;
    color:var(--green);
    font-size:14px;
}

.clock {
    font-family:'Share Tech Mono', monospace;
    color:#fff;
    font-size:15px;
}

.kpi-grid {
    display:grid;
    grid-template-columns: repeat(6, 1fr);
    gap:12px;
    margin-bottom:12px;
}

.hud-card {
    border:1px solid rgba(0,245,255,.30);
    background: linear-gradient(135deg, rgba(5,20,24,.92), rgba(2,8,10,.84));
    padding:14px;
    min-height:110px;
    position:relative;
    box-shadow:0 0 28px rgba(0,245,255,.07);
}

.kpi-label {
    font-family:'Share Tech Mono', monospace;
    color:#a4b8bd;
    font-size:12px;
    text-transform:uppercase;
}

.kpi-value {
    font-family:'Orbitron', sans-serif;
    color:var(--green);
    font-size:30px;
    font-weight:900;
    margin-top:6px;
}

.kpi-yellow { color:var(--yellow); }
.kpi-red { color:var(--red); }
.kpi-cyan { color:var(--cyan); }

.kpi-mini {
    font-family:'Share Tech Mono', monospace;
    color:#7e9599;
    font-size:11px;
}

.dashboard-grid {
    display:grid;
    grid-template-columns: 1.1fr 1.1fr .9fr 1fr;
    gap:12px;
    margin-bottom:12px;
}

.middle-grid {
    display:grid;
    grid-template-columns: 1.1fr 1.7fr;
    gap:12px;
    margin-bottom:12px;
}

.bottom-grid {
    display:grid;
    grid-template-columns: 1.1fr 1fr .9fr;
    gap:12px;
}

.panel {
    border:1px solid rgba(0,245,255,.32);
    background: rgba(2,12,15,.80);
    padding:13px;
    position:relative;
    min-height:285px;
    box-shadow:0 0 30px rgba(0,245,255,.06);
    overflow:hidden;
}

.panel-title {
    font-family:'Share Tech Mono', monospace;
    color:#dffcff;
    font-size:15px;
    margin-bottom:10px;
    text-transform:uppercase;
}

.fake-map {
    height: 300px;
    background:
        radial-gradient(circle at 22% 55%, rgba(36,255,109,.35), transparent 4%),
        radial-gradient(circle at 48% 40%, rgba(255,208,0,.35), transparent 4%),
        radial-gradient(circle at 70% 60%, rgba(36,255,109,.32), transparent 4%),
        radial-gradient(circle at 78% 30%, rgba(36,255,109,.28), transparent 3%),
        repeating-linear-gradient(35deg, transparent 0px, transparent 19px, rgba(0,245,255,.08) 20px),
        linear-gradient(135deg, #041114, #020608);
    border:1px solid rgba(0,245,255,.22);
    position:relative;
    overflow:hidden;
}

.fake-map:after {
    content:"";
    position:absolute;
    width:160%;
    height:2px;
    left:-30%;
    top:0;
    background:linear-gradient(90deg, transparent, rgba(0,245,255,.55), transparent);
    animation: sweep 3s infinite linear;
}

.node {
    position:absolute;
    border:1px solid rgba(36,255,109,.7);
    background:rgba(0,0,0,.58);
    color:#caffd8;
    font-family:'Share Tech Mono', monospace;
    font-size:12px;
    padding:6px 9px;
    box-shadow:0 0 20px rgba(36,255,109,.22);
}

.feed-grid {
    display:grid;
    grid-template-columns: repeat(4, 1fr);
    gap:9px;
}

.camera-feed {
    height:118px;
    border:1px solid rgba(0,245,255,.28);
    background:
        linear-gradient(rgba(0,0,0,.1), rgba(0,0,0,.65)),
        repeating-linear-gradient(90deg, rgba(255,255,255,.06) 0px, rgba(255,255,255,.06) 1px, transparent 1px, transparent 7px),
        radial-gradient(circle at center, rgba(160,190,200,.25), transparent 70%),
        #111a1f;
    position:relative;
    overflow:hidden;
}

.camera-feed:before {
    content:"";
    position:absolute;
    inset:0;
    background:linear-gradient(120deg, transparent, rgba(255,255,255,.18), transparent);
    transform:translateX(-120%);
    animation: shine 4s infinite;
}

.feed-label {
    position:absolute;
    bottom:0;
    left:0;
    right:0;
    padding:5px 7px;
    background:rgba(0,0,0,.72);
    color:#dffcff;
    font-family:'Share Tech Mono', monospace;
    font-size:11px;
}

.log-line {
    font-family:'Share Tech Mono', monospace;
    font-size:12px;
    padding:5px 0;
    border-bottom:1px solid rgba(255,255,255,.05);
}

.progress-bar {
    height:8px;
    background:rgba(255,255,255,.10);
    margin:7px 0;
    position:relative;
}

.progress-fill {
    height:100%;
    background:linear-gradient(90deg, var(--green), var(--cyan));
    box-shadow:0 0 14px rgba(0,245,255,.45);
}

.forms-panel {
    border:1px solid rgba(0,245,255,.32);
    background:rgba(2,12,15,.86);
    padding:18px;
    box-shadow:0 0 30px rgba(0,245,255,.08);
}

div[data-testid="stDataFrame"] {
    border:1px solid rgba(0,245,255,.28);
}

.stButton button, .stDownloadButton button {
    background:linear-gradient(90deg, var(--yellow), #b88a00) !important;
    color:#02070a !important;
    border:0 !important;
    border-radius:0 !important;
    font-family:'Share Tech Mono', monospace !important;
    text-transform:uppercase;
    font-weight:900 !important;
}

input, textarea {
    background:rgba(0,0,0,.45) !important;
    color:#dffcff !important;
    border:1px solid rgba(0,245,255,.35) !important;
    border-radius:0 !important;
}

div[data-baseweb="select"] > div {
    background:rgba(0,0,0,.45) !important;
    color:#dffcff !important;
    border:1px solid rgba(0,245,255,.35) !important;
    border-radius:0 !important;
}

@keyframes scan {
    0% {left:0; opacity:.2;}
    50% {left:70%; opacity:1;}
    100% {left:0; opacity:.2;}
}

@keyframes pulse {
    from {opacity:.25; transform:scale(.9);}
    to {opacity:.75; transform:scale(1.1);}
}

@keyframes sweep {
    from {top:-10%;}
    to {top:110%;}
}

@keyframes shine {
    0% {transform:translateX(-120%);}
    45% {transform:translateX(120%);}
    100% {transform:translateX(120%);}
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


def nav_button(label):
    active = "menu-active" if st.session_state.page == label else ""
    if st.sidebar.button(label, use_container_width=True):
        st.session_state.page = label
        st.rerun()


with st.sidebar:
    st.markdown("""
    <div class="logo-box">
        <div class="logo-main">ACF COMMAND</div>
        <div class="logo-sub">CONTROL SYSTEM</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### NAVEGAÇÃO")
    nav_button("Dashboard")
    nav_button("Inventário")
    nav_button("Cadastrar Câmera")
    nav_button("Atualizar Status")
    nav_button("Desativar / Excluir")

    st.markdown("---")
    st.markdown("### OPERAÇÕES")
    if not df.empty:
        ops = df.groupby("operacao", dropna=False).size().reset_index(name="total")
        for _, row in ops.iterrows():
            st.markdown(
                f"<div class='ops-row'><span><span class='dot-green'></span>{row['operacao']}</span><span>{row['total']}</span></div>",
                unsafe_allow_html=True
            )
    else:
        st.info("Sem operações cadastradas.")

    st.markdown("---")
    st.markdown("### ALERTAS")
    if manutencao:
        st.markdown(f"<div class='ops-row'><span><span class='dot-red'></span>AÇÕES PENDENTES</span><span>{manutencao}</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='ops-row'><span><span class='dot-green'></span>SEM ALERTAS</span><span>OK</span></div>", unsafe_allow_html=True)


hora = datetime.now().strftime("%H:%M:%S")
data = datetime.now().strftime("%d/%m/%Y")

st.markdown(f"""
<div class="topbar">
    <div class="title-panel">
        <div class="big-title">ACF COMMAND | SECURITY CAMERA CENTER</div>
        <div class="subtitle">SISTEMA DE GESTÃO DE CÂMERAS • ACF EXTREMA • MONITORAMENTO OPERACIONAL</div>
    </div>
    <div class="status-panel">
        <div class="online">● SISTEMA ONLINE</div>
        <div class="online">STATUS: OPERACIONAL</div>
    </div>
    <div class="map-panel">
        <div class="clock">{hora}</div>
        <div class="clock">{data}</div>
    </div>
</div>
""", unsafe_allow_html=True)


def make_donut(labels, values):
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.68,
        marker=dict(colors=["#24ff6d", "#ff2f2f", "#ffd000", "#00f5ff"]),
        textinfo="none"
    )])
    fig.update_layout(
        height=250,
        margin=dict(l=5, r=5, t=5, b=5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#dffcff")
    )
    return fig


def make_bar(df_bar, x, y):
    fig = px.bar(
        df_bar,
        x=x,
        y=y,
        orientation="h",
        text=x,
        color_discrete_sequence=["#00c9b7"]
    )
    fig.update_layout(
        height=260,
        margin=dict(l=5, r=5, t=5, b=5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,20,24,.22)",
        font=dict(color="#dffcff"),
        xaxis=dict(gridcolor="rgba(0,245,255,.09)"),
        yaxis=dict(gridcolor="rgba(0,245,255,.04)")
    )
    return fig


if st.session_state.page == "Dashboard":
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="hud-card"><div class="kpi-label">Total Câmeras</div><div class="kpi-value kpi-yellow">{total}</div><div class="kpi-mini">100% do parque</div></div>
        <div class="hud-card"><div class="kpi-label">Ativas</div><div class="kpi-value">{ativas}</div><div class="kpi-mini">em operação</div></div>
        <div class="hud-card"><div class="kpi-label">Inativas</div><div class="kpi-value kpi-red">{inativas}</div><div class="kpi-mini">fora de operação</div></div>
        <div class="hud-card"><div class="kpi-label">Manutenção</div><div class="kpi-value kpi-yellow">{manutencao}</div><div class="kpi-mini">ação necessária</div></div>
        <div class="hud-card"><div class="kpi-label">NVRs Online</div><div class="kpi-value kpi-cyan">{nvrs}</div><div class="kpi-mini">gravadores</div></div>
        <div class="hud-card"><div class="kpi-label">Disponibilidade</div><div class="kpi-value">{disponibilidade}%</div><div class="kpi-mini">sistema</div></div>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.warning("Nenhuma câmera cadastrada ainda.")
    else:
        col1, col2, col3, col4 = st.columns([1.05, 1.1, .9, 1.05])

        with col1:
            st.markdown("<div class='panel'><div class='panel-title'>Distribuição por Status</div>", unsafe_allow_html=True)
            status_df = df.groupby("status", dropna=False).size().reset_index(name="total")
            st.plotly_chart(make_donut(status_df["status"], status_df["total"]), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='panel'><div class='panel-title'>Câmeras por Operação</div>", unsafe_allow_html=True)
            op_df = df.groupby("operacao", dropna=False).size().reset_index(name="total").sort_values("total")
            st.plotly_chart(make_bar(op_df, "total", "operacao"), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            st.markdown("<div class='panel'><div class='panel-title'>Carga por NVR</div>", unsafe_allow_html=True)
            nvr_df = df.groupby("nvr", dropna=False).size().reset_index(name="total").sort_values("total")
            st.plotly_chart(make_bar(nvr_df, "total", "nvr"), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col4:
            st.markdown("<div class='panel'><div class='panel-title'>Qualidade de Gravação</div>", unsafe_allow_html=True)
            q_df = df.groupby("qualidade_gravacao", dropna=False).size().reset_index(name="total")
            st.plotly_chart(make_donut(q_df["qualidade_gravacao"], q_df["total"]), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        col5, col6 = st.columns([1.15, 1.85])

        with col5:
            st.markdown("""
            <div class="panel">
                <div class="panel-title">Mapa Operacional</div>
                <div class="fake-map">
                    <div class="node" style="left:18%; top:52%;">ABBVIE<br>342 CÂMERAS</div>
                    <div class="node" style="left:42%; top:37%;">CHIESI<br>128 CÂMERAS</div>
                    <div class="node" style="left:67%; top:55%;">PHILIPS<br>96 CÂMERAS</div>
                    <div class="node" style="left:72%; top:25%;">SANOFI<br>72 CÂMERAS</div>
                    <div class="node" style="left:30%; top:72%;">ADIUM<br>186 CÂMERAS</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col6:
            feeds = ""
            cameras_feed = df.head(8)
            for _, r in cameras_feed.iterrows():
                dot = "dot-green" if str(r["status"]).upper() == "ATIVA" else "dot-red"
                feeds += f"""
                <div class="camera-feed">
                    <div class="feed-label"><span class="{dot}"></span>{r['nome_camera']} - {r['operacao']}<br>{r['status']}</div>
                </div>
                """

            st.markdown(f"""
            <div class="panel">
                <div class="panel-title">Feed de Câmeras - Tempo Real</div>
                <div class="feed-grid">{feeds}</div>
            </div>
            """, unsafe_allow_html=True)

        col7, col8, col9 = st.columns([1.1, 1, .9])

        with col7:
            st.markdown("""
            <div class="panel" style="min-height:200px;">
                <div class="panel-title">Log de Atividades</div>
                <div class="log-line"><span class="dot-green"></span>15:42:10 Câmera CAM-001 voltou ao ar</div>
                <div class="log-line"><span class="dot-red"></span>15:41:22 NVR-03 carga acima de 80%</div>
                <div class="log-line"><span class="dot-yellow"></span>15:40:05 Usuário realizou atualização</div>
                <div class="log-line"><span class="dot-green"></span>15:38:42 Backup concluído com sucesso</div>
            </div>
            """, unsafe_allow_html=True)

        with col8:
            carga = min(100, int((total / max(nvrs, 1)) * 4)) if total else 0
            st.markdown(f"""
            <div class="panel" style="min-height:200px;">
                <div class="panel-title">Status dos NVRs</div>
                <div class="log-line">NVRs cadastrados: {nvrs}</div>
                <div class="log-line">Câmeras totais: {total}</div>
                <div class="log-line">Carga média estimada</div>
                <div class="progress-bar"><div class="progress-fill" style="width:{carga}%"></div></div>
                <div class="log-line"><span class="dot-green"></span>Sistema operacional</div>
            </div>
            """, unsafe_allow_html=True)

        with col9:
            meta = 1300
            progresso = round((total / meta) * 100, 1) if total else 0
            st.markdown(f"""
            <div class="panel" style="min-height:200px;">
                <div class="panel-title">Expansão do Parque</div>
                <div class="kpi-value kpi-yellow">{progresso}%</div>
                <div class="log-line">Meta: {meta} câmeras</div>
                <div class="log-line">Atual: {total} câmeras</div>
                <div class="log-line">Faltando: {max(meta-total,0)} câmeras</div>
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
