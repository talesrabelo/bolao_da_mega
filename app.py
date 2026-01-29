import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# Configuração da página
st.set_page_config(
    page_title="Bolão da Mega",
    page_icon="🍀",
    layout="wide"
)

st.header("🍀 Painel de Acompanhamento do Bolão")

# --- FUNÇÃO DE CARREGAMENTO DE DADOS BLINDADA ---
@st.cache_data(ttl=60)
def load_data():
    # URLs do GitHub
    url_participantes = "https://raw.githubusercontent.com/talesrabelo/bolao_da_mega/main/participantes.xlsx"
    url_jogos = "https://raw.githubusercontent.com/talesrabelo/bolao_da_mega/main/jogos.xlsx"

    def baixar_excel(url, header_option=None):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return pd.read_excel(BytesIO(response.content), header=header_option, engine='openpyxl')
        except Exception as e:
            st.error(f"Erro ao baixar {url}: {e}")
            return None

    # 1. PROCESSAMENTO DE PARTICIPANTES
    # Lemos sem cabeçalho (header=None) para pegar tudo cru
    df_part = baixar_excel(url_participantes, header_option=None)
    
    if df_part is not None:
        try:
            # LIMPEZA CRÍTICA: Remove linhas totalmente vazias (como a linha 1 do seu Excel atual)
            df_part = df_part.dropna(how='all').reset_index(drop=True)
            
            # Agora a linha 0 deve ser o Total e a linha 1 em diante os participantes
            # Verificação de segurança: Se a primeira célula for "Total", pegamos o valor ao lado
            valor_bruto = df_part.iloc[0, 1]
            
            # Limpeza do valor monetário (caso venha como texto "R$ ...")
            if isinstance(valor_bruto, str):
                valor_limpo = valor_bruto.replace('R$', '').replace('.', '').replace(',', '.').strip()
                valor_arrecadado = float(valor_limpo)
            else:
                valor_arrecadado = float(valor_bruto)

            # Os participantes são da linha 1 para baixo
            df_part_clean = df_part.iloc[1:].copy()
            df_part_clean.columns = ["Participante", "Cotas"]
            
            # Tratamento de tipos (Garante que Cotas sejam números e Nomes sejam texto)
            df_part_clean["Participante"] = df_part_clean["Participante"].astype(str)
            df_part_clean["Cotas"] = pd.to_numeric(df_part_clean["Cotas"], errors='coerce').fillna(0)
            
        except Exception as e:
            st.error(f"Erro ao tratar participantes: {e}")
            return None, 0, None
    else:
        return None, 0, None

    # 2. PROCESSAMENTO DE JOGOS
    # header=0 pois seu arquivo agora tem cabeçalho "ID Jogo, Dezena 1..."
    df_jogos = baixar_excel(url_jogos, header_option=0)
    
    if df_jogos is not None:
        try:
            # Pega da segunda coluna em diante como dezenas (pula ID Jogo)
            cols_dezenas = df_jogos.columns[1:] 
            df_jogos[cols_dezenas] = df_jogos[cols_dezenas].apply(pd.to_numeric, errors='coerce')
        except Exception as e:
            st.error(f"Erro ao tratar jogos: {e}")
            return None, 0, None
    else:
        return None, 0, None
        
    return df_part_clean, valor_arrecadado, df_jogos

# Carrega os dados
df_participantes, total_acumulado, df_jogos = load_data()

if df_participantes is not None and df_jogos is not None:

    # Criar abas
    tab1, tab2, tab3 = st.tabs(["👥 Participantes & Rateio", "📝 Lista de Jogos", "🔍 Conferir Resultado"])

    # --- ABA 1: PARTICIPANTES ---
    with tab1:
        st.header("Quadro de Cotistas e Estimativas")
        col_metric1, col_metric2 = st.columns(2)
        col_metric1.metric("Fundo de Reserva (Arrecadado)", f"R$ {total_acumulado:,.2f}")
        
        total_cotas_geral = df_participantes["Cotas"].sum()
        col_metric2.metric("Total de Cotas Emitidas", int(total_cotas_geral))
        
        st.divider()

        # Simulação de Rateio
        st.subheader("💰 Simulação de Rateio")
        col_input, col_result = st.columns(2)
        with col_input:
            premio_estimado = st.number_input("Valor do Prêmio (R$)", min_value=0.0, value=0.0, step=100000.0, format="%.2f")
        with col_result:
            if total_cotas_geral > 0:
                valor_por_cota = premio_estimado / total_cotas_geral
                st.metric("Valor Estimado por Cota", f"R$ {valor_por_cota:,.2f}")

        st.divider()

        # Consulta Individual (CORREÇÃO DO ERRO DE ORDENAÇÃO)
        st.subheader("🕵️ Consulta Individual")
        
        # Removemos vazios (dropna) e garantimos que é texto (astype str) antes de ordenar
        lista_nomes = sorted(df_participantes["Participante"].dropna().astype(str).unique())
        
        col_busca, col_resultado_busca = st.columns(2)
        with col_busca:
            nome_selecionado = st.selectbox("Selecione o Participante:", options=lista_nomes)
            
        with col_resultado_busca:
            if nome_selecionado:
                dados_participante = df_participantes[df_participantes["Participante"] == nome_selecionado]
                cotas_do_participante = dados_participante["Cotas"].sum()
                st.metric(label=f"Cotas de {nome_selecionado}", value=f"{int(cotas_do_participante)} cota(s)")

        st.divider()
        st.dataframe(df_participantes.sort_values(by="Participante"), use_container_width=True, hide_index=True)

    # --- ABA 2: JOGOS ---
    with tab2:
        st.header("Jogos Realizados")
        st.info("Abaixo estão listados todos os jogos registrados.")
        st.info("Link dos comprovantes: https://drive.google.com/drive/folders/1ItBEVLpSoxnKTpJ0xW-aW6Zecm-DzIQW?usp=drive_link")
        st.dataframe(df_jogos.style.format(precision=0, na_rep=""), use_container_width=True, hide_index=True)

    # --- ABA 3: CONFERÊNCIA ---
    with tab3:
        st.header("Conferência de Resultados")
        numeros_sorteados = st.multiselect("Escolha as 6 dezenas:", options=list(range(1, 61)), max_selections=6)

        if len(numeros_sorteados) > 0:
            st.divider()
            cols_dezenas = df_jogos.columns[1:]
            
            def contar_acertos(row):
                jogo = set(row[cols_dezenas].dropna().astype(int))
                sorteio = set(numeros_sorteados)
                return len(jogo.intersection(sorteio))

            df_jogos['Acertos'] = df_jogos.apply(contar_acertos, axis=1)
            
            # Resumo
            contagem = df_jogos['Acertos'].value_counts()
            resumo_data = {acerto: contagem.get(acerto, 0) for acerto in range(6, -1, -1)}
            df_resumo = pd.DataFrame(list(resumo_data.items()), columns=["Dezenas Acertadas", "Bilhetes"])
            
            def highlight_premios(row):
                if row["Dezenas Acertadas"] == 6: return ['background-color: gold; color: black'] * 2
                elif row["Dezenas Acertadas"] == 5: return ['background-color: silver; color: black'] * 2
                elif row["Dezenas Acertadas"] == 4: return ['background-color: #cd7f32; color: white'] * 2
                return [''] * 2

            st.dataframe(df_resumo.style.apply(highlight_premios, axis=1), use_container_width=True, hide_index=True)
            
            # Tabela Detalhada
            st.subheader("Detalhe dos Jogos")
            def highlight_matches(val):
                if isinstance(val, (int, float)) and int(val) in numeros_sorteados:
                    return 'background-color: #90EE90; color: black; font-weight: bold'
                return ''

            st.dataframe(df_jogos.style.applymap(highlight_matches, subset=cols_dezenas).format(precision=0), use_container_width=True, hide_index=True)
else:
    st.warning("Aguardando carregamento dos dados...")
