conda init zsh
cd /home/alex/Documents/fantasy_tennis/src
python data_pull.py 120
#git add ../data/prep/match_stats.csv
git add ../data/fantasy/atp_player_summary.csv
git add ../data/fantasy/wta_player_summary.csv
git commit -m "refresh data"
git push
#streamlit run dashboard_st.py
