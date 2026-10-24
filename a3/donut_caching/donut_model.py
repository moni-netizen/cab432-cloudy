from __future__ import annotations
import json

def get_pie_history(result: list) -> list:
    ## you have to write something for if its empty
    if not result:
        return []

    game_names = []
    play_times = []
    for game in result:
        game_name = game.get("name","")
        game_names.append(game_name)
        play_time = game.get("playtime_forever", "")
        play_times.append(play_time)

    # after this, filter for top 6 games, and group 7 and onwards as "other"
    # 1. reorder the lists in descending order. apply to names and times
    order = sorted(range(len(play_times)), key=lambda i: play_times[i], reverse=True)
    sorted_times = [play_times[i] for i in order]   
    sorted_names = [game_names[i] for i in order] 

    # 2. get top 6 times and other. same for names!
    top_n = 6

    top_n_times = sorted_times[:top_n]
    other_times = sum(sorted_times[top_n:])
    top_n_times.append(other_times)

    sorted_names = sorted_names[:top_n]
    sorted_names.append("Other")

    # 3. hooray return
    return [sorted_names, top_n_times]

def get_pie_ltw(result: list) -> list:
    if not result:
        return []

    game_names = []
    play_times = []
    for game in result:
        game_name = game.get("name","")
        game_names.append(game_name)
        play_time = game.get("playtime_2weeks", 0)
        play_times.append(play_time)
    
    # 1. reorder the lists in descending order. apply to names and times
    order = sorted(range(len(play_times)), key=lambda i: play_times[i], reverse=True)
    sorted_times = [play_times[i] for i in order]   
    sorted_names = [game_names[i] for i in order] 

    # 2. get top 6 times and other. same for names!
    top_n = 6

    top_n_times = sorted_times[:top_n]
    other_times = sum(sorted_times[top_n:])
    top_n_times.append(other_times)

    sorted_names = sorted_names[:top_n]
    sorted_names.append("Other")

    # 3. hooray return
    return [sorted_names, top_n_times]
   
