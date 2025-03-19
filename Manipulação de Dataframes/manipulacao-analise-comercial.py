import streamlit as st
import pandas as pd
import datetime

# Set page title and layout
st.set_page_config(page_title="Dashboard de Dados Comerciais", layout="wide")

# Title
st.title("Dashboard de Análise Comercial")

# Cache the data loading function to improve performance
@st.cache_data
def carregar_dados(caminho_arquivo):
    """
    Lê um arquivo Excel e o carrega como um DataFrame do Pandas.
    """
    try:
        df = pd.read_excel(caminho_arquivo)
        return df
    except Exception as e:
        st.error(f"Erro ao ler o arquivo Excel: {e}")
        return None

# Function to process data
def processar_dados(df_analise, df_categorias):
    """Processa os dados e retorna o dataframe final para exibição."""
    # Classificação ABC clientes
    df_classificacao_abc = classificar_clientes_abc(df_analise)
    
    # Merge com os dataframes
    df_resultado = pd.merge(
        df_analise[["Código Produto", "Descrição Produto", "Dt Entrada", "Cliente", 
                   "Consultor Interno", "Prob.Fech.", "Motivo Não Venda"]],
        df_classificacao_abc, on='Cliente', how='inner')
    
    # Agrupar por produto e cliente
    df_pedidos = df_resultado.groupby(["Dt Entrada", "Código Produto", "Cliente"]).agg({
        "Nome Cliente": "first",
        "Descrição Produto": "first",
        "UF": "first",
        "Cidade": "first",
        "ABC": "first",
        "Ranking": "first",
        "Prob.Fech.": "first",
        "Motivo Não Venda": "first",
        "Valor Total Orçado": "first",
        "Consultor Interno": "first"
    }).reset_index()
    
    # Adicionar categorias de produtos
    df_resultado_final = juntar_categorias_produtos(df_pedidos, df_categorias)
    
    # Converter a coluna 'Dt Entrada' para o formato desejado
    df_resultado_final['Dt Entrada'] = pd.to_datetime(df_resultado_final['Dt Entrada']).dt.strftime('%d/%m/%Y')
    
    # Filtrar apenas negócio SSO
    df_filtrado = df_resultado_final[(df_resultado_final["Negócio"] == "SSO")]
    df_filtrado['Dt Entrada_temp'] = pd.to_datetime(df_filtrado['Dt Entrada'], format='%d/%m/%Y')
    df_filtrado = df_filtrado[
        (df_filtrado["Dt Entrada_temp"] >= pd.to_datetime("2022-01-01")) &
        (df_filtrado["Dt Entrada_temp"] <= pd.to_datetime("2025-02-28"))
    ]
    
    # Processar dados para exibição final
    resultado = []
    for (subgrupo, codigo_produto, cliente), grupo in df_filtrado.groupby(["Subgrupo", "Código Produto", "Cliente"]):
        linha = {
            "Subgrupo": subgrupo,
            "Código Produto": codigo_produto,
            "Cliente": cliente
        }
        
        # Ordenar os dados por data
        grupo_ordenado = grupo.sort_values("Dt Entrada_temp")
        
        # Incluir todas as colunas relevantes
        for col in df_resultado_final.columns:
            if col in ["Dt Entrada", "Prob.Fech.", "Motivo Não Venda"]:
                linha[col] = grupo_ordenado[col].tolist()
            elif col not in ["Dt Entrada_temp", "Tupla_Dados"]:
                valores_unicos = grupo_ordenado[col].unique()
                linha[col] = valores_unicos[0] if len(valores_unicos) == 1 else valores_unicos.tolist()
        
        # Calcular a última data e o último consultor para o grupo
        ultima_data_grupo = max(grupo_ordenado["Dt Entrada_temp"])
        linha["Última Data"] = ultima_data_grupo.strftime("%d/%m/%Y")
        linha["Último Consultor"] = grupo_ordenado.loc[grupo_ordenado["Dt Entrada_temp"] == ultima_data_grupo, "Consultor Interno"].iloc[0]
        
        resultado.append(linha)
    
    # Criar um novo dataframe com o resultado
    df_final = pd.DataFrame(resultado)
    
    return df_final

# Helper functions
def classificar_clientes_abc(df):
    """Classifica os clientes conforme análise ABC baseada no valor orçado."""
    try:
        # Agrupar por cliente e somar o valor orçado
        df_clientes = df.groupby(["Nome Cliente", "Cliente"])["Valor Orçado"].sum().reset_index()
        
        # Ordenar por valor orçado em ordem decrescente
        df_clientes = df_clientes.sort_values("Valor Orçado", ascending=False)
        
        # Calcular valor total e percentuais
        valor_total = df_clientes["Valor Orçado"].sum()
        df_clientes["Percentual"] = df_clientes["Valor Orçado"] / valor_total * 100
        df_clientes["Percentual Acumulado"] = df_clientes["Percentual"].cumsum()
        
        # Classificação ABC
        df_clientes["ABC"] = df_clientes["Percentual Acumulado"].apply(
            lambda x: "A" if x <= 80 else ("B" if x <= 95 else "C")
        )
        
        # Formatação
        df_clientes = df_clientes.rename(columns={"Valor Orçado": "Valor Total Orçado"})
        df_clientes['Ranking'] = df_clientes['Valor Total Orçado'].rank(ascending=False, method='min').astype(int)
        
        # Adicionar as colunas UF e Cidade
        df_clientes = pd.merge(df_clientes, df[['Cliente', 'UF', 'Cidade']].drop_duplicates(subset=['Cliente']), on='Cliente', how='left')
        
        return df_clientes[["Cliente", "Nome Cliente", "UF", "Cidade", "Valor Total Orçado", "ABC", "Percentual", "Percentual Acumulado", "Ranking"]]
    
    except Exception as e:
        st.error(f"Erro ao processar classificação ABC: {e}")
        return pd.DataFrame()

def juntar_categorias_produtos(df, df_categorias):
    """Realiza junção dos dados de produtos com suas categorias."""
    try:
        df_categorias_slim = df_categorias[["Código Produto", "Negócio", "Grupo", "Subgrupo"]]
        return pd.merge(df, df_categorias_slim, on="Código Produto", how="left")
    except Exception as e:
        st.error(f"Erro ao juntar categorias: {e}")
        return df

# Sidebar for file upload
st.sidebar.header("Upload de Arquivos")
arquivo_analise = st.sidebar.file_uploader("Arquivo de Análise Comercial", type=["xlsx"])
arquivo_categorias = st.sidebar.file_uploader("Arquivo de Classificação de Produtos", type=["xlsx"])

# Main app logic
if arquivo_analise is not None and arquivo_categorias is not None:
    # Load data
    df_analise = carregar_dados(arquivo_analise)
    df_categorias = carregar_dados(arquivo_categorias)
    
    if df_analise is not None and df_categorias is not None:
        # Process data
        with st.spinner("Processando dados..."):
            df_final = processar_dados(df_analise, df_categorias)
        
        # Store processed data in session state
        if 'df_final' not in st.session_state:
            st.session_state.df_final = df_final
            # Initialize FUP status dictionary
            st.session_state.status_fup = {f"{row['Código Produto']}_{row['Cliente']}": False for _, row in df_final.iterrows()}
        
        # Show some statistics
        st.subheader("Resumo dos Dados")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Registros", len(df_final))
        with col2:
            st.metric("Subgrupos Únicos", df_final['Subgrupo'].nunique())
        with col3:
            st.metric("Clientes Únicos", df_final['Cliente'].nunique())
        
        # Filters
        st.sidebar.header("Filtros")
        
        # Filter by subgroup
        subgrupos = ['Todos'] + sorted(df_final['Subgrupo'].unique().tolist())
        subgrupo_selecionado = st.sidebar.selectbox("Subgrupo", subgrupos)
        
        # Filter by client
        clientes = ['Todos'] + sorted(df_final['Nome Cliente'].unique().tolist())
        cliente_selecionado = st.sidebar.selectbox("Cliente", clientes)
        
        # Filter by ABC
        categorias_abc = ['Todos'] + sorted(df_final['ABC'].unique().tolist())
        abc_selecionado = st.sidebar.selectbox("Categoria ABC", categorias_abc)
        
        # Apply filters
        df_filtrado = df_final.copy()
        if subgrupo_selecionado != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['Subgrupo'] == subgrupo_selecionado]
        if cliente_selecionado != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['Nome Cliente'] == cliente_selecionado]
        if abc_selecionado != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['ABC'] == abc_selecionado]
        
        # Show total records after filtering
        st.sidebar.info(f"Registros filtrados: {len(df_filtrado)}")
        
        # Pagination
        st.subheader("Tabela de Análise Comercial")
        items_per_page = st.select_slider("Itens por página:", options=[10, 25, 50, 100], value=25)
        
        # Calculate number of pages
        total_pages = (len(df_filtrado) + items_per_page - 1) // items_per_page
        
        # Page navigation
        col1, col2 = st.columns([1, 3])
        with col1:
            page_number = st.number_input("Página", min_value=1, max_value=max(1, total_pages), value=1)
        with col2:
            st.write(f"Total de páginas: {total_pages}")
        
        # Calculate slice for current page
        start_idx = (page_number - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(df_filtrado))
        
        # Display data for current page
        df_page = df_filtrado.iloc[start_idx:end_idx].copy()
        
        # Display data with FUP buttons
        if not df_page.empty:
            for idx, row in df_page.iterrows():
                row_id = f"{row['Código Produto']}_{row['Cliente']}"
                
                # Create expander for each record
                with st.expander(f"{row['Descrição Produto']} - {row['Nome Cliente']} ({row['ABC']})", expanded=False):
                    cols = st.columns([3, 1])
                    
                    with cols[0]:
                        st.write(f"**Código Produto:** {row['Código Produto']}")
                        st.write(f"**Cliente:** {row['Nome Cliente']} ({row['Cliente']})")
                        st.write(f"**Localização:** {row['Cidade']} - {row['UF']}")
                        st.write(f"**Subgrupo:** {row['Subgrupo']}")
                        st.write(f"**Última atualização:** {row['Última Data']}")
                        st.write(f"**Consultor:** {row['Último Consultor']}")
                    
                    with cols[1]:
                        # FUP checkbox
                        fup_status = st.checkbox("Follow-up realizado", key=f"fup_{row_id}", 
                                                value=st.session_state.status_fup.get(row_id, False))
                        st.session_state.status_fup[row_id] = fup_status
                        
                        # Status indicator
                        if fup_status:
                            st.success("✓ Concluído")
                        else:
                            st.error("☓ Pendente")
        else:
            st.warning("Nenhum registro encontrado com os filtros aplicados.")
            
        # Export button
        st.sidebar.header("Exportar Dados")
        if st.sidebar.button("Exportar para Excel"):
            # Prepare data for export
            df_export = df_filtrado.copy()
            
            # Add FUP status column
            df_export['Status FUP'] = df_export.apply(
                lambda x: "Concluído" if st.session_state.status_fup.get(f"{x['Código Produto']}_{x['Cliente']}", False) else "Pendente", 
                axis=1
            )
            
            # Generate filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analise_comercial_{timestamp}.xlsx"
            
            # Convert to Excel
            df_export.to_excel(filename, index=False)
            
            # Provide download link
            with open(filename, "rb") as file:
                st.sidebar.download_button(
                    label="Baixar arquivo Excel",
                    data=file,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            st.sidebar.success(f"Dados exportados com sucesso!")
else:
    st.info("Por favor, faça o upload dos arquivos de dados para visualizar a análise comercial.")