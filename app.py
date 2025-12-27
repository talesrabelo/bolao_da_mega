import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# Configuração da página (Mantenha a sua configuração atual)
st.set_page_config(
    page_title="Bolão da Mega",
    page_icon="🍀",
    layout="wide"
)

st.header("🍀 Painel de Acompanhamento do Bolão")

# --- FUNÇÃO DE CARREGAMENTO DE DADOS (VIA REQUESTS + BYTESIO) ---
@st.cache_data(ttl=60) # Atualiza a cada 60 segundos
def load_data():
    # Defina as URLs RAW corretas
    url_participantes = "https://raw.githubusercontent.com/talesrabelo/bolao_da_mega/main/participantes.xlsx"
    url_jogos = "https://raw.githubusercontent.com/talesrabelo/bolao_da_mega/main/jogos.xlsx"

    # Função auxiliar para baixar e ler
    def baixar_excel(url, header_option=0):
        try:
            response = requests.get(url)
            response.raise_for_status() # Verifica se deu erro 404 ou 500
            return pd.read_excel(BytesIO(response.content), header=header_option, engine='openpyxl')
        except requests.exceptions.HTTPError as err:
            st.error(f"Erro de Conexão (HTTP) ao acessar {url}: {err}")
            return None
        except Exception as e:
            st.error(f"Erro ao processar o arquivo Excel da URL {url}: {e}")
            return None

    # 1. Carregar Participantes
    df_part = baixar_excel(url_participantes, header_option=None) # header=None porque a linha 0 é o total
    
    if df_part is not None:
        try:
            # Tratamento Participantes
            valor_arrecadado = df_part.iloc[0, 1]
            df_part_clean = df_part.iloc[1:].copy()
            df_part_clean.columns = ["Participante", "Cotas"]
            df_part_clean.reset_index(drop=True, inplace=True)
            df_part_clean["Cotas"] = pd.to_numeric(df_part_clean["Cotas"], errors='coerce').fillna(0)
        except Exception as e:
            st.error(f"Erro na estrutura da planilha de Participantes: {e}")
            return None, 0, None
    else:
        return None, 0, None

    # 2. Carregar Jogos
    df_jogos = baixar_excel(url_jogos, header_option=0) # header=0 padrão
    
    if df_jogos is not None:
        try:
            # Tratamento Jogos
            cols_dezenas = df_jogos.columns[1:] 
            df_jogos[cols_dezenas] = df_jogos[cols_dezenas].apply(pd.to_numeric, errors='coerce')
        except Exception as e:
            st.error(f"Erro na estrutura da planilha de Jogos: {e}")
            return None, 0, None
    else:
        return None, 0, None
        
    return df_part_clean, valor_arrecadado, df_jogos

# Carrega os dados
df_participantes, total_acumulado, df_jogos = load_data()

if df_participantes is not None and df_jogos is not None:

    # Criar abas
    tab1, tab2, tab3 = st.tabs(["👥 Participantes & Rateio", "📝 Lista de Jogos", "🔍 Conferir Resultado"])

    # --- ABA 1: PARTICIPANTES E CÁLCULO PECUNIÁRIO ---
    with tab1:
        st.header("Quadro de Cotistas e Estimativas")
        
        # 1. Métricas Institucionais
        col_metric1, col_metric2 = st.columns(2)
        col_metric1.metric("Fundo de Reserva (Arrecadado)", f"R$ {total_acumulado:,.2f}")
        
        total_cotas_geral = df_participantes["Cotas"].sum()
        col_metric2.metric("Total de Cotas Emitidas", int(total_cotas_geral))
        
        st.divider()

        # 2. Mecanismo de Simulação de Ganhos
        st.subheader("💰 Simulação de Rateio")
        st.info("Insira o valor do prêmio estimado para calcular o ganho por cota.")
        
        col_input, col_result = st.columns(2)
        
        with col_input:
            premio_estimado = st.number_input(
                "Valor do Prêmio (R$)", 
                min_value=0.0, 
                value=0.0, 
                step=100000.0,
                format="%.2f"
            )
        
        with col_result:
            if total_cotas_geral > 0:
                valor_por_cota = premio_estimado / total_cotas_geral
                st.metric("Valor Estimado por Cota", f"R$ {valor_por_cota:,.2f}")
            else:
                st.warning("Não há cotas registradas para cálculo.")

        st.divider()

        # 3. Mecanismo de Inquirição Individual (Pesquisa Ordenada)
        st.subheader("🕵️ Consulta Individual")
        
        # --- ALTERAÇÃO AQUI: Ordenação da Lista ---
        # O comando 'sorted' organiza a lista alfabeticamente antes de exibir
        lista_nomes = sorted(df_participantes["Participante"].unique())
        
        col_busca, col_resultado_busca = st.columns(2)
        
        with col_busca:
            nome_selecionado = st.selectbox("Selecione o Participante:", options=lista_nomes)
            
        with col_resultado_busca:
            if nome_selecionado:
                dados_participante = df_participantes[df_participantes["Participante"] == nome_selecionado]
                cotas_do_participante = dados_participante["Cotas"].sum()
                
                st.metric(
                    label=f"Cotas de {nome_selecionado}", 
                    value=f"{int(cotas_do_participante)} cota(s)"
                )

        st.divider()
        st.subheader("Lista Completa")
        # Também ordenamos o dataframe principal para exibição na tabela
        st.dataframe(df_participantes.sort_values(by="Participante"), use_container_width=True, hide_index=True)

    # --- ABA 2: JOGOS ---
    with tab2:
        st.header("Jogos Realizados")
        st.info("Abaixo estão listados todos os jogos registrados para este bolão.")
        st.info("Os comprovantes dos jogos podem ser acessados no link: https://drive.google.com/drive/folders/1ItBEVLpSoxnKTpJ0xW-aW6Zecm-DzIQW?usp=drive_link")
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
