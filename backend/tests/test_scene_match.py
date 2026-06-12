"""Scene background matching — varied bg_path per node."""

from __future__ import annotations

from models import GamePack, StoryNode
from scene_match import (
    _load_registry,
    assign_node_backgrounds,
    build_search_text,
    extract_story_context,
    resolve_scene,
)


def test_registry_has_300_plus_scenes():
    _load_registry.cache_clear()
    scenes, _, _, _ = _load_registry()
    assert len(scenes) >= 300


def test_resolve_varies_by_prompt():
    a_id, _, _ = resolve_scene(
        mood="neutral",
        style="campus",
        image_prompt="school cafeteria lunch empty",
        title="食堂",
        node_id="n1",
    )
    b_id, _, _ = resolve_scene(
        mood="neutral",
        style="campus",
        image_prompt="exam hall silent desks",
        title="考场",
        node_id="n2",
    )
    assert a_id != b_id
    assert a_id == "cafeteria_serving"
    assert b_id == "exam_hall_silent"


def test_pool_fallback_varies_by_node_id():
    a_id, a_path, _ = resolve_scene(style="urban_romance", mood="neutral", node_id="node_a")
    b_id, b_path, _ = resolve_scene(style="urban_romance", mood="neutral", node_id="node_b")
    assert a_path and b_path
    assert a_id != b_id or a_path != b_path


def test_assign_node_backgrounds_on_pack():
    nodes = {
        "a": StoryNode(
            id="a",
            title="皇宫大殿",
            mood="neutral",
            image_prompt="imperial palace throne hall empty",
            scene_type="climax",
        ),
        "b": StoryNode(
            id="b",
            title="太平间",
            mood="dark_mystery",
            image_prompt="morgue corridor fluorescent",
            scene_type="buildup",
        ),
        "c": StoryNode(
            id="c",
            title="过渡",
            mood="neutral",
            image_prompt="",
            scene_type="interlude",
        ),
    }
    assign_node_backgrounds(nodes, "mystery")
    paths = {n.bg_path for n in nodes.values()}
    assert len(paths) >= 2
    assert all(p.startswith("images/scenes/") for p in paths)
    assert nodes["a"].scene_id
    assert nodes["b"].scene_id


def test_necklace_ball_resolves_wedding_banquet_hall():
    _load_registry.cache_clear()
    scene_id, path, _ = resolve_scene(
        style="period_fiction",
        mood="romantic",
        title="部长家的舞会",
        image_prompt="19th century ballroom chandeliers empty hall",
        lines=[{"text": "她戴着借来的项链，走进宴会厅。"}],
        node_id="necklace_ball",
    )
    assert scene_id == "wedding_banquet_hall"
    assert path.endswith("wedding_banquet_hall.png")


def test_necklace_home_resolves_modest_apartment():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        style="period_fiction",
        mood="sad",
        title="寒舍",
        image_prompt="modest apartment bedroom mirror candlelight",
        lines=[{"text": "回到公寓，她对着卧室镜子发呆。"}],
        node_id="necklace_home",
    )
    assert scene_id in {
        "apartment_bedroom",
        "candlelit_room",
        "insomnia_rental",
        "empress_unveil_night",
        "empress_bedchamber_empty",
    }


def test_necklace_pawn_resolves_pawnshop():
    _load_registry.cache_clear()
    scene_id, path, _ = resolve_scene(
        style="period_fiction",
        mood="tense",
        title="当铺",
        image_prompt="pawnshop counter necklace debt repayment",
        lines=[{"text": "她把项链押在当铺柜台上，换钱还债。"}],
        node_id="necklace_pawn",
    )
    assert scene_id == "pawnshop_ancient"
    assert path.endswith("pawnshop_ancient.png")


def test_charity_gala_alias_maps_to_wedding_banquet():
    _load_registry.cache_clear()
    scene_id, path, _ = resolve_scene(
        style="period_fiction",
        mood="neutral",
        image_prompt="charity gala ballroom victorian banquet",
        node_id="alias_test",
    )
    assert scene_id == "wedding_banquet_hall"
    assert "wedding_banquet_hall" in path


def test_consecutive_same_bg_is_penalized():
    _load_registry.cache_clear()
    _, path1, _ = resolve_scene(
        style="period_fiction",
        title="舞会",
        image_prompt="ballroom gala chandeliers",
        node_id="seq_a",
    )
    scene_id2, path2, _ = resolve_scene(
        style="period_fiction",
        title="宴会",
        image_prompt="banquet hall dance floor",
        node_id="seq_b",
        avoid_paths=frozenset({path1}),
    )
    assert path2 != path1


def test_parse_nodes_assigns_backgrounds():
    raw = {
        "title": "test",
        "start_node_id": "start",
        "nodes": {
            "start": {
                "id": "start",
                "title": "cafe",
                "mood": "neon_rain",
                "image_prompt": "rainy cafe neon city night",
                "lines": [{"speaker": "旁白", "text": "雨夜。", "portrait": "none"}],
                "after_lines_next": "end",
                "choices": [],
                "is_ending": False,
            },
            "end": {
                "id": "end",
                "title": "sunset beach",
                "mood": "golden_dawn",
                "image_prompt": "beach sunset empty shore",
                "lines": [{"speaker": "旁白", "text": "完。", "portrait": "none"}],
                "after_lines_next": "",
                "choices": [],
                "is_ending": True,
                "ending_type": "good",
            },
        },
    }
    from narrative_service import _parse_nodes

    pack = _parse_nodes(raw, "urban_romance")
    bg_paths = {n.bg_path for n in pack.nodes.values()}
    assert len(bg_paths) == 2
    assert all(n.bg_path for n in pack.nodes.values())


def test_necklace_ballroom_not_city_lights():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        mood="romantic",
        style="urban_romance",
        title="部长府舞会",
        image_prompt="19th century Paris ballroom gala chandeliers empty",
        lines=[
            {"speaker": "旁白", "text": "舞厅里水晶灯闪烁，她戴着借来的项链。", "portrait": "none"},
        ],
        setting="十九世纪巴黎",
        node_id="ball",
    )
    assert scene_id in {"charity_gala", "wedding_banquet_hall", "imperial_palace_hall"}
    assert scene_id not in {"city_lights", "rainy_street", "cyber_city_rain", "subway_night"}


def test_necklace_modest_apartment_from_lines():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        mood="sad",
        style="urban_romance",
        title="寒舍",
        image_prompt="modest Paris apartment interior candlelight",
        lines=[
            {"speaker": "旁白", "text": "他们回到简陋的公寓，桌上只有面包和黄油。", "portrait": "none"},
        ],
        setting="1880s Paris working-class flat",
        node_id="home",
    )
    assert scene_id in {
        "apartment_bedroom",
        "insomnia_rental",
        "candlelit_room",
        "indoor_warm",
        "landlord_doorway",
        "family_dining",
        "apartment_living",
        "old_apartment_stairwell",
        "candle_room",
    }
    assert scene_id not in {"city_lights", "rainy_street", "old_town_bridge_rain"}


def test_necklace_pawnshop_from_lines():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        mood="tense",
        style="urban_romance",
        title="当铺",
        image_prompt="ancient pawnshop interior counter empty",
        lines=[
            {"speaker": "旁白", "text": "他们走进昏暗的当铺，要把赝品项链赎回来。", "portrait": "none"},
        ],
        setting="十九世纪巴黎",
        node_id="pawn",
    )
    assert scene_id in {"pawnshop_ancient", "pawnshop_alley_night"}
    assert scene_id not in {"city_lights", "wedding_banquet_hall"}


def test_necklace_jewelry_counter():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        mood="tense",
        style="urban_romance",
        title="项链",
        image_prompt="jewelry shop counter diamond necklace display",
        lines=[{"speaker": "旁白", "text": "她借来那条钻石项链，在镜前端详。", "portrait": "none"}],
        node_id="jewelry",
    )
    assert scene_id in {"luxury_counter", "auction_booth", "empress_bedchamber_empty", "empress_unveil_night"}


def test_necklace_paris_street():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        mood="neutral",
        style="urban_romance",
        title="巴黎街景",
        image_prompt="19th century Paris street boulevard empty",
        lines=[{"speaker": "旁白", "text": "他们沿着塞纳河畔的街道走去。", "portrait": "none"}],
        setting="Paris 19th century",
        node_id="street",
    )
    assert scene_id in {
        "old_town_bridge_rain",
        "canal_ancient_night",
        "clock_tower",
        "market_alley",
        "canal_twilight",
        "old_hometown_street",
    }
    assert scene_id not in {"city_lights", "subway_night"}


def test_consecutive_nodes_avoid_same_bg_path():
    _load_registry.cache_clear()
    nodes = {
        "ball": StoryNode(
            id="ball",
            title="舞会",
            mood="romantic",
            image_prompt="Paris ballroom gala empty hall chandeliers",
            lines=[{"speaker": "旁白", "text": "舞会上人人盛装出席。", "portrait": "none"}],
            scene_type="climax",
        ),
        "mirror": StoryNode(
            id="mirror",
            title="镜前",
            mood="tense",
            image_prompt="dressing room mirror candlelight necklace",
            lines=[{"speaker": "旁白", "text": "她在镜子前整理项链。", "portrait": "none"}],
            scene_type="buildup",
        ),
        "street": StoryNode(
            id="street",
            title="归途",
            mood="sad",
            image_prompt="rainy Paris street night empty",
            lines=[{"speaker": "旁白", "text": "他们匆匆离开巴黎的街道。", "portrait": "none"}],
            scene_type="resolution",
        ),
    }
    assign_node_backgrounds(
        nodes,
        "urban_romance",
        setting="十九世纪巴黎，莫泊桑《项链》",
    )
    paths = [nodes[k].bg_path for k in ("ball", "mirror", "street")]
    assert all(p.startswith("images/scenes/") for p in paths)
    assert len(set(paths)) == 3


def test_build_search_text_includes_lines_and_setting():
    blob = build_search_text(
        title="舞会",
        image_prompt="ballroom",
        lines=[{"text": "钻石项链在灯下闪光"}],
        setting="十九世纪巴黎",
    )
    assert "舞会" in blob
    assert "钻石项链" in blob
    assert "十九世纪巴黎" in blob


PERIOD_SCENES = frozenset(
    {
        "wedding_banquet_hall",
        "pawnshop_ancient",
        "pawnshop_alley_night",
        "charity_gala",
        "tribute_gift_hall",
        "clock_tower",
        "old_town_bridge_rain",
        "canal_ancient_night",
        "luxury_counter",
        "candlelit_room",
    }
)


def test_campus_classroom_not_period_ballroom():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        style="campus",
        mood="neutral",
        title="教室",
        image_prompt="午后教室阳光",
        lines=[{"text": "她在教室里偷偷看手机，窗外是操场。"}],
        node_id="campus_class",
    )
    assert scene_id in {"classroom_drowse", "blackout_study_hall", "school_corridor", "campus_field"}
    assert scene_id not in PERIOD_SCENES


def test_campus_sports_field_not_wedding_hall():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        style="campus",
        mood="hopeful",
        title="操场",
        image_prompt="校园操场篮球",
        lines=[{"text": "体育课在操场上打篮球，烈日当空。"}],
        node_id="campus_sports",
    )
    assert scene_id in {"sunny_basketball", "campus_field", "sports_parade"}
    assert scene_id not in PERIOD_SCENES


def test_xianxia_cave_not_pawnshop():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        style="xianxia",
        mood="mysterious",
        title="洞府",
        image_prompt="仙山云海洞府",
        lines=[{"text": "修士在洞天福地打坐，灵泉潺潺。"}],
        node_id="xianxia_cave",
    )
    assert scene_id in {
        "hidden_valley_spring",
        "jade_pool_meditation",
        "xianxia_peaks",
        "cave_glow",
        "hot_spring_mist",
        "cloud_sea_stairway",
    }
    assert scene_id not in PERIOD_SCENES


def test_ceo_office_elevator_not_period():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        style="urban_romance",
        mood="tense",
        title="总裁办公室",
        image_prompt="高层办公室格子间",
        lines=[{"text": "深夜总裁在电梯里与她对视，写字楼灯火通明。"}],
        node_id="ceo_office",
    )
    assert scene_id in {
        "ceo_elevator",
        "office_midnight",
        "tense_meeting",
        "meeting_room_glass",
        "open_office",
        "apartment_elevator",
    }
    assert scene_id not in PERIOD_SCENES


def test_horror_abandoned_hospital_not_ballroom():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        style="mystery",
        mood="dark_mystery",
        title="废弃医院",
        image_prompt="荒废医院走廊",
        lines=[{"text": "深夜走进废弃的医院大厅，诡异的风从走廊吹来。"}],
        node_id="horror_hosp",
    )
    assert scene_id in {
        "abandoned_hospital",
        "hospital_hall",
        "hospital_er_waiting",
        "er_waiting_room",
        "morgue_corridor_blue",
        "hospital_blood_elevator",
        "mystery_fog",
    }
    assert scene_id not in PERIOD_SCENES


def test_horror_mirror_prefers_haunted_not_empress():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        style="mystery",
        mood="dark_mystery",
        title="鬼镜",
        image_prompt="老宅镜子",
        lines=[{"text": "鬼宅楼梯间的镜子泛着绿光，她看到诡异倒影。"}],
        node_id="horror_mirror",
    )
    assert scene_id in {"haunted_mansion_stair", "ghost_mansion", "haunted_toilet_crack"}
    assert scene_id not in {"empress_unveil_night", "empress_bedchamber_empty", "wedding_banquet_hall"}


def test_cyber_city_not_wedding_hall():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        style="urban_romance",
        mood="neon_rain",
        title="赛博雨夜",
        image_prompt="霓虹雨夜黑客城",
        lines=[{"text": "赛博朋克城市的霓虹雨夜，义肢客在巷口。"}],
        node_id="cyber_rain",
    )
    assert scene_id in {"cyber_city_rain", "cyberpunk_alley_gun", "rainy_street", "city_lights"}
    assert scene_id not in PERIOD_SCENES


def test_scifi_space_station_pool():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        style="scifi",
        mood="neutral",
        title="空间站",
        image_prompt="太空星窗",
        lines=[{"text": "透过空间站舷窗望向星球。"}],
        node_id="scifi_orbit",
    )
    assert scene_id in {
        "space_station_window",
        "mars_base_dome",
        "observatory",
        "ai_data_core",
        "warship_planet_burst",
    }
    assert scene_id not in PERIOD_SCENES


def test_rural_hometown_not_paris_street():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        style="urban_romance",
        mood="hopeful",
        title="故乡",
        image_prompt="老家乡村",
        lines=[{"text": "回到故乡的老街，爷爷奶奶在院子里等着。"}],
        node_id="rural_home",
    )
    assert scene_id in {"old_hometown_street", "grandparents_yard", "village_dusk", "rice_terraces"}
    assert scene_id not in PERIOD_SCENES


def test_modern_paris_apartment_not_period_fiction():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        style="urban_romance",
        mood="romantic",
        title="巴黎公寓",
        image_prompt="现代公寓梳妆",
        lines=[{"text": "他们在现代巴黎的公寓里，她对着镜子化妆。"}],
        setting="现代巴黎",
        node_id="modern_paris",
    )
    assert scene_id in {
        "apartment_bedroom",
        "apartment_living",
        "apartment_elevator",
        "romance_cafe",
        "balcony_night",
        "city_lights",
    }
    assert scene_id not in PERIOD_SCENES


def test_campus_street_walk_not_european_bridge():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        style="campus",
        mood="neutral",
        title="归途",
        image_prompt="放学街道",
        lines=[{"text": "沿着街道步行回家，书包晃晃悠悠。"}],
        node_id="campus_walk",
    )
    assert scene_id not in {
        "old_town_bridge_rain",
        "canal_ancient_night",
        "clock_tower",
        "wedding_banquet_hall",
    }
    assert scene_id in {
        "school_corridor",
        "campus_field",
        "classroom_drowse",
        "snack_shop_rush",
        "school_gate_rain",
        "rainy_street",
        "city_lights",
        "indoor_warm",
    }


def test_europe_travel_not_period_street():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        style="urban_romance",
        mood="romantic",
        title="欧洲旅行",
        image_prompt="欧洲城市散步",
        lines=[{"text": "他们在欧洲旅行，沿着街道散步。"}],
        node_id="europe_trip",
    )
    assert scene_id not in PERIOD_SCENES


def test_extract_story_context_doubles_setting_keywords():
    setting, era = extract_story_context(
        setting="现代大学校园",
        synopsis="青春恋爱物语",
        tone="治愈",
        themes=["暗恋", "毕业季"],
    )
    assert "校园" in setting
    assert "青春恋爱物语" in setting


def test_campus_sparse_node_uses_campus_pool_not_city_lights():
    _load_registry.cache_clear()
    scene_id, _, reason = resolve_scene(
        style="campus",
        mood="neutral",
        title="过渡",
        setting="现代大学校园青春恋爱",
        node_id="campus_sparse_1",
    )
    assert scene_id != "city_lights"
    assert scene_id in {
        "campus_field",
        "school_corridor",
        "classroom_drowse",
        "library_aisle",
        "cafeteria_serving",
        "exam_hall_silent",
        "blackout_study_hall",
        "dormitory_hallway_night",
    } or reason.startswith("keyword:")


def test_period_setting_sparse_not_city_lights():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        style="urban_romance",
        mood="neutral",
        title="场景",
        setting="十九世纪巴黎，莫泊桑《项链》寒舍公寓",
        node_id="period_sparse_1",
    )
    assert scene_id not in {"city_lights", "subway_night", "cyber_city_rain"}


def test_xianxia_setting_sparse_not_city_lights():
    _load_registry.cache_clear()
    scene_id, _, _ = resolve_scene(
        style="xianxia",
        mood="mysterious",
        title="过渡",
        setting="仙侠修仙山门云海",
        node_id="xianxia_sparse_1",
    )
    assert scene_id not in {"city_lights", "subway_night", "rainy_street"}
    assert scene_id in {
        "xianxia_peaks",
        "pagoda_mist",
        "jianghu_inn",
        "bamboo_grove",
        "shrine_path",
        "cloud_sea_stairway",
        "lotus_pond_dawn",
        "ancient_inn_courtyard",
        "sect_arena",
        "hot_spring_mist",
    }
