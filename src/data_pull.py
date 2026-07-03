#TODO: ml input table pipeline with rolling averages
#TODO: fix second servereturn nans
#TODO: fetch point by point data as far back as possible. with doubles
#.     get more accurate doubles serve data somehow (automate or crowdsource)
#TODO: ml tune glicko params 
#TODO: convert csv reading s and writings to sql (match_stats, seasons, summaries, fantasy tables done -> Postgres via db.py; sackmann retro + glicko output still CSV-only)
#TODO: fetch serve direction areas from infotennks
#TODO: fetch rally data from sackmann (and contribute, maybe train LLM?)
#TODO: automate sportradar api key gen (low priority)
#TODO: player reports patterns


import pandas as pd
import numpy as np
import os
import requests
from tqdm import tqdm
from datetime import datetime, timedelta, date
import json
import sys
from dotenv import load_dotenv
import time

from db import get_engine, write_table

# Load environment variables from the .env file
load_dotenv()

# Access the variables using os.getenv()
API_KEY = os.getenv('SPORTRADAR_API_KEY')

#with open("api_key.txt", 'r') as file:
#    API_KEY = file.read()


#SportsRadar API daily_summaries get request for a single date. Used in below loop 
def get_tennis_daily_summary(d, #date of summary in string format "yyyy-mm-dd"
                             write_json=True,
                             output_path = "../data/raw/daily_summary",
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

    while 'summaries' in list(response_json_temp.keys()) and  len(response_json_temp['summaries']) == max_api_len:
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
                             output_path = "../data/raw/daily_summary",
                             max_api_len = 200)


def parse_sackmann_retro_data(df):

    return

def refresh_match_stats_df(min_date, max_date):

    #prepare final dataframe lists
    date_ = []
    season_id_ = []
    sportevent_id = []
    comp_names = []
    comp_categories = []
    comp_levels = []
    comp_ids = []
    venue_ids = []
    venue_capacitys = []
    player_ids = []
    opponent_ids = []
    player_names = []
    player_seeds = []
    opponent_names = []
    opponent_seeds = []
    winner_flag = []
    aces = []
    breakpoints_won  = []
    double_faults  = []
    first_serve_points_won  = []
    first_serve_successful  = []
    service_games = []
    service_games_held = []
    return_games = []
    return_games_broke = []
    games_won  = []
    max_games_in_a_row  = []
    max_points_in_a_row  = []
    points_won_ = []
    points_lost_ = []
    games_won_= []
    games_lost_= []
    sets_won_=[]
    sets_lost_=[]
    set1_win_flag_ = []
    set2_win_flag_ = []
    set3_win_flag_ = []
    set4_win_flag_ = []
    set5_win_flag_ = []
    set1_games_ = []
    set2_games_ = []
    set3_games_ = []
    set4_games_ = []
    set5_games_ = []
    points_won_from_last_10  = []
    second_serve_points_won  = []
    second_serve_successful  = []
    service_points_lost  = []
    service_points_won  = []
    tiebreaks_won  = []
    tiebreaks_lost = []
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
        
        if d_num + ".json" in os.listdir("../data/raw/daily_summary"):
            #print(f'Using cache for date: {d}')
            #use cache
            with open(f"../data/raw/daily_summary/{d_num}.json", 'r') as json_file:
                response_json = json.load(json_file)
        else:
            #get and save request from API 
            print(f"API request for date: {d}")
            response_json = get_tennis_daily_summary(d)
            

        
        if "summaries" not in response_json.keys():
            print(d)
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


            if response_json['summaries'][i]['sport_event_status']['status'] not in ["closed","ended","walkover"]:
                continue
            

            #TODO: determine set format, grand slam/1000/500/250, court surface, player handedness
            event_id = response_json['summaries'][i]['sport_event']['id']
            season_id = response_json['summaries'][i]['sport_event']['sport_event_context']['season']['id']
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
            #if ("ATP" in comp_category or "WTA" in comp_category or "United Cup" in comp_category) and "doubles" not in comp_name.lower():
            if "doubles" not in comp_name.lower():

                #should return a list of two statistics dicts, one for each player
                try:
                    competitors_stats = response_json['summaries'][i]['statistics']['totals']['competitors']
                except:
                    response_json['summaries'][i]["statistics"] = {"totals":{"competitors":response_json['summaries'][i]["sport_event"]["competitors"]}}
                    competitors_stats = response_json['summaries'][i]['statistics']['totals']['competitors']
                try:
                    assert len(competitors_stats) == 2
                except:
                    #TODO: FLAG and send to sportradar
                    print(f"DATA WARNING: date {d}\ncompetitor_stats_JSON: {competitors_stats}")
                    continue

                

                                
                for j in range(2):
                    date_.append(d)
                    sportevent_id.append(event_id)
                    season_id_.append(season_id)
                    comp_names.append(comp_name)
                    comp_categories.append(comp_category)
                    comp_levels.append(comp_level)
                    comp_ids.append(comp_id)
                    venue_ids.append(venue_id)
                    venue_capacitys.append(venue_capacity)
                    player_names.append(competitors_stats[j]['name'])
                    opponent_names.append(competitors_stats[(j+1)%2]['name'])

                    if "seed" in response_json["summaries"][i]["sport_event"]["competitors"][j].keys():
                        player_seeds.append(response_json["summaries"][i]["sport_event"]["competitors"][j]["seed"])
                    else:
                        player_seeds.append(np.nan)

                    if "seed" in response_json["summaries"][i]["sport_event"]["competitors"][(j+1)%2].keys():
                        opponent_seeds.append(response_json["summaries"][i]["sport_event"]["competitors"][(j+1)%2]["seed"])
                    else:
                        opponent_seeds.append(np.nan)


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

                    try:
                        service_games.append(competitors_stats[j]['statistics']['service_games_won']+competitors_stats[(j+1)%2]['statistics']['breakpoints_won'])
                    except:
                        service_games.append(0)
                    
                    try:
                        service_games_held.append(competitors_stats[j]['statistics']['service_games_won'])
                        assert service_games_held <= service_games
                    except:
                        service_games_held.append(0)

                    try:
                        return_games.append(competitors_stats[(j+1)%2]['statistics']['service_games_won']+competitors_stats[j]['statistics']['breakpoints_won'])
                    except:
                        return_games.append(0)
                    

                    try:
                        return_games_broke.append(competitors_stats[j]['statistics']['breakpoints_won'])
                        assert return_games_broke <= return_games
                    except:
                        return_games_broke.append(0)
                    
                    #append scores (nan means set didnt happen, like 4/5th set for WTA)

                    try:
                        set1_games = response_json['summaries'][i]["sport_event_status"]["period_scores"][0][f"{player_qualifier_temp}_score"]
                        set1_games_opp = response_json['summaries'][i]["sport_event_status"]["period_scores"][0][f"{opp_qualifier_temp}_score"]
                        if set1_games > set1_games_opp:
                            set1_win_flag = 1
                        else:
                            set1_win_flag = 0
                    except:
                        set1_games = np.nan
                        set1_win_flag = np.nan

                    
                        
                    try:
                        set2_games = response_json['summaries'][i]["sport_event_status"]["period_scores"][1][f"{player_qualifier_temp}_score"]
                        set2_games_opp = response_json['summaries'][i]["sport_event_status"]["period_scores"][1][f"{opp_qualifier_temp}_score"]
                        if set2_games > set2_games_opp:
                            set2_win_flag = 1
                        else:
                            set2_win_flag = 0
                    except:
                        set2_games = np.nan
                        set2_win_flag = np.nan
                    try:
                        set3_games = response_json['summaries'][i]["sport_event_status"]["period_scores"][2][f"{player_qualifier_temp}_score"]
                        set3_games_opp = response_json['summaries'][i]["sport_event_status"]["period_scores"][2][f"{opp_qualifier_temp}_score"]
                        if set3_games > set3_games_opp:
                            set3_win_flag = 1
                        else:
                            set3_win_flag = 0
                    except:
                        set3_games = np.nan
                        set3_win_flag = np.nan
                    try:
                        set4_games = response_json['summaries'][i]["sport_event_status"]["period_scores"][3][f"{player_qualifier_temp}_score"]
                        set4_games_opp = response_json['summaries'][i]["sport_event_status"]["period_scores"][3][f"{opp_qualifier_temp}_score"]
                        if set4_games > set4_games_opp:
                            set4_win_flag = 1
                        else:
                            set4_win_flag = 0
                    except:
                        set4_games = np.nan
                        set4_win_flag = np.nan
                    try:
                        set5_games = response_json['summaries'][i]["sport_event_status"]["period_scores"][4][f"{player_qualifier_temp}_score"]
                        set5_games_opp = response_json['summaries'][i]["sport_event_status"]["period_scores"][4][f"{opp_qualifier_temp}_score"]
                        if set5_games > set5_games_opp:
                            set5_win_flag = 1
                        else:
                            set5_win_flag = 0
                    except:
                        set5_games = np.nan
                        set5_win_flag = np.nan

                    set1_win_flag_.append(set1_win_flag)
                    set2_win_flag_.append(set2_win_flag)
                    set3_win_flag_.append(set3_win_flag)
                    set4_win_flag_.append(set4_win_flag)
                    set5_win_flag_.append(set5_win_flag)
                    set1_games_.append(set1_games)
                    set2_games_.append(set2_games)
                    set3_games_.append(set3_games)
                    set4_games_.append(set4_games)
                    set5_games_.append(set5_games)
                        
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
                        tiebreaks_lost.append(competitors_stats[(j+1)%2]['statistics']['tiebreaks_won'])
                    except:
                        tiebreaks_lost.append(0)
                    try:
                        total_breakpoints.append(competitors_stats[j]['statistics']['total_breakpoints'])
                    except:
                        total_breakpoints.append(0)
                    try:
                        aces_allowed.append(competitors_stats[(j+1)%2]['statistics']['aces'])
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
                        second_serve_return_points_total.append(competitors_stats[(j+1)%2]['statistics']['second_serve_successful'])
                    except:
                        second_serve_return_points_total.append(0)

                    
    match_stats_df = pd.DataFrame({"match_date":date_,
    "event_id":sportevent_id,
    "season_id":season_id_,
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
    "player_seed":player_seeds,
    "opponent_seed":opponent_seeds,
    "aces":aces,
    "aces_allowed":aces_allowed,
    "service_games":service_games,
    "service_games_held":service_games_held,
    "return_games":return_games,
    "return_games_broke":return_games_broke,
    "breakpoints_won":breakpoints_won,
    "double_faults":double_faults,
    "first_serve_points_won":first_serve_points_won,
    "first_serve_successful":first_serve_successful,
    "max_games_in_a_row":max_games_in_a_row,
    "max_points_in_a_row":max_points_in_a_row,
    "points_won":points_won_,
    "points_lost":points_lost_,
    "games_won":games_won_,
    "games_lost":games_lost_,
    "sets_won":sets_won_,
    "sets_lost":sets_lost_,
    "second_serve_points_won":second_serve_points_won,
    "second_serve_successful":second_serve_successful,
    "service_points_lost":service_points_lost,
    "service_points_won":service_points_won,
    "tiebreaks_won":tiebreaks_won,
    "tiebreaks_lost":tiebreaks_lost,
    "total_breakpoints":total_breakpoints,
    "points_spread":points_spread,
    "games_spread":games_spread,
    "sets_spread":sets_spread,
    "breakpoints_allowed":breakpoints_allowed,
    "breakpoints_saved":breakpoints_saved,
    "first_serve_return_points_won":first_serve_return_points_won,
    "first_serve_return_points_total":first_serve_return_points_total,
    "second_serve_return_points_won":second_serve_return_points_won,
    "second_serve_return_points_total":second_serve_return_points_total,
    "set1_win_flag":set1_win_flag_,
    "set2_win_flag":set2_win_flag_,
    "set3_win_flag":set3_win_flag_,
    "set4_win_flag":set4_win_flag_,
    "set5_win_flag":set5_win_flag_,
    "set1_games":set1_games_,
    "set2_games":set2_games_,
    "set3_games":set3_games_,
    "set4_games":set4_games_,
    "set5_games":set5_games_
            })
    
    #merge with sackmann data

    match_stats_df = pd.concat([match_stats_df,pd.read_csv("../data/prep/retro/atp_sackmann.csv")]).sort_values(["match_date","event_id"]).reset_index()

    match_stats_df["first_serve_win_perc"] = 100*match_stats_df["first_serve_points_won"]/match_stats_df["first_serve_successful"]
    match_stats_df["first_serve_return_win_perc"] = 100*match_stats_df["first_serve_return_points_won"]/match_stats_df["first_serve_return_points_total"]
    match_stats_df["second_serve_win_perc"] = 100*(match_stats_df["second_serve_points_won"]/(match_stats_df["second_serve_successful"] + match_stats_df["double_faults"]))
    match_stats_df["second_serve_return_win_perc"] = 100*(match_stats_df["second_serve_return_points_won"]/(match_stats_df["second_serve_return_points_total"]))
    match_stats_df["breakpoint_conversion_perc"] = 100*(match_stats_df["breakpoints_won"]/(match_stats_df["total_breakpoints"]))
    match_stats_df["player_service_points"] = match_stats_df["first_serve_successful"] + match_stats_df["second_serve_successful"] + match_stats_df["double_faults"]
    match_stats_df["player_service_points"] = match_stats_df["first_serve_successful"] + match_stats_df["second_serve_successful"] + match_stats_df["double_faults"]
    match_stats_df["double_faults_perc"] = 100*(match_stats_df["double_faults"]/match_stats_df["player_service_points"])
    match_stats_df["aces_perc"] = 100*(match_stats_df["aces"]/match_stats_df["player_service_points"])
    match_stats_df["aces_allowed_perc"] = 100*(match_stats_df["aces_allowed"]/(match_stats_df["first_serve_return_points_total"]+match_stats_df["second_serve_return_points_total"]))
    match_stats_df["service_game_holds_perc"] = match_stats_df["service_games_held"]/match_stats_df["service_games"]
    match_stats_df["return_games_broke_perc"] = match_stats_df["return_games_broke"]/match_stats_df["return_games"]

    match_stats_df["Month"] = pd.to_datetime(match_stats_df["match_date"]).dt.strftime("%B") + " " + pd.to_datetime(match_stats_df["match_date"]).dt.strftime("%Y")
    match_stats_df["Year"] = pd.to_datetime(match_stats_df["match_date"]).dt.strftime("%Y")

    seasons_df = pd.read_csv("../data/prep/seasons.csv")

    match_stats_df = match_stats_df.merge(seasons_df[["season_id","surface"]],how="left",on="season_id")

    match_stats_df["surface"] = np.where(match_stats_df["surface_x"].isnull(), match_stats_df["surface_y"],match_stats_df["surface_x"])
    match_stats_df.drop(["surface_x","surface_y"],axis=1,inplace=True)

    print("Getting surface from season info")
    for i in tqdm(match_stats_df.index):
        
        #move on if we already know the surface
        if pd.isnull(match_stats_df.loc[i,"surface"]):
            season_id_temp = match_stats_df.loc[i,"season_id"]
            #ignore if data from sackmann (should already have surface)
            if pd.isnull(season_id_temp):
                continue 
            temp_seasons_df = seasons_df[seasons_df.season_id == season_id_temp]
            #if we already know the season, then impute
            if len(temp_seasons_df) > 0:
                assert(temp_seasons_df.shape[0]==1)
                #save durface to match_stats
                match_stats_df.loc[i,"surface"] = temp_seasons_df.surface.iloc[0]
            #otherwise API call and append to master seasons table
            else:
                try:
                    temp_season_info = get_season_info(season_id_temp)
                    temp_df = pd.DataFrame(temp_season_info,index=[season_id_temp]).reset_index().rename({"index":"season_id"},axis=1)
                    seasons_df = pd.concat([seasons_df,temp_df])
                except Exception as e:
                    #cache the data into seasons_df before raising error
                    seasons_df.drop_duplicates().to_csv("../data/prep/seasons.csv",index=False)
                    match_stats_df.to_csv("../data/prep/match_stats.csv")
                    raise Exception(e)

    match_stats_df["surface"] = match_stats_df["surface"].str.lower()   
    match_stats_df["indoors"] = match_stats_df["surface"].str.contains("indoor")       
    match_stats_df["surface"] = np.where(match_stats_df["surface"].str.contains("hard"),"hard",match_stats_df["surface"])
    match_stats_df["surface"] = np.where(match_stats_df["surface"].str.contains("clay"),"clay",match_stats_df["surface"])
    match_stats_df["surface"] = np.where(match_stats_df["surface"].str.contains("grass"),"grass",match_stats_df["surface"])
    match_stats_df["surface"] = np.where(match_stats_df["surface"].str.contains("carpet"),"carpet",match_stats_df["surface"])
    seasons_df.drop_duplicates().to_csv("../data/prep/seasons.csv",index=False)
    write_table(get_engine(), seasons_df.drop_duplicates(), "seasons", index_cols=["season_id"])
    #todo validation asserts to ensure quality (i.e. first_serve_successful >= first_serve_points_won )

    print("data cleanup")
    for i in tqdm(match_stats_df.index):
        if (match_stats_df.loc[i,"second_serve_points_won"] > match_stats_df.loc[i,"second_serve_successful"]) or match_stats_df.loc[i,"second_serve_win_perc"] > 100 or (match_stats_df.loc[i,"second_serve_successful"] + match_stats_df.loc[i,"double_faults"] == 0):
            match_stats_df.loc[i,"second_serve_points_won"] = np.nan
            match_stats_df.loc[i,"second_serve_successful"] = np.nan
            match_stats_df.loc[i,"second_serve_win_perc"] = np.nan

        if match_stats_df.loc[i,"aces_allowed_perc"] > 100:
            match_stats_df.loc[i,"aces_allowed_perc"] = np.nan

        if (match_stats_df.loc[i,"second_serve_return_points_won"] > match_stats_df.loc[i,"second_serve_return_points_total"]) or match_stats_df.loc[i,"second_serve_return_win_perc"] > 100 or match_stats_df.loc[i,"second_serve_return_points_won"] < 0:
            match_stats_df.loc[i,"second_serve_return_points_won"] = np.nan
            match_stats_df.loc[i,"second_serve_return_points_total"] = np.nan
            match_stats_df.loc[i,"second_serve_return_win_perc"] = np.nan

        if match_stats_df.loc[i,"second_serve_successful"] + match_stats_df.loc[i,"double_faults"] == 0:
            match_stats_df.loc[i,"second_serve_points_won"] = np.nan

        if (match_stats_df.loc[i,"first_serve_points_won"] > match_stats_df.loc[i,"first_serve_successful"]) or match_stats_df.loc[i,"first_serve_win_perc"] > 100 or match_stats_df.loc[i,"first_serve_successful"] == 0:
            match_stats_df.loc[i,"first_serve_points_won"] = np.nan
            match_stats_df.loc[i,"first_serve_successful"] = np.nan
            match_stats_df.loc[i,"first_serve_win_perc"] = np.nan
        
        if (match_stats_df.loc[i,"breakpoints_won"] > match_stats_df.loc[i,"total_breakpoints"]) or match_stats_df.loc[i,"breakpoint_conversion_perc"] > 100:
            match_stats_df.loc[i,"breakpoints_won"] = np.nan
            match_stats_df.loc[i,"total_breakpoints"] = np.nan
            match_stats_df.loc[i,"breakpoint_conversion_perc"] = np.nan

    match_stats_df.to_csv("../data/prep/match_stats.csv")
    write_table(get_engine(), match_stats_df, "match_stats",
                index_cols=["player_name", "match_date", "event_id"])

    return match_stats_df

def compute_grouped_player_stats(df,

                          groupby_cols=["player_name"]):
    df_grouped = df.groupby(groupby_cols).agg({"winner_flag":"sum",
            "opponent_id":"count",
            "aces":"sum",
            "aces_allowed":"sum",
            "breakpoints_won":"sum",
            "total_breakpoints":"sum",
            "double_faults":"sum",
            "first_serve_points_won":"sum",
            "first_serve_successful":"sum",
            "second_serve_points_won":"sum",
            "second_serve_successful":"sum",
            "breakpoints_allowed":"sum",
            "breakpoints_saved":"sum",
            "first_serve_return_points_won":"sum",
            "first_serve_return_points_total":"sum",
            "second_serve_return_points_won":"sum",
            "second_serve_return_points_total":"sum",
            "points_won":"sum",
            "points_lost":"sum",
            "points_spread":"sum",
            "games_won":"sum",
            "games_lost":"sum",
            "games_spread":"sum",
            "sets_won":"sum",
            "sets_lost":"sum",
            "sets_spread":"sum",
            "tiebreaks_won":"sum",
            "tiebreaks_lost":"sum"
            }).reset_index().rename({"winner_flag":"total_wins","opponent_id":"total_matches"},axis=1)
    
    df_grouped["FS Win %"] = df_grouped["first_serve_points_won"]/df_grouped["first_serve_successful"]
    df_grouped["SS Win %"] = df_grouped["second_serve_points_won"]/df_grouped["second_serve_successful"]
    df_grouped["BP Conv %"] = df_grouped["breakpoints_won"]/df_grouped["total_breakpoints"]
    df_grouped["Tiebreak Win %"] =  df_grouped["tiebreaks_won"]/(df_grouped["tiebreaks_won"]+df_grouped["tiebreaks_lost"])
    df_grouped["BP Save %"] = df_grouped["breakpoints_saved"]/df_grouped["breakpoints_allowed"]
    df_grouped["FS Return Win %"] = df_grouped["first_serve_return_points_won"]/df_grouped["first_serve_return_points_total"]
    df_grouped["SS Return Win %"] = df_grouped["second_serve_return_points_won"]/df_grouped["second_serve_return_points_total"]
    
    df_grouped["Ace Rank"] = df_grouped["aces"].rank(ascending=False)
    df_grouped["DF Rank"] = df_grouped["double_faults"].rank(ascending=True)
    df_grouped["Total Win Rank"] = df_grouped["total_wins"].rank(ascending=False)
    df_grouped["Point Spread Rank"] = df_grouped["points_spread"].rank(ascending=False)
    df_grouped["FS Win Rank"] = df_grouped["FS Win %"].rank(ascending=False)
    df_grouped["SS Win Rank"] = df_grouped["SS Win %"].rank(ascending=False)
    df_grouped["BP Rank"] = df_grouped["BP Conv %"].rank(ascending=False)
    df_grouped["Mean Ranks"] = df_grouped.loc[:,"Ace Rank":"BP Rank"].mean(axis=1)
    df_grouped["Mean Ranks Ranked"] = df_grouped["Mean Ranks"].rank(ascending=True)
    


    return df_grouped

def get_season_info(season_id):
    season_id = season_id.split(":")[-1]
    url = f"https://api.sportradar.com/tennis/trial/v3/en/seasons/sr%3Aseason%3A{season_id}/info.json"

    headers = {
        "accept": "application/json",
        "x-api-key": API_KEY
    }

    time.sleep(2)
    response_json = requests.get(url, headers=headers).json()
    with open(f"../data/raw/seasons/{season_id}.json", 'w') as json_file:
            json.dump(response_json, json_file, indent=4)     

    try:
        if 'message' in response_json.keys() and response_json['message'] == 'Wrong identifier':
            return {
                "surface": "unknown",
                "complex": "unknown",
                "complex_id": "unknown",
                "number_of_competitors": np.nan,
                "number_of_qualified_competitors": np.nan,
                "number_of_scheduled_matches": np.nan
                }
        season_info = response_json['season']['info']
    except KeyError as e:
        print(season_id)
        print(response_json)
        raise KeyError(e)
    return season_info 


def compute_player_summaries(match_stats_df, min_date, max_date):
    print("Computing player summaries")

    atp_player_summary_overall_df = compute_grouped_player_stats(match_stats_df[match_stats_df["competition_category"].isin(['ATP','United Cup'])], groupby_cols=["player_name","Year"])
    atp_player_summary_monthly_df = compute_grouped_player_stats(match_stats_df[match_stats_df["competition_category"].isin(['ATP','United Cup'])], groupby_cols=["player_name","Month"])

    wta_player_summary_overall_df = compute_grouped_player_stats(match_stats_df[match_stats_df["competition_category"].isin(['WTA','United Cup'])], groupby_cols=["player_name","Year"])
    wta_player_summary_monthly_df = compute_grouped_player_stats(match_stats_df[match_stats_df["competition_category"].isin(['WTA','United Cup'])], groupby_cols=["player_name","Month"])
            

    atp_player_summary_overall_df["last_refreshed"] = max_date
    atp_player_summary_monthly_df["last_refreshed"] = max_date

    wta_player_summary_overall_df["last_refreshed"] = max_date
    wta_player_summary_monthly_df["last_refreshed"] = max_date

    
    

    atp_player_summary_overall_df.to_csv("../data/prep/atp_player_yearly_summary.csv")
    atp_player_summary_monthly_df.to_csv("../data/prep/atp_player_monthly_summary.csv")
    wta_player_summary_overall_df.to_csv("../data/prep/wta_player_yearly_summary.csv")
    wta_player_summary_monthly_df.to_csv("../data/prep/wta_player_monthly_summary.csv")

    engine = get_engine()
    write_table(engine, atp_player_summary_overall_df, "atp_player_yearly_summary", index_cols=["player_name", "year"])
    write_table(engine, atp_player_summary_monthly_df, "atp_player_monthly_summary", index_cols=["player_name", "month"])
    write_table(engine, wta_player_summary_overall_df, "wta_player_yearly_summary", index_cols=["player_name", "year"])
    write_table(engine, wta_player_summary_monthly_df, "wta_player_monthly_summary", index_cols=["player_name", "month"])


def refresh_fantasy_data(fantasy_month):

    fantasy_cols = ["player_name",
    "total_wins",
    "aces",
    "breakpoints_won",
    "total_breakpoints",
    "double_faults",
    "first_serve_points_won",
    "first_serve_successful",
    "second_serve_points_won",
    "second_serve_successful",
    "points_spread",
    "FS Win %",
    "SS Win %",
    "BP Conv %",
    "Ace Rank",
    "DF Rank",
    "Total Win Rank",
    "Point Spread Rank",
    "FS Win Rank",
    "SS Win Rank",
    "BP Rank",
    "Mean Ranks",
    "Mean Ranks Ranked",
    "Month",
    "last_refreshed"]

    atp_fantasy_data = pd.read_csv("../data/prep/atp_player_monthly_summary.csv")
    atp_fantasy_data = atp_fantasy_data.loc[atp_fantasy_data.Month == fantasy_month,fantasy_cols]
    wta_fantasy_data = pd.read_csv("../data/prep/wta_player_monthly_summary.csv")
    wta_fantasy_data = wta_fantasy_data.loc[wta_fantasy_data.Month == fantasy_month,fantasy_cols]


    print(atp_fantasy_data.shape)
    atp_fantasy_data.to_csv("../data/fantasy/atp_player_summary.csv")
    wta_fantasy_data.to_csv("../data/fantasy/wta_player_summary.csv")

    engine = get_engine()
    write_table(engine, atp_fantasy_data, "atp_fantasy_summary", index_cols=["player_name", "month"])
    write_table(engine, wta_fantasy_data, "wta_fantasy_summary", index_cols=["player_name", "month"])


if __name__ == "__main__":

    #refresh match_stats
    min_date,max_date = "2025-01-01",str(date.today())

    fantasy_month = "February 2026"

    num_days_prev = int(sys.argv[1])
    if num_days_prev > 0:
        #refresh data for last two days just in case
        print(f"Refreshing daily summary data from API for last {num_days_prev} days")
        get_tennis_daily_summary_range(str(date.today() - timedelta(days=num_days_prev)),max_date)

    
    match_stats_df = refresh_match_stats_df(min_date,max_date)

    compute_player_summaries(match_stats_df, min_date, max_date)

    refresh_fantasy_data(fantasy_month)

    
                            