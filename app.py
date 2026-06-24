import base64
import html
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text

# =====================================================
# CONFIGURAÇÃO DA PÁGINA
# =====================================================
st.set_page_config(
    page_title="DHL Security Camera Command Center",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_VERSION = "v16.0 • filtros de edição"

# =====================================================
# CONEXÃO COM NEON
# =====================================================
DATABASE_URL = st.secrets["DATABASE_URL"]
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

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
    return consultar_df(
        """
        SELECT
            id, numero, operacao, nome_camera, canal, ip_camera, modelo, marca,
            dias_gravacao, nvr, ip_nvr, rack, status, qualidade_gravacao,
            observacao, acao_necessaria, serie_number, ativo, criado_em, atualizado_em
        FROM cameras
        ORDER BY id DESC
        """
    )


def carregar_cameras_com_foto(limit=60):
    try:
        return consultar_df(
            """
            SELECT
                id, numero, operacao, nome_camera, canal, ip_camera, modelo, marca,
                dias_gravacao, nvr, ip_nvr, rack, status, qualidade_gravacao,
                observacao, acao_necessaria, serie_number, ativo, foto_camera, foto_nome,
                criado_em, atualizado_em
            FROM cameras
            ORDER BY id DESC
            LIMIT :limit
            """,
            {"limit": limit},
        )
    except Exception:
        return pd.DataFrame()


def carregar_camera_por_id(camera_id):
    data = consultar_df(
        """
        SELECT
            id, numero, operacao, nome_camera, canal, ip_camera, login_camera, senha_camera,
            modelo, marca, inicio_gravacao, termino_gravacao, dias_gravacao,
            nvr, ip_nvr, login_nvr, senha_nvr, rack, status, qualidade_gravacao,
            observacao, horario, acao_necessaria, serie_number, ativo, foto_camera, foto_nome,
            criado_em, atualizado_em
        FROM cameras
        WHERE id = :id
        """,
        {"id": int(camera_id)},
    )
    if data.empty:
        return None
    return data.iloc[0]


def imagem_para_bytes(uploaded_file):
    if uploaded_file is None:
        return None, None
    return uploaded_file.read(), uploaded_file.name


def cadastrar_camera(dados, foto, foto_nome):
    dados["foto_camera"] = foto
    dados["foto_nome"] = foto_nome
    executar_sql(
        """
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
        """,
        dados,
    )
    registrar_historico(None, "Cadastro de câmera", f"Câmera cadastrada: {dados.get('nome_camera', '')}")


def normalizar_coluna_excel(coluna):
    """Normaliza cabeçalhos da planilha para facilitar o mapeamento."""
    import unicodedata

    txt = str(coluna).strip().upper()
    txt = unicodedata.normalize("NFKD", txt).encode("ASCII", "ignore").decode("ASCII")
    txt = txt.replace("º", "").replace("°", "")
    txt = " ".join(txt.split())
    return txt


def valor_excel(row, aliases, default=None):
    for alias in aliases:
        if alias in row.index:
            value = row.get(alias)
            if value is not None and not pd.isna(value):
                return value
    return default


def texto_importacao(value, default=""):
    if value is None or pd.isna(value):
        return default
    value = str(value).strip()
    if value.lower() in ["nan", "none", "null"]:
        return default
    return value


def inteiro_importacao(value, default=0):
    try:
        if value is None or pd.isna(value) or str(value).strip() == "":
            return default
        return int(float(value))
    except Exception:
        return default


def data_importacao(value):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def montar_payload_importacao(row):
    status = texto_importacao(valor_excel(row, ["STATUS"]), "ATIVA").upper()
    qualidade = texto_importacao(valor_excel(row, ["QUALIDADE GRAVACAO", "QUALIDADE GRAVAÇÃO"]), "BOA").upper()
    inicio_gravacao = data_importacao(valor_excel(row, ["INICIO GRAV", "INÍCIO GRAV", "INICIO GRAVACAO", "INÍCIO GRAVAÇÃO"]))
    termino_gravacao = data_importacao(valor_excel(row, ["TERM GRAV", "TERMINO GRAV", "TÉRMINO GRAV", "TERMINO GRAVACAO", "TÉRMINO GRAVAÇÃO"]))
    dias_planilha = inteiro_importacao(valor_excel(row, ["DIAS DE GRAVACAO", "DIAS DE GRAVAÇÃO", "DIAS GRAVACAO", "DIAS GRAVAÇÃO"]))
    dias_calculados = calcular_dias_gravacao(inicio_gravacao, termino_gravacao) if inicio_gravacao and termino_gravacao else dias_planilha

    return {
        "numero": inteiro_importacao(valor_excel(row, ["N", "N°", "Nº", "NUMERO", "NÚMERO"])),
        "operacao": texto_importacao(valor_excel(row, ["OPERACAO", "OPERAÇÃO"])),
        "nome_camera": texto_importacao(valor_excel(row, ["NOME CAM", "NOME CAMERA", "NOME CÂMERA", "CAMERA", "CÂMERA"])),
        "canal": texto_importacao(valor_excel(row, ["CANAL"])),
        "ip_camera": texto_importacao(valor_excel(row, ["IP CAMERA", "IP CAMERA", "IP CÂMERA", "IP"])),
        "login_camera": texto_importacao(valor_excel(row, ["LOGIN", "LOGIN CAMERA", "LOGIN CÂMERA"])),
        "senha_camera": texto_importacao(valor_excel(row, ["SENHA", "SENHA CAMERA", "SENHA CÂMERA"])),
        "modelo": texto_importacao(valor_excel(row, ["MODELO"])),
        "marca": texto_importacao(valor_excel(row, ["MARCA CAM", "MARCA", "FABRICANTE"])),
        "inicio_gravacao": inicio_gravacao,
        "termino_gravacao": termino_gravacao,
        "dias_gravacao": dias_calculados,
        "nvr": texto_importacao(valor_excel(row, ["NVR"])),
        "ip_nvr": texto_importacao(valor_excel(row, ["IP NVR"])),
        "login_nvr": texto_importacao(valor_excel(row, ["LOGIN NVR"])),
        "senha_nvr": texto_importacao(valor_excel(row, ["SENHA NVR"])),
        "rack": texto_importacao(valor_excel(row, ["RACK"])),
        "status": status if status else "ATIVA",
        "qualidade_gravacao": qualidade if qualidade else "BOA",
        "observacao": texto_importacao(valor_excel(row, ["OBSE", "OBS", "OBSERVACAO", "OBSERVAÇÃO"])),
        "horario": texto_importacao(valor_excel(row, ["HORARIO", "HORÁRIO"])),
        "acao_necessaria": texto_importacao(valor_excel(row, ["ACAO NECESSARIA", "AÇÃO NECESSÁRIA", "ACAO", "AÇÃO"])),
        "serie_number": texto_importacao(valor_excel(row, ["SERIE NUMBER", "SÉRIE NUMBER", "SERIAL", "NUMERO SERIE", "NÚMERO SÉRIE"])),
        "foto_camera": None,
        "foto_nome": None,
    }


def preparar_planilha_importacao(arquivo):
    raw = pd.read_excel(arquivo, sheet_name=0)
    raw = raw.dropna(how="all")
    raw.columns = [normalizar_coluna_excel(c) for c in raw.columns]

    registros = []
    rejeitados = []
    for idx, row in raw.iterrows():
        payload = montar_payload_importacao(row)
        if not payload["nome_camera"]:
            rejeitados.append({"linha_excel": int(idx) + 2, "motivo": "Nome da câmera vazio"})
            continue
        registros.append(payload)
    return registros, rejeitados


def importar_cameras_planilha(arquivo, modo):
    registros, rejeitados = preparar_planilha_importacao(arquivo)
    inseridos = 0
    atualizados = 0
    ignorados = 0

    for payload in registros:
        ip = payload.get("ip_camera", "").strip()
        existente = pd.DataFrame()
        if ip:
            existente = consultar_df("SELECT id FROM cameras WHERE ip_camera = :ip LIMIT 1", {"ip": ip})

        if not existente.empty and modo == "Ignorar IPs já cadastrados":
            ignorados += 1
            continue

        if not existente.empty and modo == "Atualizar pelo IP da câmera":
            payload_update = dict(payload)
            payload_update["id"] = int(existente.iloc[0]["id"])
            executar_sql(
                """
                UPDATE cameras
                SET
                    numero = :numero,
                    operacao = :operacao,
                    nome_camera = :nome_camera,
                    canal = :canal,
                    login_camera = :login_camera,
                    senha_camera = :senha_camera,
                    modelo = :modelo,
                    marca = :marca,
                    inicio_gravacao = :inicio_gravacao,
                    termino_gravacao = :termino_gravacao,
                    dias_gravacao = :dias_gravacao,
                    nvr = :nvr,
                    ip_nvr = :ip_nvr,
                    login_nvr = :login_nvr,
                    senha_nvr = :senha_nvr,
                    rack = :rack,
                    status = :status,
                    qualidade_gravacao = :qualidade_gravacao,
                    observacao = :observacao,
                    horario = :horario,
                    acao_necessaria = :acao_necessaria,
                    serie_number = :serie_number,
                    ativo = TRUE,
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE id = :id
                """,
                payload_update,
            )
            atualizados += 1
            continue

        executar_sql(
            """
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
            """,
            payload,
        )
        inseridos += 1

    registrar_historico(None, "Importação de planilha", f"Inseridos: {inseridos} | Atualizados: {atualizados} | Ignorados: {ignorados}")
    return {
        "lidos": len(registros),
        "inseridos": inseridos,
        "atualizados": atualizados,
        "ignorados": ignorados,
        "rejeitados": rejeitados,
    }


def atualizar_camera_completa(camera_id, dados, foto=None, foto_nome=None):
    payload = dict(dados)
    payload["id"] = int(camera_id)
    set_foto_sql = ""
    if foto is not None:
        payload["foto_camera"] = foto
        payload["foto_nome"] = foto_nome
        set_foto_sql = ", foto_camera = :foto_camera, foto_nome = :foto_nome"

    executar_sql(
        f"""
        UPDATE cameras
        SET
            numero = :numero,
            operacao = :operacao,
            nome_camera = :nome_camera,
            canal = :canal,
            ip_camera = :ip_camera,
            login_camera = :login_camera,
            senha_camera = :senha_camera,
            modelo = :modelo,
            marca = :marca,
            inicio_gravacao = :inicio_gravacao,
            termino_gravacao = :termino_gravacao,
            dias_gravacao = :dias_gravacao,
            nvr = :nvr,
            ip_nvr = :ip_nvr,
            login_nvr = :login_nvr,
            senha_nvr = :senha_nvr,
            rack = :rack,
            status = :status,
            qualidade_gravacao = :qualidade_gravacao,
            observacao = :observacao,
            horario = :horario,
            acao_necessaria = :acao_necessaria,
            serie_number = :serie_number,
            ativo = :ativo,
            atualizado_em = CURRENT_TIMESTAMP
            {set_foto_sql}
        WHERE id = :id
        """,
        payload,
    )
    registrar_historico(int(camera_id), "Edição de câmera", "Dados técnicos/foto atualizados")


def atualizar_status(camera_id, status, qualidade, observacao, acao):
    executar_sql(
        """
        UPDATE cameras
        SET status = :status,
            qualidade_gravacao = :qualidade,
            observacao = :observacao,
            acao_necessaria = :acao,
            atualizado_em = CURRENT_TIMESTAMP
        WHERE id = :id
        """,
        {
            "id": camera_id,
            "status": status,
            "qualidade": qualidade,
            "observacao": observacao,
            "acao": acao,
        },
    )
    registrar_historico(int(camera_id), "Atualização de status", f"Status: {status} | Qualidade: {qualidade}")


def desativar_camera(camera_id):
    executar_sql(
        """
        UPDATE cameras
        SET ativo = FALSE,
            status = 'INATIVA',
            atualizado_em = CURRENT_TIMESTAMP
        WHERE id = :id
        """,
        {"id": camera_id},
    )
    registrar_historico(int(camera_id), "Desativação", "Câmera desativada mantendo histórico")


def reativar_camera(camera_id):
    executar_sql(
        """
        UPDATE cameras
        SET ativo = TRUE,
            status = 'ATIVA',
            atualizado_em = CURRENT_TIMESTAMP
        WHERE id = :id
        """,
        {"id": camera_id},
    )
    registrar_historico(int(camera_id), "Reativação", "Câmera reativada")


def excluir_camera(camera_id):
    registrar_historico(int(camera_id), "Exclusão definitiva", "Registro removido da base")
    executar_sql("DELETE FROM cameras WHERE id = :id", {"id": camera_id})


# =====================================================
# TABELAS COMPLEMENTARES: HISTÓRICO, MANUTENÇÃO, EXPANSÃO E BACKUP
# =====================================================
def garantir_tabelas_complementares():
    executar_sql(
        """
        CREATE TABLE IF NOT EXISTS camera_audit_log (
            id SERIAL PRIMARY KEY,
            camera_id INTEGER,
            acao TEXT NOT NULL,
            detalhe TEXT,
            usuario TEXT DEFAULT 'Sistema',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    executar_sql(
        """
        CREATE TABLE IF NOT EXISTS camera_maintenance (
            id SERIAL PRIMARY KEY,
            camera_id INTEGER,
            tipo TEXT,
            prioridade TEXT,
            descricao TEXT,
            responsavel TEXT,
            status TEXT DEFAULT 'ABERTO',
            prazo DATE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    executar_sql(
        """
        CREATE TABLE IF NOT EXISTS camera_expansion_plan (
            id SERIAL PRIMARY KEY,
            operacao TEXT UNIQUE,
            meta INTEGER DEFAULT 0,
            observacao TEXT,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def registrar_historico(camera_id, acao, detalhe="", usuario="Sistema"):
    try:
        executar_sql(
            """
            INSERT INTO camera_audit_log (camera_id, acao, detalhe, usuario)
            VALUES (:camera_id, :acao, :detalhe, :usuario)
            """,
            {"camera_id": camera_id, "acao": acao, "detalhe": detalhe, "usuario": usuario},
        )
    except Exception:
        pass


def carregar_historico(limit=300):
    try:
        return consultar_df(
            """
            SELECT h.id, h.camera_id, c.numero, c.operacao, c.nome_camera,
                   h.acao, h.detalhe, h.usuario, h.criado_em
            FROM camera_audit_log h
            LEFT JOIN cameras c ON c.id = h.camera_id
            ORDER BY h.criado_em DESC, h.id DESC
            LIMIT :limit
            """,
            {"limit": limit},
        )
    except Exception:
        return pd.DataFrame()


def registrar_manutencao(camera_id, tipo, prioridade, descricao, responsavel, status, prazo):
    executar_sql(
        """
        INSERT INTO camera_maintenance (camera_id, tipo, prioridade, descricao, responsavel, status, prazo)
        VALUES (:camera_id, :tipo, :prioridade, :descricao, :responsavel, :status, :prazo)
        """,
        {
            "camera_id": camera_id,
            "tipo": tipo,
            "prioridade": prioridade,
            "descricao": descricao,
            "responsavel": responsavel,
            "status": status,
            "prazo": prazo,
        },
    )
    registrar_historico(camera_id, "Registro de manutenção", f"{tipo} | {prioridade} | {status}")


def atualizar_status_manutencao(manutencao_id, status):
    executar_sql(
        """
        UPDATE camera_maintenance
        SET status = :status, atualizado_em = CURRENT_TIMESTAMP
        WHERE id = :id
        """,
        {"id": int(manutencao_id), "status": status},
    )


def carregar_manutencoes():
    try:
        return consultar_df(
            """
            SELECT m.id, m.camera_id, c.numero, c.operacao, c.nome_camera,
                   m.tipo, m.prioridade, m.descricao, m.responsavel, m.status, m.prazo,
                   m.criado_em, m.atualizado_em
            FROM camera_maintenance m
            LEFT JOIN cameras c ON c.id = m.camera_id
            ORDER BY m.criado_em DESC, m.id DESC
            """
        )
    except Exception:
        return pd.DataFrame()


def carregar_expansao():
    try:
        return consultar_df("SELECT id, operacao, meta, observacao, atualizado_em FROM camera_expansion_plan ORDER BY operacao")
    except Exception:
        return pd.DataFrame()


def salvar_meta_expansao(operacao, meta, observacao):
    executar_sql(
        """
        INSERT INTO camera_expansion_plan (operacao, meta, observacao, atualizado_em)
        VALUES (:operacao, :meta, :observacao, CURRENT_TIMESTAMP)
        ON CONFLICT (operacao)
        DO UPDATE SET meta = EXCLUDED.meta, observacao = EXCLUDED.observacao, atualizado_em = CURRENT_TIMESTAMP
        """,
        {"operacao": operacao, "meta": int(meta), "observacao": observacao},
    )
    registrar_historico(None, "Plano de expansão", f"{operacao}: meta {meta}")


def gerar_backup_excel(df_base):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_base.to_excel(writer, sheet_name="cameras", index=False)
        hist = carregar_historico(5000)
        if not hist.empty:
            hist.to_excel(writer, sheet_name="historico", index=False)
        manut = carregar_manutencoes()
        if not manut.empty:
            manut.to_excel(writer, sheet_name="manutencao", index=False)
        exp = carregar_expansao()
        if not exp.empty:
            exp.to_excel(writer, sheet_name="expansao", index=False)
    output.seek(0)
    return output

# =====================================================
# FUNÇÕES AUXILIARES
# =====================================================
def br_now():
    return datetime.now(ZoneInfo("America/Sao_Paulo"))


def safe_text(value, default="Não informado"):
    if value is None or pd.isna(value):
        return default
    value = str(value).strip()
    if value == "" or value.lower() in ["nan", "none", "undefined", "null"]:
        return default
    return value


def esc(value, default="Não informado"):
    return html.escape(safe_text(value, default))


def safe_int(value, default=0):
    try:
        if value is None or pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def safe_date_for_input(value):
    if value is None or pd.isna(value):
        return br_now().date()
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return br_now().date()


def calcular_dias_gravacao(inicio, termino):
    """Calcula automaticamente a quantidade de dias gravados.

    A regra usada é a diferença simples entre a data de término e a data de início.
    Se a data final for anterior à inicial, retorna 0 para evitar valores negativos.
    """
    try:
        inicio_dt = pd.to_datetime(inicio).date()
        termino_dt = pd.to_datetime(termino).date()
        return max((termino_dt - inicio_dt).days, 0)
    except Exception:
        return 0


def acao_pendente_valida(value):
    """Retorna True somente quando a ação necessária representa uma pendência real.
    Valores administrativos como "Não informado", "N/A" e "OK" são ignorados.
    """
    import unicodedata

    txt = safe_text(value, "").strip().upper()
    txt = unicodedata.normalize("NFKD", txt).encode("ASCII", "ignore").decode("ASCII")
    txt = " ".join(txt.replace(".", " ").replace("-", " ").replace("_", " ").split())
    sem_pendencia = {
        "", "NAO", "N", "N/A", "NA", "NONE", "NULL", "NAN", "OK", "O K",
        "SEM ACAO", "SEM ACOES", "NENHUMA", "NENHUM", "NAO SE APLICA",
        "NAO APLICA", "NAO INFORMADO", "NAO INFORMADA", "INFORMADO",
        "SEM INFORMACAO", "SEM INFORMACOES"
    }
    return txt not in sem_pendencia


def normalizar_base(df):
    if df.empty:
        return df
    out = df.copy()
    texto_cols = [
        "operacao",
        "nome_camera",
        "status",
        "qualidade_gravacao",
        "nvr",
        "rack",
        "ip_camera",
        "canal",
        "modelo",
        "marca",
        "observacao",
        "acao_necessaria",
    ]
    for col in texto_cols:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: safe_text(x))

    if "dias_gravacao" in out.columns:
        out["dias_gravacao"] = pd.to_numeric(out["dias_gravacao"], errors="coerce").fillna(0)

    out["status_upper"] = out["status"].fillna("").str.upper()
    out["qualidade_upper"] = out["qualidade_gravacao"].fillna("").str.upper()
    out["is_ativa"] = (out["ativo"] == True) & (out["status_upper"] == "ATIVA")
    out["is_inativa"] = (out["ativo"] == False) | out["status_upper"].str.contains("INATIVA", na=False)
    out["is_sem_gravacao"] = out["status_upper"].str.contains("SEM GRAVAÇÃO", na=False) | out[
        "qualidade_upper"
    ].str.contains("SEM GRAVAÇÃO", na=False)
    out["is_falha"] = out["status_upper"].str.contains("FALHA", na=False) | out["qualidade_upper"].str.contains(
        "RUIM|SEM IMAGEM", na=False
    )
    out["is_manutencao"] = out["status_upper"].str.contains("MANUT", na=False)
    out["has_pendencia"] = out["acao_necessaria"].apply(acao_pendente_valida)
    # Criticidade real: problemas técnicos/status/qualidade ou ação relevante.
    # Câmeras apenas INATIVAS ficam em card próprio e não inflam a lista de pendências.
    out["is_critica"] = out["has_pendencia"] | out["is_falha"] | out["is_sem_gravacao"] | out["is_manutencao"]
    return out


def cameras_unicas_por_numero(df):
    """Base operacional única: prioriza Nº da câmera; fallback por IP; por último ID.
    Isso evita que imports/edições duplicadas inflem os indicadores do dashboard.
    """
    if df.empty:
        return df
    base = normalizar_base(df).copy()
    base["numero_num"] = pd.to_numeric(base.get("numero"), errors="coerce")

    def make_key(row):
        numero = row.get("numero_num")
        if pd.notna(numero) and int(numero) > 0:
            return f"NUM-{int(numero)}"
        ip = safe_text(row.get("ip_camera"), "").strip()
        if ip and ip != "Não informado":
            return f"IP-{ip}"
        return f"ID-{row.get('id')}"

    base["camera_key"] = base.apply(make_key, axis=1)
    # carregar_cameras já vem com ID desc; keep=first mantém o registro mais recente do mesmo Nº/IP.
    base = base.drop_duplicates(subset=["camera_key"], keep="first").copy()
    return base


def calcular_metricas(df):
    if df.empty:
        return {
            "total": 0,
            "ativas": 0,
            "inativas": 0,
            "pendencias": 0,
            "sem_gravacao": 0,
            "falhas": 0,
            "disponibilidade": 0,
            "nvrs": 0,
        }
    base = cameras_unicas_por_numero(df)
    total = len(base)
    ativas = int(base["is_ativa"].sum())
    inativas = int(base["is_inativa"].sum())
    pendencias = int(base["is_critica"].sum())
    sem_gravacao = int(base["is_sem_gravacao"].sum())
    falhas = int((base["is_falha"] | base["is_sem_gravacao"]).sum())
    disponibilidade = round((ativas / total) * 100, 1) if total else 0
    nvrs = base["nvr"].replace("Não informado", pd.NA).dropna().nunique()
    return {
        "total": total,
        "ativas": ativas,
        "inativas": inativas,
        "pendencias": pendencias,
        "sem_gravacao": sem_gravacao,
        "falhas": falhas,
        "disponibilidade": disponibilidade,
        "nvrs": int(nvrs),
    }


def status_class(status):
    s = safe_text(status, "").upper()
    if s == "ATIVA":
        return "status-green"
    if "MANUT" in s or "REGULAR" in s:
        return "status-yellow"
    if "FALHA" in s or "SEM" in s or "INATIVA" in s:
        return "status-red"
    return "status-gray"


def bytes_to_image_bytes(img_bytes):
    if img_bytes is None or pd.isna(img_bytes):
        return None
    if isinstance(img_bytes, memoryview):
        img_bytes = img_bytes.tobytes()
    if isinstance(img_bytes, bytearray):
        img_bytes = bytes(img_bytes)
    if not isinstance(img_bytes, (bytes, bytearray)):
        return None
    # Proteção: não renderiza texto/código salvo por engano como imagem.
    start = bytes(img_bytes[:80]).lstrip().lower()
    if start.startswith(b"<div") or start.startswith(b"<html") or start.startswith(b"import ") or start.startswith(b"st."):
        return None
    return img_bytes


def configurar_figura(fig, height=360):
    fig.update_layout(
        title=dict(text=""),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#1F2937", family="Inter", size=13),
        margin=dict(l=8, r=18, t=10, b=24),
        bargap=0.28,
        hoverlabel=dict(bgcolor="#111827", font_color="#FFFFFF", bordercolor="#111827"),
    )
    fig.update_xaxes(gridcolor="#EEF2F7", zerolinecolor="#EEF2F7", title_font=dict(size=12), tickfont=dict(size=12), showline=False)
    fig.update_yaxes(gridcolor="#EEF2F7", zerolinecolor="#EEF2F7", title_font=dict(size=12), tickfont=dict(size=12), showline=False)
    return fig


def cor_disponibilidade(valor):
    if valor >= 98:
        return "#0E9F6E"
    if valor >= 95:
        return "#F59E0B"
    return "#D40511"


def cor_risco(valor):
    if valor <= 0:
        return "#0E9F6E"
    if valor <= 2:
        return "#F59E0B"
    return "#D40511"


def grafico_barra_executivo(df_plot, x, y, texto=None, modo="dhl", altura=360, sufixo=""):
    if df_plot.empty:
        return go.Figure()
    valores = pd.to_numeric(df_plot[x], errors="coerce").fillna(0)
    if modo == "disp":
        cores = [cor_disponibilidade(v) for v in valores]
    elif modo == "risco":
        cores = [cor_risco(v) for v in valores]
    elif modo == "nvr":
        maxv = max(float(valores.max()), 1)
        cores = ["#D40511" if v >= maxv * 0.85 else "#F59E0B" if v >= maxv * 0.60 else "#FFCC00" for v in valores]
    else:
        cores = ["#D40511" if i == len(valores)-1 else "#FFCC00" for i in range(len(valores))]
    text_values = [f"{v:.1f}{sufixo}" if isinstance(v, float) and not float(v).is_integer() else f"{int(v)}{sufixo}" for v in valores]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=valores,
        y=df_plot[y].astype(str),
        orientation="h",
        text=text_values if texto is None else df_plot[texto].astype(str),
        textposition="outside",
        marker=dict(color=cores, line=dict(width=0), cornerradius=8),
        hovertemplate="<b>%{y}</b><br>Valor: %{x}<extra></extra>",
    ))
    fig.update_layout(
        height=altura,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#1F2937", family="Inter", size=13),
        margin=dict(l=8, r=38, t=8, b=26),
        bargap=0.38,
        showlegend=False,
        hoverlabel=dict(bgcolor="#111827", font_color="#FFFFFF"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#EEF2F7", zeroline=False, title="")
    fig.update_yaxes(showgrid=False, title="", automargin=True)
    return fig


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
        <div class="kpi-title">{html.escape(str(title))}</div>
        <div class="{val_cls}">{html.escape(str(value))}</div>
        <div class="kpi-caption">{html.escape(str(caption))}</div>
    </div>
    """

# =====================================================
# CSS PROFISSIONAL DHL V8
# =====================================================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

:root {
    --dhl-yellow: #FFCC00;
    --dhl-yellow-soft: #FFF7CC;
    --dhl-red: #D40511;
    --dhl-red-dark: #99000B;
    --bg: #F4F6F8;
    --surface: #FFFFFF;
    --surface-2: #F9FAFB;
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
        radial-gradient(circle at top right, rgba(255, 204, 0, .18), transparent 30%),
        linear-gradient(180deg, #F7F8FA 0%, #EEF1F5 100%);
    color: var(--text);
}

#MainMenu, footer, header { visibility: hidden; }

.block-container {
    padding-top: 1.15rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 100% !important;
}

section[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid var(--border);
    box-shadow: 8px 0 30px rgba(15, 23, 42, 0.07);
}

section[data-testid="stSidebar"] * { color: var(--text) !important; }

.sidebar-brand {
    background: linear-gradient(135deg, var(--dhl-yellow) 0%, #FFE57A 100%);
    border-radius: 24px;
    padding: 24px 20px;
    margin: 4px 0 18px 0;
    border: 1px solid #E8B900;
    box-shadow: 0 14px 34px rgba(255, 204, 0, 0.30);
    position: relative;
    overflow: hidden;
}
.sidebar-brand:after {
    content: "";
    position: absolute;
    width: 150px;
    height: 150px;
    right: -70px;
    bottom: -70px;
    background: rgba(212, 5, 17, .12);
    border-radius: 50%;
}
.sidebar-brand .brand-title {
    font-weight: 900;
    color: var(--dhl-red) !important;
    font-size: 25px;
    line-height: 1.05;
    letter-spacing: -0.04em;
    position: relative;
    z-index: 2;
}
.sidebar-brand .brand-subtitle {
    color: #2B2B2B !important;
    font-size: 11px;
    font-weight: 900;
    margin-top: 10px;
    text-transform: uppercase;
    letter-spacing: .10em;
    position: relative;
    z-index: 2;
}
.sidebar-section {
    font-size: 11px;
    color: var(--muted) !important;
    text-transform: uppercase;
    letter-spacing: .14em;
    font-weight: 900;
    margin-top: 18px;
    margin-bottom: 8px;
}
.sidebar-mini-card {
    background: #F9FAFB;
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 14px 15px;
    margin-bottom: 10px;
    box-shadow: 0 8px 22px rgba(15,23,42,.035);
}
.sidebar-mini-card .mini-title {
    color: var(--muted) !important;
    font-size: 10px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .08em;
}
.sidebar-mini-card .mini-value {
    color: var(--dhl-red) !important;
    font-size: 24px;
    font-weight: 900;
    margin-top: 3px;
}

/* Menu lateral */
div[role="radiogroup"] label {
    background: #FFFFFF !important;
    border: 1px solid transparent !important;
    border-radius: 14px !important;
    padding: 11px 12px !important;
    margin-bottom: 7px !important;
    transition: all .16s ease;
    font-weight: 700 !important;
}
div[role="radiogroup"] label:hover {
    background: #FFF7CC !important;
    border-color: #FFE066 !important;
    transform: translateX(2px);
}
div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child { display: none !important; }

.app-header {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 26px;
    padding: 26px 30px;
    margin-bottom: 20px;
    box-shadow: 0 18px 44px rgba(15, 23, 42, 0.07);
    position: relative;
    overflow: hidden;
}
.app-header:before {
    content: "";
    position: absolute;
    inset: 0 0 auto 0;
    height: 8px;
    background: linear-gradient(90deg, var(--dhl-red) 0%, var(--dhl-red) 24%, var(--dhl-yellow) 24%, var(--dhl-yellow) 100%);
}
.app-header-grid {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 24px;
    align-items: center;
    margin-top: 8px;
}
.header-title {
    font-size: 32px;
    font-weight: 900;
    color: var(--text);
    line-height: 1.1;
    letter-spacing: -0.045em;
}
.header-subtitle {
    color: var(--muted);
    font-size: 14px;
    margin-top: 8px;
    font-weight: 700;
}
.header-right {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
    justify-content: flex-end;
}
.badge {
    padding: 9px 13px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 900;
    border: 1px solid var(--border);
    background: #F9FAFB;
    color: var(--text);
}
.badge-online { background: #ECFDF5; color: #047857; border-color: #A7F3D0; }

.kpi-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 18px 18px 16px 18px;
    height: 136px;
    min-height: 136px;
    max-height: 136px;
    box-shadow: 0 11px 30px rgba(15, 23, 42, 0.055);
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
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
    font-size: 10px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .12em;
    font-weight: 900;
    margin-left: 4px;
    min-height: 24px;
}
.kpi-value {
    font-size: 28px;
    color: var(--text);
    font-weight: 900;
    margin-left: 4px;
    line-height: 1;
    white-space: nowrap;
}
.kpi-value.red { color: var(--dhl-red); }
.kpi-value.green { color: var(--success); }
.kpi-value.yellow { color: var(--warning); }
.kpi-caption {
    margin-left: 4px;
    font-size: 11px;
    color: var(--muted);
    font-weight: 700;
    min-height: 18px;
}
.panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 20px;
    box-shadow: 0 12px 34px rgba(15, 23, 42, 0.055);
    margin-bottom: 18px;
}
.panel-title {
    font-size: 18px;
    font-weight: 900;
    color: var(--text);
    margin-bottom: 12px;
    letter-spacing: -0.025em;
}
.panel-subtitle {
    color: var(--muted);
    font-size: 13px;
    margin-top: -7px;
    margin-bottom: 12px;
    font-weight: 500;
}
.form-section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 22px;
    box-shadow: 0 12px 34px rgba(15, 23, 42, 0.055);
}
.camera-card-title { font-size: 20px; font-weight: 900; color: var(--text); margin-bottom: 4px; }
.camera-card-subtitle { color: var(--muted); font-size: 13px; margin-bottom: 18px; }
.status-pill { display: inline-block; padding: 5px 9px; border-radius: 999px; font-size: 10px; font-weight: 900; text-transform: uppercase; }
.status-green { background: #ECFDF5; color: #047857; }
.status-yellow { background: #FFFBEB; color: #B45309; }
.status-red { background: #FEF2F2; color: var(--dhl-red); }
.status-gray { background: #F3F4F6; color: #4B5563; }

.stButton button {
    border-radius: 12px !important;
    background: var(--dhl-yellow) !important;
    color: #111827 !important;
    border: 1px solid #E8B900 !important;
    font-weight: 900 !important;
    min-height: 42px;
}
.stButton button:hover { background: #F4C400 !important; color: #111827 !important; }
.stDownloadButton button {
    border-radius: 12px !important;
    background: var(--dhl-red) !important;
    color: #FFFFFF !important;
    border: 1px solid var(--dhl-red-dark) !important;
    font-weight: 900 !important;
}
[data-testid="stDataFrame"] { border-radius: 18px; overflow: hidden; border: 1px solid var(--border); box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04); }
input, textarea { border-radius: 12px !important; }
div[data-baseweb="select"] > div { border-radius: 12px !important; }
hr { border-color: var(--border); }
@media (max-width: 1200px) { .app-header-grid { grid-template-columns: 1fr; } }

.metric-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-top: 10px;
}
.metric-strip-item {
    background: #F9FAFB;
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 12px 14px;
}
.metric-strip-label {
    color: var(--muted);
    font-size: 10px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .10em;
}
.metric-strip-value {
    color: var(--text);
    font-size: 22px;
    font-weight: 900;
    margin-top: 4px;
}
.executive-note {
    background: #FFF7CC;
    border: 1px solid #FDE68A;
    border-left: 6px solid var(--dhl-yellow);
    border-radius: 18px;
    padding: 14px 16px;
    font-size: 13px;
    color: #3F3F46;
    font-weight: 650;
    margin-bottom: 16px;
}
.status-summary-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
    margin-top: 8px;
}
.status-summary-row {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 10px;
    align-items: center;
    background: #F9FAFB;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 11px 12px;
}
.status-summary-name {
    font-weight: 900;
    color: var(--text);
}
.status-summary-count {
    font-weight: 900;
    color: var(--dhl-red);
    font-size: 18px;
}


.calc-field{
    background:#ffffff;
    border:1px solid #e5e7eb;
    border-left:5px solid #FFCC00;
    border-radius:14px;
    height:74px;
    padding:10px 14px;
    display:flex;
    flex-direction:column;
    justify-content:center;
    box-shadow:0 4px 14px rgba(17,24,39,.04);
}
.calc-label{
    font-size:12px;
    color:#6b7280;
    font-weight:700;
    margin-bottom:2px;
}
.calc-value{
    font-size:21px;
    line-height:1.1;
    font-weight:800;
    color:#D40511;
}
.calc-hint{
    font-size:10px;
    color:#9ca3af;
    margin-top:2px;
    font-weight:600;
}

.badge-version{
    background:#F3F4F6;
    color:#374151;
    font-size:12px;
}
.sidebar-version{
    margin-top:14px;
    color:#6B7280;
    font-size:11px;
    font-weight:700;
    letter-spacing:.04em;
    text-transform:uppercase;
}
.version-chip{
    display:inline-flex;
    align-items:center;
    padding:6px 10px;
    border-radius:999px;
    background:#FFFFFF;
    border:1px solid #E5E7EB;
    color:#6B7280;
    font-size:11px;
    font-weight:800;
    box-shadow:0 4px 14px rgba(0,0,0,.04);
}
.edit-filter-box{
    background:#FFFFFF;
    border:1px solid #E5E7EB;
    border-radius:20px;
    padding:18px;
    margin:6px 0 20px 0;
    box-shadow:0 8px 24px rgba(0,0,0,.04);
}

</style>
""",
    unsafe_allow_html=True,
)

# =====================================================
# DADOS E MÉTRICAS
# =====================================================
garantir_tabelas_complementares()
df = carregar_cameras()
df_norm_all = normalizar_base(df)
df_norm = cameras_unicas_por_numero(df)
metricas = calcular_metricas(df)

# =====================================================
# SIDEBAR PREMIUM
# =====================================================
st.sidebar.markdown(
    """
<div class="sidebar-brand">
    <div class="brand-title">DHL<br>Security</div>
    <div class="brand-subtitle">Camera Command Center</div>
</div>
""",
    unsafe_allow_html=True,
)

st.sidebar.markdown('<div class="sidebar-section">Navegação</div>', unsafe_allow_html=True)
menu = st.sidebar.radio(
    "",
    [
        "📊 Dashboard Executivo",
        "📷 Inventário Técnico",
        "🖼️ Book Visual",
        "➕ Nova Câmera",
        "📥 Importar Planilha",
        "✏️ Editar Câmera",
        "🔧 Manutenção",
        "📈 Expansão do Parque",
        "📄 Backup",
        "🧾 Histórico",
        "🗑️ Desativar / Excluir",
    ],
    label_visibility="collapsed",
)

st.sidebar.markdown('<div class="sidebar-section">Resumo operacional</div>', unsafe_allow_html=True)
st.sidebar.markdown(
    f"""
<div class="sidebar-mini-card">
    <div class="mini-title">Disponibilidade</div>
    <div class="mini-value">{metricas['disponibilidade']}%</div>
</div>
<div class="sidebar-mini-card">
    <div class="mini-title">Câmeras cadastradas</div>
    <div class="mini-value">{metricas['total']}</div>
</div>
<div class="sidebar-mini-card">
    <div class="mini-title">Inativas</div>
    <div class="mini-value">{metricas['inativas']}</div>
</div>
<div class="sidebar-mini-card">
    <div class="mini-title">Pendências</div>
    <div class="mini-value">{metricas['pendencias']}</div>
</div>
<div class="sidebar-version">Versão {APP_VERSION}</div>
""",
    unsafe_allow_html=True,
)

# =====================================================
# HEADER PROFISSIONAL
# =====================================================
last_update = br_now().strftime("%d/%m/%Y %H:%M")
st.markdown(
    f"""
<div class="app-header">
    <div class="app-header-grid">
        <div>
            <div class="header-title">DHL Security Camera Command Center</div>
            <div class="header-subtitle">ACF Extrema • Life Sciences • Gestão corporativa do parque de CFTV</div>
        </div>
        <div class="header-right">
            <div class="badge badge-online">Sistema Online</div>
            <div class="badge">Atualizado: {last_update}</div>
            <div class="badge badge-version">{APP_VERSION}</div>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# =====================================================
# DASHBOARD EXECUTIVO
# =====================================================
if menu == "📊 Dashboard Executivo":
    st.markdown(f'<div class="version-chip">Sistema {APP_VERSION}</div>', unsafe_allow_html=True)
    st.write("")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.markdown(kpi_card("Disponibilidade", f"{metricas['disponibilidade']}%", "base operacional", "success" if metricas["disponibilidade"] >= 98 else "warning" if metricas["disponibilidade"] >= 95 else "danger"), unsafe_allow_html=True)
    c2.markdown(kpi_card("Câmeras únicas", metricas["total"], "base por Nº/IP"), unsafe_allow_html=True)
    c3.markdown(kpi_card("Ativas", metricas["ativas"], "em operação", "success"), unsafe_allow_html=True)
    c4.markdown(kpi_card("Inativas", metricas["inativas"], "fora de operação", "warning" if metricas["inativas"] > 0 else "success"), unsafe_allow_html=True)
    c5.markdown(kpi_card("Sem gravação", metricas["sem_gravacao"], "falha crítica", "danger" if metricas["sem_gravacao"] > 0 else "success"), unsafe_allow_html=True)
    c6.markdown(kpi_card("Pendências reais", metricas["pendencias"], "falha/manutenção/ação", "danger" if metricas["pendencias"] > 0 else "success"), unsafe_allow_html=True)

    st.write("")

    if df_norm.empty:
        st.info("Nenhuma câmera cadastrada ainda.")
    else:
        op = df_norm.groupby("operacao", dropna=False).agg(
            total=("id", "count"),
            ativas=("is_ativa", "sum"),
            inativas=("is_inativa", "sum"),
            falhas=("is_falha", "sum"),
            sem_gravacao=("is_sem_gravacao", "sum"),
            pendencias=("is_critica", "sum"),
        ).reset_index()
        op["disponibilidade"] = (op["ativas"] / op["total"] * 100).round(1)
        op["risco"] = op["falhas"] + op["sem_gravacao"] + op["pendencias"] + op["inativas"]
        op["risco_nivel"] = op["risco"].apply(lambda v: "Alto" if v >= 4 else "Médio" if v >= 1 else "Baixo")

        registros_totais = len(df_norm_all)
        duplicidades = max(registros_totais - metricas["total"], 0)
        nvr_count = metricas.get("nvrs", 0)
        st.markdown(
            f'''
            <div class="executive-note">
                Os indicadores do dashboard usam câmeras únicas por Nº/IP para evitar distorções por importações duplicadas. Registros totais no banco: <b>{registros_totais}</b> • Possíveis duplicidades: <b>{duplicidades}</b> • NVRs identificados: <b>{nvr_count}</b>.
            </div>
            ''',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([1.08, 1])
        with col1:
            st.markdown('<div class="panel"><div class="panel-title">Disponibilidade por Operação</div><div class="panel-subtitle">Ranking para priorização operacional e manutenção.</div>', unsafe_allow_html=True)
            op_disp = op.sort_values("disponibilidade", ascending=True)
            fig_op = grafico_barra_executivo(op_disp, "disponibilidade", "operacao", modo="disp", altura=360, sufixo="%")
            fig_op.update_xaxes(range=[0, 105], title="Disponibilidade (%)")
            st.plotly_chart(fig_op, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="panel"><div class="panel-title">Saúde do Parque CFTV</div><div class="panel-subtitle">Leitura executiva sem gráfico pizza.</div>', unsafe_allow_html=True)
            disp = metricas["disponibilidade"]
            gauge_color = cor_disponibilidade(disp)
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=disp,
                number={"suffix": "%", "font": {"size": 44, "color": gauge_color}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "#CBD5E1"},
                    "bar": {"color": gauge_color, "thickness": 0.22},
                    "bgcolor": "#F9FAFB",
                    "borderwidth": 0,
                    "steps": [
                        {"range": [0, 95], "color": "#FEE2E2"},
                        {"range": [95, 98], "color": "#FEF3C7"},
                        {"range": [98, 100], "color": "#DCFCE7"},
                    ],
                    "threshold": {"line": {"color": "#111827", "width": 3}, "thickness": 0.75, "value": 98},
                },
                title={"text": "Disponibilidade geral", "font": {"size": 14, "color": "#6B7280"}},
            ))
            fig_gauge.update_layout(height=250, margin=dict(l=18, r=18, t=36, b=8), paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter"))
            st.plotly_chart(fig_gauge, use_container_width=True)
            st.markdown(
                f'''
                <div class="metric-strip">
                    <div class="metric-strip-item"><div class="metric-strip-label">Ativas</div><div class="metric-strip-value" style="color:#0E9F6E">{metricas['ativas']}</div></div>
                    <div class="metric-strip-item"><div class="metric-strip-label">Inativas</div><div class="metric-strip-value" style="color:#F59E0B">{metricas['inativas']}</div></div>
                    <div class="metric-strip-item"><div class="metric-strip-label">Falhas</div><div class="metric-strip-value" style="color:#D40511">{metricas['falhas']}</div></div>
                    <div class="metric-strip-item"><div class="metric-strip-label">Sem gravação</div><div class="metric-strip-value" style="color:#D40511">{metricas['sem_gravacao']}</div></div>
                </div>
                ''',
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        col3, col4 = st.columns([1.06, 1.02])
        with col3:
            st.markdown('<div class="panel"><div class="panel-title">Quantidade de Câmeras por Operação</div><div class="panel-subtitle">Distribuição real do parque por operação.</div>', unsafe_allow_html=True)
            op_qtd = op.sort_values("total", ascending=True)
            fig_qtd = grafico_barra_executivo(op_qtd, "total", "operacao", modo="qtd", altura=365)
            fig_qtd.update_xaxes(title="Câmeras únicas")
            st.plotly_chart(fig_qtd, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col4:
            st.markdown('<div class="panel"><div class="panel-title">Carga Operacional por NVR</div><div class="panel-subtitle">Ranking dos gravadores com maior quantidade de câmeras.</div>', unsafe_allow_html=True)
            nvr_df = df_norm.groupby("nvr", dropna=False).size().reset_index(name="total")
            nvr_df = nvr_df[~nvr_df["nvr"].isin(["", "Não informado", "Nao informado"])]
            nvr_df = nvr_df.sort_values("total", ascending=True).tail(12)
            fig_nvr = grafico_barra_executivo(nvr_df, "total", "nvr", modo="nvr", altura=365)
            fig_nvr.update_xaxes(title="Câmeras vinculadas")
            st.plotly_chart(fig_nvr, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        col5, col6 = st.columns([1.1, 1])
        with col5:
            st.markdown('<div class="panel"><div class="panel-title">Mapa de Criticidade por Operação</div><div class="panel-subtitle">Risco operacional consolidado: falhas, sem gravação, manutenção, ações reais e inativas.</div>', unsafe_allow_html=True)
            risco = op.sort_values("risco", ascending=False)[["operacao", "total", "ativas", "inativas", "falhas", "sem_gravacao", "pendencias", "disponibilidade", "risco", "risco_nivel"]]
            risco = risco.rename(columns={
                "operacao": "Operação", "total": "Total", "ativas": "Ativas", "inativas": "Inativas",
                "falhas": "Falhas", "sem_gravacao": "Sem gravação", "pendencias": "Pendências reais",
                "disponibilidade": "Disponibilidade %", "risco": "Score", "risco_nivel": "Risco"
            })
            st.dataframe(risco, use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col6:
            st.markdown('<div class="panel"><div class="panel-title">Distribuição por Status</div><div class="panel-subtitle">Contagem direta, mais legível que gráfico donut.</div>', unsafe_allow_html=True)
            status_df = df_norm.groupby("status", dropna=False).size().reset_index(name="total").sort_values("total", ascending=False)
            rows = ""
            for _, row in status_df.iterrows():
                st_name = safe_text(row["status"], "Não informado")
                val = int(row["total"])
                rows += f'<div class="status-summary-row"><div class="status-summary-name">{html.escape(st_name)}</div><div class="status-summary-count">{val}</div></div>'
            st.markdown(f'<div class="status-summary-grid">{rows}</div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        pend = df_norm[df_norm["is_critica"] == True].copy()
        pend = pend[["id", "numero", "operacao", "nome_camera", "ip_camera", "nvr", "status", "qualidade_gravacao", "acao_necessaria"]].head(20)
        st.markdown('<div class="panel"><div class="panel-title">Pendências Críticas Reais</div><div class="panel-subtitle">Exibe somente falha, sem gravação, manutenção, qualidade ruim/sem imagem ou ação necessária relevante. Não considera “Não informado” como pendência.</div>', unsafe_allow_html=True)
        if pend.empty:
            st.success("Nenhuma pendência crítica identificada.")
        else:
            st.dataframe(pend, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# INVENTÁRIO TÉCNICO
# =====================================================
elif menu == "📷 Inventário Técnico":
    st.markdown('<div class="panel"><div class="panel-title">Inventário Técnico de Câmeras</div><div class="panel-subtitle">Consulta, filtros e exportação da base técnica do parque de CFTV.</div>', unsafe_allow_html=True)
    if df_norm.empty:
        st.warning("Nenhuma câmera cadastrada.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        filtro_operacao = col1.text_input("Operação")
        filtro_status = col2.selectbox("Status", ["Todos"] + sorted(df_norm["status"].dropna().unique().tolist()))
        filtro_ativo = col3.selectbox("Situação", ["Todas", "Ativas", "Inativas"])
        filtro_busca = col4.text_input("Busca geral")
        df_filtro = df_norm.copy()
        if filtro_operacao:
            df_filtro = df_filtro[df_filtro["operacao"].str.contains(filtro_operacao, case=False, na=False)]
        if filtro_status != "Todos":
            df_filtro = df_filtro[df_filtro["status"] == filtro_status]
        if filtro_ativo == "Ativas":
            df_filtro = df_filtro[df_filtro["is_ativa"] == True]
        elif filtro_ativo == "Inativas":
            df_filtro = df_filtro[df_filtro["is_inativa"] == True]
        if filtro_busca:
            busca = filtro_busca.lower()
            df_filtro = df_filtro[
                df_filtro["nome_camera"].str.lower().str.contains(busca, na=False)
                | df_filtro["ip_camera"].str.lower().str.contains(busca, na=False)
                | df_filtro["nvr"].str.lower().str.contains(busca, na=False)
                | df_filtro["rack"].str.lower().str.contains(busca, na=False)
            ]
        cols = ["id", "numero", "operacao", "nome_camera", "canal", "ip_camera", "modelo", "marca", "dias_gravacao", "nvr", "ip_nvr", "rack", "status", "qualidade_gravacao", "observacao", "acao_necessaria", "serie_number", "ativo", "criado_em", "atualizado_em"]
        cols = [c for c in cols if c in df_filtro.columns]
        st.dataframe(df_filtro[cols], use_container_width=True, hide_index=True)
        df_filtro[cols].to_excel("inventario_cameras.xlsx", index=False)
        with open("inventario_cameras.xlsx", "rb") as file:
            st.download_button("Baixar inventário em Excel", file, file_name="inventario_cameras.xlsx")
    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# BOOK VISUAL - NATIVO STREAMLIT PARA EVITAR HTML/CÓDIGO APARECENDO
# =====================================================
elif menu == "🖼️ Book Visual":
    st.markdown('<div class="panel"><div class="camera-card-title">Book Visual de Câmeras</div><div class="camera-card-subtitle">Galeria operacional com imagens e principais informações técnicas.</div></div>', unsafe_allow_html=True)
    fotos_df = carregar_cameras_com_foto(60)
    if fotos_df.empty:
        st.info("Nenhuma câmera disponível para exibição visual.")
    else:
        busca_book = st.text_input("Filtrar book por câmera, operação, IP ou NVR")
        book_df = normalizar_base(fotos_df.drop(columns=["foto_camera", "foto_nome"], errors="ignore"))
        fotos_base = fotos_df.copy()
        if busca_book:
            busca = busca_book.lower()
            mask = (
                book_df["nome_camera"].str.lower().str.contains(busca, na=False)
                | book_df["operacao"].str.lower().str.contains(busca, na=False)
                | book_df["ip_camera"].str.lower().str.contains(busca, na=False)
                | book_df["nvr"].str.lower().str.contains(busca, na=False)
            )
            fotos_base = fotos_base[mask.values]

        for start in range(0, len(fotos_base), 4):
            cols = st.columns(4)
            for col, (_, row) in zip(cols, fotos_base.iloc[start:start + 4].iterrows()):
                with col:
                    with st.container(border=True):
                        img_bytes = bytes_to_image_bytes(row.get("foto_camera"))
                        if img_bytes:
                            st.image(img_bytes, use_container_width=True)
                        else:
                            st.markdown(
                                """
                                <div style="height:160px;border-radius:14px;background:linear-gradient(135deg,#F3F4F6,#FFFFFF);display:flex;align-items:center;justify-content:center;color:#9CA3AF;font-size:42px;border:1px solid #E5E7EB;">📷</div>
                                """,
                                unsafe_allow_html=True,
                            )
                        st.markdown(f"**{safe_text(row.get('nome_camera'))}**")
                        st.caption(f"{safe_text(row.get('operacao'))} • Canal {safe_text(row.get('canal'))}")
                        st.write(f"**IP:** {safe_text(row.get('ip_camera'))}")
                        st.write(f"**NVR:** {safe_text(row.get('nvr'))}")
                        st.write(f"**Rack:** {safe_text(row.get('rack'))}")
                        st.markdown(f"<span class='status-pill {status_class(row.get('status'))}'>{esc(row.get('status'))}</span>", unsafe_allow_html=True)

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
        col10, col11 = st.columns(2)
        modelo = col10.text_input("Modelo")
        marca = col11.text_input("Marca")
        st.markdown("##### Gravação e NVR")
        col13, col14, col15, col16a = st.columns([1, 1, 0.8, 1])
        inicio_gravacao = col13.date_input("Início gravação")
        termino_gravacao = col14.date_input("Término gravação")
        dias_gravacao = calcular_dias_gravacao(inicio_gravacao, termino_gravacao)
        col15.markdown(
            f"""
            <div class="calc-field">
                <div class="calc-label">📅 Dias de gravação</div>
                <div class="calc-value">{dias_gravacao} dias</div>
                <div class="calc-hint">calculado automaticamente</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        horario = col16a.text_input("Horário")
        col16, col17, col18 = st.columns(3)
        nvr = col16.text_input("NVR")
        ip_nvr = col17.text_input("IP NVR")
        login_nvr = col18.text_input("Login NVR")
        col19, col20 = st.columns(2)
        senha_nvr = col19.text_input("Senha NVR", type="password")
        status = col20.selectbox("Status", ["ATIVA", "INATIVA", "MANUTENÇÃO", "FALHA", "SEM GRAVAÇÃO"])
        qualidade_gravacao = st.selectbox("Qualidade da gravação", ["BOA", "REGULAR", "RUIM", "SEM IMAGEM", "SEM GRAVAÇÃO"])
        observacao = st.text_area("Observação")
        acao_necessaria = st.text_area("Ação necessária")
        foto_upload = st.file_uploader("Foto / imagem da câmera", type=["png", "jpg", "jpeg", "webp"])
        salvar = st.form_submit_button("Cadastrar câmera")
        if salvar:
            if not nome_camera:
                st.error("Informe o nome da câmera.")
            else:
                foto_bytes, foto_nome = imagem_para_bytes(foto_upload)
                cadastrar_camera({
                    "numero": numero, "operacao": operacao, "nome_camera": nome_camera, "canal": canal, "ip_camera": ip_camera,
                    "login_camera": login_camera, "senha_camera": senha_camera, "modelo": modelo, "marca": marca,
                    "inicio_gravacao": inicio_gravacao, "termino_gravacao": termino_gravacao, "dias_gravacao": dias_gravacao,
                    "nvr": nvr, "ip_nvr": ip_nvr, "login_nvr": login_nvr, "senha_nvr": senha_nvr, "rack": rack,
                    "status": status, "qualidade_gravacao": qualidade_gravacao, "observacao": observacao, "horario": horario,
                    "acao_necessaria": acao_necessaria, "serie_number": serie_number
                }, foto_bytes, foto_nome)
                st.success("Câmera cadastrada com sucesso.")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# =====================================================
# IMPORTAR PLANILHA
# =====================================================
elif menu == "📥 Importar Planilha":
    st.markdown(
        '<div class="form-section"><h3>Importação em Lote de Câmeras</h3>',
        unsafe_allow_html=True,
    )
    st.write(
        "Envie a planilha Excel no modelo atual do controle de câmeras. "
        "O sistema importará os campos técnicos para o banco Neon. Imagens não são importadas por planilha; "
        "elas podem ser adicionadas depois na aba **Editar Câmera**."
    )

    arquivo_importacao = st.file_uploader(
        "Upload da planilha de câmeras (.xlsx)",
        type=["xlsx"],
        key="upload_planilha_cameras",
    )

    modo_importacao = st.selectbox(
        "Modo de importação",
        [
            "Ignorar IPs já cadastrados",
            "Atualizar pelo IP da câmera",
            "Adicionar tudo mesmo se houver duplicidade",
        ],
        help="Recomendado: usar 'Atualizar pelo IP da câmera' quando estiver subindo uma planilha atualizada do inventário.",
    )

    if arquivo_importacao is not None:
        try:
            registros_preview, rejeitados_preview = preparar_planilha_importacao(arquivo_importacao)
            preview_df = pd.DataFrame(registros_preview)
            st.success(f"Planilha lida com sucesso: {len(registros_preview)} câmera(s) válida(s) encontradas.")

            if rejeitados_preview:
                st.warning(f"{len(rejeitados_preview)} linha(s) serão ignoradas por inconsistência.")
                st.dataframe(pd.DataFrame(rejeitados_preview), use_container_width=True, hide_index=True)

            if not preview_df.empty:
                cols_preview = [
                    "numero", "operacao", "nome_camera", "canal", "ip_camera", "modelo", "marca",
                    "dias_gravacao", "nvr", "ip_nvr", "rack", "status", "qualidade_gravacao", "observacao",
                    "acao_necessaria", "serie_number"
                ]
                cols_preview = [c for c in cols_preview if c in preview_df.columns]
                st.markdown("#### Prévia dos dados que serão importados")
                st.dataframe(preview_df[cols_preview].head(50), use_container_width=True, hide_index=True)

                confirmar = st.checkbox(
                    "Confirmo que revisei a prévia e desejo importar os dados para o banco Neon.",
                    value=False,
                )

                if st.button("Importar câmeras em lote", disabled=not confirmar):
                    arquivo_importacao.seek(0)
                    resultado = importar_cameras_planilha(arquivo_importacao, modo_importacao)
                    st.success(
                        f"Importação concluída. Inseridas: {resultado['inseridos']} | "
                        f"Atualizadas: {resultado['atualizados']} | Ignoradas: {resultado['ignorados']} | "
                        f"Linhas rejeitadas: {len(resultado['rejeitados'])}"
                    )
                    st.cache_data.clear()
                    st.rerun()
        except Exception as e:
            st.error("Não foi possível importar a planilha. Verifique se o arquivo está no modelo correto.")
            st.exception(e)
    else:
        st.info("Aguardando envio da planilha Excel.")

    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# EDITAR CÂMERA
# =====================================================
elif menu == "✏️ Editar Câmera":
    st.markdown('<div class="form-section"><h3>Editar Informações da Câmera</h3>', unsafe_allow_html=True)
    if df_norm.empty:
        st.warning("Nenhuma câmera cadastrada.")
    else:
        st.markdown("""
        <div class="edit-filter-box">
            <b>Busca rápida</b><br>
            Use os filtros abaixo para localizar a câmera pelo gravador/NVR ou pelo nome da câmera antes de editar.
        </div>
        """, unsafe_allow_html=True)

        df_edit = df_norm.copy()
        filtro_col1, filtro_col2 = st.columns([1, 1.6])

        nvr_options = sorted([safe_text(x) for x in df_edit["nvr"].dropna().unique().tolist() if safe_text(x)])
        filtro_nvr = filtro_col1.selectbox("Filtrar por gravador / NVR", ["Todos"] + nvr_options)
        filtro_nome = filtro_col2.text_input("Filtrar por nome da câmera", placeholder="Ex.: RUA 2, DOCA, CAM, ADIUM...")

        if filtro_nvr != "Todos":
            df_edit = df_edit[df_edit["nvr"].fillna("").astype(str).str.upper() == filtro_nvr.upper()]

        if filtro_nome:
            df_edit = df_edit[df_edit["nome_camera"].fillna("").astype(str).str.contains(filtro_nome, case=False, na=False)]

        if df_edit.empty:
            st.warning("Nenhuma câmera encontrada com os filtros informados.")
            st.stop()

        camera_id = st.selectbox(
            "Selecione a câmera para editar",
            df_edit["id"].tolist(),
            format_func=lambda x: f'{x} - {df_edit[df_edit["id"] == x]["nome_camera"].iloc[0]} • NVR: {df_edit[df_edit["id"] == x]["nvr"].iloc[0]}',
        )
        row = carregar_camera_por_id(camera_id)
        if row is None:
            st.error("Câmera não encontrada.")
        else:
            with st.form("editar_camera"):
                st.markdown("##### Identificação")
                col1, col2, col3 = st.columns(3)
                numero = col1.number_input("Nº", min_value=0, step=1, value=safe_int(row.get("numero")))
                operacao = col2.text_input("Operação", value=safe_text(row.get("operacao"), ""))
                nome_camera = col3.text_input("Nome da câmera", value=safe_text(row.get("nome_camera"), ""))
                col4, col5, col6 = st.columns(3)
                canal = col4.text_input("Canal", value=safe_text(row.get("canal"), ""))
                ip_camera = col5.text_input("IP da câmera", value=safe_text(row.get("ip_camera"), ""))
                rack = col6.text_input("Rack", value=safe_text(row.get("rack"), ""))
                st.markdown("##### Dados técnicos")
                col7, col8, col9 = st.columns(3)
                login_camera = col7.text_input("Login câmera", value=safe_text(row.get("login_camera"), ""))
                senha_camera = col8.text_input("Senha câmera", value=safe_text(row.get("senha_camera"), ""), type="password")
                serie_number = col9.text_input("Série Number", value=safe_text(row.get("serie_number"), ""))
                col10, col11 = st.columns(2)
                modelo = col10.text_input("Modelo", value=safe_text(row.get("modelo"), ""))
                marca = col11.text_input("Marca", value=safe_text(row.get("marca"), ""))
                st.markdown("##### Gravação e NVR")
                col13, col14, col15, col16a = st.columns([1, 1, 0.8, 1])
                inicio_gravacao = col13.date_input("Início gravação", value=safe_date_for_input(row.get("inicio_gravacao")))
                termino_gravacao = col14.date_input("Término gravação", value=safe_date_for_input(row.get("termino_gravacao")))
                dias_gravacao = calcular_dias_gravacao(inicio_gravacao, termino_gravacao)
                col15.markdown(
            f"""
            <div class="calc-field">
                <div class="calc-label">📅 Dias de gravação</div>
                <div class="calc-value">{dias_gravacao} dias</div>
                <div class="calc-hint">calculado automaticamente</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
                horario = col16a.text_input("Horário", value=safe_text(row.get("horario"), ""))
                col16, col17, col18 = st.columns(3)
                nvr = col16.text_input("NVR", value=safe_text(row.get("nvr"), ""))
                ip_nvr = col17.text_input("IP NVR", value=safe_text(row.get("ip_nvr"), ""))
                login_nvr = col18.text_input("Login NVR", value=safe_text(row.get("login_nvr"), ""))
                col19, col20, col21 = st.columns(3)
                senha_nvr = col19.text_input("Senha NVR", value=safe_text(row.get("senha_nvr"), ""), type="password")
                status_options = ["ATIVA", "INATIVA", "MANUTENÇÃO", "FALHA", "SEM GRAVAÇÃO"]
                current_status = safe_text(row.get("status"), "ATIVA")
                status_idx = status_options.index(current_status) if current_status in status_options else 0
                status = col20.selectbox("Status", status_options, index=status_idx)
                ativo = col21.selectbox("Situação", [True, False], index=0 if bool(row.get("ativo")) else 1, format_func=lambda x: "Ativa" if x else "Inativa")
                qualidade_options = ["BOA", "REGULAR", "RUIM", "SEM IMAGEM", "SEM GRAVAÇÃO"]
                current_q = safe_text(row.get("qualidade_gravacao"), "BOA")
                q_idx = qualidade_options.index(current_q) if current_q in qualidade_options else 0
                qualidade_gravacao = st.selectbox("Qualidade da gravação", qualidade_options, index=q_idx)
                observacao = st.text_area("Observação", value=safe_text(row.get("observacao"), ""))
                acao_necessaria = st.text_area("Ação necessária", value=safe_text(row.get("acao_necessaria"), ""))
                foto_atual = bytes_to_image_bytes(row.get("foto_camera"))
                if foto_atual:
                    st.image(foto_atual, caption="Foto atual", width=280)
                foto_upload = st.file_uploader("Substituir foto da câmera", type=["png", "jpg", "jpeg", "webp"])
                salvar = st.form_submit_button("Salvar alterações")
                if salvar:
                    if not nome_camera:
                        st.error("Informe o nome da câmera.")
                    else:
                        foto_bytes, foto_nome = imagem_para_bytes(foto_upload)
                        atualizar_camera_completa(camera_id, {
                            "numero": numero, "operacao": operacao, "nome_camera": nome_camera, "canal": canal, "ip_camera": ip_camera,
                            "login_camera": login_camera, "senha_camera": senha_camera, "modelo": modelo, "marca": marca,
                            "inicio_gravacao": inicio_gravacao, "termino_gravacao": termino_gravacao, "dias_gravacao": dias_gravacao,
                            "nvr": nvr, "ip_nvr": ip_nvr, "login_nvr": login_nvr, "senha_nvr": senha_nvr, "rack": rack,
                            "status": status, "qualidade_gravacao": qualidade_gravacao, "observacao": observacao, "horario": horario,
                            "acao_necessaria": acao_necessaria, "serie_number": serie_number, "ativo": ativo
                        }, foto_bytes if foto_upload else None, foto_nome if foto_upload else None)
                        st.success("Câmera atualizada com sucesso.")
                        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# MANUTENÇÃO / STATUS
# =====================================================
elif menu == "🔧 Manutenção":
    st.markdown('<div class="form-section"><h3>Gestão de Manutenção</h3><p>Atualize status operacional e registre tratativas técnicas.</p>', unsafe_allow_html=True)
    if df_norm.empty:
        st.warning("Nenhuma câmera cadastrada.")
    else:
        camera_id = st.selectbox(
            "Selecione a câmera",
            df_norm["id"].tolist(),
            format_func=lambda x: f'{x} - {df_norm[df_norm["id"] == x]["nome_camera"].iloc[0]}',
        )
        st.markdown("#### Atualização rápida de status")
        colm1, colm2 = st.columns(2)
        status = colm1.selectbox("Novo status", ["ATIVA", "INATIVA", "MANUTENÇÃO", "FALHA", "SEM GRAVAÇÃO"])
        qualidade = colm2.selectbox("Qualidade", ["BOA", "REGULAR", "RUIM", "SEM IMAGEM", "SEM GRAVAÇÃO"])
        observacao = st.text_area("Observação")
        acao = st.text_area("Ação necessária")
        if st.button("Atualizar status"):
            atualizar_status(camera_id, status, qualidade, observacao, acao)
            st.success("Status atualizado.")
            st.rerun()

        st.divider()
        st.markdown("#### Registrar manutenção / chamado")
        with st.form("form_manutencao"):
            c1, c2, c3 = st.columns(3)
            tipo_m = c1.selectbox("Tipo", ["Preventiva", "Corretiva", "Substituição", "Ajuste de imagem", "NVR/Gravação", "Outro"])
            prioridade_m = c2.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Crítica"])
            status_m = c3.selectbox("Status do chamado", ["ABERTO", "EM ANDAMENTO", "CONCLUÍDO", "CANCELADO"])
            descricao_m = st.text_area("Descrição da tratativa")
            c4, c5 = st.columns(2)
            responsavel_m = c4.text_input("Responsável")
            prazo_m = c5.date_input("Prazo", value=br_now().date())
            salvar_m = st.form_submit_button("Registrar manutenção")
            if salvar_m:
                registrar_manutencao(camera_id, tipo_m, prioridade_m, descricao_m, responsavel_m, status_m, prazo_m)
                st.success("Manutenção registrada.")
                st.rerun()

    manut_df = carregar_manutencoes()
    st.divider()
    st.markdown("#### Histórico de manutenções")
    if manut_df.empty:
        st.info("Nenhuma manutenção registrada.")
    else:
        st.dataframe(manut_df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# EXPANSÃO DO PARQUE
# =====================================================
elif menu == "📈 Expansão do Parque":
    st.markdown('<div class="form-section"><h3>Planejamento de Expansão do Parque de Câmeras</h3><p>Cadastre metas por operação para comparar parque atual x necessidade futura.</p>', unsafe_allow_html=True)
    ops_atuais = sorted([x for x in df_norm["operacao"].dropna().unique().tolist() if safe_text(x, "")]) if not df_norm.empty else []
    exp_df = carregar_expansao()

    with st.form("form_expansao"):
        col1, col2, col3 = st.columns([2, 1, 3])
        operacao_exp = col1.selectbox("Operação", ops_atuais + ["Outra"], index=0 if ops_atuais else None)
        if operacao_exp == "Outra" or not ops_atuais:
            operacao_exp = col1.text_input("Nome da nova operação")
        meta_exp = col2.number_input("Meta de câmeras", min_value=0, step=1)
        obs_exp = col3.text_input("Observação")
        salvar_exp = st.form_submit_button("Salvar meta")
        if salvar_exp:
            if not operacao_exp:
                st.error("Informe a operação.")
            else:
                salvar_meta_expansao(operacao_exp, meta_exp, obs_exp)
                st.success("Meta salva com sucesso.")
                st.rerun()

    if not df_norm.empty:
        atual = df_norm.groupby("operacao", dropna=False).size().reset_index(name="atual")
        if not exp_df.empty:
            resumo_exp = atual.merge(exp_df[["operacao", "meta", "observacao"]], on="operacao", how="outer").fillna({"atual": 0, "meta": 0, "observacao": ""})
        else:
            resumo_exp = atual.copy()
            resumo_exp["meta"] = 0
            resumo_exp["observacao"] = ""
        resumo_exp["atual"] = pd.to_numeric(resumo_exp["atual"], errors="coerce").fillna(0).astype(int)
        resumo_exp["meta"] = pd.to_numeric(resumo_exp["meta"], errors="coerce").fillna(0).astype(int)
        resumo_exp["incremento_necessario"] = (resumo_exp["meta"] - resumo_exp["atual"]).clip(lower=0)
        resumo_exp["atingimento_%"] = resumo_exp.apply(lambda r: round((r["atual"] / r["meta"]) * 100, 1) if r["meta"] else 0, axis=1)
        st.dataframe(resumo_exp[["operacao", "atual", "meta", "incremento_necessario", "atingimento_%", "observacao"]], use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# BACKUP
# =====================================================
elif menu == "📄 Backup":
    st.markdown('<div class="form-section"><h3>Backup e Exportação</h3><p>Baixe uma cópia completa dos dados do sistema em Excel.</p>', unsafe_allow_html=True)
    backup = gerar_backup_excel(df)
    nome_backup = f"backup_cameras_acf_{br_now().strftime('%Y%m%d_%H%M')}.xlsx"
    st.download_button(
        "Baixar backup completo",
        data=backup,
        file_name=nome_backup,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.info("O backup inclui câmeras, histórico, manutenção e plano de expansão, quando houver dados.")
    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# HISTÓRICO DE ALTERAÇÕES
# =====================================================
elif menu == "🧾 Histórico":
    st.markdown('<div class="form-section"><h3>Histórico de Alterações</h3><p>Rastreabilidade das principais ações realizadas no sistema.</p>', unsafe_allow_html=True)
    hist = carregar_historico(1000)
    if hist.empty:
        st.info("Ainda não há histórico registrado.")
    else:
        st.dataframe(hist, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# DESATIVAR / EXCLUIR
# =====================================================
elif menu == "🗑️ Desativar / Excluir":
    st.markdown('<div class="form-section"><h3>Desativar ou Excluir Câmera</h3>', unsafe_allow_html=True)
    if df_norm.empty:
        st.warning("Nenhuma câmera cadastrada.")
    else:
        camera_id = st.selectbox(
            "Selecione a câmera",
            df_norm["id"].tolist(),
            format_func=lambda x: f'{x} - {df_norm[df_norm["id"] == x]["nome_camera"].iloc[0]}',
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
    st.markdown("</div>", unsafe_allow_html=True)

