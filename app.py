import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import folium_static
import streamlit as st
import json
from shapely.geometry import mapping

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

# Caminho para o arquivo GeoJSON
geojson_path = "pasbr_geo.geojson"

# Carregar GeoJSON
gdf = load_geojson(geojson_path)

# Verificar se o GeoJSON foi carregado com sucesso
if gdf is not None:
    st.title("Mapa interativo com os projetos de assentamento de reforma agrária no Brasil")
    st.markdown("(As informações exibidas neste site são públicas e estão disponíveis no [Portal de Dados Abertos](https://dados.gov.br/dados/conjuntos-dados/sistema-de-informacoes-de-projetos-de-reforma-agraria---sipra))")
    st.write("Contato: 6dsvj@pm.me")

    m = folium.Map(location=[-24.0, -51.0], zoom_start=7)

    filters = {}

    filter_columns = {
        'uf': 'um estado',
        'municipio': 'um município',
        'nome_pa': 'um assentamento',
        'cd_sipra': 'um código SIPRA',
        'lotes': 'o limite de lotes',
        'quant_fami': 'o limite de famílias beneficiárias',
        'fase': 'uma fase de consolidação',
        'data_criac': 'a data de criação',
        'forma_obte': 'a forma de obtenção do imóvel',
        'data_obten': 'a data de obtenção do imóvel',
        'area_incra_min': 'a área mínima (hectares) segundo dados do INCRA',
        'area_incra': 'a área máxima (hectares) segundo dados do INCRA',
        'area_polig_min': 'a área mínima (hectares) segundo polígono',
        'area_polig': 'a área máxima (hectares) segundo polígono'
    }

    options_lotes = [10, 50, 100, 300, 500, 800, 1200, 2000, 5000, 10000, 15000, 20000]
    options_familias = options_lotes
    options_area_incra = [500, 1000, 5000, 10000, 30000, 50000, 100000, 200000, 400000, 600000]

    selected_state = 'PARANÁ'

    # Seleção de Estado
    state_options = [''] + sorted(gdf['uf'].dropna().unique().tolist())
    default_state_index = state_options.index(selected_state) if selected_state in state_options else 0
    selected_state = st.sidebar.selectbox("Escolha um estado:", state_options, index=default_state_index)
    filters['uf'] = selected_state

    # Filtrar municípios com base no estado selecionado
    if selected_state:
        filtered_gdf_state = gdf[gdf['uf'] == selected_state]
        municipality_options = [''] + sorted(filtered_gdf_state['municipio'].dropna().unique().tolist())
    else:
        municipality_options = [''] + sorted(gdf['municipio'].dropna().unique().tolist())

    for col, display_name in filter_columns.items():
        if col in gdf.columns or col in ['area_incra_min', 'area_polig_min']:
            if col == 'municipio':
                filters[col] = st.sidebar.selectbox(f"Escolha {display_name}:", municipality_options, format_func=lambda x: 'Nenhum' if x == "" else str(x))
            elif col == 'lotes' or col == 'quant_fami':
                options = [None] + sorted(options_lotes)
                filters[col] = st.sidebar.selectbox(f"Escolha {display_name}:", options, format_func=lambda x: 'Nenhum' if x is None else str(x))
            elif col in ['area_incra', 'area_incra_min', 'area_polig', 'area_polig_min']:
                options = [None] + sorted(options_area_incra)
                filters[col] = st.sidebar.selectbox(f"Escolha {display_name}:", options, format_func=lambda x: 'Nenhum' if x is None else str(x))
            elif col == 'data_criac':
                filters[col] = st.sidebar.date_input(f"Escolha {display_name}:", min_value=pd.to_datetime("1970-01-01"), max_value=pd.to_datetime("2034-12-31"))
            else:
                unique_values = [""] + sorted(gdf[col].dropna().unique().tolist())
                filters[col] = st.sidebar.selectbox(f"Escolha {display_name}:", unique_values, format_func=lambda x: 'Nenhum' if x == "" else str(x))

    filtered_gdf = gdf.copy()
    for col, value in filters.items():
        if value is not None and value != "":
            if col == 'area_incra':
                filtered_gdf = filtered_gdf[filtered_gdf['area_incra'] <= value]
            elif col == 'area_incra_min':
                filtered_gdf = filtered_gdf[filtered_gdf['area_incra'] >= value]
            elif col == 'area_polig':
                filtered_gdf = filtered_gdf[filtered_gdf['area_polig'] <= value]
            elif col == 'area_polig_min':
                filtered_gdf = filtered_gdf[filtered_gdf['area_polig'] >= value]
            elif col == 'lotes':
                filtered_gdf = filtered_gdf[filtered_gdf['lotes'] <= value]
            elif col == 'quant_fami':
                filtered_gdf = filtered_gdf[filtered_gdf['quant_fami'] <= value]
            elif col == 'data_criac':
                filtered_gdf = filtered_gdf[pd.to_datetime(filtered_gdf['data_criac'], errors='coerce') <= pd.to_datetime(value)]
            else:
                filtered_gdf = filtered_gdf[filtered_gdf[col] == value]

    # Verificar se há resultados filtrados
    if not filtered_gdf.empty:
        bounds = filtered_gdf.total_bounds  # retorna (minx, miny, maxx, maxy)
        m = folium.Map(location=[(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2], zoom_start=10)
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    else:
        st.warning("Nenhum resultado encontrado para os filtros selecionados.")

    for idx, row in filtered_gdf.iterrows():
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

    folium_static(m)

    # Baixar polígonos selecionados como GeoJSON
    geojson = download_geojson(filtered_gdf)

    st.markdown(f"### Baixar polígonos selecionados como GeoJSON")
    st.markdown("Clique abaixo para baixar um arquivo GeoJSON contendo os polígonos dos assentamentos selecionados.")

    st.download_button(
        label="Baixar GeoJSON dos polígonos selecionados",
        data=geojson,
        file_name='poligonos_selecionados.geojson',
        mime='application/json',
    )

    # Exibir tabela de dados filtrados
    filtered_gdf = filtered_gdf[['uf', 'municipio', 'cd_sipra', 'nome_pa', 'lotes', 'quant_fami', 'fase', 'area_incra', 'area_polig', 'data_criac', 'forma_obte', 'data_obten']]
    st.write("Tabela de dados:")
    st.dataframe(filtered_gdf)

    # Baixar dados filtrados como CSV
    @st.cache(suppress_st_warning=True)
    def convert_df(df):
        return df.to_csv(index=False).encode('utf-8')

    csv = convert_df(filtered_gdf)

    st.download_button(
        label="Baixar dados filtrados como CSV",
        data=csv,
        file_name='dados_filtrados.csv',
        mime='text/csv',
    )
else:
    st.error("Falha ao carregar o GeoJSON. Verifique o arquivo de dados.")
