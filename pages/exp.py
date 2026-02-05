import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from requests.exceptions import ConnectionError, Timeout
from urllib3.exceptions import ProtocolError
from datetime import datetime, timedelta

# Configuração
st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="PMJA - Dashboard Expedição")

# Inicializar session_state para controle de navegação
if 'inicio_exibicao' not in st.session_state:
    st.session_state.inicio_exibicao = time.time()

# Calcular tempo decorrido
tempo_decorrido = time.time() - st.session_state.inicio_exibicao

# Após 2 minutos (120 segundos), navegar para pallet.py
if tempo_decorrido >= 120:
    st.session_state.inicio_exibicao = time.time()
    st.switch_page("pages/rec.py")

# CSS com fontes compatíveis e sem scroll nos gráficos
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Poppins:wght@600;700;800;900&display=swap');
        
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            height: 100vh !important; width: 100vw !important; margin: 0 !important;
            padding: 0 !important; overflow: hidden !important;
            background: linear-gradient(135deg, #f5f7fa 0%, #e8eef5 100%);
        }
        .block-container { 
            padding: 0.2rem 0.5rem !important; 
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
            padding: 0 0.2rem !important; 
        }
        .stPlotlyChart { 
            height: 100% !important; 
            width: 100% !important; 
            background: white;
            border-radius: 0 0 8px 8px; 
            box-shadow: 0 2px 8px rgba(0, 58, 112, 0.06); 
            padding: 0.1rem;
            overflow: hidden !important;
        }
        /* Remover scroll dos gráficos Plotly */
        .js-plotly-plot, .plotly, .plot-container {
            overflow: hidden !important;
        }
        .svg-container {
            overflow: visible !important;
        }
        div[data-testid="stVerticalBlock"] > div { 
            gap: 0.2rem !important; 
        }
        ::-webkit-scrollbar { 
            width: 8px; 
            height: 8px; 
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
            border-radius: 10px; 
            box-shadow: 0 4px 15px rgba(0, 58, 112, 0.12);
            padding: 0.2rem 1rem; 
            margin-bottom: 0.8rem; 
        }
        .metric-card { 
            background: white; 
            border-radius: 8px; 
            padding: 0.8rem;
            box-shadow: 0 2px 8px rgba(0, 58, 112, 0.06); 
            border-left: 3px solid;
            transition: all 0.3s ease; 
            min-height: 80px; 
        }
        .metric-card:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 4px 15px rgba(0, 58, 112, 0.12); 
        }
        .metric-label { 
            font-family: 'Inter', sans-serif; 
            font-size: 14px; 
            color: #666;
            font-weight: 700; 
            text-transform: uppercase; 
            letter-spacing: 0.5px; 
            margin-bottom: 0.15rem; 
        }
        .metric-value { 
            font-family: 'Poppins', sans-serif; 
            font-size: 24px; 
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
                 style="height: 40px; filter: brightness(0) invert(1);" alt="Logo AZ">
            <div style="text-align: center; flex: 1;">
                <h1 style="font-family: 'Poppins', sans-serif; font-size: 22px; color: white; 
                           margin: 0; font-weight: 800; letter-spacing: -0.5px;">
                    PMJA - Dashboard Gestão de Materiais
                </h1>
                <p style="font-family: 'Inter', sans-serif; font-size: 15px; color: rgba(255,255,255,0.9); 
                          margin: 0.05rem 0 0 0; font-weight: 700;">
                    Evolução Temporal - Expedição
                </p>
            </div>
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Logo-engie.svg/2445px-Logo-engie.svg.png" 
                 style="height: 40px; filter: brightness(0) invert(1);" alt="Logo Engie">
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
def carregar_dados_com_retry(max_tentativas=3):
    """Carrega dados do Google Sheets com retry e cache"""
    for tentativa in range(max_tentativas):
        try:
            if tentativa > 0:
                delay = min(tentativa * 3, 10)
                time.sleep(delay)
            
            conn = st.connection("gsheets_itens_pacote", type=GSheetsConnection)
            df = conn.read(worksheet="exp_dados", ttl="10m")
            
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

def processar_dados_expedicao(df_raw):
    """Processa os dados brutos e calcula totais corretamente"""
    if df_raw is None or df_raw.empty:
        return None, None
    
    df = df_raw.copy()
    
    # Renomear primeira coluna para 'mes'
    df.rename(columns={df.columns[0]: 'mes'}, inplace=True)
    
    # Remover linhas vazias
    df = df[df['mes'].notna()].copy()
    
    # Converter mês para datetime
    df['data'] = pd.to_datetime(df['mes'], format='%m/%Y', errors='coerce')
    df = df.dropna(subset=['data']).copy()
    
    # Extrair ano e mês
    df['ano'] = df['data'].dt.year
    df['mes_num'] = df['data'].dt.month
    df['mes_ano'] = df['data'].dt.strftime('%m/%Y')
    
    # Identificar colunas dinamicamente
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
    
    # Converter para numérico
    for col in colunas_requisicoes + colunas_unidades + colunas_itens_unidade:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Calcular totais
    df['qtd_requisicoes'] = df[colunas_requisicoes].sum(axis=1)
    df['qtd_unidades_emitidas'] = df[colunas_unidades].sum(axis=1)
    
    if colunas_itens_unidade:
        df['qtd_itens_total'] = df[colunas_itens_unidade].sum(axis=1)
    else:
        df['qtd_itens_total'] = 0
    
    # Selecionar colunas finais
    df_final = df[['mes_ano', 'ano', 'mes_num', 'qtd_requisicoes', 
                   'qtd_unidades_emitidas', 'qtd_itens_total']].copy()
    
    df_detalhado = df[['mes_ano', 'ano', 'mes_num'] + colunas_requisicoes + colunas_unidades + colunas_itens_unidade].copy()
    
    # Ordenar
    df_final = df_final.sort_values(['ano', 'mes_num']).reset_index(drop=True)
    df_detalhado = df_detalhado.sort_values(['ano', 'mes_num']).reset_index(drop=True)
    
    return df_final, df_detalhado

def extrair_categoria(nome_coluna):
    """Extrair nomes das categorias removendo sufixos"""
    categoria = nome_coluna.replace(' Requisições', '').replace(' Requisiçoes', '')
    categoria = categoria.replace(' Unid. Itens', '').replace(' Unid Itens', '')
    categoria = categoria.replace(' Itens por unidade', '').replace(' Items por unidade', '')
    return categoria.strip()

# CARREGAMENTO DE DADOS
with st.spinner('📊 Carregando dados do Google Sheets...'):
    df_raw = carregar_dados_com_retry()
    
    if df_raw is not None and not df_raw.empty:
        df_expedicao, df_detalhado = processar_dados_expedicao(df_raw)
    else:
        df_expedicao = None
        df_detalhado = None

if df_expedicao is not None and not df_expedicao.empty:
    df_plot = df_expedicao.copy()
    df_plot.rename(columns={'mes_num': 'mes'}, inplace=True)
    
    if 'data' not in df_plot.columns:
        df_plot['data'] = pd.to_datetime(df_plot['mes_ano'], format='%m/%Y', errors='coerce')
    
    for col in ['qtd_requisicoes', 'qtd_unidades_emitidas', 'qtd_itens_total']:
        df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce').fillna(0)
    
    mes_maximo_dados = df_plot['mes'].max()
    
    # ========== CARDS ==========
    col1, col2, col3 = st.columns(3, gap="small")
    placeholders_cards = [col1.empty(), col2.empty(), col3.empty()]
    cards = [
        ('qtd_requisicoes', 'Requisições', '#003a70', ''),
        ('qtd_unidades_emitidas', 'Unidades Emitidas', '#005a9c', ''),
        ('qtd_itens_total', 'Total de Itens', '#0075be', '')
    ]
    
    # Inicializar cards com valor 0
    for idx, (coluna, titulo, cor, sufixo) in enumerate(cards):
        placeholders_cards[idx].markdown(f"""
            <div class="metric-card" style="border-left-color: {cor};">
                <div class="metric-label">{titulo}</div>
                <div class="metric-value" style="color: {cor};">0{sufixo}</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='margin: 0.1rem 0;'></div>", unsafe_allow_html=True)
    
    # ========== CONFIGURAÇÃO DOS GRÁFICOS ==========
    metricas = [
        {'coluna': 'qtd_requisicoes', 'titulo': 'Requisições', 'tipo': 'barra_horizontal',
         'cores': ['#001a33', '#003366', '#004d99', '#0066cc'], 'sufixo': ''},
        {'coluna': 'qtd_unidades_emitidas', 'titulo': 'Unidades Emitidas', 'tipo': 'barra_vertical',
         'cores': ['#003d66', '#005a9c', '#0077cc', '#3399dd'], 'sufixo': ''},
        {'coluna': 'qtd_itens_total', 'titulo': 'Total de Itens', 'tipo': 'linha',
         'cores': ['#0056A3', '#0075be', '#3399dd', '#66b3ee'], 'sufixo': ''}
    ]
    
    meses_pt = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    
    def formatar_numero(num, inteiro=False):
        if pd.isna(num): return "0"
        return f"{int(num):,}".replace(',', '.') if inteiro else f"{num:,.1f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    anos_unicos = sorted(df_plot['ano'].unique())
    
    # ========== CRIAR PLACEHOLDERS PARA GRÁFICOS SUPERIORES ==========
    placeholders_graficos = []
    cols = st.columns(3, gap="small")
    row_placeholders = []
    
    for j, config in enumerate(metricas):
        with cols[j]:
            container = st.container()
            coluna = config['coluna']
            
            if coluna in df_plot.columns:
                # Título com totais por ano
                titulo_anos = [f"<span style='color: {config['cores'][anos_unicos.index(ano) % len(config['cores'])]}; font-weight: 700;'>{ano}: {formatar_numero(df_plot[df_plot['ano'] == ano][coluna].sum(), True)}{config['sufixo']}</span>" 
                              for ano in anos_unicos]
                titulo_completo = "<span style='color: #666;'> | </span>".join(titulo_anos)
                
                with container:
                    st.markdown(f"""
                        <div style="background: white; padding: 0.15rem; border-radius: 8px 8px 0 0; 
                                    border-bottom: 1px solid #f0f0f0; margin-bottom: -0.3rem;">
                            <div style="font-family: 'Poppins', sans-serif; font-size: 17px; 
                                        color: #1a1a1a; font-weight: 800; text-align: center;">
                                {config['titulo']}
                            </div>
                            <div style="text-align: center; margin-top: 0.05rem; font-size: 12px; font-weight: 700;">
                                {titulo_completo}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    grafico_placeholder = st.empty()
                    row_placeholders.append({'placeholder': grafico_placeholder, 'config': config})
    
    if row_placeholders:
        placeholders_graficos.append(row_placeholders)
    
    # ========== GRÁFICOS INFERIORES (3 GRÁFICOS POR SISTEMA) ==========
    st.markdown("<div style='margin: 0.5rem 0;'></div>", unsafe_allow_html=True)
    
    # Identificar colunas do df_detalhado
    colunas_req_det = [col for col in df_detalhado.columns if 'requisi' in col.lower() and 'unid' not in col.lower() and 'por' not in col.lower()]
    colunas_unid_det = [col for col in df_detalhado.columns if 'unid' in col.lower() and 'iten' in col.lower().replace('.', '') and 'por' not in col.lower()]
    colunas_itens_det = [col for col in df_detalhado.columns if 'iten' in col.lower().replace('.', '') and 'por' in col.lower() and 'unid' in col.lower()]
    
    # Pegar categorias únicas
    categorias_req = [extrair_categoria(col) for col in colunas_req_det]
    categorias_unid = [extrair_categoria(col) for col in colunas_unid_det]
    categorias_itens = [extrair_categoria(col) for col in colunas_itens_det]
    
    # Cores
    cores_categorias = ['#001a33', '#002d4d', '#003d66', '#004d80', '#005d99', 
                       '#006db3', '#007dcc', '#1a8dd4', '#3399dd', '#4da6e6', 
                       '#66b3ee', '#80c0f5', '#99ccff', '#b3d9ff']
    
    # Criar 3 colunas e placeholders para os gráficos inferiores
    col_g1, col_g2, col_g3 = st.columns(3, gap="small")
    
    graficos_config = [
        {'metrica': 'requisicoes', 'titulo': 'Requisições por Sistema', 'col': col_g1, 
         'cor_principal': '#003a70', 'tipo': 'donut', 'colunas_dados': colunas_req_det},
        {'metrica': 'unidades', 'titulo': 'Unidades Emitidas por Sistema', 'col': col_g2, 
         'cor_principal': '#0056A3', 'tipo': 'linha', 'colunas_dados': colunas_unid_det},
        {'metrica': 'itens', 'titulo': 'Total de Itens por Sistema', 'col': col_g3, 
         'cor_principal': '#0075be', 'tipo': 'barra_vertical', 'colunas_dados': colunas_itens_det}
    ]
    
    # Criar placeholders
    placeholders_inferiores = []
    for config in graficos_config:
        with config['col']:
            st.markdown(f"""
                <div style="background: white; padding: 0.4rem; border-radius: 12px; 
                            box-shadow: 0 4px 15px rgba(0, 58, 112, 0.1);
                            border-top: 4px solid {config['cor_principal']};">
                </div>
            """, unsafe_allow_html=True)
            placeholder = st.empty()
            placeholders_inferiores.append({'placeholder': placeholder, 'config': config})
    
    # ========== ANIMAÇÃO MÊS A MÊS - TODOS OS 6 GRÁFICOS JUNTOS ==========
    time.sleep(0.5)
    
    for mes_atual in range(1, mes_maximo_dados + 1):
        df_ate_mes = df_plot[df_plot['mes'] <= mes_atual]
        df_detalhado_ate_mes = df_detalhado[df_detalhado['mes_num'] <= mes_atual]
        
        # Atualizar cards com animação
        for idx, (coluna, titulo, cor, sufixo) in enumerate(cards):
            valor_acumulado = int(df_ate_mes[coluna].sum())
            valor_formatado = f"{valor_acumulado:,}".replace(',', '.')
            
            placeholders_cards[idx].markdown(f"""
                <div class="metric-card" style="border-left-color: {cor};">
                    <div class="metric-label">{titulo}</div>
                    <div class="metric-value" style="color: {cor};">{valor_formatado}{sufixo}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # ========== ATUALIZAR GRÁFICOS SUPERIORES (3 gráficos principais) ==========
        for row in placeholders_graficos:
            for item in row:
                config = item['config']
                grafico_placeholder = item['placeholder']
                coluna = config['coluna']
                tipo_grafico = config['tipo']
                
                fig = go.Figure()
                
                # GRÁFICO DE LINHA
                if tipo_grafico == 'linha':
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
                            marker=dict(size=10, color=cor, line=dict(width=2, color='white')),
                            text=text_values, textposition='top center',
                            textfont=dict(size=10, color='#1a1a1a', family='Inter, sans-serif'),
                            cliponaxis=False, fill='tonexty' if idx_ano > 0 else None,
                            fillcolor=f"rgba({int(cor[1:3], 16)}, {int(cor[3:5], 16)}, {int(cor[5:7], 16)}, 0.1)",
                            hovertemplate=f'<b>{ano} - %{{customdata}}</b><br><b>Valor:</b> %{{y:,.0f}}<br><extra></extra>',
                            customdata=[meses_pt[m] for m in df_ano_filtrado['mes']]
                        ))
                    
                    fig.update_layout(
                        hovermode='x unified', template='plotly_white', height=350,
                        font=dict(family='Inter, sans-serif', size=11), showlegend=False,
                        margin=dict(l=45, r=20, t=10, b=25), plot_bgcolor='rgba(248, 249, 250, 0.5)',
                        xaxis=dict(tickmode='array', tickvals=list(range(1, 13)),
                                  ticktext=[meses_pt[m] for m in range(1, 13)], tickangle=0,
                                  tickfont=dict(size=11, family='Inter, sans-serif'),
                                  showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.2)'),
                        yaxis=dict(tickfont=dict(size=11, family='Inter, sans-serif'),
                                  showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.2)',
                                  rangemode='tozero'),
                        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, sans-serif")
                    )
                
                # GRÁFICO DE BARRAS HORIZONTAL
                elif tipo_grafico == 'barra_horizontal':
                    meses_exibidos = sorted(df_plot[df_plot['mes'] <= mes_atual]['mes'].unique(), reverse=True)
                    
                    for idx_ano, ano in enumerate(anos_unicos):
                        df_ano_filtrado = df_plot[(df_plot['ano'] == ano) & (df_plot['mes'] <= mes_atual)].sort_values('mes', ascending=False)
                        if df_ano_filtrado.empty: continue
                        
                        cor = config['cores'][idx_ano % len(config['cores'])]
                        
                        valores = []
                        textos = []
                        for mes in meses_exibidos:
                            row_mes = df_ano_filtrado[df_ano_filtrado['mes'] == mes]
                            if not row_mes.empty:
                                valor = row_mes[coluna].iloc[0]
                                valores.append(valor)
                                textos.append(f"{int(valor):,}".replace(',', '.') if not pd.isna(valor) and int(valor) != 0 else "")
                            else:
                                valores.append(0)
                                textos.append("")
                        
                        fig.add_trace(go.Bar(
                            x=valores, 
                            y=[meses_pt[m] for m in meses_exibidos],
                            orientation='h',
                            name=str(ano),
                            text=textos, 
                            textposition='inside',
                            insidetextanchor='middle',
                            textfont=dict(size=10, color='white', family='Inter, sans-serif'),
                            marker=dict(color=cor, line=dict(color='white', width=1), cornerradius=6),
                            hovertemplate=f'<b>{ano} - %{{y}}</b><br><b>Valor:</b> %{{x:,.0f}}<br><extra></extra>',
                        ))
                    
                    fig.update_layout(
                        template='plotly_white', height=350,
                        font=dict(family='Inter, sans-serif', size=11),
                        margin=dict(l=45, r=40, t=10, b=25), 
                        plot_bgcolor='rgba(248, 249, 250, 0.5)',
                        barmode='stack',
                        bargap=0.12,
                        showlegend=False,
                        xaxis=dict(
                            tickfont=dict(size=11, family='Inter, sans-serif'),
                            showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.2)',
                            rangemode='tozero'
                        ),
                        yaxis=dict(
                            tickfont=dict(size=12, family='Inter, sans-serif'),
                            showgrid=False,
                            categoryorder='array',
                            categoryarray=[meses_pt[m] for m in meses_exibidos]
                        ),
                        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, sans-serif")
                    )
                
                # GRÁFICO DE BARRAS VERTICAL
                elif tipo_grafico == 'barra_vertical':
                    meses_exibidos = sorted(df_plot[df_plot['mes'] <= mes_atual]['mes'].unique())
                    
                    for idx_ano, ano in enumerate(anos_unicos):
                        df_ano_filtrado = df_plot[(df_plot['ano'] == ano) & (df_plot['mes'] <= mes_atual)].sort_values('mes')
                        if df_ano_filtrado.empty: continue
                        
                        cor = config['cores'][idx_ano % len(config['cores'])]
                        
                        valores = []
                        textos = []
                        for mes in meses_exibidos:
                            row_mes = df_ano_filtrado[df_ano_filtrado['mes'] == mes]
                            if not row_mes.empty:
                                valor = row_mes[coluna].iloc[0]
                                valores.append(valor)
                                textos.append(f"{int(valor):,}".replace(',', '.') if not pd.isna(valor) and int(valor) != 0 else "")
                            else:
                                valores.append(0)
                                textos.append("")
                        
                        fig.add_trace(go.Bar(
                            x=[meses_pt[m] for m in meses_exibidos], 
                            y=valores,
                            name=str(ano),
                            text=textos, 
                            textposition='inside',
                            insidetextanchor='middle',
                            textfont=dict(size=10, color='white', family='Inter, sans-serif'),
                            marker=dict(color=cor, line=dict(color='white', width=1), cornerradius=6),
                            hovertemplate=f'<b>{ano} - %{{x}}</b><br><b>Valor:</b> %{{y:,.0f}}<br><extra></extra>',
                        ))
                    
                    fig.update_layout(
                        template='plotly_white', height=350,
                        font=dict(family='Inter, sans-serif', size=11),
                        margin=dict(l=40, r=20, t=30, b=40), 
                        plot_bgcolor='rgba(248, 249, 250, 0.5)',
                        barmode='stack',
                        bargap=0.12,
                        showlegend=False,
                        xaxis=dict(
                            tickfont=dict(size=12, family='Inter, sans-serif'),
                            showgrid=False,
                            tickangle=0
                        ),
                        yaxis=dict(
                            tickfont=dict(size=10, family='Inter, sans-serif'),
                            showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.2)',
                            rangemode='tozero'
                        ),
                        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, sans-serif")
                    )
                
                grafico_placeholder.plotly_chart(
                    fig, 
                    key=f"chart_{coluna}_{mes_atual}", 
                    config={'displayModeBar': False, 'scrollZoom': False},
                    width='stretch'
                )
        
        # ========== ATUALIZAR GRÁFICOS INFERIORES (3 gráficos por sistema) ==========
        for item in placeholders_inferiores:
            config = item['config']
            placeholder = item['placeholder']
            metrica = config['metrica']
            titulo = config['titulo']
            cor_principal = config['cor_principal']
            tipo_grafico_barras = config['tipo']
            colunas_dados = config['colunas_dados']
            
            # Calcular totais acumulados por categoria até o mês atual
            totais_por_categoria = {}
            
            for i, col in enumerate(colunas_dados):
                cat = extrair_categoria(col)
                
                if cat not in totais_por_categoria:
                    totais_por_categoria[cat] = {
                        'valor': 0,
                        'cor': cores_categorias[len(totais_por_categoria) % len(cores_categorias)]
                    }
                
                valor_total = df_detalhado_ate_mes[col].sum()
                totais_por_categoria[cat]['valor'] += valor_total
            
            # Filtrar apenas categorias com valor > 0
            dados_filtrados = {cat: dados for cat, dados in totais_por_categoria.items() if dados['valor'] > 0}
            
            if dados_filtrados:
                # Ordenar por valor
                dados_ordenados = sorted(dados_filtrados.items(), key=lambda x: x[1]['valor'], reverse=True)
                
                categorias = [cat for cat, _ in dados_ordenados]
                valores = [dados['valor'] for _, dados in dados_ordenados]
                cores = [dados['cor'] for _, dados in dados_ordenados]
                
                # Calcular total e percentuais
                total = sum(valores)
                percentuais = [(v/total)*100 for v in valores]
                
                fig = go.Figure()
                
                # GRÁFICO DONUT
                if tipo_grafico_barras == 'donut':
                    # Criar labels da legenda com nome: valor (%)
                    labels_legenda = [f"{cat}: {int(val):,} ({p:.1f}%)".replace(',', '.') 
                                     for cat, val, p in zip(categorias, valores, percentuais)]
                    
                    # Criar texto para aparecer nas fatias (apenas %)
                    texto_fatias = [f"{p:.1f}%" for p in percentuais]
                    
                    fig.add_trace(go.Pie(
                        labels=labels_legenda,
                        values=valores,
                        hole=0.4,
                        marker=dict(colors=cores, line=dict(color='white', width=3)),
                        text=texto_fatias,
                        textfont=dict(size=13, family='Poppins, sans-serif', weight='bold'),
                        insidetextorientation='radial',
                        textinfo='text',
                        hovertemplate='<b>%{label}</b><br><extra></extra>',
                        showlegend=True,
                        pull=[0.03 if valores[i] == max(valores) else 0 for i in range(len(categorias))],
                        rotation=90,
                        direction='clockwise',
                        sort=False
                    ))
                    
                    fig.update_layout(
                        title=dict(
                            text=f'<b>{titulo}</b>',
                            font=dict(family='Poppins, sans-serif', size=16, color='#1a1a1a'),
                            x=0.5, xanchor='center', y=0.98, yanchor='top'
                        ),
                        template='plotly_white',
                        height=360,
                        font=dict(family='Inter, sans-serif', size=11),
                        margin=dict(l=20, r=20, t=50, b=20),
                        legend=dict(
                            orientation="v", 
                            yanchor="middle", 
                            y=0.5, 
                            xanchor="left", 
                            x=1.05,
                            font=dict(size=10, family='Inter, sans-serif', color='#333'),
                            bgcolor='rgba(255,255,255,0.9)', 
                            borderwidth=1
                        ),
                        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, sans-serif")
                    )
                
                # GRÁFICO DE LINHA
                elif tipo_grafico_barras == 'linha':
                    x_valores = list(range(len(categorias)))
                    textos_visiveis = [f"<b>{int(v):,}</b><br>{p:.1f}%".replace(',', '.') if v > 0 else "" for v, p in zip(valores, percentuais)]
                    
                    fig.add_trace(go.Scatter(
                        x=x_valores, y=valores,
                        mode='lines+markers+text',
                        text=textos_visiveis,
                        textposition='top center',
                        textfont=dict(size=11, color='#1a1a1a', family='Inter, sans-serif'),
                        line=dict(width=4, color=cor_principal, shape='spline'),
                        marker=dict(size=15, color=cores, symbol='circle'),
                        hovertemplate='<b>%{customdata}</b><br><b>Quantidade:</b> %{y:,.0f}<br><extra></extra>',
                        customdata=categorias,
                        showlegend=False,
                        fill='tozeroy',
                        fillcolor=f"rgba({int(cor_principal[1:3], 16)}, {int(cor_principal[3:5], 16)}, {int(cor_principal[5:7], 16)}, 0.2)",
                        cliponaxis=False
                    ))
                    
                    fig.update_layout(
                        title=dict(
                            text=f'<b>{titulo}</b>',
                            font=dict(family='Poppins, sans-serif', size=16, color='#1a1a1a'),
                            x=0.5, xanchor='center', y=0.95, yanchor='top'
                        ),
                        template='plotly_white',
                        height=360,
                        font=dict(family='Inter, sans-serif', size=11),
                        margin=dict(l=50, r=25, t=100, b=80),
                        xaxis=dict(
                            tickmode='array', tickvals=x_valores, ticktext=categorias,
                            tickfont=dict(size=11, family='Inter, sans-serif', color='#333'),
                            showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.25)',
                            tickangle=-35
                        ),
                        yaxis=dict(
                            tickfont=dict(size=11, family='Inter, sans-serif'),
                            showgrid=True, gridwidth=1.5, gridcolor='rgba(200, 200, 200, 0.4)',
                            range=[0, max(valores) * 1.6], showticklabels=False
                        ),
                        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, sans-serif")
                    )
                
                # GRÁFICO DE BARRAS VERTICAL
                elif tipo_grafico_barras == 'barra_vertical':
                    textos_customizados = [f"<b>{int(v):,}</b><br>{p:.1f}%".replace(',', '.') if v > 0 else "" for v, p in zip(valores, percentuais)]
                    
                    fig.add_trace(go.Bar(
                        x=categorias, y=valores,
                        text=textos_customizados,
                        textposition='outside',
                        textfont=dict(size=10, color='#1a1a1a', family='Inter, sans-serif'),
                        marker=dict(color=cores, line=dict(color='white', width=2.5), cornerradius=15),
                        hovertemplate='<b>%{x}</b><br><b>Quantidade:</b> %{y:,.0f}<br><extra></extra>',
                        showlegend=False,
                        width=0.65
                    ))
                    
                    fig.update_layout(
                        title=dict(
                            text=f'<b>{titulo}</b>',
                            font=dict(family='Poppins, sans-serif', size=16, color='#1a1a1a'),
                            x=0.5, xanchor='center', y=0.97, yanchor='top'
                        ),
                        template='plotly_white',
                        height=360,
                        font=dict(family='Inter, sans-serif', size=11),
                        margin=dict(l=50, r=25, t=50, b=70),
                        plot_bgcolor='rgba(248, 249, 250, 0.6)',
                        xaxis=dict(
                            tickfont=dict(size=11, family='Inter, sans-serif', color='#333'),
                            showgrid=False, tickangle=-35
                        ),
                        yaxis=dict(
                            tickfont=dict(size=11, family='Inter, sans-serif'),
                            showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.35)',
                            range=[0, max(valores) * 1.25], showticklabels=False
                        ),
                        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, sans-serif"),
                        bargap=0.25
                    )
                
                placeholder.plotly_chart(
                    fig, 
                    key=f"grafico_inferior_{metrica}_{mes_atual}",
                    config={'displayModeBar': False, 'scrollZoom': False},
                    width='stretch'
                )
            else:
                placeholder.markdown(f"""
                    <div style="background: white; padding: 2rem; border-radius: 12px; 
                                box-shadow: 0 4px 15px rgba(0, 58, 112, 0.1);
                                border-top: 4px solid {cor_principal};
                                text-align: center; color: #999;">
                        <p style="margin: 0; font-size: 15px; font-weight: 600;">Carregando dados...</p>
                    </div>
                """, unsafe_allow_html=True)
        
        time.sleep(0.7)  # Pausa entre cada mês da animação

# Auto-recarregamento
time.sleep(60)
st.rerun()