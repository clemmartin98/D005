import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page config
st.set_page_config(layout="wide")
st.title("D0005 - Destore Analysis Dashboard")

# Load data
@st.cache_data
def load_data():
    df = pd.read_excel("D0005_systemLogs.xlsx", header=0)
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_convert('Europe/Brussels')
    df.set_index('timestamp', inplace=True)
    df = df.select_dtypes(include=[np.number])
    df = df.resample("2min").mean()
    df['P_Sur'] = -df['P_grid_elec'] + df['P_HP_elec']
    df['P_conso'] = -df['P_grid_elec']
    return df

df_D005 = load_data()

# Date selection
dates = [
    ["2024-11-04","2024-11-10"],
    ["2024-11-11","2024-11-17"],
    ["2024-11-18","2024-11-24"],
    ["2024-11-25","2024-12-01"],
    ["2024-12-02","2024-12-08"],
    ["2024-12-09","2024-12-15"],
    ["2024-12-16","2024-12-22"],
    ["2024-12-23","2024-12-29"],
    ["2024-12-30","2025-01-05"],
    ["2025-01-06","2025-01-12"],
    ["2025-01-13","2025-01-19"],
    ["2025-01-20","2025-01-26"],
    ["2025-01-27","2025-02-02"]
]
st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] {
            width:300px !important; # Set the width to your desired value
        }
    </style>
    """,
    unsafe_allow_html=True,
)
hide_github_icon = """
#GithubIcon {
  visibility: hidden;
}
"""
st.markdown(hide_github_icon, unsafe_allow_html=True)
st.write('test')
selected_week = st.sidebar.selectbox(
    "Sélectionnez la semaine que vous souhaitez analyser",
    options=dates,
    format_func=lambda x: f"Du {pd.to_datetime(x[0]).strftime('%d/%m/%Y')} au {pd.to_datetime(x[1]).strftime('%d/%m/%Y')}"
)

# Prepare data for selected week
df_temp = df_D005.loc[f"{selected_week[0]}":f"{selected_week[1]} 23:59:59"]
df_temp['grid_elec_positive'] = np.maximum(-df_temp['P_grid_elec'], 0)
df_temp['autoprod'] = np.where(df_temp['P_HP_elec'] > 100,
                          np.minimum(np.maximum(df_temp['P_Sur'],0)/df_temp['P_HP_elec']*100, 100),
                          np.nan)

# Common layout settings
def set_common_layout(fig, title, y_suffix=""):
    fig.update_layout(
        template='simple_white',
        title=title,
        xaxis=dict(
            title="Date",
            tickformat="%b %d \n %H:%M",
            dtick=3600000*12
        ),
        yaxis=dict(ticksuffix=y_suffix)
    )
    fig.update_layout(
            xaxis=dict(rangeslider=dict(visible=True))
        )
    return fig
st.markdown("Ce Dashboard temporaire a pour but de visualiser les différentes données disponibles concernant votre installation.")
# Create and display figures
st.subheader("Bilan électrique")
with st.expander("Show more"):
    fig1 = go.Figure()
    for col in ['P_HP_elec', 'P_Sur', 'P_conso']:
        fig1.add_trace(go.Scatter(x=df_temp.index, y=df_temp[col],
                                mode='lines', fill='tozeroy', name=col))
        
    set_common_layout(fig1, "Bilan électrique", " W")
    st.plotly_chart(fig1, use_container_width=True)

st.subheader("Température de la pompe à chaleur")
with st.expander("Show more"):
    color_map = {"T_HP_flow": "#C21806", "T_HP_return": "#0F52BA"}
    fig2 = px.line(df_temp, df_temp.index, ['T_HP_return','T_HP_flow'],
                    line_shape='spline', color_discrete_map=color_map)
    set_common_layout(fig2, "Températures départ/retour de la pompe à chaleur (sondes Destore)", " °C")
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Température intérieure")
with st.expander("Show more"):
    df_hourly = df_temp.resample("1h").mean()
    fig3 = px.line(df_hourly, y='T_house_actual', line_shape='spline')
    set_common_layout(fig3, "Température intérieure", " °C")
    fig3.update_layout(showlegend=False)
    fig3.update_yaxes(range=[15, None])
    st.plotly_chart(fig3, use_container_width=True)

st.subheader("Auto-production")
with st.expander("Show more"):
    fig4 = px.area(df_temp, y='autoprod', line_shape='spline')
    set_common_layout(fig4, "Autoproduction de la pompe à chaleur", " %")
    st.plotly_chart(fig4, use_container_width=True)

st.subheader("Auto-production moyenne")
with st.expander("Show more"):
    df_daily = df_temp.resample('1D').mean()
    fig5 = px.bar(df_daily, y='autoprod', text='autoprod')
    fig5.update_traces(marker_color='#4CBB17', texttemplate="%{text:.1f}%", textposition='auto')
    fig5.update_layout(template='simple_white', title="Autoproduction moyenne journalière")
    st.plotly_chart(fig5, use_container_width=True)

# Prepare heatmap data
df_temp["Hour"] = df_temp.index.hour
df_temp["Day"] = df_temp.index.dayofweek
heatmap_data_1 = df_temp.groupby(["Day", "Hour"])["P_HP_elec"].mean().unstack().fillna(0)
heatmap_data_2 = df_temp.groupby(["Day", "Hour"])["P_conso"].mean().unstack().fillna(0)
zmin = 0
zmax1 = heatmap_data_1.max().max()
zmax2 = heatmap_data_2.max().max()

def create_weekly_heatmap(data, title, zmin=0, zmax=None, scale_factor=1):
    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    fig = make_subplots(rows=7, cols=1, subplot_titles=days)
    
    for i, (day, row_data) in enumerate(data.iterrows()):
        fig.add_trace(
            go.Heatmap(z=[scale_factor * row_data.values], x=row_data.index, y=[day],
                    colorscale="Plasma", showscale=(i == 0),
                    zmin=zmin, zmax=zmax),
            row=i+1, col=1
        )
    
    fig.update_layout(title=title, xaxis_title="", height=1500)
    for i in range(1, 8):
        fig.update_xaxes(dtick=2, row=i, col=1)
    return fig

st.subheader("Fonctionnement hebdomadaire")
with st.expander("Show more"):
    fig6 = create_weekly_heatmap(heatmap_data_1, "Puissance moyenne horaire de la pompe à chaleur", scale_factor=3)
    st.plotly_chart(fig6, use_container_width=True)

    fig7 = create_weekly_heatmap(heatmap_data_2.clip(lower=0), "Surplus horaire moyen",zmin=zmin,zmax=zmax2)
    st.plotly_chart(fig7, use_container_width=True)

    # Working minutes heatmap
    df_result = df_temp.groupby(["Day","Hour"]).agg(
        minutes_working=('P_HP_elec', lambda x: (x > 0).sum())
    ).reset_index()

    heatmap_data_3 = df_result.pivot(index='Day', columns='Hour', values='minutes_working')
    zmax3 = heatmap_data_3.max().max()

    fig8 = create_weekly_heatmap(heatmap_data_3, "Minutes de fonctionnement horaire de la pompe à chaleur", zmin=0, zmax=zmax3)
    st.plotly_chart(fig8, use_container_width=True)
