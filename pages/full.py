from altair import param
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from requests.exceptions import ConnectionError, Timeout
from urllib3.exceptions import ProtocolError
from datetime import datetime, timedelta

#pages
# Configuração
st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="PMJA - Dashboard Completo")

# Inicializar session_state para controle de navegação
if 'inicio_exibicao' not in st.session_state:
    st.session_state.inicio_exibicao = time.time()

# Calcular tempo decorrido
tempo_decorrido = time.time() - st.session_state.inicio_exibicao

# Após 2 minutos (120 segundos), navegar para pallet.py
if tempo_decorrido >= 120:
    st.session_state.inicio_exibicao = time.time()
    st.switch_page("pages/rec.py")

# CSS OTIMIZADO
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Poppins:wght@600;700;800;900&display=swap');
        
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            height: 100vh !important; width: 100vw !important; margin: 0 !important;
            padding: 0 !important; overflow: hidden !important;
            background: linear-gradient(135deg, #f5f7fa 0%, #e8eef5 100%);
        }
        .block-container { 
            padding: 0.2rem 0.3rem !important; 
            max-width: 100% !important;
            height: calc(100vh - 0.4rem) !important; 
            overflow-y: auto !important; 
        }
        header, #MainMenu, footer { 
            visibility: hidden !important; 
            height: 0 !important; 
            display: none !important; 
        }
        .element-container, [data-testid="column"] { 
            margin: 0 !important; 
            padding: 0 0.1rem !important; 
        }
        .stPlotlyChart { 
            height: 100% !important; 
            width: 100% !important; 
            background: white;
            border-radius: 0 0 6px 6px; 
            box-shadow: 0 1px 4px rgba(0, 58, 112, 0.06); 
            padding: 0.05rem;
            overflow: hidden !important;
        }
        .js-plotly-plot, .plotly, .plot-container {
            overflow: hidden !important;
        }
        .svg-container {
            overflow: visible !important;
        }
        div[data-testid="stVerticalBlock"] > div { 
            gap: 0.1rem !important; 
        }
        ::-webkit-scrollbar { 
            width: 6px; 
            height: 6px; 
        }
        ::-webkit-scrollbar-track { 
            background: #f1f3f6; 
            border-radius: 10px; 
        }
        ::-webkit-scrollbar-thumb { 
            background: linear-gradient(135deg, #003a70 0%, #0056A3 100%); 
            border-radius: 10px; 
        }
        .header-container { 
            background: linear-gradient(135deg, #003a70 0%, #0056A3 100%);
            border-radius: 6px; 
            box-shadow: 0 2px 8px rgba(0, 58, 112, 0.12);
            padding: 0.15rem 0.8rem; 
            margin-bottom: 0.3rem; 
        }
        .section-divider {
            background: linear-gradient(135deg, #0056A3 0%, #0075be 100%);
            border-radius: 6px;
            padding: 0.15rem 0.5rem;
            margin: 0.4rem 0 0.2rem 0;
            box-shadow: 0 1px 4px rgba(0, 86, 163, 0.15);
        }
        .section-divider-exp {
            background: linear-gradient(135deg, #4a5568 0%, #718096 100%);
            border-radius: 6px;
            padding: 0.15rem 0.5rem;
            margin: 0.4rem 0 0.2rem 0;
            box-shadow: 0 1px 4px rgba(74, 85, 104, 0.15);
        }
        .metric-card { 
            background: white; 
            border-radius: 6px; 
            padding: 0.25rem 0.4rem;
            box-shadow: 0 1px 4px rgba(0, 58, 112, 0.06); 
            border-left: 3px solid;
            transition: all 0.3s ease; 
            min-height: 48px; 
        }
        .metric-card:hover { 
            transform: translateY(-1px); 
            box-shadow: 0 2px 8px rgba(0, 58, 112, 0.12); 
        }
        .metric-label { 
            font-family: 'Inter', sans-serif; 
            font-size: 8.5px; 
            color: #666;
            font-weight: 700; 
            text-transform: uppercase; 
            letter-spacing: 0.3px; 
            margin-bottom: 0.1rem; 
        }
        .metric-value { 
            font-family: 'Poppins', sans-serif; 
            font-size: 16px; 
            font-weight: 800; 
            line-height: 1; 
        }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="header-container">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <img src="https://companieslogo.com/img/orig/AZ2.F-d26946db.png?t=1720244490" 
                 style="height: 30px; filter: brightness(0) invert(1);" alt="Logo AZ">
            <div style="text-align: center; flex: 1;">
                <h1 style="font-family: 'Poppins', sans-serif; font-size: 18px; color: white; 
                           margin: 0; font-weight: 800; letter-spacing: -0.5px;">
                    PMJA - Dashboard Gestão de Materiais
                </h1>
                <p style="font-family: 'Inter', sans-serif; font-size: 12px; color: rgba(255,255,255,0.9); 
                          margin: 0.02rem 0 0 0; font-weight: 700;">
                    Visão Completa - Recebimento & Expedição
                </p>
            </div>
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Logo-engie.svg/2445px-Logo-engie.svg.png" 
                 style="height: 30px; filter: brightness(0) invert(1);" alt="Logo Engie">
        </div>
    </div>
""", unsafe_allow_html=True)

def fix_dataframe(df):
    """Corrige tipos de dados do dataframe"""
    df_fixed = df.copy()
    for col in df_fixed.columns:
        if df_fixed[col].dtype == 'object':
            try:
                numeric_col = pd.to_numeric(df_fixed[col], errors='coerce')
                if numeric_col.notna().sum() == df_fixed[col].notna().sum():
                    df_fixed[col] = numeric_col
                else:
                    df_fixed[col] = df_fixed[col].fillna('').astype(str).replace('nan', '')
            except:
                df_fixed[col] = df_fixed[col].fillna('').astype(str).replace('nan', '')
        elif df_fixed[col].dtype in ['float64', 'int64'] and df_fixed[col].isna().any():
            df_fixed[col] = df_fixed[col].astype('float64')
    return df_fixed

@st.cache_data(ttl=600, show_spinner=False)
def carregar_dados_com_retry(worksheet_name, max_tentativas=3):
    """Carrega dados do Google Sheets com retry e cache"""
    for tentativa in range(max_tentativas):
        try:
            if tentativa > 0:
                delay = min(tentativa * 3, 10)
                time.sleep(delay)
            
            conn = st.connection("gsheets_itens_pacote", type=GSheetsConnection)
            df = conn.read(worksheet=worksheet_name, ttl="10m")
            return fix_dataframe(df)
            
        except Timeout:
            if tentativa < max_tentativas - 1:
                st.warning(f'⏱️ Timeout. Tentando novamente... ({tentativa + 1}/{max_tentativas})')
                continue
            else:
                st.error("⏱️ Timeout após 3 tentativas. Aguarde 1 minuto e recarregue (F5)")
                return None
                
        except (ConnectionError, ProtocolError):
            if tentativa < max_tentativas - 1:
                st.warning(f'🔌 Erro de conexão. Reconectando... ({tentativa + 1}/{max_tentativas})')
                continue
            else:
                st.error(f"❌ Erro de conexão após {max_tentativas} tentativas.")
                return None
                
        except Exception as e:
            erro_str = str(e)
            if "quota" in erro_str.lower() or "rate" in erro_str.lower():
                st.error("🚫 Limite de requisições da API excedido. Aguarde 1-2 minutos e recarregue (F5)")
                return None
            
            if tentativa < max_tentativas - 1:
                st.warning(f'⚠️ Erro inesperado. Tentando novamente... ({tentativa + 1}/{max_tentativas})')
                continue
            else:
                st.error(f"❌ Erro ao carregar dados: {erro_str[:200]}")
                return None
    
    return None

def processar_dados_expedicao(df_raw):
    """Processa os dados de expedição"""
    if df_raw is None or df_raw.empty:
        return None, None
    
    df = df_raw.copy()
    df.rename(columns={df.columns[0]: 'mes'}, inplace=True)
    df = df[df['mes'].notna()].copy()
    df['data'] = pd.to_datetime(df['mes'], format='%m/%Y', errors='coerce')
    df = df.dropna(subset=['data']).copy()
    df['ano'] = df['data'].dt.year
    df['mes_num'] = df['data'].dt.month
    df['mes_ano'] = df['data'].dt.strftime('%m/%Y')
    
    colunas_requisicoes = []
    colunas_unidades = []
    colunas_itens_unidade = []
    
    for col in df.columns:
        col_normalizado = col.lower().strip().replace('.', '').replace('  ', ' ')
        
        if 'requisi' in col_normalizado:
            if 'unid' not in col_normalizado and 'por' not in col_normalizado:
                colunas_requisicoes.append(col)
        
        if 'unid' in col_normalizado and 'iten' in col_normalizado:
            if 'por' not in col_normalizado:
                colunas_unidades.append(col)
        
        if 'iten' in col_normalizado and 'por' in col_normalizado and 'unid' in col_normalizado:
            colunas_itens_unidade.append(col)
    
    for col in colunas_requisicoes + colunas_unidades + colunas_itens_unidade:
        if col in df.columns:
            df.loc[:, col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    df['qtd_requisicoes'] = df[colunas_requisicoes].sum(axis=1)
    df['qtd_unidades_emitidas'] = df[colunas_unidades].sum(axis=1)
    df['qtd_itens_total'] = df[colunas_itens_unidade].sum(axis=1) if colunas_itens_unidade else 0
    
    df_final = df[['mes_ano', 'ano', 'mes_num', 'qtd_requisicoes', 
                   'qtd_unidades_emitidas', 'qtd_itens_total']].copy()
    
    df_detalhado = df[['mes_ano', 'ano', 'mes_num'] + colunas_requisicoes + colunas_unidades + colunas_itens_unidade].copy()
    
    df_final = df_final.sort_values(['ano', 'mes_num']).reset_index(drop=True)
    df_detalhado = df_detalhado.sort_values(['ano', 'mes_num']).reset_index(drop=True)
    
    return df_final, df_detalhado

def extrair_categoria(nome_coluna):
    """Extrair nomes das categorias removendo sufixos"""
    categoria = nome_coluna.replace(' Requisições', '').replace(' Requisiçoes', '')
    categoria = categoria.replace(' Unid. Itens', '').replace(' Unid Itens', '')
    categoria = categoria.replace(' Itens por unidade', '').replace(' Items por unidade', '')
    categoria = categoria.replace(' Volumes', '')
    return categoria.strip()

def extrair_sistemas_dinamicamente(df):
    """Extrai sistemas dinamicamente a partir dos nomes das colunas"""
    sistemas_set = set()
    palavras_metricas = ['Volumes', 'Unid. Itens', 'Itens por unidade', 'mes_ano', 'data', 'mes', 'ano']
    
    for col in df.columns:
        col_str = str(col).strip()
        
        if col_str in ['data', 'mes', 'ano']:
            continue
            
        possui_metrica = False
        sistema_extraida = col_str
        
        for metrica in palavras_metricas:
            if metrica in col_str:
                possui_metrica = True
                sistema_extraida = col_str.replace(metrica, '').strip()
                break
        
        if possui_metrica and sistema_extraida and sistema_extraida not in palavras_metricas:
            sistemas_set.add(sistema_extraida)
    
    return sorted(list(sistemas_set))

def formatar_numero(num):
    """Formata número com separador de milhares"""
    if pd.isna(num):
        return "0"
    valor_int = int(num)
    return f"{valor_int:,}".replace(',', '.')

# CARREGAMENTO DE DADOS
with st.spinner('📊 Carregando dados...'):
    df_recebimento = carregar_dados_com_retry("recebimento")
    df_rec_dados = carregar_dados_com_retry("rec_dados")
    df_exp_raw = carregar_dados_com_retry("exp_dados")
    df_expedicao, df_exp_detalhado = processar_dados_expedicao(df_exp_raw) if df_exp_raw is not None else (None, None)

# Processar dados de Recebimento
df_rec = None
mes_max_rec = 0

if df_recebimento is not None and not df_recebimento.empty:
    df_rec = df_recebimento.copy()
    colunas_rec = ['mes_ano', 'qtd_descarregamentos', 'qtd_volumes_recebidos', 
                   'peso_recebido', 'qtd_unidades_recebidos', 'qtd_itens_por_unidade']
    
    if len(df_rec.columns) == 6:
        df_rec.columns = colunas_rec
    
    df_rec['data'] = pd.to_datetime(df_rec.iloc[:, 0] if 'mes_ano' not in df_rec.columns else df_rec['mes_ano'], 
                                    format='%m/%Y', errors='coerce')
    df_rec = df_rec.dropna(subset=['data']).sort_values('data')
    df_rec['ano'] = df_rec['data'].dt.year
    df_rec['mes'] = df_rec['data'].dt.month
    
    for col in ['qtd_descarregamentos', 'qtd_volumes_recebidos', 'peso_recebido', 
                'qtd_unidades_recebidos', 'qtd_itens_por_unidade']:
        if col in df_rec.columns:
            df_rec.loc[:, col] = pd.to_numeric(df_rec[col], errors='coerce').fillna(0)
    
    mes_max_rec = df_rec['mes'].max()

# Processar dados de Expedição
df_exp = None
mes_max_exp = 0

if df_expedicao is not None and not df_expedicao.empty:
    df_exp = df_expedicao.copy()
    df_exp.rename(columns={'mes_num': 'mes'}, inplace=True)
    
    if 'data' not in df_exp.columns:
        df_exp['data'] = pd.to_datetime(df_exp['mes_ano'], format='%m/%Y', errors='coerce')
    
    for col in ['qtd_requisicoes', 'qtd_unidades_emitidas', 'qtd_itens_total']:
        df_exp.loc[:, col] = pd.to_numeric(df_exp[col], errors='coerce').fillna(0)
    
    mes_max_exp = df_exp['mes'].max()

# Processar rec_dados para gráficos por sistema
df_rec_sistemas = None
mes_max_rec_sistemas = 0
sistemas_rec = []

if df_rec_dados is not None and not df_rec_dados.empty:
    df_rec_sistemas = df_rec_dados.copy()
    df_rec_sistemas['data'] = pd.to_datetime(df_rec_sistemas.iloc[:, 0], format='%m/%Y', errors='coerce')
    df_rec_sistemas = df_rec_sistemas.dropna(subset=['data']).sort_values('data').copy()
    df_rec_sistemas['mes'] = df_rec_sistemas['data'].dt.month
    df_rec_sistemas['ano'] = df_rec_sistemas['data'].dt.year
    
    sistemas_rec = extrair_sistemas_dinamicamente(df_rec_sistemas)
    mes_max_rec_sistemas = df_rec_sistemas['mes'].max()

# ========== TODAS AS MÉTRICAS NA PRIMEIRA LINHA ==========
col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8, gap="small")
placeholders_metricas = [col1.empty(), col2.empty(), col3.empty(), col4.empty(), 
                         col5.empty(), col6.empty(), col7.empty(), col8.empty()]

metricas_config = [
    ('qtd_descarregamentos', 'Descarregamentos', '#003a70', '', 'rec'),
    ('peso_recebido', 'Peso Recebido', '#005a9c', ' kg', 'rec'),
    ('qtd_volumes_recebidos', 'Volumes', '#0075be', '', 'rec'),
    ('qtd_unidades_recebidos', 'Unidades Rec', '#4d9fd6', '', 'rec'),
    ('qtd_itens_por_unidade', 'Itens/Unid', '#80b9e5', '', 'rec'),
    ('qtd_requisicoes', 'Requisições', '#4a5568', '', 'exp'),
    ('qtd_unidades_emitidas', 'Unid. Emitidas', '#718096', '', 'exp'),
    ('qtd_itens_total', 'Total Itens', '#a0aec0', '', 'exp')
]

for idx, (coluna, titulo, cor, sufixo, tipo) in enumerate(metricas_config):
    placeholders_metricas[idx].markdown(f"""
        <div class="metric-card" style="border-left-color: {cor};">
            <div class="metric-label">{titulo}</div>
            <div class="metric-value" style="color: {cor};">0{sufixo}</div>
        </div>
    """, unsafe_allow_html=True)

# ========== SEÇÃO RECEBIMENTO ==========
st.markdown("""
    <div class="section-divider">
        <div style="font-family: 'Poppins', sans-serif; font-size: 12px; color: white; 
                    font-weight: 800; text-align: center;">
            📦 RECEBIMENTO
        </div>
    </div>
""", unsafe_allow_html=True)

# Linha 1: Descarregamentos, Peso Recebido (Kg), Volumes Recebidos, Volumes por Sistema
col_r1, col_r2, col_r3, col_r4 = st.columns(4, gap="small")
placeholders_rec_linha1 = [col_r1.empty(), col_r2.empty(), col_r3.empty(), col_r4.empty()]

# Linha 2: Unidades Recebidas, Unidades Itens por Sistema, Itens por Unidade, Itens/Unidades por Sistema
col_r5, col_r6, col_r7, col_r8 = st.columns(4, gap="small")
placeholders_rec_linha2 = [col_r5.empty(), col_r6.empty(), col_r7.empty(), col_r8.empty()]

# ========== SEÇÃO EXPEDIÇÃO ==========
st.markdown("""
    <div class="section-divider-exp">
        <div style="font-family: 'Poppins', sans-serif; font-size: 12px; color: white; 
                    font-weight: 800; text-align: center;">
            🚚 EXPEDIÇÃO
        </div>
    </div>
""", unsafe_allow_html=True)

# Linha 1: Requisições, Unidades Emitidas, Total Itens
col_e1, col_e2, col_e3 = st.columns(3, gap="small")
placeholders_exp_linha1 = [col_e1.empty(), col_e2.empty(), col_e3.empty()]

# Linha 2: Gráficos por sistema (3 gráficos)
col_es1, col_es2, col_es3 = st.columns(3, gap="small")
placeholders_exp_sistema = [col_es1.empty(), col_es2.empty(), col_es3.empty()]

meses_pt = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}

cores_sistemas = ['#001a33', '#002d4d', '#003d66', '#004d80', '#005d99', 
                  '#006db3', '#007dcc', '#1a8dd4', '#3399dd', '#4da6e6', 
                  '#66b3ee', '#80c0f5', '#99ccff', '#b3d9ff']

# Cores distintas para cada ano nos gráficos de linha
cores_anos_rec = ['#003a70', '#007dcc', '#004d80', '#4da6e6', '#003d66', '#99ccff']
cores_anos_exp = ['#2d3748',   '#99a3af','#5a6575','#7f8c99', '#4b5563',  '#d0d5db']

# ANIMAÇÃO
if df_rec is not None and df_exp is not None and mes_max_rec > 0 and mes_max_exp > 0:
    mes_maximo = max(mes_max_rec, mes_max_exp, mes_max_rec_sistemas if mes_max_rec_sistemas > 0 else 0)
    anos_unicos_rec = sorted(df_rec['ano'].unique())
    anos_unicos_exp = sorted(df_exp['ano'].unique())
    
    time.sleep(0.5)
    
    for mes_atual in range(1, mes_maximo + 1):
        # ========== ATUALIZAR TODAS AS MÉTRICAS ==========
        df_rec_ate_mes = df_rec[df_rec['mes'] <= mes_atual].copy() if mes_atual <= mes_max_rec else df_rec.copy()
        df_exp_ate_mes = df_exp[df_exp['mes'] <= mes_atual].copy() if mes_atual <= mes_max_exp else df_exp.copy()
        
        for idx, (coluna, titulo, cor, sufixo, tipo) in enumerate(metricas_config):
            if tipo == 'rec' and mes_atual <= mes_max_rec:
                valor = df_rec_ate_mes[coluna].sum()
            elif tipo == 'exp' and mes_atual <= mes_max_exp:
                valor = df_exp_ate_mes[coluna].sum()
            else:
                valor = 0
            
            valor_formatado = formatar_numero(valor)
            
            placeholders_metricas[idx].markdown(f"""
                <div class="metric-card" style="border-left-color: {cor};">
                    <div class="metric-label">{titulo}</div>
                    <div class="metric-value" style="color: {cor};">{valor_formatado}{sufixo}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # ========== GRÁFICOS RECEBIMENTO LINHA 1 ==========
        graficos_rec_l1_basicos = [
            ('qtd_descarregamentos', 'Descarregamentos'),
            ('peso_recebido', 'Peso Recebido (kg)'),
            ('qtd_volumes_recebidos', 'Volumes Recebidos')
        ]
        
        for idx_g, (coluna, titulo) in enumerate(graficos_rec_l1_basicos):
            if mes_atual <= mes_max_rec:
                fig = go.Figure()
                
                # Calcular totais por ano
                totais_anos = {}
                for idx_ano, ano in enumerate(anos_unicos_rec):
                    df_ano = df_rec[(df_rec['ano'] == ano) & (df_rec['mes'] <= mes_atual)].sort_values('mes').copy()
                    if df_ano.empty: continue
                    
                    total_ano = df_ano[coluna].sum()
                    totais_anos[ano] = total_ano
                    
                    cor = cores_anos_rec[idx_ano % len(cores_anos_rec)]
                    text_values = [formatar_numero(v) if v > 0 else "" for v in df_ano[coluna]]
                    
                    fig.add_trace(go.Scatter(
                        x=df_ano['mes'], y=df_ano[coluna],
                        mode='lines+markers+text', name=str(ano),
                        line=dict(width=2.5, color=cor, shape='spline'),
                        marker=dict(size=7, color=cor, line=dict(width=1.5, color='white')),
                        text=text_values, textposition='top center',
                        textfont=dict(size=8, color='#1a1a1a', family='Inter', weight=700),
                        cliponaxis=False
                    ))
                
                # Adicionar anotações para os totais
                annotations = []
                x_pos = 0.98
                y_start = 1.35
                
                for i, (ano, total) in enumerate(totais_anos.items()):
                    cor_ano = cores_anos_rec[i % len(cores_anos_rec)]
                    annotations.append(dict(
                        x=x_pos,
                        y=y_start - (i * 0.08),
                        xref='paper',
                        yref='paper',
                        text=f'<b style="color:{cor_ano};">■ {ano}</b> <span style="font-size:9px;">{formatar_numero(total)}</span>',
                        showarrow=False,
                        xanchor='right',
                        yanchor='top',
                        font=dict(size=8, family='Inter')
                    ))
                
                fig.update_layout(
                    title=dict(text=f'<b>{titulo}</b>', font=dict(family='Poppins', size=11), x=0.5, xanchor='center'),
                    template='plotly_white', height=170, showlegend=False,
                    margin=dict(l=30, r=10, t=35, b=20),
                    annotations=annotations,
                    xaxis=dict(tickmode='array', tickvals=list(range(1, 13)), 
                              ticktext=[meses_pt[m] for m in range(1, 13)], tickfont=dict(size=8)),
                    yaxis=dict(tickfont=dict(size=8), rangemode='tozero'),
                )
                
                placeholders_rec_linha1[idx_g].plotly_chart(
                    fig, width='stretch', key=f"rec_l1_{idx_g}_{mes_atual}", 
                    config={'displayModeBar': False}
                )
        
        # Gráfico 4: Volumes por Sistema (Donut)
        if df_rec_sistemas is not None and mes_atual <= mes_max_rec_sistemas and sistemas_rec:
            palavra_chave = 'Volumes'
            excluir = ['Unid.', 'unidade']
            
            colunas_metrica = []
            mapeamento_sistemas = {}
            
            for col in df_rec_sistemas.columns:
                col_str = str(col)
                if palavra_chave in col_str:
                    if not any(exc in col_str for exc in excluir):
                        colunas_metrica.append(col)
                        for sistema in sistemas_rec:
                            if sistema in col_str:
                                mapeamento_sistemas[col] = sistema
                                break
            
            if colunas_metrica:
                valores = []
                labels = []
                cores = []
                
                for cat_idx, sistema in enumerate(sistemas_rec):
                    col_nome = None
                    for col in colunas_metrica:
                        if mapeamento_sistemas.get(col) == sistema:
                            col_nome = col
                            break
                    
                    if col_nome and col_nome in df_rec_sistemas.columns:
                        df_rec_sistemas.loc[:, col_nome] = pd.to_numeric(df_rec_sistemas[col_nome], errors='coerce').fillna(0)
                        df_filtrado = df_rec_sistemas[df_rec_sistemas['mes'] <= mes_atual].copy()
                        total = df_filtrado[col_nome].sum()
                        if total > 0:
                            valores.append(total)
                            labels.append(sistema)
                            cores.append(cores_sistemas[cat_idx % len(cores_sistemas)])
                
                if valores:
                    total_geral = sum(valores)
                    labels_info = [f"{label}: {formatar_numero(val)} ({(val/total_geral*100):.1f}%)" 
                                  for label, val in zip(labels, valores)]
                    
                    fig = go.Figure()
                    fig.add_trace(go.Pie(
                        labels=labels_info, values=valores, hole=0.35,
                        marker=dict(colors=cores, line=dict(color='white', width=2)),
                        textfont=dict(size=8)
                    ))
                    
                    fig.update_layout(
                        title=dict(text='<b>Volumes por Sistema</b>', font=dict(family='Poppins', size=11), x=0.5, xanchor='center'),
                        template='plotly_white', height=170, showlegend=True,
                        legend=dict(orientation="v", y=0.5, x=1.02, font=dict(size=7)),
                        margin=dict(l=10, r=80, t=30, b=10)
                    )
                    
                    placeholders_rec_linha1[3].plotly_chart(
                        fig, width='stretch', key=f"rec_l1_vol_sis_{mes_atual}",
                        config={'displayModeBar': False}
                    )
        
        # ========== GRÁFICOS RECEBIMENTO LINHA 2 ==========
        # Gráfico 1: Unidades Recebidas
        if mes_atual <= mes_max_rec:
            fig = go.Figure()
            
            totais_anos = {}
            for idx_ano, ano in enumerate(anos_unicos_rec):
                df_ano = df_rec[(df_rec['ano'] == ano) & (df_rec['mes'] <= mes_atual)].sort_values('mes').copy()
                if df_ano.empty: continue
                
                total_ano = df_ano['qtd_unidades_recebidos'].sum()
                totais_anos[ano] = total_ano
                
                cor = cores_anos_rec[idx_ano % len(cores_anos_rec)]
                text_values = [formatar_numero(v) if v > 0 else "" for v in df_ano['qtd_unidades_recebidos']]
                
                fig.add_trace(go.Scatter(
                    x=df_ano['mes'], y=df_ano['qtd_unidades_recebidos'],
                    mode='lines+markers+text', name=str(ano),
                    line=dict(width=2.5, color=cor, shape='spline'),
                    marker=dict(size=7, color=cor, line=dict(width=1.5, color='white')),
                    text=text_values, textposition='top center',
                    textfont=dict(size=8, color='#1a1a1a', family='Inter', weight=700),
                    cliponaxis=False
                ))
            
            annotations = []
            x_pos = 0.98
            y_start = 1.35
            
            for i, (ano, total) in enumerate(totais_anos.items()):
                cor_ano = cores_anos_rec[i % len(cores_anos_rec)]
                annotations.append(dict(
                    x=x_pos,
                    y=y_start - (i * 0.08),
                    xref='paper',
                    yref='paper',
                    text=f'<b style="color:{cor_ano};">■ {ano}</b> <span style="font-size:9px;">{formatar_numero(total)}</span>',
                    showarrow=False,
                    xanchor='right',
                    yanchor='top',
                    font=dict(size=8, family='Inter')
                ))
            
            fig.update_layout(
                title=dict(text='<b>Unidades Recebidas</b>', font=dict(family='Poppins', size=11), x=0.5, xanchor='center'),
                template='plotly_white', height=170, showlegend=False,
                margin=dict(l=30, r=10, t=35, b=20),
                annotations=annotations,
                xaxis=dict(tickmode='array', tickvals=list(range(1, 13)), 
                          ticktext=[meses_pt[m] for m in range(1, 13)], tickfont=dict(size=8)),
                yaxis=dict(tickfont=dict(size=8), rangemode='tozero'),
            )
            
            placeholders_rec_linha2[0].plotly_chart(
                fig, width='stretch', key=f"rec_l2_unid_{mes_atual}", 
                config={'displayModeBar': False}
            )
        
        # Gráfico 2: Unidades Itens por Sistema (Barras Horizontais)
        if df_rec_sistemas is not None and mes_atual <= mes_max_rec_sistemas and sistemas_rec:
            palavra_chave = 'Unid. Itens'
            excluir = ['por unidade']
            
            colunas_metrica = []
            mapeamento_sistemas = {}
            
            for col in df_rec_sistemas.columns:
                col_str = str(col)
                if palavra_chave in col_str:
                    if not any(exc in col_str for exc in excluir):
                        colunas_metrica.append(col)
                        for sistema in sistemas_rec:
                            if sistema in col_str:
                                mapeamento_sistemas[col] = sistema
                                break
            
            if colunas_metrica:
                valores = []
                labels = []
                cores = []
                
                for cat_idx, sistema in enumerate(sistemas_rec):
                    col_nome = None
                    for col in colunas_metrica:
                        if mapeamento_sistemas.get(col) == sistema:
                            col_nome = col
                            break
                    
                    if col_nome and col_nome in df_rec_sistemas.columns:
                        df_rec_sistemas.loc[:, col_nome] = pd.to_numeric(df_rec_sistemas[col_nome], errors='coerce').fillna(0)
                        df_filtrado = df_rec_sistemas[df_rec_sistemas['mes'] <= mes_atual].copy()
                        total = df_filtrado[col_nome].sum()
                        if total > 0:
                            valores.append(total)
                            labels.append(sistema)
                            cores.append(cores_sistemas[cat_idx % len(cores_sistemas)])
                
                if valores:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=valores, y=labels, orientation='h',
                        marker=dict(color=cores, cornerradius=6),
                        text=[formatar_numero(v) for v in valores],
                        textposition='outside', textfont=dict(size=8)
                    ))
                    
                    fig.update_layout(
                        title=dict(text='<b>Unidades Itens por Sistema</b>', font=dict(family='Poppins', size=11), x=0.5, xanchor='center'),
                        template='plotly_white', height=170, showlegend=False,
                        margin=dict(l=80, r=40, t=30, b=20),
                        yaxis=dict(tickfont=dict(size=8))
                    )
                    
                    placeholders_rec_linha2[1].plotly_chart(
                        fig, width='stretch', key=f"rec_l2_unid_sis_{mes_atual}",
                        config={'displayModeBar': False}
                    )
        
        # Gráfico 3: Itens por Unidade
        if mes_atual <= mes_max_rec:
            fig = go.Figure()
            
            totais_anos = {}
            for idx_ano, ano in enumerate(anos_unicos_rec):
                df_ano = df_rec[(df_rec['ano'] == ano) & (df_rec['mes'] <= mes_atual)].sort_values('mes').copy()
                if df_ano.empty: continue
                
                total_ano = df_ano['qtd_itens_por_unidade'].sum()
                totais_anos[ano] = total_ano
                
                cor = cores_anos_rec[idx_ano % len(cores_anos_rec)]
                text_values = [formatar_numero(v) if v > 0 else "" for v in df_ano['qtd_itens_por_unidade']]
                
                fig.add_trace(go.Scatter(
                    x=df_ano['mes'], y=df_ano['qtd_itens_por_unidade'],
                    mode='lines+markers+text', name=str(ano),
                    line=dict(width=2.5, color=cor, shape='spline'),
                    marker=dict(size=7, color=cor, line=dict(width=1.5, color='white')),
                    text=text_values, textposition='top center',
                    textfont=dict(size=8, color='#1a1a1a', family='Inter', weight=700),
                    cliponaxis=False
                ))
            
            annotations = []
            x_pos = 0.98
            y_start = 1.35
            
            for i, (ano, total) in enumerate(totais_anos.items()):
                cor_ano = cores_anos_rec[i % len(cores_anos_rec)]
                annotations.append(dict(
                    x=x_pos,
                    y=y_start - (i * 0.08),
                    xref='paper',
                    yref='paper',
                    text=f'<b style="color:{cor_ano};">■ {ano}</b> <span style="font-size:9px;">{formatar_numero(total)}</span>',
                    showarrow=False,
                    xanchor='right',
                    yanchor='top',
                    font=dict(size=8, family='Inter')
                ))
            
            fig.update_layout(
                title=dict(text='<b>Itens por Unidade</b>', font=dict(family='Poppins', size=11), x=0.5, xanchor='center'),
                template='plotly_white', height=170, showlegend=False,
                margin=dict(l=30, r=10, t=35, b=20),
                annotations=annotations,
                xaxis=dict(tickmode='array', tickvals=list(range(1, 13)), 
                          ticktext=[meses_pt[m] for m in range(1, 13)], tickfont=dict(size=8)),
                yaxis=dict(tickfont=dict(size=8), rangemode='tozero'),
            )
            
            placeholders_rec_linha2[2].plotly_chart(
                fig, width='stretch', key=f"rec_l2_itens_{mes_atual}", 
                config={'displayModeBar': False}
            )
        
        # Gráfico 4: Itens/Unidades por Sistema (Barras Verticais)
        if df_rec_sistemas is not None and mes_atual <= mes_max_rec_sistemas and sistemas_rec:
            palavra_chave = 'Itens por unidade'
            excluir = ['Unid. Itens']
            
            colunas_metrica = []
            mapeamento_sistemas = {}
            
            for col in df_rec_sistemas.columns:
                col_str = str(col)
                if palavra_chave in col_str:
                    if not any(exc in col_str for exc in excluir):
                        colunas_metrica.append(col)
                        for sistema in sistemas_rec:
                            if sistema in col_str:
                                mapeamento_sistemas[col] = sistema
                                break
            
            if colunas_metrica:
                valores = []
                labels = []
                cores = []
                
                for cat_idx, sistema in enumerate(sistemas_rec):
                    col_nome = None
                    for col in colunas_metrica:
                        if mapeamento_sistemas.get(col) == sistema:
                            col_nome = col
                            break
                    
                    if col_nome and col_nome in df_rec_sistemas.columns:
                        df_rec_sistemas.loc[:, col_nome] = pd.to_numeric(df_rec_sistemas[col_nome], errors='coerce').fillna(0)
                        df_filtrado = df_rec_sistemas[df_rec_sistemas['mes'] <= mes_atual].copy()
                        total = df_filtrado[col_nome].sum()
                        if total > 0:
                            valores.append(total)
                            labels.append(sistema)
                            cores.append(cores_sistemas[cat_idx % len(cores_sistemas)])
                
                if valores:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=labels, y=valores,
                        marker=dict(color=cores, cornerradius=6),
                        text=[formatar_numero(v) for v in valores],
                        textposition='outside', textfont=dict(size=8)
                    ))
                    
                    fig.update_layout(
                        title=dict(text='<b>Itens/Unidade por Sistema</b>', font=dict(family='Poppins', size=11), x=0.5, xanchor='center'),
                        template='plotly_white', height=170, showlegend=False,
                        margin=dict(l=30, r=10, t=30, b=60),
                        xaxis=dict(tickfont=dict(size=7), tickangle=-45)
                    )
                    
                    placeholders_rec_linha2[3].plotly_chart(
                        fig, width='stretch', key=f"rec_l2_itens_sis_{mes_atual}",
                        config={'displayModeBar': False}
                    )
        
        # ========== GRÁFICOS EXPEDIÇÃO LINHA 1 ==========
        graficos_exp = [
            ('qtd_requisicoes', 'Requisições'),
            ('qtd_unidades_emitidas', 'Unidades Emitidas'),
            ('qtd_itens_total', 'Total de Itens')
        ]
        
        for idx_g, (coluna, titulo) in enumerate(graficos_exp):
            if mes_atual <= mes_max_exp:
                fig = go.Figure()
                
                totais_anos = {}
                for idx_ano, ano in enumerate(anos_unicos_exp):
                    df_ano = df_exp[(df_exp['ano'] == ano) & (df_exp['mes'] <= mes_atual)].sort_values('mes').copy()
                    if df_ano.empty: continue
                    
                    total_ano = df_ano[coluna].sum()
                    totais_anos[ano] = total_ano
                    
                    cor = cores_anos_exp[idx_ano % len(cores_anos_exp)]
                    text_values = [formatar_numero(v) if v > 0 else "" for v in df_ano[coluna]]
                    
                    fig.add_trace(go.Scatter(
                        x=df_ano['mes'], y=df_ano[coluna],
                        mode='lines+markers+text', name=str(ano),
                        line=dict(width=2.5, color=cor, shape='spline'),
                        marker=dict(size=7, color=cor, line=dict(width=1.5, color='white')),
                        text=text_values, textposition='top center',
                        textfont=dict(size=8, color='#1a1a1a', family='Inter', weight=700),
                        cliponaxis=False
                    ))
                
                annotations = []
                x_pos = 0.98
                y_start = 1.35
                
                for i, (ano, total) in enumerate(totais_anos.items()):
                    cor_ano = cores_anos_exp[i % len(cores_anos_exp)]
                    annotations.append(dict(
                        x=x_pos,
                        y=y_start - (i * 0.08),
                        xref='paper',
                        yref='paper',
                        text=f'<b style="color:{cor_ano};">■ {ano}</b> <span style="font-size:9px;">{formatar_numero(total)}</span>',
                        showarrow=False,
                        xanchor='right',
                        yanchor='top',
                        font=dict(size=8, family='Inter')
                    ))
                
                fig.update_layout(
                    title=dict(text=f'<b>{titulo}</b>', font=dict(family='Poppins', size=11), x=0.5, xanchor='center'),
                    template='plotly_white', height=170, showlegend=False,
                    margin=dict(l=30, r=10, t=35, b=20),
                    annotations=annotations,
                    xaxis=dict(tickmode='array', tickvals=list(range(1, 13)), 
                              ticktext=[meses_pt[m] for m in range(1, 13)], tickfont=dict(size=8)),
                    yaxis=dict(tickfont=dict(size=8), rangemode='tozero'),
                )
                
                placeholders_exp_linha1[idx_g].plotly_chart(
                    fig, width='stretch', key=f"exp_{idx_g}_{mes_atual}", 
                    config={'displayModeBar': False}
                )
        
        # ========== GRÁFICOS POR SISTEMA - EXPEDIÇÃO ==========
        if df_exp_detalhado is not None and mes_atual <= mes_max_exp:
            colunas_req_det = [col for col in df_exp_detalhado.columns if 'requisi' in col.lower() and 'unid' not in col.lower() and 'por' not in col.lower()]
            colunas_unid_det = [col for col in df_exp_detalhado.columns if 'unid' in col.lower() and 'iten' in col.lower().replace('.', '') and 'por' not in col.lower()]
            colunas_itens_det = [col for col in df_exp_detalhado.columns if 'iten' in col.lower().replace('.', '') and 'por' in col.lower() and 'unid' in col.lower()]
            
            # Paleta de cores CINZA para Expedição
            cores_sistemas_exp = ['#2d3748', '#374151', '#4b5563', '#5a6575', '#6b7280', 
                                  '#7f8c99', '#8592a3', '#99a3af', '#a0aec0', '#adb5bd', 
                                  '#b8c1cc', '#c0c7cf', '#cbd5e0', '#d0d5db']
            
            graficos_exp_sistema = [
                {'colunas': colunas_req_det, 'titulo': 'Requisições por Sistema', 'tipo': 'donut'},
                {'colunas': colunas_unid_det, 'titulo': 'Unidades Emitidas por Sistema', 'tipo': 'bar_h'},
                {'colunas': colunas_itens_det, 'titulo': 'Itens por Sistema', 'tipo': 'bar_v'}
            ]
            
            df_exp_detalhado_filtrado = df_exp_detalhado[df_exp_detalhado['mes_num'] <= mes_atual].copy()
            
            for idx_grafico, config_grafico in enumerate(graficos_exp_sistema):
                colunas = config_grafico['colunas']
                titulo = config_grafico['titulo']
                tipo_grafico = config_grafico['tipo']
                
                if not colunas:
                    continue
                
                totais_por_cat = {}
                for col in colunas:
                    cat = extrair_categoria(col)
                    if cat not in totais_por_cat:
                        totais_por_cat[cat] = {'valor': 0, 'cor': cores_sistemas_exp[len(totais_por_cat) % len(cores_sistemas_exp)]}
                    
                    df_exp_detalhado_filtrado.loc[:, col] = pd.to_numeric(df_exp_detalhado_filtrado[col], errors='coerce').fillna(0)
                    totais_por_cat[cat]['valor'] += df_exp_detalhado_filtrado[col].sum()
                
                dados_filtrados = {cat: dados for cat, dados in totais_por_cat.items() if dados['valor'] > 0}
                
                if dados_filtrados:
                    dados_ordenados = sorted(dados_filtrados.items(), key=lambda x: x[1]['valor'], reverse=True)
                    categorias = [cat for cat, _ in dados_ordenados]
                    valores = [dados['valor'] for _, dados in dados_ordenados]
                    cores = [dados['cor'] for _, dados in dados_ordenados]
                    
                    fig = go.Figure()
                    
                    if tipo_grafico == 'donut':
                        total = sum(valores)
                        labels_info = [f"{cat}: {formatar_numero(val)} ({(val/total*100):.1f}%)" 
                                      for cat, val in zip(categorias, valores)]
                        
                        fig.add_trace(go.Pie(
                            labels=labels_info, values=valores, hole=0.35,
                            marker=dict(colors=cores, line=dict(color='white', width=2)),
                            textfont=dict(size=8)
                        ))
                        
                        fig.update_layout(
                            title=dict(text=f'<b>{titulo}</b>', font=dict(family='Poppins', size=11), x=0.5, xanchor='center'),
                            template='plotly_white', height=170, showlegend=True,
                            legend=dict(orientation="v", y=0.5, x=1.02, font=dict(size=7)),
                            margin=dict(l=10, r=80, t=30, b=10)
                        )
                    
                    elif tipo_grafico == 'bar_h':
                        fig.add_trace(go.Bar(
                            x=valores, y=categorias, orientation='h',
                            marker=dict(color=cores, cornerradius=6),
                            text=[formatar_numero(v) for v in valores],
                            textposition='outside', textfont=dict(size=8)
                        ))
                        
                        fig.update_layout(
                            title=dict(text=f'<b>{titulo}</b>', font=dict(family='Poppins', size=11), x=0.5, xanchor='center'),
                            template='plotly_white', height=170, showlegend=False,
                            margin=dict(l=80, r=40, t=30, b=20),
                            yaxis=dict(tickfont=dict(size=8))
                        )
                    
                    elif tipo_grafico == 'bar_v':
                        fig.add_trace(go.Bar(
                            x=categorias, y=valores,
                            marker=dict(color=cores, cornerradius=6),
                            text=[formatar_numero(v) for v in valores],
                            textposition='auto', textfont=dict(size=8)
                        ))
                        
                        fig.update_layout(
                            title=dict(text=f'<b>{titulo}</b>', font=dict(family='Poppins', size=11), x=0.5, xanchor='center'),
                            template='plotly_white', height=170, showlegend=False,
                            margin=dict(l=30, r=10, t=30, b=60),
                            xaxis=dict(tickfont=dict(size=7), tickangle=-45)
                        )
                    
                    placeholders_exp_sistema[idx_grafico].plotly_chart(
                        fig, width='stretch', key=f"exp_sis_{idx_grafico}_{mes_atual}",
                        config={'displayModeBar': False}
                    )
        
        time.sleep(0.6)

elif df_rec is None or df_exp is None:
    st.info("💡 **Aguardando dados... Recarregue a página em alguns instantes.**")

# Auto-recarregamento
time.sleep(60)
st.rerun()