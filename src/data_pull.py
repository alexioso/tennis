import pandas as pd
import numpy as np
import os
import requests
from tqdm import tqdm
from datetime import datetime, timedelta, date
import json

with open("api_key.txt", 'r') as file:
    API_KEY = file.read()


#SportsRadar API daily_summaries get request for a single date. Used in below loop 
def get_tennis_daily_summary(d, #date of summary in string format "yyyy-mm-dd"
                             write_json=True,
                             output_path = "../data/json",
                             max_api_len = 200):
    
    d_num = d.replace("-","")
    
    
    
    url = f"https://api.sportradar.com/tennis/trial/v3/en/schedules/{d}/summaries.json"
    headers = {
            'accept'  : 'application/json',
            'x-api-key'  : API_KEY
    }
    response = requests.get(url,headers=headers)
        
    #parse response
    response_json = response.json() 
    
    response_json_temp = response_json
    
    #if length of response_json is 200, max limit may have been reached. need to append more possible data
    ind = max_api_len + 1
    while len(response_json_temp['summaries']) == max_api_len:
        url = f"https://api.sportradar.com/tennis/trial/v3/en/schedules/{d}/summaries.json?start={ind}"
        headers = {
                'accept'  : 'application/json',
                'x-api-key'  : API_KEY
        }
        response = requests.get(url,headers=headers)
            
        #parse response
        response_json_temp = response.json() 
        response_json['summaries'].extend(response_json_temp['summaries'])
        
        ind += max_api_len
    
    if write_json:
        file_path = os.path.join(output_path,f"{d_num}.json")
        with open(file_path, 'w') as json_file:
            json.dump(response_json, json_file, indent=4) 
    return response_json
    
    
def get_tennis_daily_summary_range(min_date,max_date):
    start = datetime.strptime(min_date, "%Y-%m-%d").date()
    end = datetime.strptime(max_date, "%Y-%m-%d").date()

    date_strings = [
        (start + timedelta(days=i)).isoformat()
        for i in range((end - start).days + 1)
    ]
    
    for dd in tqdm(range(len(date_strings))):
    
        d = date_strings[dd]
        temp = get_tennis_daily_summary(d, #date of summary in string format "yyyy-mm-dd"
                             write_json=True,
                             output_path = "../data/json",
                             max_api_len = 200)



min_date,max_date = "2026-01-01",str(date.today())

#refresh data for last two days just in case
get_tennis_daily_summary_range(str(date.today() - timedelta(days=1)),max_date)



#prepare final dataframe lists
date_ = []
comp_names = []
comp_categories = []
player_names = []
opponent_names = []
winner_flag = []
aces = []
breakpoints_won  = []
double_faults  = []
first_serve_points_won  = []
first_serve_successful  = []
games_won  = []
max_games_in_a_row  = []
max_points_in_a_row  = []
points_won_ = []
points_lost_ = []
points_won_from_last_10  = []
second_serve_points_won  = []
second_serve_successful  = []
service_games_won  = []
service_points_lost  = []
service_points_won  = []
tiebreaks_won  = []
total_breakpoints  = []
points_spread = []


start = datetime.strptime(min_date, "%Y-%m-%d").date()
end = datetime.strptime(max_date, "%Y-%m-%d").date()

date_strings = [
    (start + timedelta(days=i)).isoformat()
    for i in range((end - start).days + 1)
]


for dd in tqdm(range(len(date_strings))):
    
    d = date_strings[dd]
    
    d_num = d.replace("-","")
    
    if d_num + ".json" in os.listdir("../data/json"):
        print(f'Using cache for date: {d}')
        #use cache
        with open(f"../data/json/{d_num}.json", 'r') as json_file:
            response_json = json.load(json_file)
    else:
        #get and save request from API 
        print(f"API request for date: {d}")
        response_json = get_tennis_daily_summary(d)
          

    
    if "summaries" not in response_json.keys():
        print(response_json)
        continue

    for i in range(len(response_json['summaries'])):
        
        if response_json['summaries'][i]['sport_event_status']['status']!="closed":
            continue
        
        comp_name = response_json['summaries'][i]['sport_event']['sport_event_context']['competition']['name']
        comp_type = response_json['summaries'][i]['sport_event']['sport_event_context']['competition']['type']
        comp_category = response_json['summaries'][i]['sport_event']['sport_event_context']['category']['name']
        if ("ATP" in comp_category or "WTA" in comp_category or "United Cup" in comp_category) and "doubles" not in comp_name.lower():
        #if "doubles" not in comp_name.lower():
            #should return a list of two statistics dicts, one for each player
            try:
                competitors_stats = response_json['summaries'][i]['statistics']['totals']['competitors']
            except:
                #print(comp_name)
                #print(comp_category)
                #print(response_json['summaries'][i].keys())
                continue
            assert len(competitors_stats) == 2
                            
            for j in range(2):
                date_.append(d)
                comp_names.append(comp_name)
                comp_categories.append(comp_category)
                player_names.append(competitors_stats[j]['name'])
                opponent_names.append(competitors_stats[(j+1)%2]['name'])
                
                #determine winner
                if response_json['summaries'][i]["sport_event_status"]["winner_id"] == response_json['summaries'][i]["sport_event"]["competitors"][j]['id']:
                    winner_flag.append(1)
                else:
                    winner_flag.append(0)
                    
                #append stats
                try:
                    aces.append(competitors_stats[j]['statistics']['aces'])
                except:
                    aces.append(0)
                try:
                    breakpoints_won.append(competitors_stats[j]['statistics']['breakpoints_won'])
                except:
                    breakpoints_won.append(0)
                try:
                    double_faults.append(competitors_stats[j]['statistics']['double_faults'])
                except:
                    double_faults.append(0)
                try:
                    first_serve_points_won.append(competitors_stats[j]['statistics']['first_serve_points_won'])
                except:
                    first_serve_points_won.append(0)
                try:
                    first_serve_successful.append(competitors_stats[j]['statistics']['first_serve_successful'])
                except:
                    first_serve_successful.append(0)
                try:
                    games_won.append(competitors_stats[j]['statistics']['games_won'])
                except:
                    games_won.append(0)
                try:
                    max_games_in_a_row.append(competitors_stats[j]['statistics']['max_games_in_a_row'])
                except:
                    max_games_in_a_row.append(0)
                try:
                    max_points_in_a_row.append(competitors_stats[j]['statistics']['max_points_in_a_row'])
                except:
                    max_points_in_a_row.append(0)
                try:
                    points_won = competitors_stats[j]['statistics']['points_won']
                    points_lost = competitors_stats[(j+1)%2]['statistics']['points_won']
                    
                    points_won_.append(points_won)
                    points_lost_.append(points_lost)
                    points_spread.append(points_won-points_lost)
                except:
                    points_won_.append(0)
                    points_lost_.append(0)
                    points_spread.append(0)
                try:
                    second_serve_points_won.append(competitors_stats[j]['statistics']['second_serve_points_won'])
                except:
                    second_serve_points_won.append(0)
                try:
                    second_serve_successful.append(competitors_stats[j]['statistics']['second_serve_successful'])
                except:
                    second_serve_successful.append(0)
                try:
                    service_games_won.append(competitors_stats[j]['statistics']['service_games_won'])
                except:
                    service_games_won.append(0)
                try:
                    service_points_lost.append(competitors_stats[j]['statistics']['service_points_lost'])
                except:
                    service_points_lost.append(0)
                try:
                    service_points_won.append(competitors_stats[j]['statistics']['service_points_won'])
                except:
                    service_points_won.append(0)
                try:
                    tiebreaks_won.append(competitors_stats[j]['statistics']['tiebreaks_won'])
                except:
                    tiebreaks_won.append(0)
                try:
                    total_breakpoints.append(competitors_stats[j]['statistics']['total_breakpoints'])
                except:
                    total_breakpoints.append(0)
                    
                

                
atp_wta_fantasy_df = pd.DataFrame({"match_date":date_,
            "competition_name":comp_names,
            "competition_category":comp_categories,
            "player_name":player_names,
            "opponent_name":opponent_names,
            "winner_flag":winner_flag,
            "aces":aces,
            "breakpoints_won":breakpoints_won,
            "double_faults":double_faults,
            "first_serve_points_won":first_serve_points_won ,
            "first_serve_successful":first_serve_successful ,
            "games_won":games_won,
            "max_games_in_a_row":max_games_in_a_row ,
            "max_points_in_a_row":max_points_in_a_row ,
            "points_won":points_won_ ,
            "points_spread":points_spread,
            "second_serve_points_won":second_serve_points_won ,
            "second_serve_successful":second_serve_successful ,
            "service_games_won":service_games_won,
            "service_points_lost":service_points_lost ,
            "service_points_won":service_points_won ,
            "tiebreaks_won":tiebreaks_won ,
            "total_breakpoints":total_breakpoints
        })

atp_wta_fantasy_df["first_serve_win_perc"] = 100*atp_wta_fantasy_df["first_serve_points_won"]/atp_wta_fantasy_df["first_serve_successful"]
atp_wta_fantasy_df["second_serve_win_perc"] = 100*(atp_wta_fantasy_df["second_serve_points_won"]/(atp_wta_fantasy_df["second_serve_successful"] + atp_wta_fantasy_df["double_faults"]))
atp_wta_fantasy_df["breakpoint_conversion_perc"] = 100*(atp_wta_fantasy_df["breakpoints_won"]/(atp_wta_fantasy_df["total_breakpoints"]))
atp_wta_fantasy_df["Month"] = pd.to_datetime(atp_wta_fantasy_df["match_date"]).dt.strftime("%B") + " " + pd.to_datetime(atp_wta_fantasy_df["match_date"]).dt.strftime("%Y")

atp_wta_fantasy_df.to_csv("../data/match_stats.csv")

print("Computing player summaries")

atp_summary_df = atp_wta_fantasy_df[atp_wta_fantasy_df["competition_category"].isin(['ATP','United Cup'])].\
        groupby("player_name").agg({"winner_flag":"sum",
        "aces":"sum",
        "breakpoints_won":"sum",
        "total_breakpoints":"sum",
        "double_faults":"sum",
        "first_serve_points_won":"sum",
        "first_serve_successful":"sum",
        "second_serve_points_won":"sum",
        "second_serve_successful":"sum",
        "points_spread":"sum"}).reset_index().rename({"winner_flag":"total_wins"},axis=1)
atp_summary_df["FS Win %"] = atp_summary_df["first_serve_points_won"]/atp_summary_df["first_serve_successful"]
atp_summary_df["SS Win %"] = atp_summary_df["second_serve_points_won"]/atp_summary_df["second_serve_successful"]
atp_summary_df["BP Conv %"] = atp_summary_df["breakpoints_won"]/atp_summary_df["total_breakpoints"]
atp_summary_df["Ace Rank"] = atp_summary_df["aces"].rank(ascending=False)
atp_summary_df["DF Rank"] = atp_summary_df["double_faults"].rank(ascending=True)
atp_summary_df["Total Win Rank"] = atp_summary_df["total_wins"].rank(ascending=False)
atp_summary_df["Point Spread Rank"] = atp_summary_df["points_spread"].rank(ascending=False)
atp_summary_df["FS Win Rank"] = atp_summary_df["FS Win %"].rank(ascending=False)
atp_summary_df["SS Win Rank"] = atp_summary_df["SS Win %"].rank(ascending=False)
atp_summary_df["BP Rank"] = atp_summary_df["BP Conv %"].rank(ascending=False)
atp_summary_df["Mean Ranks"] = atp_summary_df.loc[:,"Ace Rank":"BP Rank"].mean(axis=1)
atp_summary_df["Mean Ranks Ranked"] = atp_summary_df["Mean Ranks"].rank(ascending=True)
					

wta_summary_df = atp_wta_fantasy_df[atp_wta_fantasy_df["competition_category"].isin(['WTA','United Cup'])].\
        groupby("player_name").agg({"winner_flag":"sum",
        "aces":"sum",
        "breakpoints_won":"sum",
        "total_breakpoints":"sum",
        "double_faults":"sum",
        "first_serve_points_won":"sum",
        "first_serve_successful":"sum",
        "second_serve_points_won":"sum",
        "second_serve_successful":"sum",
        "points_spread":"sum"}).reset_index().rename({"winner_flag":"total_wins"},axis=1)
wta_summary_df["FS Win %"] = wta_summary_df["first_serve_points_won"]/wta_summary_df["first_serve_successful"]
wta_summary_df["SS Win %"] = wta_summary_df["second_serve_points_won"]/wta_summary_df["second_serve_successful"]
wta_summary_df["BP Conv %"] = wta_summary_df["breakpoints_won"]/wta_summary_df["total_breakpoints"]
wta_summary_df["Ace Rank"] = wta_summary_df["aces"].rank(ascending=False)
wta_summary_df["DF Rank"] = wta_summary_df["double_faults"].rank(ascending=True)
wta_summary_df["Total Win Rank"] = wta_summary_df["total_wins"].rank(ascending=False)
wta_summary_df["Point Spread Rank"] = wta_summary_df["points_spread"].rank(ascending=False)
wta_summary_df["FS Win Rank"] = wta_summary_df["FS Win %"].rank(ascending=False)
wta_summary_df["SS Win Rank"] = wta_summary_df["SS Win %"].rank(ascending=False)
wta_summary_df["BP Rank"] = wta_summary_df["BP Conv %"].rank(ascending=False)
wta_summary_df["Mean Ranks"] = wta_summary_df.loc[:,"Ace Rank":"BP Rank"].mean(axis=1)
wta_summary_df["Mean Ranks Ranked"] = wta_summary_df["Mean Ranks"].rank(ascending=True)

atp_summary_df["last_refreshed"] = max_date
wta_summary_df["last_refreshed"] = max_date

atp_summary_df.to_csv("../data/atp_player_summary.csv")
wta_summary_df.to_csv("../data/wta_player_summary.csv")
					