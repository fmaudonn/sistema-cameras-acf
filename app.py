import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

st.set_page_config(
    page_title="Security Camera Command Center",
    page_icon="📷",
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top left, rgba(255, 204, 0, .14), transparent 28%),
        radial-gradient(circle at top right, rgba(0, 229, 255, .12), transparent 28%),
        linear-gradient(135deg, #040711 0%, #0b1020 45%, #02040a 100%);
    color: #f8fafc;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #050816 0%, #0d1327 100%);
    border-right: 1px solid rgba(255,255,255,.08);
}

h1, h2, h3 {
    color: #f8fafc !important;
    letter-spacing: -0.04em;
}

.hero {
    padding: 34px;
    border-radius: 28px;
    background: linear-gradient(135deg, rgba(255,255,255,.13), rgba(255,255,255,.04));
    border: 1px solid rgba(255,255,255,.13);
    box-shadow: 0 25px 80px rgba(0,0,0,.40);
    margin-bottom: 24px;
}

.hero h1 {
    font-size: 42px;
    margin-bottom: 6px;
    background: linear-gradient(90deg, #ffffff, #ffcc00, #00e5ff);
    -webkit-background-clip: text;
    color: transparent !important;
}

.hero p {
    color: #aab4cf;
    font-size: 15px;
}

.kpi {
    padding: 24px;
    border-radius: 24px;
    background: rgba(255,255,255,.075);
    border: 1px solid rgba(255,255,255,.13);
    box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 16px 50px rgba(0,0,0,.30);
}

.kpi span {
    color: #9aa4bf;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: .13em;
}

.kpi strong {
    display: block;
    color: #ffcc00;
    font-size: 38px;
    margin-top: 10px;
}

.kpi small {
    color: #8fa3c7;
}

div[data-testid="stMetric"] {
    background: rgba(255,255,255,.075);
    padding: 22px;
    border-radius: 22px;
    border: 1px solid rgba(255,255,255,.12);
}

div[data-testid="stMetricValue"] {
    color: #ffcc00;
    font-size: 34px;
}

.stButton button {
    border-radius: 14px;
    background: linear-gradient(90deg, #ffcc00, #00e5ff);
    color: #020409;
    border: 0;
    font-weight: 800;
}

.stDownloadButton button {
    border-radius: 14px;
    background: #ffcc00;
    color: #020409;
    border: 0;
    font-weight: 800;
}

[data-testid="stDataFrame"] {
    border-radius: 22px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,.12);
}

input, textarea, select {
    border-radius: 14px !important;
}

.block-container {
    padding-top: 2rem;
}
</style>
""", unsafe_allow_html=True)


df = carregar_cameras()

st.markdown("""
<div class="hero">
    <h1>Security Camera Command Center</h1>
    <p>Gestão inteligente do parque de CFTV | Inventário, disponibilidade, NVRs, gravações e expansão operacional.</p>
</div>
""", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "Navegação",
    [
        "Dashboard Executivo",
        "Inventário",
        "Cadastrar Câmera",
        "Atualizar Status",
        "Desativar / Excluir"
    ]
)

if menu == "Dashboard Executivo":
    total = len(df)
    ativas = len(df[(df["ativo"] == True) & (df["status"].fillna("").str.upper() == "ATIVA")]) if not df.empty else 0
    inativas = len(df[df["ativo"] == False]) if not df.empty else 0
    manutencao = len(df[df["acao_necessaria"].fillna("").str.len() > 0]) if not df.empty else 0
    disponibilidade = round((ativas / total) * 100, 1) if total > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.markdown(f'<div class="kpi"><span>Total</span><strong>{total}</strong><small>Câmeras cadastradas</small></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi"><span>Ativas</span><strong>{ativas}</strong><small>Em operação</small></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi"><span>Disponibilidade</span><strong>{disponibilidade}%</strong><small>Base operacional</small></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi"><span>Inativas</span><strong>{inativas}</strong><small>Desativadas</small></div>', unsafe_allow_html=True)
    c5.markdown(f'<div class="kpi"><span>Ação</span><strong>{manutencao}</strong><small>Correção pendente</small></div>', unsafe_allow_html=True)

    st.divider()

    if df.empty:
        st.info("Nenhuma câmera cadastrada ainda.")
    else:
        col1, col2 = st.columns(2)

        template = "plotly_dark"

        with col1:
            fig = px.pie(
                df,
                names="status",
                title="Distribuição por Status",
                hole=0.55,
                template=template
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#f8fafc"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            operacao_df = df.groupby("operacao", dropna=False).size().reset_index(name="total")
            fig2 = px.bar(
                operacao_df,
                x="operacao",
                y="total",
                title="Câmeras por Operação",
                template=template,
                text="total"
            )
            fig2.update_traces(textposition="outside")
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,0.03)",
                font_color="#f8fafc"
            )
            st.plotly_chart(fig2, use_container_width=True)

        nvr_df = df.groupby("nvr", dropna=False).size().reset_index(name="total")
        fig3 = px.bar(
            nvr_df,
            x="nvr",
            y="total",
            title="Carga Operacional por NVR",
            template=template,
            text="total"
        )
        fig3.update_traces(textposition="outside")
        fig3.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.03)",
            font_color="#f8fafc"
        )
        st.plotly_chart(fig3, use_container_width=True)


elif menu == "Inventário":
    st.subheader("Inventário de Câmeras")

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
            st.download_button(
                "Baixar inventário em Excel",
                file,
                file_name="inventario_cameras.xlsx"
            )


elif menu == "Cadastrar Câmera":
    st.subheader("Cadastrar Nova Câmera")

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


elif menu == "Atualizar Status":
    st.subheader("Atualizar Status")

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


elif menu == "Desativar / Excluir":
    st.subheader("Desativar / Excluir Câmera")

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
