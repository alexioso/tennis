import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

#TODO: preserve colors when adding new players

df_glicko = pd.read_csv("../data/prep/atp_glicko_output_df.csv")

categories = df_glicko['glicko2_category'].unique()
players = df_glicko['player_name'].unique()
surfaces = ["overall","hard","clay","grass"]

selected_category = st.selectbox('Select Glicko2 Score Categories:', options=categories, placeholder=categories[0])
selected_surface = st.selectbox('Select surface:', options=surfaces, placeholder="overall")
selected_players = st.multiselect('Select Player(s)', options=players, default=["Sinner, Jannik","Alcaraz, Carlos"])

# Filter the data based on user selections
filtered_df = df_glicko[
    (df_glicko['glicko2_category'] == selected_category) & 
    (df_glicko['player_name'].isin(selected_players)) &
    (df_glicko['surface'] == selected_surface) 
]


# Create and display the line chart using Plotly Express for better customization
# Plotly Express is recommended for interactive plots with multiple lines
if not filtered_df.empty:
    st.subheader('Glicko Trends')
    # The 'color' parameter automatically plots different lines for each category
    fig = px.line(filtered_df, x='date', y='glicko2_mu', color='player_name', 
                  title='Glicko2 Trends over Time')
    fig = px.line(
    filtered_df,
    x="date",
    y="glicko2_mu",
    color="player_name",
    title="Glicko2 Trends over Time (95% CI)",
    )

    # Add a CI band per player
    for player, d in filtered_df.sort_values("date").groupby("player_name"):
        fig.add_trace(go.Scatter(
            x=pd.concat([d["date"], d["date"][::-1]]),
            y=pd.concat([d["glicko2_mu_upper"], d["glicko2_mu_lower"][::-1]]),
            fill="toself",
            fillcolor="rgba(0,0,0,0.12)",   # will tint; see note below to match line color
            line=dict(color="rgba(0,0,0,0)"),
            hoverinfo="skip",
            showlegend=False,
            name=f"{player} 95% CI",
        ))

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No data to display after filtering.")


st.header(f"Top Ranked Players with {selected_category} {selected_surface} Glicko Score")
player_date_max = df_glicko.groupby(["player_name","surface"])["date"].max().reset_index().rename({"date":"max_date"},axis=1)
df_glicko = df_glicko.merge(player_date_max, how="left", on=["player_name","surface"])
print(df_glicko.columns)

top_players_table = df_glicko.loc[(df_glicko.date==df_glicko.max_date)&
                                  (df_glicko.glicko2_category==selected_category)&
                                  (df_glicko.surface==selected_surface),
                                  ["player_name","glicko2_mu","date","glicko2_mu_lower"]].sort_values("glicko2_mu_lower",ascending=False)
# Display the DataFrame with filtering enabled
st.dataframe(top_players_table.rename({"player_name":"Player", "date":"Date of Last Match","glicko2_mu":f"Glicko2 {selected_category} {selected_surface}"},axis=1), 
             use_container_width=True)
#show top players in current glicko category
