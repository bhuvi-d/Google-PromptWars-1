VENUE_GRAPH = {
    "entrance_north": { 
        "concourse_west": {"weight": 5, "stairs": False, "outdoor": True}, 
        "concourse_east": {"weight": 5, "stairs": False, "outdoor": True}
    },
    "entrance_south": { 
        "concourse_west": {"weight": 5, "stairs": False, "outdoor": True}, 
        "concourse_east": {"weight": 5, "stairs": False, "outdoor": True}
    },
    "concourse_west": { 
        "entrance_north": {"weight": 5, "stairs": False, "outdoor": True}, 
        "entrance_south": {"weight": 5, "stairs": False, "outdoor": True},
        "food_court_1": {"weight": 2, "stairs": False, "outdoor": False},
        "restroom_1": {"weight": 3, "stairs": False, "outdoor": False},
        "seating_section_a": {"weight": 4, "stairs": True, "outdoor": False},
        "seating_section_b": {"weight": 5, "stairs": True, "outdoor": False},
        "emergency_exit_west": {"weight": 1, "stairs": False, "outdoor": False},
        "trophy_room": {"weight": 3, "stairs": False, "outdoor": False},
        "merch_store_1": {"weight": 2, "stairs": False, "outdoor": False}
    },
    "concourse_east": { 
        "entrance_north": {"weight": 5, "stairs": False, "outdoor": True}, 
        "entrance_south": {"weight": 5, "stairs": False, "outdoor": True},
        "food_court_2": {"weight": 2, "stairs": False, "outdoor": False},
        "restroom_2": {"weight": 3, "stairs": False, "outdoor": False},
        "seating_section_c": {"weight": 4, "stairs": True, "outdoor": False},
        "seating_section_d": {"weight": 5, "stairs": True, "outdoor": False},
        "emergency_exit_east": {"weight": 1, "stairs": False, "outdoor": False},
        "fan_zone": {"weight": 3, "stairs": False, "outdoor": True},
        "merch_store_2": {"weight": 2, "stairs": False, "outdoor": False}
    },
    "trophy_room": {
        "concourse_west": {"weight": 3, "stairs": False, "outdoor": False},
        "seating_section_a": {"weight": 4, "stairs": False, "outdoor": False}
    },
    "fan_zone": {
        "concourse_east": {"weight": 3, "stairs": False, "outdoor": True},
        "seating_section_c": {"weight": 4, "stairs": False, "outdoor": False}
    },
    "food_court_1": {"concourse_west": {"weight": 2, "stairs": False, "outdoor": False}},
    "restroom_1": {"concourse_west": {"weight": 3, "stairs": False, "outdoor": False}},
    "seating_section_a": {"concourse_west": {"weight": 4, "stairs": True, "outdoor": False}, "trophy_room": {"weight": 4, "stairs": False, "outdoor": False}},
    "seating_section_b": {"concourse_west": {"weight": 5, "stairs": True, "outdoor": False}},
    "food_court_2": {"concourse_east": {"weight": 2, "stairs": False, "outdoor": False}},
    "restroom_2": {"concourse_east": {"weight": 3, "stairs": False, "outdoor": False}},
    "seating_section_c": {"concourse_east": {"weight": 4, "stairs": True, "outdoor": False}, "fan_zone": {"weight": 4, "stairs": False, "outdoor": False}},
    "seating_section_d": {"concourse_east": {"weight": 5, "stairs": True, "outdoor": False}},
    "emergency_exit_west": {"concourse_west": {"weight": 1, "stairs": False, "outdoor": False}},
    "emergency_exit_east": {"concourse_east": {"weight": 1, "stairs": False, "outdoor": False}},
    "merch_store_1": {"concourse_west": {"weight": 2, "stairs": False, "outdoor": False}},
    "merch_store_2": {"concourse_east": {"weight": 2, "stairs": False, "outdoor": False}}
}

SCENIC_NODES = ["trophy_room", "fan_zone", "merch_store_1", "merch_store_2"]
FOOD_NODES = ["food_court_1", "food_court_2"]
RESTROOM_NODES = ["restroom_1", "restroom_2"]
EXIT_NODES = ["entrance_north", "entrance_south", "emergency_exit_west", "emergency_exit_east"]
MERCH_NODES = ["merch_store_1", "merch_store_2"]
