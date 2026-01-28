import pandas as pd
import numpy as np
import os
import requests
from tqdm import tqdm
from datetime import datetime, timedelta, date
import json

min_date,max_date = "2025-01-01",str(date.today())


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




#refresh data for last two days just in case
#get_tennis_daily_summary_range(str(date.today() - timedelta(days=2)),max_date)
#get_tennis_daily_summary_range(str(date.today() - timedelta(days=2)),str(date.today() - timedelta(days=2)))
#get_tennis_daily_summary_range(min_date,max_date)


#prepare final dataframe lists
date_ = []
comp_names = []
comp_categories = []
comp_levels = []
comp_ids = []
venue_ids = []
venue_capacitys = []
player_ids = []
opponent_ids = []
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
games_won_= []
games_lost_= []
sets_won_=[]
sets_lost_=[]
points_won_from_last_10  = []
second_serve_points_won  = []
second_serve_successful  = []
service_games_won  = []
service_points_lost  = []
service_points_won  = []
tiebreaks_won  = []
total_breakpoints  = []
points_spread = []
games_spread = []
sets_spread = []
aces_allowed = []
breakpoints_allowed = []
breakpoints_saved = []
first_serve_return_points_won = []
first_serve_return_points_total = []
second_serve_return_points_won = []
second_serve_return_points_total = []


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
        

        todo_walkover_wins = """
        if response_json['summaries'][i]['sport_event_status']['status'] == "walkover":
            #determine winner
            if response_json['summaries'][i]["sport_event_status"]["winner_id"] == response_json['summaries'][i]["statistics"]["totals"]["competitors"][j]['id']:
                winner_flag.append(1)
            else:
                winner_flag.append(0)"""


        if response_json['summaries'][i]['sport_event_status']['status'] not in ["closed","ended"]:
            continue
        

        #TODO: determine set format, grand slam/1000/500/250, court surface, player handedness
        comp_name = response_json['summaries'][i]['sport_event']['sport_event_context']['competition']['name']
        comp_type = response_json['summaries'][i]['sport_event']['sport_event_context']['competition']['type']
        try:
            comp_level = response_json['summaries'][i]['sport_event']['sport_event_context']['competition']['level']
        except: 
            comp_level = "unknown"
        comp_category = response_json['summaries'][i]['sport_event']['sport_event_context']['category']['name']
        comp_id = response_json['summaries'][i]['sport_event']['sport_event_context']['competition']['id']
        try:
            venue_id = response_json['summaries'][i]['sport_event']["venue"]["id"]
        except:
            venue_id = ""
        try:
            venue_capacity = response_json['summaries'][i]['sport_event']["venue"]["capacity"]
        except:
            venue_capacity = 0
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
                comp_levels.append(comp_level)
                comp_ids.append(comp_id)
                venue_ids.append(venue_id)
                venue_capacitys.append(venue_capacity)
                player_names.append(competitors_stats[j]['name'])
                opponent_names.append(competitors_stats[(j+1)%2]['name'])

                player_ids.append(response_json['summaries'][i]["statistics"]["totals"]["competitors"][j]['id'])
                opponent_ids.append(response_json['summaries'][i]["statistics"]["totals"]["competitors"][(j+1)%2]['id'])
                player_qualifier_temp = response_json['summaries'][i]["statistics"]["totals"]["competitors"][j]['qualifier']
                opp_qualifier_temp = response_json['summaries'][i]["statistics"]["totals"]["competitors"][(j+1)%2]['qualifier']
                    
                #determine winner
                try:
                    if response_json['summaries'][i]["sport_event_status"]["winner_id"] == response_json['summaries'][i]["statistics"]["totals"]["competitors"][j]['id']:
                        winner_flag.append(1)
                    else:
                        winner_flag.append(0)
                except:
                    winner_flag.append(-1)
                    
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
                    games_won = competitors_stats[j]['statistics']['games_won']
                    games_lost = competitors_stats[(j+1)%2]['statistics']['games_won']
                    
                    games_won_.append(games_won)
                    games_lost_.append(games_lost)
                    games_spread.append(games_won-games_lost)
                except:
                    games_won_.append(0)
                    games_lost_.append(0)
                    games_spread.append(0)
                try:
                    sets_won = response_json['summaries'][i]["sport_event_status"][f"{player_qualifier_temp}_score"]
                    sets_lost = response_json['summaries'][i]["sport_event_status"][f"{opp_qualifier_temp}_score"]

                    sets_won_.append(sets_won)
                    sets_lost_.append(sets_lost)
                    sets_spread.append(sets_won-sets_lost)
                except:
                    sets_won_.append(0)
                    sets_lost_.append(0)
                    sets_spread.append(0)
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
                try:
                    aces_allowed.append(competitors_stats[(j+1)%2]['aces'])
                except:
                    aces_allowed.append(0)
                try:
                    breakpoints_allowed.append(competitors_stats[(j+1)%2]['statistics']['total_breakpoints'])
                except:
                    breakpoints_allowed.append(0)
                try:
                    breakpoints_saved.append(competitors_stats[(j+1)%2]['statistics']['total_breakpoints'] - competitors_stats[(j+1)%2]['statistics']['breakpoints_won'])
                except:
                    breakpoints_saved.append(0)
                try:
                    first_serve_return_points_won.append(competitors_stats[(j+1)%2]['statistics']['first_serve_points_won'])
                except:
                    first_serve_return_points_won.append(0)
                try:
                    first_serve_return_points_total.append(competitors_stats[(j+1)%2]['statistics']['first_serve_successful'])
                except:
                    first_serve_return_points_total.append(0)
                try:
                    second_serve_return_points_won.append(competitors_stats[(j+1)%2]['statistics']['second_serve_successful'] - competitors_stats[(j+1)%2]['statistics']['second_serve_points_won'])
                except:
                    second_serve_return_points_won.append(0)
                try:
                    second_serve_return_points_total.append(competitors_stats[(j+1)%2]['statistics']['second_serve_successful'] - competitors_stats[(j+1)%2]['statistics']['second_serve_points_won'])
                except:
                    second_serve_return_points_total.append(0)
                    

print("date_: " + str(len(date_)))
print("comp_names: " + str(len(comp_names)))
print("comp_categories: " + str(len(comp_categories)))
print("comp_levels: " + str(len(comp_levels)))
print("venue_ids: " + str(len(venue_ids)))
print("venue_capacitys: " + str(len(venue_capacitys)))
print("player_ids: " + str(len(player_ids)))
print("opponent_ids: " + str(len(opponent_ids)))
print("player_names: " + str(len(player_names)))
print("opponent_names: " + str(len(opponent_names)))
print("winner_flag: " + str(len(winner_flag)))
print("aces: " + str(len(aces)))
print("breakpoints_won: " + str(len(breakpoints_won)))
print("double_faults: " + str(len(double_faults)))
print("first_serve_points_won: " + str(len(first_serve_points_won)))
print("first_serve_successful: " + str(len(first_serve_successful)))
print("max_games_in_a_row: " + str(len(max_games_in_a_row)))
print("max_points_in_a_row: " + str(len(max_points_in_a_row)))
print("points_won_: " + str(len(points_won_)))
print("points_lost_: " + str(len(points_lost_)))
print("games_won_: " + str(len(games_won_)))
print("games_lost_: " + str(len(games_lost_)))
print("sets_won_: " + str(len(sets_won_)))
print("sets_lost_: " + str(len(sets_lost_)))
print("second_serve_points_won: " + str(len(second_serve_points_won)))
print("second_serve_successful: " + str(len(second_serve_successful)))
print("service_games_won: " + str(len(service_games_won)))
print("service_points_lost: " + str(len(service_points_lost)))
print("service_points_won: " + str(len(service_points_won)))
print("tiebreaks_won: " + str(len(tiebreaks_won)))
print("total_breakpoints: " + str(len(total_breakpoints)))
print("points_spread: " + str(len(points_spread)))
print("games_spread: " + str(len(games_spread)))
print("sets_spread: " + str(len(sets_spread)))
print("aces_allowed: " + str(len(aces_allowed)))
print("breakpoints_allowed: " + str(len(breakpoints_allowed)))
print("breakpoints_saved: " + str(len(breakpoints_saved)))
print("first_serve_return_points_won: " + str(len(first_serve_return_points_won)))
print("second_serve_return_points_won: " + str(len(second_serve_return_points_won)))
print("second_serve_return_points_total: " + str(len(second_serve_return_points_total)))


                
match_stats_df = pd.DataFrame({"match_date":date_,
"competition_name":comp_names,
"competition_category":comp_categories,
"competition_level":comp_levels,
"venue_ids":venue_ids,
"venue_capacitys":venue_capacitys,
"player_id":player_ids,
"opponent_id":opponent_ids,
"player_name":player_names,
"opponent_name":opponent_names,
"winner_flag":winner_flag,
"aces":aces,
"breakpoints_won":breakpoints_won,
"double_faults":double_faults,
"first_serve_points_won":first_serve_points_won,
"first_serve_successful":first_serve_successful,
"games_won":games_won,
"max_games_in_a_row":max_games_in_a_row,
"max_points_in_a_row":max_points_in_a_row,
"points_won_":points_won_,
"points_lost_":points_lost_,
"games_won_":games_won_,
"games_lost_":games_lost_,
"sets_won_":sets_won_,
"sets_lost_":sets_lost_,
"second_serve_points_won":second_serve_points_won,
"second_serve_successful":second_serve_successful,
"service_games_won":service_games_won,
"service_points_lost":service_points_lost,
"service_points_won":service_points_won,
"tiebreaks_won":tiebreaks_won,
"total_breakpoints":total_breakpoints,
"points_spread":points_spread,
"games_spread":games_spread,
"sets_spread":sets_spread,
"aces_allowed":aces_allowed,
"breakpoints_allowed":breakpoints_allowed,
"breakpoints_saved":breakpoints_saved,
"first_serve_return_points_won":first_serve_return_points_won,
"first_serve_return_points_total":first_serve_return_points_total,
"second_serve_return_points_won":second_serve_return_points_won,
"second_serve_return_points_total":second_serve_return_points_total,
        })



match_stats_df["first_serve_win_perc"] = 100*match_stats_df["first_serve_points_won"]/match_stats_df["first_serve_successful"]
match_stats_df["first_serve_return_win_perc"] = 100*match_stats_df["first_serve_return_points_won"]/match_stats_df["first_serve_return_points_total"]
match_stats_df["second_serve_win_perc"] = 100*(match_stats_df["second_serve_points_won"]/(match_stats_df["second_serve_successful"] + match_stats_df["double_faults"]))
match_stats_df["breakpoint_conversion_perc"] = 100*(match_stats_df["breakpoints_won"]/(match_stats_df["total_breakpoints"]))
match_stats_df["Month"] = pd.to_datetime(match_stats_df["match_date"]).dt.strftime("%B") + " " + pd.to_datetime(match_stats_df["match_date"]).dt.strftime("%Y")

match_stats_df.to_csv("../data/match_stats.csv")

print("Computing player summaries")

atp_player_summary_df = match_stats_df[match_stats_df["competition_category"].isin(['ATP','United Cup'])].\
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
atp_player_summary_df["FS Win %"] = atp_player_summary_df["first_serve_points_won"]/atp_player_summary_df["first_serve_successful"]
atp_player_summary_df["SS Win %"] = atp_player_summary_df["second_serve_points_won"]/atp_player_summary_df["second_serve_successful"]
atp_player_summary_df["BP Conv %"] = atp_player_summary_df["breakpoints_won"]/atp_player_summary_df["total_breakpoints"]
atp_player_summary_df["Ace Rank"] = atp_player_summary_df["aces"].rank(ascending=False)
atp_player_summary_df["DF Rank"] = atp_player_summary_df["double_faults"].rank(ascending=True)
atp_player_summary_df["Total Win Rank"] = atp_player_summary_df["total_wins"].rank(ascending=False)
atp_player_summary_df["Point Spread Rank"] = atp_player_summary_df["points_spread"].rank(ascending=False)
atp_player_summary_df["FS Win Rank"] = atp_player_summary_df["FS Win %"].rank(ascending=False)
atp_player_summary_df["SS Win Rank"] = atp_player_summary_df["SS Win %"].rank(ascending=False)
atp_player_summary_df["BP Rank"] = atp_player_summary_df["BP Conv %"].rank(ascending=False)
atp_player_summary_df["Mean Ranks"] = atp_player_summary_df.loc[:,"Ace Rank":"BP Rank"].mean(axis=1)
atp_player_summary_df["Mean Ranks Ranked"] = atp_player_summary_df["Mean Ranks"].rank(ascending=True)
					

wta_player_summary_df = match_stats_df[match_stats_df["competition_category"].isin(['WTA','United Cup'])].\
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
wta_player_summary_df["FS Win %"] = wta_player_summary_df["first_serve_points_won"]/wta_player_summary_df["first_serve_successful"]
wta_player_summary_df["SS Win %"] = wta_player_summary_df["second_serve_points_won"]/wta_player_summary_df["second_serve_successful"]
wta_player_summary_df["BP Conv %"] = wta_player_summary_df["breakpoints_won"]/wta_player_summary_df["total_breakpoints"]
wta_player_summary_df["Ace Rank"] = wta_player_summary_df["aces"].rank(ascending=False)
wta_player_summary_df["DF Rank"] = wta_player_summary_df["double_faults"].rank(ascending=True)
wta_player_summary_df["Total Win Rank"] = wta_player_summary_df["total_wins"].rank(ascending=False)
wta_player_summary_df["Point Spread Rank"] = wta_player_summary_df["points_spread"].rank(ascending=False)
wta_player_summary_df["FS Win Rank"] = wta_player_summary_df["FS Win %"].rank(ascending=False)
wta_player_summary_df["SS Win Rank"] = wta_player_summary_df["SS Win %"].rank(ascending=False)
wta_player_summary_df["BP Rank"] = wta_player_summary_df["BP Conv %"].rank(ascending=False)
wta_player_summary_df["Mean Ranks"] = wta_player_summary_df.loc[:,"Ace Rank":"BP Rank"].mean(axis=1)
wta_player_summary_df["Mean Ranks Ranked"] = wta_player_summary_df["Mean Ranks"].rank(ascending=True)

atp_player_summary_df["last_refreshed"] = max_date
wta_player_summary_df["last_refreshed"] = max_date

atp_player_summary_df.to_csv("../data/atp_player_summary.csv")
wta_player_summary_df.to_csv("../data/wta_player_summary.csv")
					