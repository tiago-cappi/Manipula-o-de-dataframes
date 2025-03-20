import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from typing import List, Dict

def carregar_arquivo_excel(arquivo):
    """
    Carrega um arquivo Excel e retorna um dataframe
    """
    try:
        return pd.read_excel(arquivo)
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")
        return None

def processar_arquivos_pendentes(arquivos: List) -> pd.DataFrame:
    """
    Processa múltiplos arquivos Excel e retorna um dataframe consolidado
    contendo apenas os registros com status 'PENDENTE'
    """
    if not arquivos:
        return None
    
    # Lista para armazenar os dataframes de cada arquivo
    dfs = []
    
    # Processar cada arquivo
    for idx, arquivo in enumerate(arquivos):
        df = carregar_arquivo_excel(arquivo)
        
        if df is not None:
            # Filtrar apenas os registros pendentes
            if 'Status Processo' in df.columns:
                df_pendentes = df[df['Status Processo'] == 'PENDENTE'].copy()
                
                # Adicionar informação sobre qual semana este arquivo representa
                semana_num = idx + 1
                df_pendentes['Semana'] = f"Semana -{semana_num}" if idx > 0 else "Semana Atual"
                
                # Adicionar à lista de dataframes
                dfs.append(df_pendentes)
            else:
                st.warning(f"O arquivo {arquivo.name} não contém a coluna 'Status Processo' e foi ignorado.")
    
    # Consolidar todos os dataframes
    if dfs:
        df_consolidado = pd.concat(dfs, ignore_index=True)
        return df_consolidado
    else:
        return None

def exibir_analise_pendentes():
    """
    Função principal para renderizar a aba de análise de pendentes
    """
    st.header("Análise de Propostas Pendentes")
    
    # Área para upload de arquivos múltiplos
    st.subheader("Upload de Arquivos de Propostas")
    arquivos_propostas = st.file_uploader(
        "Selecione os arquivos das propostas (comece pelo mais recente)",
        type=["xlsx"],
        accept_multiple_files=True
    )
    
    if not arquivos_propostas:
        st.info("Por favor, faça o upload de pelo menos um arquivo Excel com as propostas.")
        return
    
    # Processar os arquivos
    df_pendentes = processar_arquivos_pendentes(arquivos_propostas)
    
    if df_pendentes is not None and not df_pendentes.empty:
        # Mostrar estatísticas básicas
        st.subheader("Resumo das Propostas Pendentes")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Propostas Pendentes", len(df_pendentes))
        
        with col2:
            total_semanas = df_pendentes['Semana'].nunique()
            st.metric("Total de Semanas", total_semanas)
        
        with col3:
            if 'Valor Proposta' in df_pendentes.columns:
                valor_total = df_pendentes['Valor Proposta'].sum()
                st.metric("Valor Total", f"R$ {valor_total:,.2f}")
        
        # Filtros para os dados
        st.sidebar.header("Filtros de Propostas Pendentes")
        
        # Filtrar por semana
        semanas = ['Todas'] + sorted(df_pendentes['Semana'].unique().tolist())
        semana_selecionada = st.sidebar.selectbox("Semana", semanas, key="semana_pendentes")
        
        # Aplicar filtros
        df_filtrado = df_pendentes.copy()
        if semana_selecionada != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['Semana'] == semana_selecionada]
        
        # Mostrar tabela de dados
        st.subheader("Tabela de Propostas Pendentes")
        st.dataframe(df_filtrado, use_container_width=True)
        
        # Opção para exportar
        if st.button("Exportar Propostas Pendentes para Excel"):
            # Gerar nome de arquivo com timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"propostas_pendentes_{timestamp}.xlsx"
            
            # Salvar para Excel
            df_filtrado.to_excel(filename, index=False)
            
            # Botão de download
            with open(filename, "rb") as file:
                st.download_button(
                    label="Baixar arquivo Excel",
                    data=file,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.warning("Não foram encontradas propostas pendentes nos arquivos fornecidos.")

if __name__ == "__main__":
    # Para testes executando o arquivo diretamente
    st.set_page_config(page_title="Análise de Pendentes", layout="wide")
    exibir_analise_pendentes()