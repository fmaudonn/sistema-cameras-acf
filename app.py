import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from datetime import datetime
import base64

st.set_page_config(
    page_title="Sistema de Câmeras ACF",
    page_icon="📷",
    layout="wide"
)

DATABASE_URL = st.secrets["DATABASE_URL"]
engine = create_engine(DATABASE_URL)


def executar_sql(sql, params=None):
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})


def consultar_df(sql, params=None):
    with engine.begin() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def imagem_para_bytes(uploaded_file):
    if uploaded_file is None:
        return None, None
    return uploaded_file.read(), uploaded_file.name


def cadastrar_camera(dados, foto, foto_nome):
    sql = """
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
    """
    dados["foto_camera"] = foto
    dados["foto_nome"] = foto_nome
    executar_sql(sql, dados)


def carregar_cameras():
    return consultar_df("""
        SELECT 
            id, numero, operacao, nome_camera, canal, ip_camera, modelo, marca,
            dias_gravacao, nvr, ip_nvr, rack, status, qualidade_gravacao,
            observacao, acao_necessaria, serie_number, ativo, criado_em, atualizado_em
        FROM cameras
        ORDER BY id DESC
    """)


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
.stApp {
    background: radial-gradient(circle at top left, #263238 0%, #071018 35%, #020409 100%);
    color: white;
}
[data-testid="stMetricValue"] {
    font-size: 34px;
}
.card {
    padding: 22px;
    border-radius: 22px;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    box-shadow: 0 0 35px rgba(0,255,255,0.08);
}
h1, h2, h3 {
    color: #F5F7FA;
}
</style>
""", unsafe_allow_html=True)


st.title("📷 Security Camera Command Center")
st.caption("Sistema de Gestão de Câmeras | ACF Extrema")

menu = st.sidebar.radio(
    "Menu",
    [
        "Dashboard",
        "Inventário",
        "Cadastrar Câmera",
        "Atualizar Status",
        "Desativar / Excluir"
    ]
)

df = carregar_cameras()

if menu == "Dashboard":
    total = len(df)
    ativas = len(df[(df["ativo"] == True) & (df["status"].str.upper() == "ATIVA")]) if not df.empty else 0
    inativas = len(df[df["ativo"] == False]) if not df.empty else 0
    manutencao = len(df[df["acao_necessaria"].fillna("").str.len() > 0]) if not df.empty else 0

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Câmeras cadastradas", total)
    col2.metric("Câmeras ativas", ativas)
    col3.metric("Inativas", inativas)
    col4.metric("Com ação necessária", manutencao)

    st.divider()

    if not df.empty:
        col_a, col_b = st.columns(2)

        with col_a:
            fig = px.pie(df, names="status", title="Distribuição por Status")
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            fig2 = px.bar(
                df.groupby("operacao", dropna=False).size().reset_index(name="total"),
                x="operacao",
                y="total",
                title="Câmeras por Operação"
            )
            st.plotly_chart(fig2, use_container_width=True)

        fig3 = px.bar(
            df.groupby("nvr", dropna=False).size().reset_index(name="total"),
            x="nvr",
            y="total",
            title="Carga Operacional por NVR"
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Nenhuma câmera cadastrada ainda.")


elif menu == "Inventário":
    st.subheader("Inventário de Câmeras")

    if df.empty:
        st.warning("Nenhuma câmera cadastrada.")
    else:
        col1, col2, col3 = st.columns(3)
        operacao = col1.text_input("Filtrar por operação")
        status = col2.selectbox("Status", ["Todos"] + sorted(df["status"].dropna().unique().tolist()))
        ativo = col3.selectbox("Situação", ["Todas", "Ativas", "Inativas"])

        df_filtro = df.copy()

        if operacao:
            df_filtro = df_filtro[df_filtro["operacao"].fillna("").str.contains(operacao, case=False)]

        if status != "Todos":
            df_filtro = df_filtro[df_filtro["status"] == status]

        if ativo == "Ativas":
            df_filtro = df_filtro[df_filtro["ativo"] == True]
        elif ativo == "Inativas":
            df_filtro = df_filtro[df_filtro["ativo"] == False]

        st.dataframe(df_filtro, use_container_width=True)

        excel = df_filtro.to_excel("inventario_cameras.xlsx", index=False)
        with open("inventario_cameras.xlsx", "rb") as file:
            st.download_button(
                "Baixar inventário em Excel",
                file,
                file_name="inventario_cameras.xlsx"
            )


elif menu == "Cadastrar Câmera":
    st.subheader("Cadastrar Nova Câmera")

    with st.form("form_cadastro"):
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


elif menu == "Atualizar Status":
    st.subheader("Atualizar Status da Câmera")

    if df.empty:
        st.warning("Nenhuma câmera cadastrada.")
    else:
        camera_id = st.selectbox(
            "Selecione a câmera",
            df["id"].tolist(),
            format_func=lambda x: f'{x} - {df[df["id"] == x]["nome_camera"].iloc[0]}'
        )

        status = st.selectbox("Novo status", ["ATIVA", "INATIVA", "MANUTENÇÃO", "FALHA", "SEM GRAVAÇÃO"])
        qualidade = st.selectbox("Qualidade gravação", ["BOA", "REGULAR", "RUIM", "SEM IMAGEM", "SEM GRAVAÇÃO"])
        observacao = st.text_area("Observação")
        acao = st.text_area("Ação necessária")

        if st.button("Atualizar"):
            atualizar_status(camera_id, status, qualidade, observacao, acao)
            st.success("Status atualizado com sucesso.")
            st.rerun()


elif menu == "Desativar / Excluir":
    st.subheader("Desativar ou Excluir Câmera")

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
