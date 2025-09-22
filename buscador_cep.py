import streamlit as st
import pandas as pd
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
import brazilcep
import requests
import urllib3
import base64
import googlemaps

# --- Ignorar SSL ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Forçar todas as requisições requests a ignorarem SSL
old_request_get = requests.get
def new_request_get(*args, **kwargs):
    kwargs['verify'] = False
    return old_request_get(*args, **kwargs)
requests.get = new_request_get

# --- Configuração da página ---
st.set_page_config(
    page_title="Buscador de Credenciados por Geolocalização.",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Função para converter imagem local em base64 ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# --- Incluir logo no canto superior esquerdo ---
try:
    logo_base64 = get_base64_of_bin_file("convenio040.png")
    st.markdown(
        f"""
        <style>
            .logo-container {{
                position: absolute;
                top: 15px;
                left: 15px; /* canto esquerdo */
                z-index: 100;
            }}
            .logo-container img {{
                width: 200px;
            }}
        </style>
        <div class="logo-container">
            <img src="data:image/png;base64,{logo_base64}">
        </div>
        """,
        unsafe_allow_html=True
    )
except Exception:
    st.warning("⚠️ Logo não encontrada (convenio040.png).")

# --- CSS para mapa em tela cheia ---
st.markdown(
    """
    <style>
        .main > div {
            padding: 0rem;
        }
        iframe {
            height: 100vh!important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Carregar base de clínicas ---
@st.cache_data
def carregar_base():
    return pd.read_excel("enderecos_com_cep_latlong.xlsx")

df_clinicas = carregar_base()

# --- Criar lista única de especialidades ---
lista_especialidades = []
for esp in df_clinicas["ESPECIALIDADE"].dropna():
    for item in str(esp).split(","):
        item_limpo = item.strip().upper()
        if item_limpo:
            lista_especialidades.append(item_limpo)
lista_especialidades = sorted(set(lista_especialidades))

# --- Criar lista única de redes ---
lista_redes = df_clinicas["Rede"].dropna().unique().tolist()
lista_redes = sorted(lista_redes)

# --- Configurar Google Maps ---
gmaps = googlemaps.Client(key=st.secrets["GOOGLE_API_KEY"])

# --- Função para buscar lat/lon a partir de um endereço ---
def buscar_lat_long_por_endereco(endereco):
    try:
        geocode_result = gmaps.geocode(endereco)
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            return None, None
    except Exception as e:
        st.error(f"Erro na geocodificação (Google): {e}")
        return None, None

# --- Função para calcular distância ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    try:
        if None in [lat1, lon1, lat2, lon2]:
            return None
        return geodesic((lat1, lon1), (lat2, lon2)).km
    except:
        return None

# --- Streamlit ---
st.title("🔎 Buscador de Credenciados por Geolocalização.")

if "buscou" not in st.session_state:
    st.session_state.buscou = False

cep_input = st.text_input("Digite seu CEP:", "")

# Filtro por especialidade
especialidades_selecionadas = st.multiselect(
    "Filtrar por Especialidade (se não escolher, mostra todas):",
    options=lista_especialidades,
    default=[]
)

# Filtro por Rede
redes_selecionadas = st.multiselect(
    "Filtrar por Plano (se não escolher, mostra todas):",
    options=lista_redes,
    default=[]
)

# Botão de busca
if st.button("🔍 Buscar"):
    st.session_state.buscou = True

# Só executa se já buscou e tem CEP válido
if st.session_state.buscou and cep_input:
    try:
        endereco_detalhes = brazilcep.get_address_from_cep(
            cep_input.replace("-", "").strip()
        )
        if endereco_detalhes:
            endereco_completo = f"{endereco_detalhes.get('street', '')}, {endereco_detalhes.get('city', '')} - {endereco_detalhes.get('uf', '')}"
            lat_ref, lon_ref = buscar_lat_long_por_endereco(endereco_completo)
        else:
            st.error("CEP não encontrado. Verifique o CEP digitado.")
            lat_ref, lon_ref = None, None

    except Exception as e:
        st.error(f"Erro ao buscar o CEP: {e}")
        lat_ref, lon_ref = None, None

    if lat_ref and lon_ref:
        st.success(f"Localização encontrada: {lat_ref:.6f}, {lon_ref:.6f}")

        df_filtrado = df_clinicas.copy()

        if especialidades_selecionadas:
            df_filtrado = df_filtrado[
                df_filtrado["ESPECIALIDADE"].apply(
                    lambda x: any(esp in str(x).upper() for esp in especialidades_selecionadas)
                )
            ].copy()

        if redes_selecionadas:
            df_filtrado = df_filtrado[
                df_filtrado["Rede"].isin(redes_selecionadas)
            ].copy()

        # Calcular distância
        df_filtrado["DISTANCIA_KM"] = df_filtrado.apply(
            lambda row: calcular_distancia(lat_ref, lon_ref, row.get("LATITUDE"), row.get("LONGITUDE")),
            axis=1
        )

        resultados = df_filtrado.dropna(subset=["DISTANCIA_KM"]).sort_values("DISTANCIA_KM").head(10)

        if not resultados.empty:
            st.subheader("🏥 Clínicas mais próximas")
            st.dataframe(resultados, use_container_width=True)

            st.subheader("🗺️ Mapa das clínicas próximas")
            mapa = folium.Map(location=[lat_ref, lon_ref], zoom_start=12)
            folium.Marker([lat_ref, lon_ref], tooltip="Você está aqui", icon=folium.Icon(color="blue")).add_to(mapa)

            for _, row in resultados.iterrows():
                folium.Marker(
                    [row["LATITUDE"], row["LONGITUDE"]],
                    tooltip=f"{row['NOME DO PRESTADOR']} - {row['ESPECIALIDADE']} ({row['DISTANCIA_KM']:.1f} km)",
                    icon=folium.Icon(color="red")
                ).add_to(mapa)

            st_folium(mapa, use_container_width=True, height=800)
        else:
            st.warning("Nenhuma clínica encontrada com os filtros selecionados.")
    else:
        st.error("Não foi possível encontrar a localização do CEP. Verifique e tente novamente.")
