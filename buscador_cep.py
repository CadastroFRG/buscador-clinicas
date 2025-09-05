import streamlit as st
import pandas as pd
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium

# --- Configuração da página ---
st.set_page_config(
    page_title="Buscador de Clínicas",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS para mapa em tela cheia ---
st.markdown(
    """
    <style>
        .main > div {
            padding: 0rem;
        }
        iframe {
            height: 100vh !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Carregar CSV de CEPs com lat/lon (Kaggle) ---
df_ceps = pd.read_csv(
    r"C:\Users\brunomelo\sla_cadastro_frg\census_code_cep_coordinates.csv", 
    dtype=str
)
df_ceps["POSTCODE"] = df_ceps["POSTCODE"].str.replace("-", "").str.strip()
df_ceps["LAT"] = pd.to_numeric(df_ceps["LAT"], errors="coerce")
df_ceps["LON"] = pd.to_numeric(df_ceps["LON"], errors="coerce")

# --- Carregar base de clínicas ---
df_clinicas = pd.read_excel("enderecos_com_cep_latlong.xlsx")

# --- Função para buscar lat/lon por CEP ---
def buscar_lat_long_por_cep(cep):
    cep_clean = cep.replace("-", "").strip()
    linha = df_ceps[df_ceps["POSTCODE"] == cep_clean]
    if linha.empty:
        return None, None
    return linha["LAT"].values[0], linha["LON"].values[0]

# --- Função para calcular distância em linha reta ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    try:
        if None in [lat1, lon1, lat2, lon2]:
            return None
        return geodesic((lat1, lon1), (lat2, lon2)).km
    except:
        return None

# --- Streamlit ---
st.title("🔎 Buscador de Clínicas por CEP")

cep_input = st.text_input("Digite seu CEP:", "")

if cep_input:
    lat_ref, lon_ref = buscar_lat_long_por_cep(cep_input)

    if lat_ref and lon_ref:
        st.success(f"Localização encontrada: {lat_ref:.6f}, {lon_ref:.6f}")

        # Calcular distância em linha reta para todas as clínicas
        df_clinicas["DISTANCIA_KM"] = df_clinicas.apply(
            lambda row: calcular_distancia(lat_ref, lon_ref, row["LATITUDE"], row["LONGITUDE"]),
            axis=1
        )

        # Selecionar 10 clínicas mais próximas
        resultados = df_clinicas.dropna(subset=["DISTANCIA_KM"]).sort_values("DISTANCIA_KM").head(10)

        st.subheader("🏥 Clínicas mais próximas")
        st.dataframe(
            resultados[["ENDERECO", "BAIRRO", "CIDADE", "CEP", "DISTANCIA_KM"]],
            use_container_width=True
        )

        st.subheader("🗺️ Mapa das clínicas próximas")
        mapa = folium.Map(location=[lat_ref, lon_ref], zoom_start=12)
        folium.Marker([lat_ref, lon_ref], tooltip="Você está aqui", icon=folium.Icon(color="blue")).add_to(mapa)

        # Adicionar clínicas
        for _, row in resultados.iterrows():
            folium.Marker(
                [row["LATITUDE"], row["LONGITUDE"]],
                tooltip=f"{row['ENDERECO']} ({row['DISTANCIA_KM']:.1f} km)",
                icon=folium.Icon(color="red")
            ).add_to(mapa)

        # Exibir mapa
        st_folium(mapa, use_container_width=True, height=800)

    else:
        st.error("CEP não encontrado na base de dados.")
