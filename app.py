import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(
    page_title="Bolão da Mega",
    page_icon="🍀",
    layout="wide"
)

st.header("🍀 Painel de Acompanhamento do Bolão")

# --- FUNÇÃO DE CARREGAMENTO DE DADOS ---
@st.cache_data
def load_data():
    try:
        # Carregar Participantes
        df_part = pd.read_excel("participantes.xlsx", header=None)
        
        # Extrair valor total acumulado (arrecadado)
        valor_arrecadado = df_part.iloc[0, 1]
        
        # Ajustar dataframe de participantes (removendo a linha do total)
        df_part_clean = df_part.iloc[1:].copy()
        df_part_clean.columns = ["Participante", "Cotas"]
        df_part_clean.reset_index(drop=True, inplace=True)
        
        # --- INTERVENÇÃO CRÍTICA ---
        # Garantir que a coluna 'Cotas' seja numérica para permitir cálculos de rateio
        df_part_clean["Cotas"] = pd.to_numeric(df_part_clean["Cotas"], errors='coerce').fillna(0)
        
        # Carregar Jogos
        df_jogos = pd.read_excel("jogos.xlsx")
        # Garante que as colunas de dezenas sejam numéricas e trata vazios
        cols_dezenas = df_jogos.columns[1:] # Pula a primeira (ID)
        df_jogos[cols_dezenas] = df_jogos[cols_dezenas].apply(pd.to_numeric, errors='coerce')
        
        return df_part_clean, valor_arrecadado, df_jogos
        
    except FileNotFoundError as e:
        st.error(f"Erro: Arquivo não encontrado. ({e})")
        return None, 0, None
    except Exception as e:
        st.error(f"Erro ao ler planilhas: {e}")
        return None, 0, None

# Carrega os dados
df_participantes, total_acumulado, df_jogos = load_data()

if df_participantes is not None and df_jogos is not None:

    # Criar abas
    tab1, tab2, tab3 = st.tabs(["👥 Participantes & Rateio", "📝 Lista de Jogos", "🔍 Conferir Resultado"])

    # --- ABA 1: PARTICIPANTES E CÁLCULO PECUNIÁRIO ---
    with tab1:
        st.header("Quadro de Cotistas e Estimativas")
        
        # 1. Métricas Institucionais (Dados do Bolão)
        col_metric1, col_metric2 = st.columns(2)
        col_metric1.metric("Fundo de Reserva (Arrecadado)", f"R$ {total_acumulado:,.2f}")
        
        # Cálculo do total de cotas existentes (Soma da coluna Cotas)
        total_cotas_geral = df_participantes["Cotas"].sum()
        col_metric2.metric("Total de Cotas Emitidas", int(total_cotas_geral))
        
        st.divider()

        # 2. Mecanismo de Simulação de Ganhos (A pedido: Valor do Prêmio e Rateio)
        st.subheader("💰 Simulação de Rateio")
        st.info("Insira o valor do prêmio estimado para calcular o ganho por cota.")
        
        col_input, col_result = st.columns(2)
        
        with col_input:
            # Campo para o usuário preencher o prêmio
            premio_estimado = st.number_input(
                "Valor do Prêmio (R$)", 
                min_value=0.0, 
                value=0.0, 
                step=100000.0,
                format="%.2f"
            )
        
        with col_result:
            # Cálculo do valor por cota
            if total_cotas_geral > 0:
                valor_por_cota = premio_estimado / total_cotas_geral
                st.metric("Valor Estimado por Cota", f"R$ {valor_por_cota:,.2f}")
            else:
                st.warning("Não há cotas registradas para cálculo.")

        st.divider()

        # 3. Mecanismo de Inquirição Individual (Pesquisa de Participante)
        st.subheader("🕵️ Consulta Individual")
        
        # Cria uma lista única de participantes para o selectbox (aumenta a eficiência da busca)
        lista_nomes = df_participantes["Participante"].unique()
        
        col_busca, col_resultado_busca = st.columns(2)
        
        with col_busca:
            nome_selecionado = st.selectbox("Selecione o Participante:", options=lista_nomes)
            
        with col_resultado_busca:
            if nome_selecionado:
                # Filtra o dataframe para encontrar o participante
                dados_participante = df_participantes[df_participantes["Participante"] == nome_selecionado]
                # Soma as cotas (caso o nome apareça mais de uma vez, embora o ideal seja aparecer uma vez com N cotas)
                cotas_do_participante = dados_participante["Cotas"].sum()
                
                st.metric(
                    label=f"Cotas de {nome_selecionado}", 
                    value=f"{int(cotas_do_participante)} cota(s)"
                )

        st.divider()
        st.subheader("Lista Completa")
        st.dataframe(df_participantes, use_container_width=True, hide_index=True)

    # --- ABA 2: JOGOS ---
    with tab2:
        st.header("Jogos Realizados")
        st.info("Abaixo estão listados todos os jogos registrados para este bolão.")
        st.dataframe(df_jogos.style.format(precision=0, na_rep=""), use_container_width=True, hide_index=True)

    # --- ABA 3: CONFERÊNCIA ---
    with tab3:
        st.header("Conferência de Resultados")
        st.write("Selecione as dezenas sorteadas na Mega Sena:")
        
        numeros_sorteados = st.multiselect(
            "Escolha as 6 dezenas:",
            options=list(range(1, 61)),
            max_selections=6,
            placeholder="Selecione 6 números..."
        )

        if len(numeros_sorteados) > 0:
            st.divider()
            
            # Lógica de Conferência
            cols_dezenas = df_jogos.columns[1:]
            
            def contar_acertos(row):
                jogo = set(row[cols_dezenas].dropna().astype(int))
                sorteio = set(numeros_sorteados)
                return len(jogo.intersection(sorteio))

            df_jogos['Acertos'] = df_jogos.apply(contar_acertos, axis=1)
            
            # --- QUADRO RESUMO ---
            st.subheader("📊 Resumo de Premiação")
            contagem = df_jogos['Acertos'].value_counts()
            resumo_data = {acerto: contagem.get(acerto, 0) for acerto in range(6, -1, -1)}
            df_resumo = pd.DataFrame(list(resumo_data.items()), columns=["Dezenas Acertadas", "Quantidade de Bilhetes"])
            
            def highlight_premios(row):
                if row["Dezenas Acertadas"] == 6:
                    return ['background-color: gold; color: black'] * 2
                elif row["Dezenas Acertadas"] == 5:
                    return ['background-color: silver; color: black'] * 2
                elif row["Dezenas Acertadas"] == 4:
                    return ['background-color: #cd7f32; color: white'] * 2
                return [''] * 2

            st.dataframe(df_resumo.style.apply(highlight_premios, axis=1), use_container_width=True, hide_index=True)
            
            # --- TABELA DETALHADA COM HIGHLIGHT ---
            st.subheader("Detalhe dos Jogos")
            st.write("Os números sorteados estão destacados em verde.")

            def highlight_matches(val):
                color = ''
                try:
                    if int(val) in numeros_sorteados:
                        color = 'background-color: #90EE90; color: black; font-weight: bold'
                except:
                    pass
                return color

            st.dataframe(
                df_jogos.style
                .applymap(highlight_matches, subset=cols_dezenas)
                .format(precision=0, na_rep=""),
                use_container_width=True,
                hide_index=True
            )
            
        else:
            st.info("Aguardando inserção dos números sorteados para gerar a conferência.")

else:
    st.warning("Por favor, certifique-se de que os arquivos 'participantes.xlsx' e 'jogos.xlsx' estão no repositório.")
