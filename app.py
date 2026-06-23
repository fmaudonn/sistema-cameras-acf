import streamlit as st

st.set_page_config(
    page_title="Sistema de Câmeras ACF",
    page_icon="📷",
    layout="wide"
)

st.title("📷 Sistema de Gestão de Câmeras")

st.markdown("""
### Bem-vindo ao Sistema de Gestão de Câmeras

Este sistema irá permitir:

- Cadastro de câmeras
- Inclusão de fotos
- Controle de NVR
- Controle de gravação
- Dashboard executivo
- Gestão de disponibilidade
- Expansão do parque CFTV

""")

st.success("Sistema inicial criado com sucesso.")
