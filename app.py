import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(
    page_title="Bolão da Mega",
    page_icon="🍀",  # Aqui mudamos a identidade da aba
    layout="wide"
)

st.header("🍀 Painel de Acompanhamento do Bolão")

# --- FUNÇÃO DE CARREGAMENTO DE DADOS ---
@st.cache_data
def load_data():
    try:
        # Carregar Participantes
        df_part = pd.read_excel("participantes.xlsx", header=None)
        
        # Extrair valor total (assumindo linha 0, coluna 1)
        valor_total = df_part.iloc[0, 1]
        
        # Ajustar dataframe de participantes (removendo a linha do total)
        df_part_clean = df_part.iloc[1:].copy()
        df_part_clean.columns = ["Participante", "Cotas"]
        df_part_clean.reset_index(drop=True, inplace=True)
        
        # Carregar Jogos
        df_jogos = pd.read_excel("jogos.xlsx")
        # Garante que as colunas de dezenas sejam numéricas e trata vazios
        cols_dezenas = df_jogos.columns[1:] # Pula a primeira (ID)
        df_jogos[cols_dezenas] = df_jogos[cols_dezenas].apply(pd.to_numeric, errors='coerce')
        
        return df_part_clean, valor_total, df_jogos
        
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
    tab1, tab2, tab3 = st.tabs(["👥 Participantes", "📝 Lista de Jogos", "🔍 Conferir Resultado"])

    # --- ABA 1: PARTICIPANTES ---
    with tab1:
        st.header("Quadro de Cotistas")
        
        # Metric Cards
        col_metric1, col_metric2 = st.columns(2)
        col_metric1.metric("Total Acumulado (R$)", f"R$ {total_acumulado:,.2f}")
        col_metric2.metric("Total de Participantes", len(df_participantes))
        
        st.divider()
        st.dataframe(df_participantes, use_container_width=True, hide_index=True)

    # --- ABA 2: JOGOS ---
    with tab2:
        st.header("Jogos Realizados")
        st.info("Abaixo estão listados todos os jogos registrados para este bolão.")
        
        # Formatação simples para exibir sem casas decimais (ex: 1.0 -> 1)
        st.dataframe(df_jogos.style.format(precision=0, na_rep=""), use_container_width=True, hide_index=True)

    # --- ABA 3: CONFERÊNCIA ---
    with tab3:
        st.header("Conferência de Resultados")
        
        st.write("Selecione as dezenas sorteadas na Mega Sena:")
        
        # Input das dezenas sorteadas
        numeros_sorteados = st.multiselect(
            "Escolha as 6 dezenas:",
            options=list(range(1, 61)),
            max_selections=6,
            placeholder="Selecione 6 números..."
        )

        if len(numeros_sorteados) > 0:
            st.divider()
            
            # Lógica de Conferência
            # Pegamos apenas as colunas de dezenas (ignorando a coluna ID do jogo)
            cols_dezenas = df_jogos.columns[1:]
            
            # Função para contar acertos em uma linha
            def contar_acertos(row):
                # Pega os valores da linha, remove NaNs e converte para set
                jogo = set(row[cols_dezenas].dropna().astype(int))
                sorteio = set(numeros_sorteados)
                return len(jogo.intersection(sorteio))

            # Cria coluna temporária de acertos
            df_jogos['Acertos'] = df_jogos.apply(contar_acertos, axis=1)
            
            # --- QUADRO RESUMO ---
            st.subheader("📊 Resumo de Premiação")
            
            # Conta quantos jogos tiveram X acertos (0 a 6)
            contagem = df_jogos['Acertos'].value_counts()
            
            # Garante que apareçam todas as categorias mesmo que zeradas
            resumo_data = {acerto: contagem.get(acerto, 0) for acerto in range(6, -1, -1)}
            df_resumo = pd.DataFrame(list(resumo_data.items()), columns=["Dezenas Acertadas", "Quantidade de Bilhetes"])
            
            # Destaque visual para prêmios
            def highlight_premios(row):
                if row["Dezenas Acertadas"] == 6:
                    return ['background-color: gold; color: black'] * 2
                elif row["Dezenas Acertadas"] == 5:
                    return ['background-color: silver; color: black'] * 2
                elif row["Dezenas Acertadas"] == 4:
                    return ['background-color: #cd7f32; color: white'] * 2 # Bronze
                return [''] * 2

            st.dataframe(df_resumo.style.apply(highlight_premios, axis=1), use_container_width=True, hide_index=True)
            
            # --- TABELA DETALHADA COM HIGHLIGHT ---
            st.subheader("Detalhe dos Jogos")
            st.write("Os números sorteados estão destacados em verde.")

            # Função de estilo para colorir células
            def highlight_matches(val):
                color = ''
                try:
                    # Verifica se o valor da célula está nos números sorteados
                    if int(val) in numeros_sorteados:
                        color = 'background-color: #90EE90; color: black; font-weight: bold' # Verde claro
                except:
                    pass
                return color

            # Aplicar estilo nas colunas de dezenas
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
    st.warning("Por favor, certifique-se de que os arquivos 'participantes.xlsx' e 'jogos.xlsx' estão na mesma pasta.")
