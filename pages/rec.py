import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from requests.exceptions import ConnectionError, Timeout
from urllib3.exceptions import ProtocolError
from datetime import datetime, timedelta

#width='stretch'
#use_container_width=True

# Configuração
st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="PMJA - Dashboard")

# Inicializar session_state para controle de navegação
if 'inicio_exibicao' not in st.session_state:
    st.session_state.inicio_exibicao = time.time()

# Calcular tempo decorrido
tempo_decorrido = time.time() - st.session_state.inicio_exibicao

# Após 2 minutos, navegar para rc.py
if tempo_decorrido >= 120:
    st.session_state.inicio_exibicao = time.time()
    st.switch_page("pages/exp.py")

# CSS OTIMIZADO - Reduzido padding e margens
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            height: 100vh !important; width: 100vw !important; margin: 0 !important;
            padding: 0 !important; overflow: hidden !important;
            background: linear-gradient(135deg, #f5f7fa 0%, #e8eef5 100%);
        }
        .block-container { 
            padding: 0.2rem 0.5rem !important; 
            max-width: 100% !important;
            height: calc(100vh - 0.4rem) !important; 
            overflow-y: hidden !important; 
        }
        header, #MainMenu, footer { visibility: hidden !important; height: 0 !important; display: none !important; }
        .element-container, [data-testid="column"] { margin: 0 !important; padding: 0 0.1rem!important; }
        .stPlotlyChart { 
            height: 100% !important; 
            width: 100% !important; 
            background: white;
            border-radius: 0 0 8px 8px; 
            box-shadow: 0 2px 8px rgba(0, 58, 112, 0.06); 
            padding: 0.1rem; 
        }
        div[data-testid="stVerticalBlock"] > div { gap: 0.2rem !important; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #f1f3f6; border-radius: 10px; }
        ::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #003a70 0%, #0056A3 100%); border-radius: 10px; }
        .header-container { 
            background: linear-gradient(135deg, #003a70 0%, #0056A3 100%);
            border-radius: 8px; 
            box-shadow: 0 4px 12px rgba(0, 58, 112, 0.12);
            padding: 0.2rem 1rem; 
            margin-bottom: 0.6rem; 
        }
        .metric-card { 
            background: white; 
            border-radius: 8px; 
            padding: 0.4rem 0.6rem;
            box-shadow: 0 2px 8px rgba(0, 58, 112, 0.06); 
            border-left: 3px solid;
            transition: all 0.3s ease; 
            min-height: 55px; 
        }
        .metric-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0, 58, 112, 0.12); }
        .metric-label { 
            font-family: 'Inter', sans-serif; 
            font-size: 11px; 
            color: #666;
            font-weight: 700; 
            text-transform: uppercase; 
            letter-spacing: 0.3px; 
            margin-bottom: 0.2rem; 
        }
        .metric-value { 
            font-family: 'Poppins', sans-serif; 
            font-size: 20px; 
            font-weight: 800; 
            line-height: 1; 
        }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@700;800&family=Inter:wght@700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# Header COMPACTO
st.markdown("""
    <div class="header-container">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <img src="https://companieslogo.com/img/orig/AZ2.F-d26946db.png?t=1720244490" 
                 style="height: 35px; filter: brightness(0) invert(1);" alt="Logo AZ">
            <div style="text-align: center; flex: 1;">
                <h1 style="font-family: 'Poppins', sans-serif; font-size: 20px; color: white; 
                           margin: 0; font-weight: 800; letter-spacing: -0.5px;">
                    PMJA - Dashboard Gestão de Materiais
                </h1>
                <p style="font-family: 'Inter', sans-serif; font-size: 14px; color: rgba(255,255,255,0.9); 
                          margin: 0.05rem 0 0 0; font-weight: 700;">
                    Evolução Temporal - Recebimento
                </p>
            </div>
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Logo-engie.svg/2445px-Logo-engie.svg.png" 
                 style="height: 35px; filter: brightness(0) invert(1);" alt="Logo Engie">
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
            df = conn.read(
                worksheet=worksheet_name,
                ttl="10m"
            )
            
            return fix_dataframe(df)
            
        except Timeout:
            if tentativa < max_tentativas - 1:
                st.warning(f'⏱️ Timeout na requisição. Tentando novamente... ({tentativa + 1}/{max_tentativas})')
                continue
            else:
                st.error("⏱️ Timeout: A requisição excedeu 180 segundos. Aguarde 1 minuto e recarregue (F5)")
                return None
                
        except (ConnectionError, ProtocolError) as e:
            if tentativa < max_tentativas - 1:
                st.warning(f'🔌 Erro de conexão. Reconectando... ({tentativa + 1}/{max_tentativas})')
                continue
            else:
                st.error(f"❌ Erro de conexão após {max_tentativas} tentativas. Aguarde 1 minuto antes de recarregar.")
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

def extrair_sistemas_dinamicamente(df_rec):
    """
    Extrai sistemas dinamicamente a partir dos nomes das colunas.
    Retorna uma lista ordenada de sistemas únicas.
    """
    sistemas_set = set()
    
    # Palavras-chave que indicam métricas (não são sistemas)
    palavras_metricas = ['Volumes', 'Unid. Itens', 'Itens por unidade', 'mes_ano', 'data', 'mes', 'ano']
    
    for col in df_rec.columns:
        col_str = str(col).strip()
        
        # Pular colunas de controle
        if col_str in ['data', 'mes', 'ano']:
            continue
            
        # Verificar se a coluna contém uma métrica
        possui_metrica = False
        sistema_extraida = col_str
        
        for metrica in palavras_metricas:
            if metrica in col_str:
                possui_metrica = True
                # Remover a palavra da métrica para extrair a sistema
                sistema_extraida = col_str.replace(metrica, '').strip()
                break
        
        # Se encontrou uma métrica e extraiu uma sistema válida, adicionar
        if possui_metrica and sistema_extraida and sistema_extraida not in palavras_metricas:
            sistemas_set.add(sistema_extraida)
    
    # Retornar lista ordenada alfabeticamente
    return sorted(list(sistemas_set))

# CARREGAMENTO DE DADOS
with st.spinner('📊 Carregando dados do Google Sheets...'):
    df_recebimento = carregar_dados_com_retry(st.secrets["connections"]["gsheets_itens_pacote"]["worksheet_recebimento"])
    df_rec_dados = carregar_dados_com_retry("rec_dados")

if df_recebimento is not None and not df_recebimento.empty:
    df_plot = df_recebimento.copy()
    colunas = ['mes_ano', 'qtd_descarregamentos', 'qtd_volumes_recebidos', 
               'peso_recebido', 'qtd_unidades_recebidos', 'qtd_itens_por_unidade']
    
    if len(df_plot.columns) == 6:
        df_plot.columns = colunas
    
    df_plot['data'] = pd.to_datetime(df_plot.iloc[:, 0] if 'mes_ano' not in df_plot.columns else df_plot['mes_ano'], 
                                     format='%m/%Y', errors='coerce')
    df_plot = df_plot.dropna(subset=['data']).sort_values('data')
    df_plot['ano'] = df_plot['data'].dt.year
    df_plot['mes'] = df_plot['data'].dt.month
    
    # Obter o mês máximo disponível nos dados
    mes_maximo_dados = df_plot['mes'].max()
    
    # Cards COMPACTOS
    col1, col2, col3, col4, col5 = st.columns(5, gap="small")
    placeholders_cards = [col1.empty(), col2.empty(), col3.empty(), col4.empty(), col5.empty()]
    cards = [
        ('qtd_descarregamentos', 'Descarregamentos', '#003a70', ''),
        ('peso_recebido', 'Peso Recebido', '#005a9c', ' kg'),
        ('qtd_volumes_recebidos', 'Volumes Recebidos', '#0075be', ''),
        ('qtd_unidades_recebidos', 'Unidades Recebidas', '#4d9fd6', ''),
        ('qtd_itens_por_unidade', 'Itens por Unidade', '#80b9e5', '')
    ]
    
    # Inicializar cards com valor 0
    for idx, (coluna, titulo, cor, sufixo) in enumerate(cards):
        placeholders_cards[idx].markdown(f"""
            <div class="metric-card" style="border-left-color: {cor};">
                <div class="metric-label">{titulo}</div>
                <div class="metric-value" style="color: {cor};">0{sufixo}</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='margin: 0.2rem 0;'></div>", unsafe_allow_html=True)
    
    # Configuração dos gráficos - Primeira linha (3 gráficos)
    metricas_linha1 = [
        {'coluna': 'qtd_descarregamentos', 'titulo': 'Descarregamentos',
         'cores': ['#003a70', '#1a5a8f', '#3379ae', '#4d99cd'], 'sufixo': ''},
        {'coluna': 'peso_recebido', 'titulo': 'Peso Recebido',
         'cores': ['#0075be', '#3390cc', '#66abd9', '#99c6e6'], 'sufixo': ' kg'},
        {'coluna': 'qtd_volumes_recebidos', 'titulo': 'Volumes Recebidos',
         'cores': ['#005a9c', '#3377b3', '#6694c9', '#99b1df'], 'sufixo': ''}
    ]
    
    # Configuração dos gráficos - Segunda linha (2 gráficos)
    metricas_linha2 = [
        {'coluna': 'qtd_unidades_recebidos', 'titulo': 'Unidades Recebidas',
         'cores': ['#003a70', '#266190', '#4d88b0', '#73afd0'], 'sufixo': ''},
        {'coluna': 'qtd_itens_por_unidade', 'titulo': 'Itens por Unidade',
         'cores': ['#0075be', '#3390cc', '#66abd9', '#99c6e6'], 'sufixo': ''}
    ]
    
    meses_pt = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    
    def formatar_numero(num, inteiro=False):
        if pd.isna(num): return "0"
        return f"{int(num):,}".replace(',', '.') if inteiro else f"{num:,.1f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    anos_unicos = sorted(df_plot['ano'].unique())
    
    # Criar placeholders para LINHA 1 (3 gráficos)
    placeholders_linha1 = []
    cols_linha1 = st.columns(3, gap="small")
    
    for j, config in enumerate(metricas_linha1):
        coluna = config['coluna']
        if coluna in df_plot.columns:
            df_plot[coluna] = pd.to_numeric(df_plot[coluna], errors='coerce')
            
            titulo_anos = [f"<span style='color: {config['cores'][anos_unicos.index(ano) % len(config['cores'])]}; font-weight: 700;'>{ano}: {formatar_numero(df_plot[df_plot['ano'] == ano][coluna].sum(), True)}{config['sufixo']}</span>" 
                          for ano in anos_unicos]
            titulo_completo = "<span style='color: #666;'> | </span>".join(titulo_anos)
            
            with cols_linha1[j]:
                container = st.container()
                with container:
                    st.markdown(f"""
                        <div style="background: white; padding: 0.15rem 0.3rem; border-radius: 8px 8px 0 0; 
                                    border-bottom: 1px solid #f0f0f0; margin-bottom: -0.2rem;">
                            <div style="font-family: 'Poppins', sans-serif; font-size: 14px; 
                                        color: #1a1a1a; font-weight: 800; text-align: center;">
                                {config['titulo']}
                            </div>
                            <div style="text-align: center; margin-top: 0.05rem; font-size: 10px; font-weight: 700;">
                                {titulo_completo}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    grafico_placeholder = st.empty()
                    placeholders_linha1.append({'placeholder': grafico_placeholder, 'config': config})
    
    # Criar placeholders para LINHA 2 (2 gráficos)
    placeholders_linha2 = []
    col_esquerda, col_direita = st.columns(2, gap="small")
    
    for j, config in enumerate(metricas_linha2):
        coluna = config['coluna']
        if coluna in df_plot.columns:
            df_plot[coluna] = pd.to_numeric(df_plot[coluna], errors='coerce')
            
            titulo_anos = [f"<span style='color: {config['cores'][anos_unicos.index(ano) % len(config['cores'])]}; font-weight: 700;'>{ano}: {formatar_numero(df_plot[df_plot['ano'] == ano][coluna].sum(), True)}{config['sufixo']}</span>" 
                          for ano in anos_unicos]
            titulo_completo = "<span style='color: #666;'> | </span>".join(titulo_anos)
            
            col_atual = col_esquerda if j == 0 else col_direita
            
            with col_atual:
                container = st.container()
                with container:
                    st.markdown(f"""
                        <div style="background: white; padding: 0.15rem 0.3rem; border-radius: 8px 8px 0 0; 
                                    border-bottom: 1px solid #f0f0f0; margin-bottom: -0.2rem;">
                            <div style="font-family: 'Poppins', sans-serif; font-size: 14px; 
                                        color: #1a1a1a; font-weight: 800; text-align: center;">
                                {config['titulo']}
                            </div>
                            <div style="text-align: center; margin-top: 0.05rem; font-size: 10px; font-weight: 700;">
                                {titulo_completo}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    grafico_placeholder = st.empty()
                    placeholders_linha2.append({'placeholder': grafico_placeholder, 'config': config})
    
    # Processar dados de rec_dados se disponível
    placeholders_linha3 = []
    if df_rec_dados is not None and not df_rec_dados.empty:
        df_rec = df_rec_dados.copy()
        
        # Processar data - primeira coluna
        df_rec['data'] = pd.to_datetime(df_rec.iloc[:, 0], format='%m/%Y', errors='coerce')
        df_rec = df_rec.dropna(subset=['data']).sort_values('data')
        df_rec['mes'] = df_rec['data'].dt.month
        df_rec['ano'] = df_rec['data'].dt.year
        
        # EXTRAÇÃO DINÂMICA DE sistemaS
        sistemas = extrair_sistemas_dinamicamente(df_rec)
        
        # Gerar cores dinamicamente baseado no número de sistemas
        cores_base = ['#003a70', '#0056A3', '#0075be', '#4d9fd6', '#80b9e5', '#b3d9f2', '#e6f2ff']
        cores_sistemas = [cores_base[i % len(cores_base)] for i in range(len(sistemas))]
        
        # Criar 3 gráficos para rec_dados - SEM ESPAÇAMENTO EXTRA
        
        # Definir os 3 tipos de métricas
        metricas_rec = [
            {'palavra_chave': 'Volumes', 'titulo': 'Volumes Recebidos por Sistema', 'excluir': ['Unid.', 'unidade']},
            {'palavra_chave': 'Unid. Itens', 'titulo': 'Unidades de Itens por Sistema', 'excluir': ['por unidade']},
            {'palavra_chave': 'Itens por unidade', 'titulo': 'Itens por Unidade por Sistema', 'excluir': ['Unid. Itens']}
        ]
        
        cols_rec = st.columns(3, gap="small")
        
        for idx_metrica, metrica_info in enumerate(metricas_rec):
            palavra_chave = metrica_info['palavra_chave']
            titulo = metrica_info['titulo']
            excluir = metrica_info['excluir']
            
            # Encontrar colunas que contenham a palavra-chave MAS NÃO as palavras de exclusão
            colunas_metrica = []
            mapeamento_sistemas = {}
            
            for col in df_rec.columns:
                col_str = str(col)
                if palavra_chave in col_str:
                    if not any(exc in col_str for exc in excluir):
                        colunas_metrica.append(col)
                        for sistema in sistemas:
                            if sistema in col_str:
                                mapeamento_sistemas[col] = sistema
                                break
            
            if colunas_metrica:
                # Calcular totais por sistema
                totais_txt = []
                for cat_idx, sistema in enumerate(sistemas):
                    col_nome = None
                    for col in colunas_metrica:
                        if mapeamento_sistemas.get(col) == sistema:
                            col_nome = col
                            break
                    
                    if col_nome:
                        df_rec[col_nome] = pd.to_numeric(df_rec[col_nome], errors='coerce').fillna(0)
                        total = df_rec[col_nome].sum()
                        cor = cores_sistemas[cat_idx]
                        totais_txt.append(f"<span style='color: {cor}; font-weight: 700;'>{sistema}: {formatar_numero(total, True)}</span>")
                
                titulo_completo = "<span style='color: #666;'> | </span>".join(totais_txt)
                
                with cols_rec[idx_metrica]:
                    st.markdown(f"""
                        <div style="background: white; padding: 0.1rem 0.2rem; border-radius: 8px 8px 0 0; 
                                    border-bottom: 1px solid #f0f0f0; margin-bottom: -0.2rem;">
                            <div style="font-family: 'Poppins', sans-serif; font-size: 12px; 
                                        color: #1a1a1a; font-weight: 800; text-align: center;">
                                {titulo}
                            </div>
                            <div style="text-align: center; margin-top: 0.05rem; font-size: 8px; font-weight: 700; line-height: 1.2;">
                                {titulo_completo}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    grafico_placeholder = st.empty()
                    placeholders_linha3.append({
                        'placeholder': grafico_placeholder, 
                        'palavra_chave': palavra_chave,
                        'titulo': titulo,
                        'colunas': colunas_metrica,
                        'mapeamento': mapeamento_sistemas,
                        'idx': idx_metrica
                    })
    
    mes_maximo_rec = df_rec['mes'].max() if df_rec_dados is not None and not df_rec_dados.empty else 0
    
    # ANIMAÇÃO SINCRONIZADA
    time.sleep(0.8)
    
    for mes_atual in range(1, mes_maximo_dados + 1):
        # Atualizar CARDS
        df_ate_mes = df_plot[df_plot['mes'] <= mes_atual]
        for idx, (coluna, titulo, cor, sufixo) in enumerate(cards):
            valor_acumulado = int(df_ate_mes[coluna].sum())
            valor_formatado = f"{valor_acumulado:,}".replace(',', '.')
            placeholders_cards[idx].markdown(f"""
                <div class="metric-card" style="border-left-color: {cor};">
                    <div class="metric-label">{titulo}</div>
                    <div class="metric-value" style="color: {cor};">{valor_formatado}{sufixo}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Atualizar GRÁFICOS LINHA 1 - ALTURA 240px
        for item in placeholders_linha1:
            config = item['config']
            grafico_placeholder = item['placeholder']
            coluna = config['coluna']
            
            fig = go.Figure()
            
            for idx_ano, ano in enumerate(anos_unicos):
                df_ano_filtrado = df_plot[(df_plot['ano'] == ano) & (df_plot['mes'] <= mes_atual)].sort_values('mes')
                if df_ano_filtrado.empty: continue
                
                cor = config['cores'][idx_ano % len(config['cores'])]
                text_values = [f"{int(v):,}".replace(',', '.') if not pd.isna(v) and int(v) != 0 else "" 
                             for v in df_ano_filtrado[coluna]]
                
                fig.add_trace(go.Scatter(
                    x=df_ano_filtrado['mes'], y=df_ano_filtrado[coluna],
                    mode='lines+markers+text', name=str(ano),
                    line=dict(width=3, color=cor, shape='spline'),
                    marker=dict(size=9, color=cor, line=dict(width=2, color='white')),
                    text=text_values, textposition='top center',
                    textfont=dict(size=10, color='#1a1a1a', family='Inter', weight=900),
                    cliponaxis=False, fill='tonexty' if idx_ano > 0 else None,
                    fillcolor=f"rgba({int(cor[1:3], 16)}, {int(cor[3:5], 16)}, {int(cor[5:7], 16)}, 0.1)",
                    hovertemplate=f'<b>{ano} - %{{customdata}}</b><br><b>Valor:</b> %{{y:,.0f}}{config["sufixo"]}<br><extra></extra>',
                    customdata=[meses_pt[m] for m in df_ano_filtrado['mes']]
                ))
            
            fig.update_layout(
                hovermode='x unified', template='plotly_white', height=240,
                font=dict(family='Inter', size=10, weight=700), showlegend=False,
                margin=dict(l=35, r=15, t=10, b=25), plot_bgcolor='rgba(248, 249, 250, 0.5)',
                xaxis=dict(tickmode='array', tickvals=list(range(1, 13)),
                          ticktext=[meses_pt[m] for m in range(1, 13)], tickangle=0,
                          tickfont=dict(size=9, family='Inter', weight=700),
                          showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.2)'),
                yaxis=dict(tickfont=dict(size=9, family='Inter', weight=700),
                          showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.2)',
                          rangemode='tozero'),
                hoverlabel=dict(bgcolor="white", font_size=11, font_family="Inter", bordercolor="#e0e0e0")
            )
            grafico_placeholder.plotly_chart(fig, width='stretch', 
                                            key=f"chart_l1_{coluna}_{mes_atual}", config={'displayModeBar': False})
        
        # Atualizar GRÁFICOS LINHA 2 - ALTURA 240px
        for item in placeholders_linha2:
            config = item['config']
            grafico_placeholder = item['placeholder']
            coluna = config['coluna']
            
            fig = go.Figure()
            
            for idx_ano, ano in enumerate(anos_unicos):
                df_ano_filtrado = df_plot[(df_plot['ano'] == ano) & (df_plot['mes'] <= mes_atual)].sort_values('mes')
                if df_ano_filtrado.empty: continue
                
                cor = config['cores'][idx_ano % len(config['cores'])]
                text_values = [f"{int(v):,}".replace(',', '.') if not pd.isna(v) and int(v) != 0 else "" 
                             for v in df_ano_filtrado[coluna]]
                
                fig.add_trace(go.Scatter(
                    x=df_ano_filtrado['mes'], y=df_ano_filtrado[coluna],
                    mode='lines+markers+text', name=str(ano),
                    line=dict(width=3, color=cor, shape='spline'),
                    marker=dict(size=9, color=cor, line=dict(width=2, color='white')),
                    text=text_values, textposition='top center',
                    textfont=dict(size=10, color='#1a1a1a', family='Inter', weight=900),
                    cliponaxis=False, fill='tonexty' if idx_ano > 0 else None,
                    fillcolor=f"rgba({int(cor[1:3], 16)}, {int(cor[3:5], 16)}, {int(cor[5:7], 16)}, 0.1)",
                    hovertemplate=f'<b>{ano} - %{{customdata}}</b><br><b>Valor:</b> %{{y:,.0f}}{config["sufixo"]}<br><extra></extra>',
                    customdata=[meses_pt[m] for m in df_ano_filtrado['mes']]
                ))
            
            fig.update_layout(
                hovermode='x unified', template='plotly_white', height=240,
                font=dict(family='Inter', size=10, weight=700), showlegend=False,
                margin=dict(l=35, r=15, t=10, b=25), plot_bgcolor='rgba(248, 249, 250, 0.5)',
                xaxis=dict(tickmode='array', tickvals=list(range(1, 13)),
                          ticktext=[meses_pt[m] for m in range(1, 13)], tickangle=0,
                          tickfont=dict(size=9, family='Inter', weight=700),
                          showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.2)'),
                yaxis=dict(tickfont=dict(size=9, family='Inter', weight=700),
                          showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.2)',
                          rangemode='tozero'),
                hoverlabel=dict(bgcolor="white", font_size=11, font_family="Inter", bordercolor="#e0e0e0")
            )
            grafico_placeholder.plotly_chart(fig, width='stretch', 
                                            key=f"chart_l2_{coluna}_{mes_atual}", config={'displayModeBar': False})
        
        # Atualizar GRÁFICOS LINHA 3 - ALTURA 260px
        if placeholders_linha3 and mes_atual <= mes_maximo_rec:
            for item in placeholders_linha3:
                grafico_placeholder = item['placeholder']
                palavra_chave = item['palavra_chave']
                mapeamento = item['mapeamento']
                idx_grafico = item['idx']
                
                # GRÁFICO 1: PIZZA (Volumes Recebidos)
                if idx_grafico == 0:
                    valores_pizza = []
                    labels_pizza = []
                    cores_pizza = []
                    
                    for cat_idx, sistema in enumerate(sistemas):
                        col_nome = None
                        for col, cat in mapeamento.items():
                            if cat == sistema:
                                col_nome = col
                                break
                        
                        if col_nome and col_nome in df_rec.columns:
                            df_cat_filtrado = df_rec[df_rec['mes'] <= mes_atual]
                            total = df_cat_filtrado[col_nome].fillna(0).sum()
                            if total > 0:
                                valores_pizza.append(total)
                                labels_pizza.append(sistema)
                                cores_pizza.append(cores_sistemas[cat_idx])
                    
                    # Calcular total e percentuais para a legenda
                    total_geral = sum(valores_pizza)
                    labels_com_info = []
                    for i, (label, valor) in enumerate(zip(labels_pizza, valores_pizza)):
                        percentual = (valor / total_geral * 100) if total_geral > 0 else 0
                        valor_formatado = f"{int(valor):,}".replace(',', '.')
                        labels_com_info.append(f"{label}: {valor_formatado} ({percentual:.1f}%)")
                    
                    fig = go.Figure()
                    fig.add_trace(go.Pie(
                        labels=labels_com_info,
                        values=valores_pizza,
                        marker=dict(colors=cores_pizza, line=dict(color='white', width=2)),
                        #textinfo='percent',
                        #textfont=dict(size=10, family='Inter', weight=700, color='white'),
                        hovertemplate='<b>%{label}</b><br>Volumes: %{value:,.0f}<br>Percentual: %{percent}<extra></extra>',
                        hole=0.3
                    ))
                    
                    fig.update_layout(
                        template='plotly_white', height=240,
                        font=dict(family='Inter', size=9, weight=700),
                        showlegend=True,
                        legend=dict(
                            orientation="v",
                            yanchor="middle",
                            y=0.5,
                            xanchor="left",
                            x=1.02,
                            font=dict(size=8.5)
                        ),
                        margin=dict(l=20, r=150, t=10, b=10),
                        hoverlabel=dict(bgcolor="white", font_size=11, font_family="Inter", bordercolor="#e0e0e0")
                    )
                    grafico_placeholder.plotly_chart(fig, width='stretch',
                                                    key=f"chart_l3_pizza_{mes_atual}", config={'displayModeBar': False})
                
                # GRÁFICO 2: BARRAS HORIZONTAL (Unidades de Itens)
                elif idx_grafico == 1:
                    valores_barras = []
                    labels_barras = []
                    cores_barras = []
                    
                    for cat_idx, sistema in enumerate(sistemas):
                        col_nome = None
                        for col, cat in mapeamento.items():
                            if cat == sistema:
                                col_nome = col
                                break
                        
                        if col_nome and col_nome in df_rec.columns:
                            df_cat_filtrado = df_rec[df_rec['mes'] <= mes_atual]
                            total = df_cat_filtrado[col_nome].fillna(0).sum()
                            valores_barras.append(total)
                            labels_barras.append(sistema)
                            cores_barras.append(cores_sistemas[cat_idx])
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=valores_barras,
                        y=labels_barras,
                        orientation='h',
                        marker=dict(
                            color=cores_barras, 
                            line=dict(color='white', width=1.5),
                            cornerradius=8  # Border radius nas barras horizontais
                        ),
                        text=[f"{int(v):,}".replace(',', '.') if v > 0 else "" for v in valores_barras],
                        textposition='outside',
                        textfont=dict(size=10, family='Inter', weight=800, color='#1a1a1a'),
                        hovertemplate='<b>%{y}</b><br>Unidades: %{x:,.0f}<extra></extra>'
                    ))
                    
                    # Calcula o valor máximo para ajustar o range do eixo X
                    max_valor = max(valores_barras) if valores_barras else 0
                    
                    fig.update_layout(
                        template='plotly_white', 
                        height=260,
                        font=dict(family='Inter', size=9, weight=700),
                        showlegend=False,
                        margin=dict(l=100, r=50, t=10, b=25),
                        plot_bgcolor='rgba(248, 249, 250, 0.5)',
                        xaxis=dict(
                            tickfont=dict(size=9, family='Inter', weight=700),
                            showgrid=True, 
                            gridwidth=1, 
                            gridcolor='rgba(200, 200, 200, 0.2)',
                            range=[0, max_valor * 1.15]  # Adiciona 15% de espaço à direita para os valores
                        ),
                        yaxis=dict(
                            tickfont=dict(size=9, family='Inter', weight=700),
                            showgrid=False
                        ),
                        hoverlabel=dict(
                            bgcolor="white", 
                            font_size=11, 
                            font_family="Inter", 
                            bordercolor="#e0e0e0"
                        )
                    )
                    
                    grafico_placeholder.plotly_chart(
                        fig, 
                        width='stretch',
                        key=f"chart_l3_barras_h_{mes_atual}", 
                        config={'displayModeBar': False}
                    ) 
                # GRÁFICO 3: BARRAS VERTICAL (Itens por Unidade)
                elif idx_grafico == 2:
                    valores_barras = []
                    labels_barras = []
                    cores_barras = []
                    
                    for cat_idx, sistema in enumerate(sistemas):
                        col_nome = None
                        for col, cat in mapeamento.items():
                            if cat == sistema:
                                col_nome = col
                                break
                        
                        if col_nome and col_nome in df_rec.columns:
                            df_cat_filtrado = df_rec[df_rec['mes'] <= mes_atual]
                            total = df_cat_filtrado[col_nome].fillna(0).sum()
                            valores_barras.append(total)
                            labels_barras.append(sistema)
                            cores_barras.append(cores_sistemas[cat_idx])
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=labels_barras,
                        y=valores_barras,
                        marker=dict(
                            color=cores_barras, 
                            line=dict(color='white', width=1.5),
                            cornerradius=8  # Border radius nas barras
                        ),
                        text=[f"{int(v):,}".replace(',', '.') if v > 0 else "" for v in valores_barras],
                        textposition='outside',  # Valores acima das barras
                        textfont=dict(size=10, family='Inter', weight=700, color='#1a1a1a'),
                        hovertemplate='<b>%{x}</b><br>Itens: %{y:,.0f}<extra></extra>'
                    ))
                    
                    # Calcula o valor máximo para ajustar o range do eixo Y
                    max_valor = max(valores_barras) if valores_barras else 0
                    
                    fig.update_layout(
                        template='plotly_white', 
                        height=260,
                        font=dict(family='Inter', size=9, weight=700),
                        showlegend=False,
                        margin=dict(l=20, r=20, t=40, b=100),  # Aumentei margem superior para os valores
                        plot_bgcolor='rgba(248, 249, 250, 0.5)',
                        xaxis=dict(
                            tickfont=dict(size=8, family='Inter', weight=700),
                            tickangle=-45,
                            showgrid=False
                        ),
                        yaxis=dict(
                            tickfont=dict(size=9, family='Inter', weight=700),
                            showgrid=True, 
                            gridwidth=1, 
                            gridcolor='rgba(200, 200, 200, 0.2)',
                            range=[0, max_valor * 1.15]  # Adiciona 15% de espaço acima para os valores
                        ),
                        hoverlabel=dict(
                            bgcolor="white", 
                            font_size=11, 
                            font_family="Inter", 
                            bordercolor="#e0e0e0"
                        )
                    )
                    
                    grafico_placeholder.plotly_chart(
                        fig, 
                        width='stretch',
                        key=f"chart_l3_barras_v_{mes_atual}", 
                        config={'displayModeBar': False}
                    )
        time.sleep(0.9)
    
elif df_recebimento is None:
    st.info("💡 **Aguarde 1 minuto e clique no botão 🔄 acima para tentar novamente.**")
else:
    st.error("❌ Não há dados suficientes para gerar os gráficos.")

# Auto-recarregamento
time.sleep(60)
st.rerun()