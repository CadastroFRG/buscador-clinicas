import pandas as pd
import requests
import time
from geopy.geocoders import Nominatim

# Caminho da sua planilha
arquivo_excel = r"C:\Users\brunomelo\Downloads\REDE PLAMES IDEAL ATUALIZADA_28-08-25.xlsx"

# Lê a planilha
df = pd.read_excel(arquivo_excel)

# Função para buscar o CEP no ViaCEP
def buscar_cep(logradouro, bairro, cidade, uf="RJ"):
    try:
        url = f"https://viacep.com.br/ws/{uf}/{cidade}/{logradouro}/json/"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            dados = resp.json()
            if isinstance(dados, list) and len(dados) > 0:
                # tenta filtrar pelo bairro
                for d in dados:
                    if d.get("bairro", "").lower() == bairro.lower():
                        return d["cep"]
                return dados[0]["cep"]  # fallback
    except Exception as e:
        print(f"Erro ao buscar CEP: {e}")
    return None

# Função para buscar latitude/longitude pelo endereço (usando Nominatim)
def buscar_lat_long(endereco_completo):
    try:
        geolocator = Nominatim(user_agent="meu_app")
        location = geolocator.geocode(endereco_completo, timeout=10)
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        print(f"Erro ao buscar lat/long: {e}")
    return None, None

# Cria as novas colunas
ceps = []
latitudes = []
longitudes = []

for i, row in df.iterrows():
    logradouro = str(row.get("ENDERECO", "")).strip()
    bairro = str(row.get("BAIRRO", "")).strip()
    cidade = str(row.get("CIDADE", "")).strip()
    uf = str(row.get("UF", "RJ")).strip()

    if not logradouro or not cidade:
        ceps.append(None)
        latitudes.append(None)
        longitudes.append(None)
        continue

    # Buscar CEP
    cep = buscar_cep(logradouro, bairro, cidade, uf)
    ceps.append(cep)

    # Montar endereço completo para geocodificação
    endereco_completo = f"{logradouro}, {bairro}, {cidade}, {uf}, Brasil"
    lat, lon = buscar_lat_long(endereco_completo)
    latitudes.append(lat)
    longitudes.append(lon)

    time.sleep(1)  # evitar bloqueio das APIs

df["CEP"] = ceps
df["LATITUDE"] = latitudes
df["LONGITUDE"] = longitudes

# Salva em um novo arquivo
df.to_excel("enderecos_com_cep_latlong.xlsx", index=False)
print("Arquivo gerado: enderecos_com_cep_latlong.xlsx")
