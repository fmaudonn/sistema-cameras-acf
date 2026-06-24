import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import datetime
import base64

# =====================================================
# CONFIGURAÇÃO DA PÁGINA
# =====================================================
st.set_page_config(
    page_title="DHL Security Camera Command Center",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# CONEXÃO COM NEON
# =====================================================
DATABASE_URL = st.secrets["DATABASE_URL"]
engine = create_engine(DATABASE_URL)


# =====================================================
# FUNÇÕES DE BANCO
# =====================================================
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


def carregar_cameras_com_foto(limit=12):
    try:
        return consultar_df("""
            SELECT 
                id, numero, operacao, nome_camera, canal, ip_camera, modelo, marca,
                dias_gravacao, nvr, ip_nvr, rack, status, qualidade_gravacao,
                observacao, acao_necessaria, serie_number, ativo, foto_camera, foto_nome,
                criado_em, atualizado_em
            FROM cameras
            ORDER BY id DESC
            LIMIT :limit
        """, {"limit": limit})
    except Exception:
        return pd.DataFrame()


def imagem_para_bytes(uploaded_file):
    if uploaded_file is None:
        return None, None
    return uploaded_file.read(), uploaded_file.name


def bytes_para_base64(img_bytes):
    if img_bytes is None:
        return None
    if isinstance(img_bytes, memoryview):
        img_bytes = img_bytes.tobytes()
    if isinstance(img_bytes, str):
        return None
    try:
        return base64.b64encode(img_bytes).decode("utf-8")
    except Exception:
        return None


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


# =====================================================
# CSS PROFISSIONAL DHL
# =====================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

:root {
    --dhl-yellow: #FFCC00;
    --dhl-yellow-soft: #FFF4BF;
    --dhl-red: #D40511;
    --dhl-red-dark: #9F000A;
    --bg: #F4F6F8;
    --surface: #FFFFFF;
    --surface-soft: #FAFAFA;
    --border: #E5E7EB;
    --text: #1F2937;
    --muted: #6B7280;
    --success: #0E9F6E;
    --warning: #F59E0B;
    --danger: #D40511;
    --info: #2563EB;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

.stApp {
    background:
        radial-gradient(circle at top right, rgba(255,204,0,.18), transparent 28%),
        linear-gradient(180deg, #F7F8FA 0%, #F1F3F6 100%);
    color: var(--text);
}

#MainMenu, footer, header {
    visibility: hidden;
}

.block-container {
    padding-top: 1.1rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 100% !important;
}

section[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid var(--border);
    box-shadow: 6px 0 26px rgba(15, 23, 42, 0.06);
}

section[data-testid="stSidebar"] * {
    color: var(--text) !important;
}

.sidebar-brand {
    background: linear-gradient(135deg, var(--dhl-yellow) 0%, #FFE066 100%);
    border-radius: 22px;
    padding: 22px 18px;
    margin: 0 0 18px 0;
    border: 1px solid #E8B900;
    box-shadow: 0 12px 30px rgba(255, 204, 0, 0.25);
}

.sidebar-brand .brand-title {
    font-weight: 900;
    color: var(--dhl-red) !important;
    font-size: 24px;
    line-height: 1.05;
    letter-spacing: -0.04em;
}

.sidebar-brand .brand-subtitle {
    color: #2B2B2B !important;
    font-size: 12px;
    font-weight: 700;
    margin-top: 6px;
    text-transform: uppercase;
    letter-spacing: .05em;
}

.sidebar-section {
    font-size: 11px;
    color: var(--muted) !important;
    text-transform: uppercase;
    letter-spacing: .12em;
    font-weight: 800;
    margin-top: 18px;
    margin-bottom: 8px;
}

.sidebar-mini-card {
    background: #F9FAFB;
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 14px;
    margin-bottom: 10px;
}

.sidebar-mini-card .mini-title {
    color: var(--muted) !important;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
}

.sidebar-mini-card .mini-value {
    color: var(--dhl-red) !important;
    font-size: 24px;
    font-weight: 900;
    margin-top: 3px;
}

/* Radio menu */
div[role="radiogroup"] label {
    background: #FFFFFF !important;
    border: 1px solid transparent !important;
    border-radius: 14px !important;
    padding: 10px 12px !important;
    margin-bottom: 6px !important;
    transition: all .15s ease;
}

div[role="radiogroup"] label:hover {
    background: #FFF9DB !important;
    border-color: #FFE066 !important;
}

div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child {
    display: none !important;
}

h1, h2, h3 {
    color: var(--text) !important;
    letter-spacing: -0.035em;
}

.app-header {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 26px;
    padding: 24px 28px;
    margin-bottom: 20px;
    box-shadow: 0 14px 38px rgba(15, 23, 42, 0.06);
    position: relative;
    overflow: hidden;
}

.app-header:before {
    content: "";
    position: absolute;
    inset: 0 0 auto 0;
    height: 7px;
    background: linear-gradient(90deg, var(--dhl-red) 0%, var(--dhl-red) 24%, var(--dhl-yellow) 24%, var(--dhl-yellow) 100%);
}

.app-header-grid {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 20px;
    align-items: center;
    margin-top: 6px;
}

.header-title {
    font-size: 30px;
    font-weight: 900;
    color: var(--text);
    line-height: 1.1;
}

.header-subtitle {
    color: var(--muted);
    font-size: 14px;
    margin-top: 6px;
    font-weight: 600;
}

.header-right {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
    justify-content: flex-end;
}

.badge {
    padding: 8px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
    border: 1px solid var(--border);
    background: #F9FAFB;
    color: var(--text);
}

.badge-online {
    background: #ECFDF5;
    color: #047857;
    border-color: #A7F3D0;
}

.badge-dhl {
    background: var(--dhl-yellow-soft);
    color: var(--dhl-red);
    border-color: #FFE066;
}

.kpi-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 18px 18px 16px 18px;
    min-height: 116px;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.045);
    position: relative;
    overflow: hidden;
}

.kpi-card:before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 6px;
    height: 100%;
    background: var(--dhl-yellow);
}

.kpi-card.kpi-danger:before { background: var(--dhl-red); }
.kpi-card.kpi-success:before { background: var(--success); }
.kpi-card.kpi-warning:before { background: var(--warning); }

.kpi-title {
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .10em;
    font-weight: 900;
    margin-left: 4px;
}

.kpi-value {
    font-size: 28px;
    color: var(--text);
    font-weight: 900;
    margin-top: 8px;
    margin-left: 4px;
    line-height: 1;
}

.kpi-value.red { color: var(--dhl-red); }
.kpi-value.green { color: var(--success); }
.kpi-value.yellow { color: var(--warning); }

.kpi-caption {
    margin-left: 4px;
    margin-top: 10px;
    font-size: 12px;
    color: var(--muted);
    font-weight: 600;
}

.panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 20px;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.045);
    margin-bottom: 18px;
}

.panel-title {
    font-size: 17px;
    font-weight: 900;
    color: var(--text);
    margin-bottom: 12px;
    letter-spacing: -0.02em;
}

.panel-subtitle {
    color: var(--muted);
    font-size: 13px;
    margin-top: -6px;
    margin-bottom: 12px;
}

.risk-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.risk-table th {
    color: var(--muted);
    text-align: left;
    padding: 10px 8px;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: .08em;
    border-bottom: 1px solid var(--border);
}

.risk-table td {
    padding: 11px 8px;
    border-bottom: 1px solid #F1F5F9;
    font-weight: 600;
}

.status-pill {
    display: inline-block;
    padding: 5px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 900;
}

.status-green { background: #ECFDF5; color: #047857; }
.status-yellow { background: #FFFBEB; color: #B45309; }
.status-red { background: #FEF2F2; color: var(--dhl-red); }
.status-gray { background: #F3F4F6; color: #4B5563; }

.camera-card-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(180px, 1fr));
    gap: 14px;
}

.camera-card {
    border: 1px solid var(--border);
    background: #FFFFFF;
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.045);
}

.camera-img {
    height: 125px;
    background: linear-gradient(135deg, #E5E7EB, #F9FAFB);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--muted);
    font-weight: 800;
    font-size: 12px;
    text-transform: uppercase;
}

.camera-img img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.camera-body {
    padding: 13px 14px;
}

.camera-title {
    font-weight: 900;
    color: var(--text);
    font-size: 14px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.camera-meta {
    color: var(--muted);
    font-size: 12px;
    margin-top: 4px;
    font-weight: 600;
}

.form-section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 22px;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.045);
}

.stButton button {
    border-radius: 12px !important;
    background: var(--dhl-yellow) !important;
    color: #111827 !important;
    border: 1px solid #E8B900 !important;
    font-weight: 900 !important;
    min-height: 42px;
}

.stButton button:hover {
    background: #F4C400 !important;
    color: #111827 !important;
}

.stDownloadButton button {
    border-radius: 12px !important;
    background: var(--dhl-red) !important;
    color: #FFFFFF !important;
    border: 1px solid var(--dhl-red-dark) !important;
    font-weight: 900 !important;
}

[data-testid="stDataFrame"] {
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid var(--border);
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}

input, textarea {
    border-radius: 12px !important;
}

div[data-baseweb="select"] > div {
    border-radius: 12px !important;
}

hr {
    border-color: var(--border);
}

@media (max-width: 1200px) {
    .camera-card-grid { grid-template-columns: repeat(2, minmax(180px, 1fr)); }
    .app-header-grid { grid-template-columns: 1fr; }
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# DADOS E MÉTRICAS
# =====================================================
df = carregar_cameras()

def calcular_metricas(df):
    if df.empty:
        return {
            "total": 0, "ativas": 0, "inativas": 0, "pendencias": 0,
            "sem_gravacao": 0, "falhas": 0, "retencao_media": 0,
            "disponibilidade": 0, "nvrs": 0, "sem_foto": 0
        }

    status = df["status"].fillna("").str.upper()
    qualidade = df["qualidade_gravacao"].fillna("").str.upper()

    total = len(df)
    ativas = len(df[(df["ativo"] == True) & (status == "ATIVA")])
    inativas = len(df[df["ativo"] == False])
    pendencias = len(df[df["acao_necessaria"].fillna("").str.len() > 0])
    sem_gravacao = len(df[status.str.contains("SEM GRAVAÇÃO", na=False) | qualidade.str.contains("SEM GRAVAÇÃO", na=False)])
    falhas = len(df[status.str.contains("FALHA", na=False) | qualidade.str.contains("RUIM|SEM IMAGEM", na=False)])
    retencao_media = round(pd.to_numeric(df["dias_gravacao"], errors="coerce").fillna(0).mean(), 1)
    disponibilidade = round((ativas / total) * 100, 1) if total else 0
    nvrs = df["nvr"].replace("", pd.NA).dropna().nunique()

    return {
        "total": total,
        "ativas": ativas,
        "inativas": inativas,
        "pendencias": pendencias,
        "sem_gravacao": sem_gravacao,
        "falhas": falhas,
        "retencao_media": retencao_media,
        "disponibilidade": disponibilidade,
        "nvrs": nvrs,
        "sem_foto": 0
    }


metricas = calcular_metricas(df)


# =====================================================
# SIDEBAR PREMIUM
# =====================================================
st.sidebar.markdown("""
<div class="sidebar-brand">
    <div class="brand-title">DHL<br>Security</div>
    <div class="brand-subtitle">Camera Command Center</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown('<div class="sidebar-section">Navegação</div>', unsafe_allow_html=True)

menu = st.sidebar.radio(
    "",
    [
        "📊 Dashboard Executivo",
        "📷 Inventário Técnico",
        "🖼️ Book Visual",
        "➕ Nova Câmera",
        "🔧 Manutenção",
        "🗑️ Desativar / Excluir"
    ],
    label_visibility="collapsed"
)

st.sidebar.markdown('<div class="sidebar-section">Resumo operacional</div>', unsafe_allow_html=True)
st.sidebar.markdown(f"""
<div class="sidebar-mini-card">
    <div class="mini-title">Disponibilidade</div>
    <div class="mini-value">{metricas['disponibilidade']}%</div>
</div>
<div class="sidebar-mini-card">
    <div class="mini-title">Câmeras cadastradas</div>
    <div class="mini-value">{metricas['total']}</div>
</div>
<div class="sidebar-mini-card">
    <div class="mini-title">Pendências</div>
    <div class="mini-value">{metricas['pendencias']}</div>
</div>
""", unsafe_allow_html=True)


# =====================================================
# HEADER PROFISSIONAL
# =====================================================
last_update = datetime.now().strftime("%d/%m/%Y %H:%M")
st.markdown(f"""
<div class="app-header">
    <div class="app-header-grid">
        <div>
            <div class="header-title">DHL Security Camera Command Center</div>
            <div class="header-subtitle">ACF Extrema • Life Sciences • Gestão corporativa do parque de CFTV</div>
        </div>
        <div class="header-right">
            <div class="badge badge-online">Sistema Online</div>
            <div class="badge badge-dhl">DHL Theme</div>
            <div class="badge">Atualizado: {last_update}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# =====================================================
# FUNÇÕES VISUAIS
# =====================================================
def kpi_card(title, value, caption, kind="default"):
    cls = "kpi-card"
    val_cls = "kpi-value"
    if kind == "danger":
        cls += " kpi-danger"
        val_cls += " red"
    elif kind == "success":
        cls += " kpi-success"
        val_cls += " green"
    elif kind == "warning":
        cls += " kpi-warning"
        val_cls += " yellow"

    return f"""
    <div class="{cls}">
        <div class="kpi-title">{title}</div>
        <div class="{val_cls}">{value}</div>
        <div class="kpi-caption">{caption}</div>
    </div>
    """


def status_class(status):
    s = str(status).upper()
    if "ATIVA" in s:
        return "status-green"
    if "MANUT" in s or "REGULAR" in s:
        return "status-yellow"
    if "FALHA" in s or "SEM" in s or "INATIVA" in s:
        return "status-red"
    return "status-gray"


def status_label(status):
    if pd.isna(status) or str(status).strip() == "":
        return "NÃO INFORMADO"
    return str(status)


def configurar_figura(fig, height=340):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#1F2937", family="Inter"),
        margin=dict(l=10, r=10, t=50, b=20),
        title_font=dict(size=16, color="#1F2937", family="Inter")
    )
    return fig


# =====================================================
# DASHBOARD EXECUTIVO
# =====================================================
if menu == "📊 Dashboard Executivo":
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.markdown(kpi_card("Disponibilidade", f"{metricas['disponibilidade']}%", "base operacional", "success" if metricas['disponibilidade'] >= 95 else "danger"), unsafe_allow_html=True)
    c2.markdown(kpi_card("Total", metricas['total'], "câmeras cadastradas"), unsafe_allow_html=True)
    c3.markdown(kpi_card("Ativas", metricas['ativas'], "em operação", "success"), unsafe_allow_html=True)
    c4.markdown(kpi_card("Falhas", metricas['falhas'], "imagem/status crítico", "danger" if metricas['falhas'] > 0 else "success"), unsafe_allow_html=True)
    c5.markdown(kpi_card("Sem gravação", metricas['sem_gravacao'], "falha crítica", "danger" if metricas['sem_gravacao'] > 0 else "success"), unsafe_allow_html=True)
    c6.markdown(kpi_card("Retenção média", f"{metricas['retencao_media']}d", "dias gravados", "warning"), unsafe_allow_html=True)

    st.write("")

    if df.empty:
        st.info("Nenhuma câmera cadastrada ainda.")
    else:
        template = "plotly_white"
        cores_dhl = ["#FFCC00", "#D40511", "#2B2B2B", "#8C8C8C", "#F7D154", "#0E9F6E"]

        # Dados por operação
        df_work = df.copy()
        df_work["status_upper"] = df_work["status"].fillna("").str.upper()
        df_work["qualidade_upper"] = df_work["qualidade_gravacao"].fillna("").str.upper()
        df_work["is_ativa"] = (df_work["ativo"] == True) & (df_work["status_upper"] == "ATIVA")
        df_work["is_falha"] = df_work["status_upper"].str.contains("FALHA|SEM GRAVAÇÃO", na=False) | df_work["qualidade_upper"].str.contains("RUIM|SEM IMAGEM|SEM GRAVAÇÃO", na=False)

        op = df_work.groupby("operacao", dropna=False).agg(
            total=("id", "count"),
            ativas=("is_ativa", "sum"),
            falhas=("is_falha", "sum"),
            retencao_media=("dias_gravacao", "mean")
        ).reset_index()
        op["disponibilidade"] = (op["ativas"] / op["total"] * 100).round(1)
        op["risco"] = op["falhas"]
        op = op.sort_values("disponibilidade", ascending=True)

        col1, col2 = st.columns([1.1, 1])

        with col1:
            st.markdown('<div class="panel"><div class="panel-title">Disponibilidade por Operação</div><div class="panel-subtitle">Ranking operacional para priorização de manutenção.</div>', unsafe_allow_html=True)
            fig_op = px.bar(
                op,
                x="disponibilidade",
                y="operacao",
                orientation="h",
                text="disponibilidade",
                color="disponibilidade",
                color_continuous_scale=[[0, "#D40511"], [0.5, "#F59E0B"], [1, "#0E9F6E"]],
                range_x=[0, 100],
                template=template
            )
            fig_op.update_traces(texttemplate="%{text}%", textposition="outside")
            fig_op.update_layout(showlegend=False, coloraxis_showscale=False, xaxis_title="Disponibilidade (%)", yaxis_title="")
            st.plotly_chart(configurar_figura(fig_op, 385), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="panel"><div class="panel-title">Saúde do Parque CFTV</div><div class="panel-subtitle">Visão consolidada de status das câmeras.</div>', unsafe_allow_html=True)
            status_df = df.groupby("status", dropna=False).size().reset_index(name="total")
            fig_status = px.pie(
                status_df,
                names="status",
                values="total",
                hole=0.62,
                color_discrete_sequence=cores_dhl,
                template=template
            )
            fig_status.update_traces(textinfo="percent+label")
            st.plotly_chart(configurar_figura(fig_status, 385), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        col3, col4 = st.columns([1, 1])

        with col3:
            st.markdown('<div class="panel"><div class="panel-title">Carga Operacional por NVR</div><div class="panel-subtitle">Quantidade de câmeras vinculadas por gravador.</div>', unsafe_allow_html=True)
            nvr_df = df.groupby("nvr", dropna=False).size().reset_index(name="total").sort_values("total", ascending=True)
            fig_nvr = px.bar(
                nvr_df,
                x="total",
                y="nvr",
                orientation="h",
                text="total",
                color_discrete_sequence=["#D40511"],
                template=template
            )
            fig_nvr.update_traces(textposition="outside")
            fig_nvr.update_layout(xaxis_title="Câmeras", yaxis_title="")
            st.plotly_chart(configurar_figura(fig_nvr, 360), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col4:
            st.markdown('<div class="panel"><div class="panel-title">Qualidade das Gravações</div><div class="panel-subtitle">Classificação da imagem/gravação registrada.</div>', unsafe_allow_html=True)
            qualidade_df = df.groupby("qualidade_gravacao", dropna=False).size().reset_index(name="total")
            fig_q = px.bar(
                qualidade_df,
                x="qualidade_gravacao",
                y="total",
                text="total",
                color_discrete_sequence=["#FFCC00"],
                template=template
            )
            fig_q.update_traces(textposition="outside", marker_line_color="#D40511", marker_line_width=1)
            fig_q.update_layout(xaxis_title="Qualidade", yaxis_title="Câmeras")
            st.plotly_chart(configurar_figura(fig_q, 360), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Pendências críticas
        pend = df_work[
            (df_work["acao_necessaria"].fillna("").str.len() > 0) |
            (df_work["is_falha"] == True) |
            (df_work["ativo"] == False)
        ].copy()
        pend = pend[["id", "operacao", "nome_camera", "ip_camera", "nvr", "status", "qualidade_gravacao", "acao_necessaria"]].head(15)

        st.markdown('<div class="panel"><div class="panel-title">Pendências Críticas</div><div class="panel-subtitle">Lista priorizada para tratativa operacional e manutenção.</div>', unsafe_allow_html=True)
        if pend.empty:
            st.success("Nenhuma pendência crítica identificada.")
        else:
            st.dataframe(pend, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)


# =====================================================
# INVENTÁRIO TÉCNICO
# =====================================================
elif menu == "📷 Inventário Técnico":
    st.markdown('<div class="panel"><div class="panel-title">Inventário Técnico de Câmeras</div><div class="panel-subtitle">Consulta, filtros e exportação da base técnica do parque de CFTV.</div>', unsafe_allow_html=True)

    if df.empty:
        st.warning("Nenhuma câmera cadastrada.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        filtro_operacao = col1.text_input("Operação")
        filtro_status = col2.selectbox("Status", ["Todos"] + sorted(df["status"].dropna().unique().tolist()))
        filtro_ativo = col3.selectbox("Situação", ["Todas", "Ativas", "Inativas"])
        filtro_busca = col4.text_input("Busca geral")

        df_filtro = df.copy()

        if filtro_operacao:
            df_filtro = df_filtro[df_filtro["operacao"].fillna("").str.contains(filtro_operacao, case=False)]

        if filtro_status != "Todos":
            df_filtro = df_filtro[df_filtro["status"] == filtro_status]

        if filtro_ativo == "Ativas":
            df_filtro = df_filtro[df_filtro["ativo"] == True]
        elif filtro_ativo == "Inativas":
            df_filtro = df_filtro[df_filtro["ativo"] == False]

        if filtro_busca:
            busca = filtro_busca.lower()
            df_filtro = df_filtro[
                df_filtro["nome_camera"].fillna("").str.lower().str.contains(busca) |
                df_filtro["ip_camera"].fillna("").str.lower().str.contains(busca) |
                df_filtro["nvr"].fillna("").str.lower().str.contains(busca) |
                df_filtro["rack"].fillna("").str.lower().str.contains(busca)
            ]

        st.dataframe(df_filtro, use_container_width=True, hide_index=True)

        df_filtro.to_excel("inventario_cameras.xlsx", index=False)
        with open("inventario_cameras.xlsx", "rb") as file:
            st.download_button(
                "Baixar inventário em Excel",
                file,
                file_name="inventario_cameras.xlsx"
            )

    st.markdown('</div>', unsafe_allow_html=True)


# =====================================================
# BOOK VISUAL
# =====================================================
elif menu == "🖼️ Book Visual":
    st.markdown('<div class="panel"><div class="panel-title">Book Visual de Câmeras</div><div class="panel-subtitle">Galeria operacional com imagens e principais informações técnicas.</div>', unsafe_allow_html=True)

    fotos_df = carregar_cameras_com_foto(16)

    if fotos_df.empty:
        st.info("Nenhuma câmera disponível para exibição visual.")
    else:
        cards_html = '<div class="camera-card-grid">'
        for _, row in fotos_df.iterrows():
            img64 = bytes_para_base64(row.get("foto_camera"))
            if img64:
                img_html = f'<img src="data:image/png;base64,{img64}" />'
            else:
                img_html = 'SEM FOTO'

            status = status_label(row.get("status"))
            cls = status_class(status)
            cards_html += f"""
            <div class="camera-card">
                <div class="camera-img">{img_html}</div>
                <div class="camera-body">
                    <div class="camera-title">{row.get('nome_camera', '')}</div>
                    <div class="camera-meta">{row.get('operacao', '')} • Canal {row.get('canal', '')}</div>
                    <div class="camera-meta">IP: {row.get('ip_camera', '')}</div>
                    <div class="camera-meta">NVR: {row.get('nvr', '')}</div>
                    <div style="margin-top:10px;"><span class="status-pill {cls}">{status}</span></div>
                </div>
            </div>
            """
        cards_html += '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# =====================================================
# CADASTRO
# =====================================================
elif menu == "➕ Nova Câmera":
    st.markdown('<div class="form-section"><h3>Cadastro de Nova Câmera</h3>', unsafe_allow_html=True)

    with st.form("cadastro"):
        st.markdown("##### Identificação")
        col1, col2, col3 = st.columns(3)
        numero = col1.number_input("Nº", min_value=0, step=1)
        operacao = col2.text_input("Operação")
        nome_camera = col3.text_input("Nome da câmera")

        col4, col5, col6 = st.columns(3)
        canal = col4.text_input("Canal")
        ip_camera = col5.text_input("IP da câmera")
        rack = col6.text_input("Rack")

        st.markdown("##### Dados técnicos")
        col7, col8, col9 = st.columns(3)
        login_camera = col7.text_input("Login câmera")
        senha_camera = col8.text_input("Senha câmera", type="password")
        serie_number = col9.text_input("Série Number")

        col10, col11, col12 = st.columns(3)
        modelo = col10.text_input("Modelo")
        marca = col11.text_input("Marca")
        dias_gravacao = col12.number_input("Dias de gravação", min_value=0, step=1)

        st.markdown("##### Gravação e NVR")
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

    st.markdown('</div>', unsafe_allow_html=True)


# =====================================================
# MANUTENÇÃO / STATUS
# =====================================================
elif menu == "🔧 Manutenção":
    st.markdown('<div class="form-section"><h3>Manutenção e Atualização de Status</h3>', unsafe_allow_html=True)

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

        if st.button("Atualizar status"):
            atualizar_status(camera_id, status, qualidade, observacao, acao)
            st.success("Status atualizado.")
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# =====================================================
# DESATIVAR / EXCLUIR
# =====================================================
elif menu == "🗑️ Desativar / Excluir":
    st.markdown('<div class="form-section"><h3>Desativar ou Excluir Câmera</h3>', unsafe_allow_html=True)

    if df.empty:
        st.warning("Nenhuma câmera cadastrada.")
    else:
        camera_id = st.selectbox(
            "Selecione a câmera",
            df["id"].tolist(),
            format_func=lambda x: f'{x} - {df[df["id"] == x]["nome_camera"].iloc[0]}'
        )

        st.warning("Recomendação: use desativar para manter histórico. Excluir remove definitivamente o cadastro.")
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

    st.markdown('</div>', unsafe_allow_html=True)

