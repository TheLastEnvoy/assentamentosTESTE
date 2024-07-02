import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import folium_static
import streamlit as st
import json
import requests
from requests.exceptions import RequestException, HTTPError

# Função para carregar GeoJSON com cache seletivo
@st.cache(suppress_st_warning=True)
def load_geojson(file_path):
    try:
        gdf = gpd.read_file(file_path)
        gdf['area_incra'] = pd.to_numeric(gdf['area_incra'], errors='coerce')
        gdf['area_polig'] = pd.to_numeric(gdf['area_polig'], errors='coerce')
        if gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        gdf = gdf[gdf.geometry.is_valid & gdf.geometry.notna()]
        return gdf
    except Exception as e:
        st.error(f"Erro ao carregar GeoJSON: {e}")
        return None

# Função para formatar a área
def format_area(area):
    return f"{area:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Função para gerar GeoJSON dos polígonos filtrados
def download_geojson(filtered_gdf):
    selected_features = []
    for idx, row in filtered_gdf.iterrows():
        geom = row['geometry']
        feature = {
            'type': 'Feature',
            'geometry': mapping(geom),
            'properties': {
                'nome_pa': row.get('nome_pa', 'N/A'),
                'area_incra': row.get('area_incra', 'N/A'),
                'area_polig': row.get('area_polig', 'N/A'),
                'lotes': row.get('lotes', 'N/A'),
                'quant_fami': row.get('quant_fami', 'N/A'),
                'fase': row.get('fase', 'N/A'),
                'data_criac': row.get('data_criac', 'N/A'),
                'forma_obte': row.get('forma_obte', 'N/A'),
                'data_obten': row.get('data_obten', 'N/A')
            }
        }
        selected_features.append(feature)

    feature_collection = {
        'type': 'FeatureCollection',
        'features': selected_features
    }

    return json.dumps(feature_collection)

# Função para obter GeoJSON a partir de uma URL
def get_geojson_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        st.error(f"Erro ao carregar dados da camada: {e}")
        return None

# Caminho para o arquivo GeoJSON
geojson_path = "pasbr_geo.geojson"

# Carregar GeoJSON
gdf = load_geojson(geojson_path)

# Verificar se o GeoJSON foi carregado com sucesso
if gdf is not None:
    st.title("Mapa interativo com os projetos de assentamento de reforma agrária no Brasil")
    st.markdown("(As informações exibidas neste site são públicas e estão disponíveis no [Portal de Dados Abertos](https://dados.gov.br/dados/conjuntos-dados/sistema-de-informacoes-de-projetos-de-reforma-agraria---sipra))")
    st.write("Contato: 6dsvj@pm.me")

    # Menu lateral para seleção de camadas
    layer_options = {
        'Assentamentos de Reforma Agrária': gdf.to_crs("EPSG:4326").to_json(),
        'Vegetação': 'https://raw.githubusercontent.com/giswqs/data/main/world/world_cities.zip',
        'Hidrografia': 'https://raw.githubusercontent.com/giswqs/data/main/world/rivers.geojson'
    }
    selected_layer = st.sidebar.selectbox("Escolha uma camada para visualizar:", list(layer_options.keys()))

    if selected_layer == 'Assentamentos de Reforma Agrária':
        m = folium.Map(location=[-24.0, -51.0], zoom_start=7)
        for idx, row in gdf.iterrows():
            area_formatted = format_area(row.get('area_incra', 0))
            area_polig_formatted = format_area(row.get('area_polig', 0))
            tooltip = f"<b>{row.get('nome_pa', 'N/A')} (Assentamento)</b><br>" \
                      f"Área: {area_formatted} hectares<br>" \
                      f"Área (segundo polígono): {area_polig_formatted} hectares<br>" \
                      f"Lotes: {row.get('lotes', 'N/A')}<br>" \
                      f"Famílias: {row.get('quant_fami', 'N/A')}<br>" \
                      f"Fase: {row.get('fase', 'N/A')}<br>" \
                      f"Data de criação: {row.get('data_criac', 'N/A')}<br>" \
                      f"Forma de obtenção: {row.get('forma_obte', 'N/A')}<br>" \
                      f"Data de obtenção: {row.get('data_obten', 'N/A')}"
            folium.GeoJson(
                row.geometry,
                tooltip=tooltip,
            ).add_to(m)
    else:
        geojson_data = get_geojson_from_url(layer_options[selected_layer])
        if geojson_data:
            m = folium.Map(location=[0, 0], zoom_start=2)
            folium.GeoJson(
                geojson_data,
                name=selected_layer
            ).add_to(m)

    folium_static(m)

    # Baixar polígonos selecionados como GeoJSON
    geojson = download_geojson(gdf)

    st.markdown(f"### Baixar polígonos selecionados como GeoJSON")
    st.markdown("Clique abaixo para baixar um arquivo GeoJSON contendo os polígonos dos assentamentos selecionados.")

    st.download_button(
        label="Baixar GeoJSON dos polígonos selecionados",
        data=geojson,
        file_name='poligonos_selecionados.geojson',
        mime='application/json',
    )

    # Exibir tabela de dados
    st.write("Tabela de dados:")
    st.dataframe(gdf)

    # Baixar dados como CSV
    @st.cache(suppress_st_warning=True)
    def convert_df(df):
        return df.to_csv(index=False).encode('utf-8')

    csv = convert_df(gdf)

    st.download_button(
        label="Baixar dados como CSV",
        data=csv,
        file_name='dados_assentamentos.csv',
        mime='text/csv',
    )
