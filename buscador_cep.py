import streamlit as st
import pandas as pd
from geopy.distance import geodesic
from geopy.geocoders import ArcGIS  # Alterado para ArcGIS
import folium
from streamlit_folium import st_folium
import brazilcep
import requests
import base64

# --- Configuração da página ---
st.set_page_config(
    page_title="Buscador de Credenciados",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Inicializar o Estado da Sessão ---
if "df_resultados" not in st.session_state:
    st.session_state.df_resultados = None
if "coords_ref" not in st.session_state:
    st.session_state.coords_ref = None
if "endereco_texto" not in st.session_state:
    st.session_state.endereco_texto = ""

# --- Função para logo ---
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None

logo_base64 = get_base64_of_bin_file("convenio040.png")
if logo_base64:
    st.markdown(
        f"""
        <style>
            .logo-container {{ position: absolute; top: 15px; right: 15px; z-index: 100; }}
            .logo-container img {{ width: 200px; }}
        </style>
        <div class="logo-container"><img src="data:image/png;base64,{logo_base64}"></div>
        """,
        unsafe_allow_html=True
    )

# --- Carregar base de dados ---
@st.cache_data
def carregar_base():
    # Certifique-se que o arquivo está na mesma pasta do script no GitHub/Streamlit
    df = pd.read_excel("enderecos_com_cep_latlong.xlsx")
    df = df.dropna(subset=["LATITUDE", "LONGITUDE"])
    return df

try:
    df_clinicas = carregar_base()
except Exception as e:
    st.error(f"Erro ao carregar base de dados: {e}")
    st.stop()

# --- Filtros ---
lista_especialidades = []
for esp in df_clinicas["ESPECIALIDADE"].dropna():
    for item in str(esp).split(","):
        item_limpo = item.strip().upper()
        if item_limpo: lista_especialidades.append(item_limpo)
lista_especialidades = sorted(set(lista_especialidades))
lista_redes = sorted(df_clinicas["Rede"].dropna().unique().tolist())

# --- Geocodificação (Ajustada para Produção) ---
@st.cache_data(show_spinner="Buscando coordenadas...")
def buscar_lat_long_por_endereco(endereco):
    try:
        # ArcGIS é mais amigável com IPs de servidores (Streamlit Cloud, Heroku, etc)
        geolocator = ArcGIS(user_agent="buscador_credenciados_v1")
        location = geolocator.geocode(endereco, timeout=15)
        if location:
            return (location.latitude, location.longitude)
        return (None, None)
    except Exception as e:
        print(f"Erro geopy: {e}")
        return None, None

def calcular_distancia(lat1, lon1, lat2, lon2):
    try:
        return geodesic((lat1, lon1), (lat2, lon2)).km
    except:
        return None

# --- Interface ---
st.title("🔎 Buscador de Credenciados")

c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    cep_input = st.text_input("Seu CEP:", placeholder="00000-000")
with c2:
    espec_sel = st.multiselect("Especialidade:", options=lista_especialidades)
with c3:
    rede_sel = st.multiselect("Plano/Rede:", options=lista_redes)

if st.button("🔍 Localizar Clínicas", use_container_width=True):
    if not cep_input:
        st.error("Por favor, digite um CEP.")
    else:
        try:
            # Limpa o CEP e busca o endereço
            cep_limpo = cep_input.replace("-", "").replace(".", "").strip()
            end_detalhes = brazilcep.get_address_from_cep(cep_limpo)
            
            if end_detalhes:
                rua = end_detalhes.get('street', '')
                cidade = end_detalhes.get('city', '')
                uf = end_detalhes.get('uf', '')
                # Monta string de busca para o geolocator
                endereco_completo = f"{rua}, {cidade} - {uf}, Brazil"
                
                lat_ref, lon_ref = buscar_lat_long_por_endereco(endereco_completo)
                
                if lat_ref and lon_ref:
                    df_f = df_clinicas.copy()
                    
                    # Filtro Especialidade
                    if espec_sel:
                        df_f = df_f[df_f["ESPECIALIDADE"].apply(lambda x: any(e in str(x).upper() for e in espec_sel))]
                    
                    # Filtro Rede
                    if rede_sel:
                        df_f = df_f[df_f["Rede"].isin(rede_sel)]
                    
                    if not df_f.empty:
                        # Cálculo de distância
                        df_f["DISTANCIA_KM"] = df_f.apply(
                            lambda r: calcular_distancia(lat_ref, lon_ref, r["LATITUDE"], r["LONGITUDE"]), axis=1
                        )
                        
                        df_res = df_f.dropna(subset=["DISTANCIA_KM"]).sort_values("DISTANCIA_KM").head(25).copy()
                        
                        # Link do Google Maps
                        df_res['Google Maps'] = df_res.apply(
                            lambda r: f"https://www.google.com/maps/dir/?api=1&origin={lat_ref},{lon_ref}&destination={r['LATITUDE']},{r['LONGITUDE']}&travelmode=driving", axis=1
                        )

                        st.session_state.df_resultados = df_res
                        st.session_state.coords_ref = (lat_ref, lon_ref)
                        st.session_state.endereco_texto = f"{rua}, {cidade}"
                    else:
                        st.session_state.df_resultados = "vazio"
                else:
                    st.error("Não conseguimos obter as coordenadas do seu endereço. Tente um CEP próximo.")
            else:
                st.error("CEP não encontrado na base do BrazilCEP.")
        except Exception as e:
            st.error(f"Erro ao processar CEP: {e}")

# --- Exibição ---
if st.session_state.df_resultados is not None:
    if isinstance(st.session_state.df_resultados, str):
        st.warning("Nenhuma clínica encontrada para os filtros selecionados.")
    else:
        df_exibir = st.session_state.df_resultados
        lat_ref, lon_ref = st.session_state.coords_ref
        
        st.success(f"📍 Resultados para: {st.session_state.endereco_texto}")

        st.subheader("🏥 Unidades Próximas")
        st.dataframe(
            df_exibir[["NOME DO PRESTADOR", "ESPECIALIDADE", "Rede", "DISTANCIA_KM", "Google Maps"]],
            column_config={
                "DISTANCIA_KM": st.column_config.NumberColumn("Km", format="%.1f km"),
                "Google Maps": st.column_config.LinkColumn("Mapa", display_text="Ver Rota")
            },
            use_container_width=True, hide_index=True
        )

        st.subheader("🗺️ Visualização no Mapa")
        mapa = folium.Map(location=[lat_ref, lon_ref], zoom_start=14)
        folium.Marker(
            [lat_ref, lon_ref], 
            tooltip="Você está aqui", 
            icon=folium.Icon(color="blue", icon="home")
        ).add_to(mapa)

        for _, row in df_exibir.iterrows():
            folium.Marker(
                [row["LATITUDE"], row["LONGITUDE"]],
                popup=f"<b>{row['NOME DO PRESTADOR']}</b><br>{row['ESPECIALIDADE']}",
                tooltip=row['NOME DO PRESTADOR'],
                icon=folium.Icon(color="red", icon="plus", prefix="fa")
            ).add_to(mapa)

        st_folium(mapa, use_container_width=True, height=500, key="mapa_final")

st.markdown("---")
st.caption("Buscador FRG © 2026")