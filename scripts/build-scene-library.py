#!/usr/bin/env python3
"""Merge generic + narrative scenes into scene-prompts.json and keyword map."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
STYLE = json.loads((SCRIPTS / "art-style.json").read_text(encoding="utf-8"))
PREFIX = STYLE["style_prefix"]

# id, english scene description, zh keywords (comma-separated), png archetype fallback
NARRATIVE: list[tuple[str, str, str, str]] = [
    # 校园 1-15
    ("classroom_drowse", "sleepy humid afternoon Japanese classroom, teacher at blackboard, student hiding behind tall textbook stack secretly reading phone, warm sunbeams", "催眠,午后,课堂,教室,偷偷,手机", "school_corridor"),
    ("snack_shop_rush", "crowded school snack shop rush after bell, students squeezing in for grilled sausage and iced drinks, energetic chaos", "小卖部,下课,烤肠,饮料,冲刺", "campus_field"),
    ("hallway_rainstorm", "school building entrance hall during sudden downpour, students sheltering, wet courtyard visible, hesitant shared umbrella moment", "穿堂,骤雨,避雨,共撑伞,教学楼", "rainy_street"),
    ("sunny_basketball", "school sports field under blazing sun, boys playing basketball, girls under tree shade holding water bottle, youth romance mood", "篮球,体育课,烈日,操场,矿泉水", "campus_field"),
    ("sunset_duty", "empty classroom at golden hour after school, long desk shadows, lone student sweeping floor, volleyball sounds outside window", "值日,放学,斜阳,扫帚,教室", "school_corridor"),
    ("rooftop_secret", "school rooftop behind rusty door, two figures leaning on railing, secret talk or confession, overcast sky", "天台,告白,不良,抽烟,秘密", "rooftop_sky"),
    ("blackout_study_hall", "evening self-study classroom plunged into sudden darkness, students cheering, silhouettes in moonlit windows", "晚自习,停电,黑暗,欢呼,教室", "school_corridor"),
    ("corridor_punishment", "student punished standing in hallway outside classroom window, watching classmates inside, wry smile with friend", "罚站,走廊,迟到,窗口", "school_corridor"),
    ("exam_rank_board", "exam results bulletin board crowded with anxious students, someone gasping at top rank, another clutching paper in back", "红榜,排名,期末,成绩,布告栏", "school_corridor"),
    ("infirmary_curtain", "school infirmary with white bed curtain, antiseptic smell, resting student hears gossip whisper beyond curtain", "医务室,床帘,来苏水,八卦", "hospital_hall"),
    ("sports_parade", "school sports day opening parade, class formation passing review stand, girl holding class sign, crowd whispering", "运动会,方阵,举牌,检阅", "campus_field"),
    ("library_window_nap", "quiet library corner by window, dappled leaf sunlight on books, girl napping, boy gently closing curtain", "图书馆,靠窗,打盹,窗帘,午后", "library_aisle"),
    ("grad_backstage", "chaotic graduation party backstage, costumes and stage call lights, emotional farewell behind prop curtain", "毕业晚会,后台,告别,幕布", "school_corridor"),
    ("cafeteria_serving", "long cafeteria queue, server shaking ladle so meat falls back into tray, disappointed student at window", "食堂,打饭,阿姨,肉,排队", "school_corridor"),
    ("netcafe_allnight", "dim smoky internet cafe booth at night, roommates gaming side by side, monitor glow on excited faces", "网吧,通宵,开黑,泡面,室友", "city_lights"),
    # 都市 16-35
    ("crowded_subway", "packed rush hour subway, bodies pressed together, awkward foot step on businessman's shoe as train sways", "地铁,早高峰,拥挤,沙丁鱼", "subway_night"),
    ("office_midnight", "only lit office floor at 2am, rejected proposal drafts, cold takeout boxes, frantic keyboard typing", "格子间,凌晨,加班,方案,外卖", "city_lights"),
    ("tense_meeting", "frozen corporate boardroom, angry boss slamming table, managers heads down barely breathing", "会议室,老板,训斥,高层", "indoor_warm"),
    ("pantry_gossip", "office pantry coffee machine humming, two employees whispering corporate politics and scandal", "茶水间,八卦,咖啡,人事", "indoor_warm"),
    ("storm_no_ride", "stormy crossroads, ride app showing 300 queue, soaked protagonist watching taxi splash mud away", "暴雨,打车,排队,湿透", "rainy_street"),
    ("blind_date_restaurant", "upscale restaurant blind date, partner cutting steak while interrogating about salary and property", "相亲,西餐厅,牛排,年薪", "romance_cafe"),
    ("late_bbq_street", "neon dim late night street BBQ stall, office workers drinking skewers venting about bosses and life", "烧烤,深夜,撸串,社畜", "night_bazaar"),
    ("bar_booth_drink", "loud bar with flashing lights, lonely figure in corner booth drinking shot after shot", "酒吧,卡座,借酒,消愁", "city_lights"),
    ("er_waiting_room", "3am emergency room waiting bench, pale face holding bills, gurney wheels echoing in corridor", "急诊,凌晨,缴费,医院", "hospital_hall"),
    ("insomnia_rental", "tiny rental apartment bed at night, phone glow on anxious sleepless face, unread messages", "失眠,出租屋,深夜,手机", "balcony_night"),
    ("luxury_counter", "luxury boutique counter, snobbish clerk sizing up plain clothes customer until black card appears", "奢侈品,柜台,导购,黑卡", "city_lights"),
    ("police_mediation", "bright police mediation room, families shouting across table, officer slamming desk demanding silence", "派出所,调解,对骂,民警", "indoor_warm"),
    ("hotel_hangover", "presidential suite morning hangover, silk sheets, stranger's hand from blanket, splitting headache", "总统套房,宿醉,酒店,清晨", "indoor_warm"),
    ("parking_ambush", "dim underground parking, unlock beep, masked figures with iron bars emerging from pillars", "停车场,伏击,地下,黑衣人", "mystery_fog"),
    ("charity_gala", "glittering charity ball center stage, protagonist in borrowed gown alone in corner watching hypocrisy", "慈善晚宴,宴会,礼服,角落", "city_lights"),
    ("landlord_rent", " shabby rental iron door hammered from outside, landlady shouting overdue rent through door", "房东,催租,砸门,出租屋", "indoor_warm"),
    ("newyear_crowd", "new year countdown plaza crush, balloons rising, lovers separated in crowd at ten second mark", "跨年,广场,倒计时,失散", "lantern_festival"),
    ("ceo_elevator", "private CEO elevator ascending fast, only two people breathing close in tight space, tension", "总裁,电梯,暧昧,呼吸", "indoor_warm"),
    ("wet_market_haggle", "wet noisy outdoor market stall, haggling over cilantro price in dialect, humble protagonist", "菜市场,砍价,香菜,市井", "market_alley"),
    ("bank_vip_room", "elegant bank VIP lounge, branch manager bowing pouring tea presenting premium wealth plan", "银行,VIP,贵宾,理财", "indoor_warm"),
    # 玄幻 36-60
    ("sect_arena", "xianxia sect tournament on blue stone arena, crowd mocking, lone hero preparing to challenge genius", "家族大比,擂台,宗门,天才", "xianxia_peaks"),
    ("hall_disciple_fight", "grand sect hall smoke and gold, white-haired elders fighting over taking protagonist as disciple", "宗门大殿,长老,收徒", "pagoda_mist"),
    ("mist_beast_forest", "poison mist ancient forest, giant beast crushing trees, protagonist hiding in bushes holding breath", "迷雾,巨兽,森林,秘境", "mystery_fog"),
    ("tomb_wall_script", "deep ancient tomb torchlight on carved wall revealing lost supreme cultivation manual", "古墓,功法,石壁,火把", "cave_glow"),
    ("tribulation_peak", "lonely peak under swirling purple thundercloud vortex, cultivator bare chest meditating for ninth lightning tribulation", "渡劫,雷云,孤峰,紫霄", "thunder_field"),
    ("auction_booth", "treasure pavilion crystal VIP booth, calm bidder pressing bell driving rival to ruin", "拍卖行,包厢,竞价", "indoor_warm"),
    ("black_market_stall", "underground black market corner stall junk pile, system alert vibrating as protagonist stops", "黑市,捡漏,地摊,外挂", "night_bazaar"),
    ("hot_spring_mist", "spiritual hot spring mist peach petals, clothes folded on bank, accidental encounter with saintess cultivating", "寒潭,温泉,沐浴,圣女", "hot_spring"),
    ("library_sweeping_monk", "scripture pavilion bottom floor dusty corner, old sweeping monk speaks one line solving cultivation bottleneck", "藏经阁,扫地,老僧,点化", "library_aisle"),
    ("trial_tower_99", "sect trial tower 99th floor collapsing void, bones creaking under hundredfold gravity last step", "试炼塔,重力,突破", "xianxia_peaks"),
    ("sand_battlefield", "yellow sand frontier two armies of cultivators banners blocking sun, killing intent warping space", "黄沙,战场,两军,修士", "desert_oasis"),
    ("jianghu_inn", "misty Jiangnan xianxia inn, travelers drinking, hooded table plotting ambush tonight", "客栈,江湖,密谋,烟雨", "tea_house"),
    ("cliff_leap", "desperate cliff edge villains closing in, bloodied hero smirks and leaps into abyss", "悬崖,纵身,深渊,绝境", "cliff_lighthouse"),
    ("alchemy_last_seal", "blazing alchemy room trembling bronze cauldron, sweat drenched alchemist forming final pill hand seal", "炼丹,成丹,丹炉,控火", "indoor_warm"),
    ("sword_grave", "silent sword grave millions of rusted blades trembling and screaming as protagonist enters", "剑冢,万剑,认主,剑鸣", "enchanted_grove"),
    ("underground_arena", "underground iron cage arena, frenzied crowd, one hand choking three meter half-beast opponent", "角斗场,搏杀,兽人,铁笼", "indoor_warm"),
    ("gate_white_stairs", "mysterious sect gate endless white jade stairs to clouds, youths crawling upward under crushing pressure", "山门,天梯,石阶,考核", "shrine_path"),
    ("nether_bridge", "underworld Naihe bridge ghost queue whipped by guards, protagonist hiding living aura to rescue soul", "奈何桥,冥界,还魂,阴魂", "mystery_fog"),
    ("roast_chicken_spirit", "spirit beast cliff tree hollow, protagonist waving sizzling roast drumstick tempting baby qilin", "烤鸡,神兽,幼崽,诱拐", "forest_path"),
    ("magic_academy", "magic academy meditation hall floating elemental light particles, merging fire and water at center", "魔法学院,冥想,元素", "floating_isles"),
    ("dragon_nest_egg", "dragon nest mountain of gold, sneaking protagonist hugging huge egg while dragon snores fiery breath", "龙巢,偷蛋,金币,鼾声", "cave_glow"),
    ("guild_quest_board", "gothic adventurer guild hall quest board, scarred mercenaries grabbing fresh dragon slayer bounty", "公会,悬赏,屠龙,看板", "indoor_warm"),
    ("temple_ruins_array", "rainy ruined temple altar suddenly glowing purple array tearing space among broken walls", "古庙,法阵,紫光,废墟", "ruins_vine"),
    ("alchemy_explosion", "steampunk alchemy lab gears and tubes, muffled bang, soot black face coughing from smoke", "炼金,爆炸,实验室,黑脸", "indoor_warm"),
    ("bronze_coffin_stars", "vast silent star road inside drifting giant bronze coffin, lone figure sitting in cosmic void", "青铜古棺,星空,漂流", "night_stars"),
    # 科幻惊悚 61-80
    ("supermarket_siege", "supermarket rolling shutter dented by zombies outside, survivors pushing shelves against door", "超市,丧尸,卷帘门,防御", "indoor_warm"),
    ("highway_ammo", "abandoned highway jam of rusted cars, mutant birds overhead, wiping last bullets in SUV", "公路,弹药,废土,怪鸟", "train_countryside"),
    ("bunker_red_alarm", "underground bunker corridor flashing red alarm, claws scraping in ventilation shaft", "避难所,警报,防空洞,爪子", "mystery_fog"),
    ("cyberpunk_alley_gun", "cyberpunk rainy neon alley holographic fish overhead, cyborg mercenaries laser firefight", "赛博朋克,霓虹,枪战,义肢", "city_lights"),
    ("warship_planet_burst", "starship command deck red alerts, curved window showing blue planet tearing apart", "战舰,星球,爆炸,指挥舱", "night_stars"),
    ("infinite_white_orb", "infinite flow pure white void space, giant god-light orb judging reward points", "无限流,光球,结算,主神", "indoor_warm"),
    ("paper_doll_village", "eerie deserted village white lanterns, forced stay in courtyard full of smiling paper effigies", "荒村,纸扎,灯笼,诡异", "ghost_mansion"),
    ("wasteland_can_market", "radiation dust underground survivor market, trading spam cans and bullets for scrap parts", "废土,黑市,罐头,辐射", "night_bazaar"),
    ("bio_lab_embryo", "secret bio lab green tank, mutated embryo with tentacles opening pure black eyes at observer", "生化,胚胎,实验舱,变异", "hospital_hall"),
    ("plane_door_fall", "transport plane tail smoke open cargo door, pushed out into cloud layer without parachute", "运输机,坠落,推下,高空", "airport_sunset"),
    ("hospital_blood_elevator", "horror game hospital elevator at night, floor numbers flickering, fresh blood dripping from vent", "电梯,血滴,医院,惊悚", "hospital_hall"),
    ("haunted_toilet_crack", "dusty old school girls toilet stall, peeking through door crack at backwards walking feet", "女厕所,门缝,怪谈,反向", "ghost_mansion"),
    ("mech_hangar_weld", "massive mech hangar robotic arms welding hundred meter red white humanoid mech sparks flying", "机甲,整备库,焊接,机库", "indoor_warm"),
    ("wasteland_radar", "scorched wasteland squatting with broken radar catching faint old era broadcast music", "雷达,荒原,广播,废土", "desert_oasis"),
    ("cursed_bus_ride", "midnight cursed bus route, protagonist staring ahead pretending not to see faceless passenger in funeral robe", "公交车,怪谈,寿衣,末班", "subway_night"),
    ("ai_data_core", "AI data center blue fiber veins, giant holographic girl smiling mechanically at intruder", "AI,数据中心,全息,女童", "city_lights"),
    ("submarine_sonar", "submarine control room sonar ping, massive red dot bigger than whale rushing toward hull", "潜艇,声呐,深海,红点", "mystery_fog"),
    ("ghost_wedding_hall", "horror copy ancient wedding hall yin wind, lifting bride red veil reveals paper white face", "鬼新娘,喜堂,红盖头,纸脸", "ghost_mansion"),
    ("mars_greenhouse_patch", "Mars base greenhouse meteor punctures film, pressure dropping, scrambling for space tape", "火星,温室,胶带,失压", "desert_oasis"),
    ("colosseum_cyber_arm", "wasteland colosseum undercarriage rest room, machining fusion battery into mechanical right arm", "角斗场,机械臂,改装,电池", "indoor_warm"),
    # 古代宫廷 81-100
    ("throne_hall_debate", "imperial throne hall young emperor on dragon seat, civil and military officials fiercely debating memorial", "金銮殿,朝堂,舌战,折子", "indoor_warm"),
    ("plum_garden_snow", "snowy imperial plum garden, heroine reaching red branch suddenly meets emperor in black fox fur", "御花园,梅林,折梅,微服", "winter_snow"),
    ("manor_kneeling_punish", "snow sealed side hall candle flicker, mistress sipping tea, concubine daughter kneeling on cold brick", "侯府,偏厅,跪训,庶女", "candle_room"),
    ("wedding_room_alone", "festive prince mansion bridal chamber alone on bed edge, dragon phoenix candles burning out unseen groom", "婚房,龙凤烛,独守,王府", "candle_room"),
    ("prison_cell_taunt", "deepest dungeon heavy chains on straw, protagonist mocking victorious enemy through iron bars", "天牢,铁窗,脚镣,嘲讽", "mystery_fog"),
    ("teahouse_spy_story", "busy capital teahouse second floor storyteller gavel, spy exchanging intel through peephole", "茶馆,说书,密探,惊堂木", "tea_house"),
    ("poem_on_painted_boat", "Qinhuai painted boat musicians, poets around courtesan, corner figure recites poem stunning all", "画舫,秦淮,绝句,花魁", "harbor_dawn"),
    ("border_rally_war", "border muster platform torn flags wind, general sword to sky, hundred thousand troops roaring war", "点将台,边关,将士,怒吼", "thunder_field"),
    ("royal_hunt_arrow", "royal hunting grounds mist, arrow pierces bullseye hundred paces, noble ladies gasp", "围猎,百步穿杨,弓弦", "forest_path"),
    ("empress_unveil_night", "silent empress chamber night removing heavy phoenix crown before mirror, eunuch reports emperor at concubine", "坤宁宫,凤冠,卸妆,深夜", "candle_room"),
    ("rabbit_lantern_fair", "lantern festival street sea of lights riddle stall, two hands touch same rabbit lantern", "元宵,灯市,兔子灯,灯谜", "lantern_festival"),
    ("pharmacy_search_antidote", "imperial pharmacy boiling furnaces steam, frantic search scattered herbs for emperor antidote", "太医院,解药,煎药,药炉", "hospital_hall"),
    ("cold_palace_body", "narrow cold palace passage never sees sun, two eunuchs carrying straw wrapped body to mass grave", "冷宫,草席,裹尸,夹道", "ghost_mansion"),
    ("farm_pardon_edict", "misty dawn farm fields exiled protagonist in hemp clothes hoeing, dust horse bearing pardon edict", "贬谪,农田,平反,圣旨", "village_dusk"),
    ("school_prank_fly", "ancient private school master reciting eyes closed, rear row noble son dropping dead fly into classmate ink", "私塾,捉弄,苍蝇,墨汁", "school_corridor"),
    ("execution_scaffold", "execution ground prisoner kneeling, executioner spraying liquor on huge blade, magistrate reaching for token", "断头台,法场,鬼头刀,斩", "mystery_fog"),
    ("rebellion_sandbox", "prince mansion secret room candle maps on wall, black clad advisers around terrain sandbox coup plan", "谋反,沙盘,密室,兵变", "indoor_warm"),
    ("nunnery_well", "peach blossom nunnery backyard heroine drawing water at well, heavy knocks of palace guard outside", "尼姑庵,井边,打水,叩门", "shrine_path"),
    ("silk_shop_ledger", "Jiangnan silk merchant account room abacus clatter, teen protagonist exposes decade hidden fraud one glance", "丝绸,账房,亏空,算盘", "indoor_warm"),
    ("noon_gate_kneeling", "Noon Gate white jade steps torrential rain, protagonist kowtowing blood washing down for imperial mercy", "午门,长跪,叩首,暴雨", "rainy_street"),
]

GENERIC_PATH = SCRIPTS / "scene-prompts-generic.json"
OUT_PROMPTS = SCRIPTS / "scene-prompts.json"
OUT_KEYWORDS = SCRIPTS / "scene-keywords.json"
OUT_ARCHETYPES = SCRIPTS / "scene-archetypes.json"


def wrap(desc: str) -> str:
    return f"{PREFIX} {desc}"


def main() -> None:
    generic: dict[str, str] = {}
    if GENERIC_PATH.is_file():
        generic = json.loads(GENERIC_PATH.read_text(encoding="utf-8"))
    else:
        generic = json.loads(OUT_PROMPTS.read_text(encoding="utf-8"))

    merged: dict[str, str] = dict(generic)
    keywords: dict[str, list[str]] = {}
    archetypes: dict[str, str] = {}

    for sid, desc, zh_kw, arch in NARRATIVE:
        merged[sid] = wrap(desc)
        keywords[sid] = [k.strip() for k in zh_kw.split(",") if k.strip()]
        archetypes[sid] = arch

    OUT_PROMPTS.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_KEYWORDS.write_text(json.dumps(keywords, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_ARCHETYPES.write_text(json.dumps(archetypes, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save generic baseline once
    if not GENERIC_PATH.is_file():
        GENERIC_PATH.write_text(json.dumps(generic, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"scene-prompts: {len(merged)} total ({len(NARRATIVE)} narrative + {len(generic)} generic)")


if __name__ == "__main__":
    main()
