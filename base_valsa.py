import pandas as pd
from datetime import datetime

# ✅ OK - Obtém a data atual para usar no nome do arquivo final
data = datetime.today().date()

# ✅ OK - Define colunas que serão utilizadas no CSV e Excel
colunas_63 = [
    'MATRICULA', 'ID FRG', 'NOME', 'SEXO', 'NASCIMENTO', 'COBERTURA',
    'PLANO DE COBERTURA', 'PLANO SUPLEMENTAR', 'PLANO EXTRA 1',
    'CPF', 'CARTEIRINHA', 'VALIDADE'
]
colunas_filemaker = [
    'ID FRG','UF', 'CIDADE', 'BAIRRO','DDD1', 'FONE1','DDD2', 'FONE2',
    'EMAIL1', 'EMAIL2','LOGRADOURO', 'NUMERO', 'COMPLEMENTO', 'CEP'
]

# 🚨 Ponto de atenção 1: pode falhar se:
# - o arquivo tiver linhas corrompidas (ex: strings com quebras de linha sem aspas)
# - as colunas listadas não existirem exatamente como estão escritas (acentos, espaços)
# 1. Lê o CSV ignorando linhas malformadas
relatorio_63_completo = pd.read_csv(
    r"C:\Users\brunomelo\Downloads\Relatorio_63_03_07_2025.csv",
    sep=';',
    encoding='latin-1',
    on_bad_lines='skip',  # ignora as linhas com erro de parsing
    low_memory=False
)

# 2. Seleciona apenas as colunas desejadas e faz cópia (evita SettingWithCopyWarning)
relatorio_63 = relatorio_63_completo[colunas_63].copy()

# ✅ OK - Leitura do Excel com colunas específicas
basevalsa_filemaker = pd.read_excel(
    r"C:\Users\brunomelo\Downloads\base valsa 23092025.xlsx",
    usecols=colunas_filemaker
)

# ✅ Padroniza tipos da chave para merge (como string, preserva zeros à esquerda)
relatorio_63["ID FRG"] = relatorio_63["ID FRG"].astype(str).str.strip()
basevalsa_filemaker["ID FRG"] = basevalsa_filemaker["ID FRG"].astype(str).str.strip()

# ✅ OK - Renomeia a coluna para um nome mais descritivo
relatorio_63.rename(
    columns={'PLANO EXTRA 1': 'Faz parte de algum programa de Saude (S/N)?'},
    inplace=True
)

# ✅ OK - Faz o merge entre os dois dataframes usando "ID FRG" como chave
base_valsa = relatorio_63.merge(basevalsa_filemaker, how='left', on='ID FRG')

# 🚨 Ponto de atenção 2: se alguma data estiver mal formatada, isso vai virar NaT
base_valsa['Nascimento'] = pd.to_datetime(
    base_valsa['NASCIMENTO'],  # corrigido: coluna correta
    format='%d/%m/%Y',
    errors='coerce'  # evita erro se a data estiver inválida
)

# ✅ OK - Calcula a idade em anos
base_valsa['IDADE'] = (datetime.now() - base_valsa['Nascimento']).apply(
    lambda x: x.days // 365 if pd.notnull(x) else 0
)

# ✅ OK - Preenche todos os NaNs com zero
base_valsa = base_valsa.fillna(0)

# ✅ OK - Salva o resultado no Excel
base_valsa.to_excel(
    fr"C:\Users\brunomelo\Downloads\Base_Valsa_{data}.xlsx",
    index=False
)
