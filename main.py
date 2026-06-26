# ============================================================
# TRIGGER BOT 2  |  BETA
# ============================================================
import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import asyncio
import json
import random
import time
import os
import traceback
import datetime
from dotenv import load_dotenv
from flask import Flask, send_file
import threading


# ============================================================
# CONFIG
# ============================================================
load_dotenv()
TOKEN   = os.getenv("TOKEN")
DB_NAME = "world_trigger.db"
COLOR   = 0x1abc9c

# ============================================================
# DATA — FACTIONS
# ============================================================
FACTIONS = {
    "Kido": {
        "emoji": "<:Kido:1518990445190053888>",
        "description": "Believe all Neighbors are enemies. Aggressive, disciplined, powerful.",
        "buffs": {"attack": 1},
    },
    "Shinoda": {
        "emoji": "<:Shinoda:1518989973238317077>",
        "description": "Neutral. Prioritise citizen safety without anti-Neighbor prejudice.",
        "buffs": {"defense": 1},
    },
    "Tamakoma": {
        "emoji": "<:Rindo:1518990992710307882>",
        "description": "Believe some Neighbors are allies. Seek to understand and befriend them.",
        "buffs": {"mobility": 1},
    },
}

# ============================================================
# DATA — CLASSES
# Rock-paper-scissors: Attacker > Sniper > Gunner > Shooter > All Rounder > Attacker
# ============================================================
CLASSES = {
    "Attacker":    {"emoji": "<:Tachikawa_Chibi:1519442237874765868>",  "strong_against": "Sniper",
                   "image": "https://static.wikitide.net/worldtriggerwiki/b/b2/Tachikawa_deflecting_despinis.gif",
                   "description": "Close-combat specialist. Closes distance to overwhelm snipers."},
    "Sniper":      {"emoji": "<:Toma_Chibi:1519442091736825986>",  "strong_against": "Gunner",
                   "image": "https://static.wikitide.net/worldtriggerwiki/a/a8/Toma_Egret.gif",
                   "description": "Long-range precision. Outranges and punishes gunner positioning."},
    "Gunner":      {"emoji": "<:Jun_Chibi:1519442008819765409>",  "strong_against": "Shooter",
                   "image": "https://i.redd.it/eq7jxwbl1jwg1.gif",
                   "description": "Accurate suppressive fire. More reliable than unpredictable trajectories."},
    "Shooter":     {"emoji": "<:Ninomiya_Chibi:1519441882701234216>",  "strong_against": "All Rounder",
                   "image": "https://static.wikia.nocookie.net/worldtrigger/images/6/6f/Izumi_Viper_anime.gif/revision/latest?cb=20160420224052",
                   "description": "Unpredictable trajectories that overwhelm balanced fighters."},
    "All Rounder": {"emoji": "<:Reiji_Chibi:1519441141714391090>",  "strong_against": "Attacker",
                   # Yuma Kuga is the ultimate All-Rounder. Used a Yuma gif as a placeholder!
                   "image": "https://static.wikitide.net/worldtriggerwiki/f/fa/Kizaki_Hound_%28edited%29.gif",
                   "description": "Versatile and adaptive. Handles close-combat and long-range rushdown with ease."},
}
CLASS_ADVANTAGE_MULT = 1.3

# ============================================================
# DATA — TRIGGERS  (main triggers carry moves; optional carry passives)
# ============================================================
TRIGGERS = {
    # ── Attacker (Main) ─────────────────────────────────────
    "Kogetsu": {
        "price": 80, "trion_cost": 2, "type": "main",
        "buffs": {"attack": 5, "defense": 1},
        "moves": [
            {"name": "Slash",          "dmg": 1.0, "cost": 0, "level": 1},
            {"name": "Senkū",          "dmg": 1.5, "cost": 1, "level": 3},
            {"name": "Whirlwind",      "dmg": 1.8, "cost": 2, "level": 5},
        ],
    },
    "Raygust": {
        "price": 90, "trion_cost": 3, "type": "main",
        "buffs": {"attack": 3, "defense": 4},
        "moves": [
            {"name": "Shield Bash",    "dmg": 0.8, "cost": 0, "level": 1},
            {"name": "Raygust Slash",  "dmg": 1.2, "cost": 1, "level": 2},
            {"name": "Full Guard",     "dmg": 0.5, "cost": 2, "level": 4},
        ],
    },
    "Scorpion": {
        "price": 100, "trion_cost": 2, "type": "main",
        "buffs": {"attack": 4, "mobility": 3},
        "moves": [
            {"name": "Sting",          "dmg": 1.2, "cost": 0, "level": 1},
            {"name": "Mole Claw",      "dmg": 1.5, "cost": 1, "level": 2},
            {"name": "Scorpion Pin",   "dmg": 1.7, "cost": 2, "level": 4},
        ],
    },
    # ── Shooter (Main) ──────────────────────────────────────
    "Asteroid": {
        "price": 50, "trion_cost": 1, "type": "main",
        "buffs": {"attack": 3},
        "moves": [
            {"name": "Asteroid Shot",  "dmg": 1.0, "cost": 0, "level": 1},
            {"name": "Rapid Fire",     "dmg": 1.3, "cost": 1, "level": 2},
            {"name": "Full Burst",     "dmg": 1.6, "cost": 2, "level": 4},
        ],
    },
    "Meteor": {
        "price": 80, "trion_cost": 3, "type": "main",
        "buffs": {"attack": 5, "trion_control": 1},
        "moves": [
            {"name": "Meteor Bomb",    "dmg": 1.2, "cost": 0, "level": 1},
            {"name": "Meteor Storm",   "dmg": 1.5, "cost": 1, "level": 2},
            {"name": "Meteor Crash",   "dmg": 1.9, "cost": 2, "level": 5},
        ],
    },
    "Hound": {
        "price": 90, "trion_cost": 2, "type": "main",
        "buffs": {"attack": 4, "intelligence": 1},
        "moves": [
            {"name": "Hound Chaser",   "dmg": 1.1, "cost": 0, "level": 1},
            {"name": "Hound Volley",   "dmg": 1.4, "cost": 1, "level": 2},
            {"name": "Hound Swarm",    "dmg": 1.6, "cost": 2, "level": 4},
        ],
    },
    "Viper": {
        "price": 120, "trion_cost": 3, "type": "main",
        "buffs": {"attack": 4, "intelligence": 2},
        "moves": [
            {"name": "Viper Bite",     "dmg": 1.2, "cost": 0, "level": 1},
            {"name": "Viper Path",     "dmg": 1.5, "cost": 1, "level": 2},
            {"name": "Viper Cage",     "dmg": 1.8, "cost": 2, "level": 4},
        ],
    },
    # ── Sniper (Main) ───────────────────────────────────────
    "Ibis": {
        "price": 150, "trion_cost": 5, "type": "main",
        "buffs": {"attack": 8, "trion_control": 2},
        "moves": [
            {"name": "Ibis Pierce",    "dmg": 1.5, "cost": 0, "level": 1},
            {"name": "Ibis Break",     "dmg": 2.0, "cost": 2, "level": 3},
            {"name": "Ibis Siege",     "dmg": 2.5, "cost": 3, "level": 5},
        ],
    },
    "Egret": {
        "price": 100, "trion_cost": 3, "type": "main",
        "buffs": {"attack": 5, "perception": 1},
        "moves": [
            {"name": "Egret Snipe",    "dmg": 1.2, "cost": 0, "level": 1},
            {"name": "Egret Focus",    "dmg": 1.5, "cost": 1, "level": 2},
            {"name": "Egret Eagle",    "dmg": 1.8, "cost": 2, "level": 4},
        ],
    },
    "Lightning": {
        "price": 80, "trion_cost": 2, "type": "main",
        "buffs": {"attack": 4, "mobility": 1},
        "moves": [
            {"name": "Lightning Bolt", "dmg": 1.1, "cost": 0, "level": 1},
            {"name": "Lightning Flash","dmg": 1.4, "cost": 1, "level": 2},
            {"name": "Lightning Storm","dmg": 1.7, "cost": 2, "level": 4},
        ],
    },
    # ── Gunner (Main) ───────────────────────────────────────
    # Gunners wield the Gun trigger, which manifests a physical firearm.
    # Unlike Shooters (who shape trion cubes themselves), Gunners trade
    # flexibility for accuracy and sustained suppressive fire.
    # All four gun-forms below pair with bullet triggers in lore; here they
    # are standalone Gunner-class main triggers.
    "Handgun": {
        "price": 60, "trion_cost": 2, "type": "main",
        "buffs": {"attack": 4, "mobility": 2},
        "moves": [
            {"name": "Single Shot",   "dmg": 1.0, "cost": 0, "level": 1},
            {"name": "Quick Draw",    "dmg": 1.3, "cost": 1, "level": 2},
            {"name": "Double Tap",    "dmg": 1.6, "cost": 2, "level": 4},
        ],
    },
    "Assault Rifle": {
        "price": 90, "trion_cost": 2, "type": "main",
        "buffs": {"attack": 5, "perception": 1},
        "moves": [
            {"name": "Burst Fire",    "dmg": 1.1, "cost": 0, "level": 1},
            {"name": "Suppressing Spray","dmg": 1.4, "cost": 1, "level": 2},
            {"name": "Full Auto",     "dmg": 1.7, "cost": 2, "level": 4},
        ],
    },
    "Shotgun": {
        "price": 100, "trion_cost": 3, "type": "main",
        "buffs": {"attack": 6, "defense": 1},
        "moves": [
            {"name": "Scatter Shot",  "dmg": 1.2, "cost": 0, "level": 1},
            {"name": "Close Blast",   "dmg": 1.5, "cost": 1, "level": 2},
            {"name": "Point Blank",   "dmg": 1.9, "cost": 2, "level": 4},
        ],
    },
    "Minigun": {
        "price": 140, "trion_cost": 4, "type": "main",
        "buffs": {"attack": 7, "trion_control": 2},
        "moves": [
            {"name": "Sustained Fire","dmg": 1.3, "cost": 0, "level": 1},
            {"name": "Spin Up",       "dmg": 1.6, "cost": 1, "level": 3},
            {"name": "Bullet Hell",   "dmg": 2.1, "cost": 3, "level": 5},
        ],
    },
    # ── Optional (no moves — passive buffs only) ────────────
    "Grasshopper":  {"price": 60,  "trion_cost": 1, "type": "optional", "buffs": {"mobility": 5},               "moves": []},
    "Bagworm":      {"price": 50,  "trion_cost": 1, "type": "optional", "buffs": {"evasion": 3, "mobility": 1}, "moves": []},
    "Shield":       {"price": 40,  "trion_cost": 1, "type": "optional", "buffs": {"defense": 4},                "moves": []},
    "Chameleon":    {"price": 90,  "trion_cost": 2, "type": "optional", "buffs": {"evasion": 5},                "moves": []},
    "Spider":       {"price": 70,  "trion_cost": 2, "type": "optional", "buffs": {"attack": 2, "intelligence": 1}, "moves": []},
    "Escudo":       {"price": 75,  "trion_cost": 2, "type": "optional", "buffs": {"defense": 5, "attack": 1},   "moves": []},
    "Thruster":     {"price": 80,  "trion_cost": 2, "type": "optional", "buffs": {"mobility": 4, "attack": 1},  "moves": []},
    "Silencer":     {"price": 60,  "trion_cost": 1, "type": "optional", "buffs": {"evasion": 2, "perception": 1}, "moves": []},
    "Dummy Beacon": {"price": 55,  "trion_cost": 1, "type": "optional", "buffs": {"intelligence": 3},           "moves": []},
    # ── Custom ──────────────────────────────────────────────
    "Shadow Cloak": {"price": 120, "trion_cost": 2, "type": "optional", "buffs": {"evasion": 5},                "moves": []},
    "Wallbreaker":  {"price": 70,  "trion_cost": 1, "type": "optional", "buffs": {"attack": 3},                 "moves": []},

    # ── Aftokrator Black Triggers (Earned via Story) ───────
    "Organon": {
        "price": 0, "trion_cost": 5, "type": "main", "black_trigger": True,
        "buffs": {"attack": 15, "defense": 5, "mobility": 5},
        "moves": [
            {"name": "Organon Slash",  "dmg": 2.0, "cost": 0, "level": 1},
            {"name": "Blade Storm",    "dmg": 2.5, "cost": 1, "level": 2},
            {"name": "Dimensional Cut","dmg": 3.5, "cost": 3, "level": 5},
        ],
    },
    "Vorvoros": {
        "price": 0, "trion_cost": 5, "type": "main", "black_trigger": True,
        "buffs": {"attack": 12, "defense": 10, "intelligence": 5},
        "moves": [
            {"name": "Liquid Form",     "dmg": 1.5, "cost": 0, "level": 1},
            {"name": "Poison Splash",   "dmg": 2.2, "cost": 1, "level": 2},
            {"name": "Toxic Devastation","dmg": 3.0, "cost": 3, "level": 5},
        ],
    },
    "Alektor": {
        "price": 0, "trion_cost": 6, "type": "main", "black_trigger": True,
        "buffs": {"attack": 14, "mobility": 8, "perception": 5},
        "moves": [
            {"name": "Feather Shot",   "dmg": 1.8, "cost": 0, "level": 1},
            {"name": "Homing Flock",   "dmg": 2.4, "cost": 1, "level": 2},
            {"name": "Sky God's Wrath","dmg": 3.2, "cost": 3, "level": 5},
        ],
    },
}

# ============================================================
# DATA — COMBINED TRIGGERS  (Trigger Forge)
# ============================================================
COMBINED_TRIGGERS = {
    ("Kogetsu", "Scorpion"): {
        "name": "Kogetsu: Mantis", "price": 250, "trion_cost": 4, "type": "main",
        "buffs": {"attack": 8, "mobility": 5, "defense": 2},
        "moves": [
            {"name": "Mantis Slash",      "dmg": 1.5, "cost": 0, "level": 1},
            {"name": "Mantis Leap",       "dmg": 1.8, "cost": 1, "level": 3},
            {"name": "Mantis Guillotine", "dmg": 2.2, "cost": 3, "level": 5},
        ],
    },
    ("Raygust", "Asteroid"): {
        "name": "Raygust: Cannon", "price": 200, "trion_cost": 4, "type": "main",
        "buffs": {"attack": 6, "defense": 5, "trion_control": 2},
        "moves": [
            {"name": "Cannon Bash",    "dmg": 1.2, "cost": 0, "level": 1},
            {"name": "Cannon Shot",    "dmg": 1.6, "cost": 2, "level": 3},
            {"name": "Cannon Barrage", "dmg": 2.0, "cost": 3, "level": 5},
        ],
    },
    ("Viper", "Hound"): {
        "name": "Viper: Tracker", "price": 220, "trion_cost": 3, "type": "main",
        "buffs": {"attack": 6, "intelligence": 3},
        "moves": [
            {"name": "Tracker Swarm",  "dmg": 1.4, "cost": 0, "level": 1},
            {"name": "Tracker Net",    "dmg": 1.7, "cost": 1, "level": 3},
            {"name": "Tracker Volley", "dmg": 2.0, "cost": 3, "level": 5},
        ],
    },
}

def get_trigger(name: str):
    if name in TRIGGERS:
        return TRIGGERS[name]
    for combo in COMBINED_TRIGGERS.values():
        if combo["name"] == name:
            return combo
    return None

def get_combo_key(t1: str, t2: str):
    if (t1, t2) in COMBINED_TRIGGERS:
        return (t1, t2)
    if (t2, t1) in COMBINED_TRIGGERS:
        return (t2, t1)
    return None

# ============================================================
# DATA — NEIGHBORS
# ============================================================
NEIGHBORS = {
    "Bamster": {"hp": 30, "damage": 6},
    "Marmod":  {"hp": 25, "damage": 8},
    "Rabbit":  {"hp": 40, "damage": 10},
    "Ilgar":   {"hp": 35, "damage": 9},
    "Bander":  {"hp": 28, "damage": 7},
    "Rad":     {"hp": 10, "damage": 3},
    "Dog":     {"hp": 20, "damage": 5},
    "Idra":    {"hp": 25, "damage": 6},
}

def random_neighbor():
    name  = random.choice(list(NEIGHBORS.keys()))
    stats = NEIGHBORS[name]
    return name, stats["hp"], stats["damage"]

# ============================================================
# DATA — STORY BOSSES  (lore-accurate Aftokrator invaders)
# Each boss wields a Black Trigger and has stats far beyond a
# regular Neighbor.  Used by boss-type story missions.
# ============================================================
BOSSES = {
    # ── Chapter 3 boss: the "main Neighbor threat" ──
    "Radar": {
        "title": "Trion Soldier",
        "hp": 120, "damage": 9,
        "description": "A massive Trion Soldier rampages through Mikado City.",
    },
    # ── Chapter 4: Aftokrator invasion — the three commanders ──
    "Viza": {
        "title": "Aftokrator Commander — wielder of Organon",
        "hp": 220, "damage": 16,
        "description": "Viza, a veteran Aftokrator commander, wields the Black Trigger **Organon** — "
                       "a blade that can slice through dimensions themselves.",
    },
    "Enedora": {
        "title": "Aftokrator Invader — wielder of Vorvoros",
        "hp": 200, "damage": 14,
        "description": "Enedora transforms his body into toxic liquid using the Black Trigger **Vorvoros**, "
                       "dissolving anything he touches.",
    },
    "Hyrein": {
        "title": "Aftokrator Commander-in-Chief — wielder of Alektor",
        "hp": 280, "damage": 19,
        "description": "Hyrein, the supreme commander of the Aftokrator expedition force, unleashes the "
                       "Black Trigger **Alektor** — flocks of homing feather-blades.",
    },
}

# Map each boss story mission (chapter, mission) to a boss name.
BOSS_MISSIONS = {
    (3, 1): "Radar",
    (4, 1): "Viza",
    (4, 2): "Enedora",
    (4, 3): "Hyrein",
}

# ============================================================
# DATA — SIDE EFFECTS
# ============================================================
COMMON_EFFECTS = [
    {"name": "Enhanced Vision",   "buffs": {"perception": 1}},
    {"name": "Enhanced Hearing",  "buffs": {"perception": 1}},
    {"name": "Emotion Detection", "buffs": {"intelligence": 1}},
    {"name": "Quick Reflexes",    "buffs": {"mobility": 1}},
    {"name": "Adaptive Thinking", "buffs": {"intelligence": 1}},
]
RARE_EFFECTS = [
    {"name": "Future Sight",     "buffs": {"attack": 2, "intelligence": 2}},
    {"name": "Lie Detection",    "buffs": {"intelligence": 2, "perception": 2}},
    {"name": "Combat Instinct",  "buffs": {"attack": 2, "mobility": 1}, "passive": "crit"},
    {"name": "Trion Efficiency", "buffs": {"trion_control": 2}},
    {"name": "Sniper Precision", "buffs": {"attack": 2, "perception": 1}},
    {"name": "Battle Foresight", "buffs": {"intelligence": 2, "mobility": 1}},
    {"name": "Enhanced Agility", "buffs": {"mobility": 2}},
]

def roll_side_effect():
    if random.random() <= 0.6:
        return random.choice(COMMON_EFFECTS) if random.random() <= 0.85 else random.choice(RARE_EFFECTS)
    return None

# ============================================================
# DATA — TRION ROLLS
# ============================================================
def roll_trion():
    roll = random.randint(1, 100)
    if roll <= 50:  return random.randint(2, 6)
    if roll <= 85:  return random.randint(7, 12)
    if roll <= 97:  return random.randint(13, 20)
    return random.randint(21, 38)

def trion_rarity(trion: int) -> str:
    if trion <= 6:  return "Low"
    if trion <= 12: return "Average"
    if trion <= 20: return "High"
    return "EXTREMELY RARE"

# ============================================================
# DATA — RANK / STAT CAPS
# ============================================================
RANK_CAPS = {
    "C-Rank": {"elo_min": 0,    "elo_max": 1199, "cap": 15},
    "B-Rank": {"elo_min": 1200, "elo_max": 1599, "cap": 30},
    "A-Rank": {"elo_min": 1600, "elo_max": 9999, "cap": 50},
}
RANK_COLORS = {"C-Rank": 0x95a5a6, "B-Rank": 0x3498db, "A-Rank": 0xf39c12}

def get_rank(elo: int) -> str:
    if elo >= 1600: return "A-Rank"
    if elo >= 1200: return "B-Rank"
    return "C-Rank"

def get_stat_cap(elo: int) -> int:
    return RANK_CAPS[get_rank(elo)]["cap"]

# ============================================================
# DATA — OPERATORS
# ============================================================
OPERATORS = {
    "Shiori": {"buff": "cooldown_reduction", "battle_effect": {"type": "next_move_dmg_mult", "value": 1.3}},
    "Asami":  {"buff": "intelligence_bonus",  "battle_effect": {"type": "add_damage",        "value": 20}},
    "Hana":   {"buff": "credit_bonus",        "battle_effect": {"type": "next_move_dmg_mult", "value": 1.2}},
}

# ============================================================
# DATA — SKILL TREES
# ============================================================
SKILL_TREES = {
    "Attacker": [
        {"name": "Close Combat Expert", "cost": 3, "effect": {"dmg_mult": 0.10}, "max_level": 3},
        {"name": "Whirlwind Mastery",   "cost": 5, "effect": {"dmg_mult": 0.20}, "max_level": 2},
    ],
    "Sniper": [
        {"name": "Eagle Eye",    "cost": 4, "effect": {"dmg_mult": 0.10}, "max_level": 3},
        {"name": "Sniper Focus", "cost": 5, "effect": {"dmg_mult": 0.15}, "max_level": 2},
    ],
    "Gunner": [
        {"name": "Suppressive Fire", "cost": 3, "effect": {"dmg_mult": 0.10}, "max_level": 3},
    ],
    "Shooter": [
        {"name": "Trajectory Calculation", "cost": 4, "effect": {"dmg_mult": 0.15}, "max_level": 3},
    ],
    "All Rounder": [
        {"name": "Versatile Fighter", "cost": 4, "effect": {"stat_boost": 1}, "max_level": 5},
    ],
}

# ============================================================
# DATA — DAILY MISSIONS
# ============================================================
DAILY_MISSION_POOL = [
    {"desc": "Win 3 arena battles",          "type": "arena_wins",   "target": 3, "reward_credits": 150, "reward_spins": 1},
    {"desc": "Complete 2 story missions",    "type": "mission_wins", "target": 2, "reward_credits": 100, "reward_spins": 1},
    {"desc": "Win a duel",                   "type": "duel_wins",    "target": 1, "reward_credits": 200, "reward_spins": 2},
    {"desc": "Use Kogetsu moves 5 times",    "type": "trigger_move", "trigger": "Kogetsu", "target": 5, "reward_credits": 80, "reward_spins": 0},
    {"desc": "Complete an expedition",       "type": "expedition",   "target": 1, "reward_credits": 120, "reward_spins": 1},
    {"desc": "Defeat 5 Neighbors in combat", "type": "neighbor_kills","target": 5, "reward_credits": 130, "reward_spins": 1},
    {"desc": "Defeat a boss in the story",   "type": "boss_kills",   "target": 1, "reward_credits": 250, "reward_spins": 2},
]

# ============================================================
# DATA — TRAINERS
# ============================================================
TRAINERS = {
    "Shinoda":  {"specialty": "Intelligence",  "stat": "intelligence",  "boost": 2,      "cost": 150},
    "Kido":     {"specialty": "Trion Control", "stat": "trion_control", "boost": 2,      "cost": 150},
    "Karasuma": {"specialty": "Combat",        "stat": None,            "boost": (1, 1),
                 "stats": ("attack", "defense"),                                          "cost": 200},
    "Yūma":     {"specialty": "Mobility",      "stat": "mobility",      "boost": 2,      "cost": 120},
}

# ============================================================
# UTILITY — ELO
# ============================================================
def win_elo(current: int) -> int:
    return current + random.randint(15, 30)

def lose_elo(current: int) -> int:
    return max(current - random.randint(15, 30), 0)

# ============================================================
# UTILITY — DAMAGE CALCULATION
# ============================================================
async def calculate_damage(user_id, trion, side_effect=None, triggers=None, stats=None,
                            attacker_class=None, defender_class=None,
                            faction=None, move=None, skills=None):
    if stats is None:
        stats = {k: 1 for k in ("attack", "defense", "mobility", "intelligence", "trion_control", "perception")}

    base            = trion * 3
    buff            = 0
    remaining_trion = trion

    STAT_WEIGHTS = {"attack": 5, "mobility": 2, "perception": 2, "intelligence": 3,
                    "trion_control": 4, "defense": 1, "evasion": 1}

    if side_effect:
        for stat, value in side_effect.get("buffs", {}).items():
            buff += value * STAT_WEIGHTS.get(stat, 1)

    if triggers:
        for trig_name in triggers:
            trig = get_trigger(trig_name)
            if not trig:
                continue
            # Black Triggers are powered by their creator's trion, not the
            # wielder's — their buffs ALWAYS apply regardless of trion cost.
            # (This fixes Black Triggers being a nerf for low-trion agents.)
            if trig.get("black_trigger"):
                for stat, value in trig.get("buffs", {}).items():
                    buff += value * STAT_WEIGHTS.get(stat, 1)
                continue
            cost = trig.get("trion_cost", 0)
            if remaining_trion >= cost:
                remaining_trion -= cost
                for stat, value in trig.get("buffs", {}).items():
                    buff += value * STAT_WEIGHTS.get(stat, 1)

    if faction and faction in FACTIONS:
        for stat, value in FACTIONS[faction].get("buffs", {}).items():
            buff += value * STAT_WEIGHTS.get(stat, 1)

    if skills:
        for skill_name, level in skills.items():
            for nodes in SKILL_TREES.values():
                for node in nodes:
                    if node["name"] == skill_name:
                        effect = node.get("effect", {})
                        if "dmg_mult" in effect:
                            base += int(base * effect["dmg_mult"] * level)
                        if "stat_boost" in effect:
                            buff += effect["stat_boost"] * level * 3

    buff += stats.get("attack", 1)        * 5
    buff += stats.get("mobility", 1)      * 2
    buff += stats.get("intelligence", 1)  * 3
    buff += stats.get("trion_control", 1) * 4
    buff += stats.get("perception", 1)    * 2
    buff += stats.get("defense", 1)       * 1

    damage = base + buff + random.randint(0, 10)

    if move and "dmg" in move:
        damage *= move["dmg"]

    if side_effect and side_effect.get("passive") == "crit":
        if random.random() < 0.2:
            damage *= 1.5

    if attacker_class and defender_class:
        cls = CLASSES.get(attacker_class)
        if cls and cls["strong_against"] == defender_class:
            damage *= CLASS_ADVANTAGE_MULT

    return int(damage)

# ============================================================
# UTILITY — TRIGGER MASTERY
# ============================================================
async def gain_trigger_xp(db, user_id: int, trigger_name: str, amount: int = 10):
    await db.execute(
        "INSERT INTO trigger_mastery (user_id, trigger, xp, level) VALUES (?,?,?,1) "
        "ON CONFLICT(user_id, trigger) DO UPDATE SET xp = xp + ?",
        (user_id, trigger_name, amount, amount)
    )
    cursor = await db.execute(
        "SELECT xp, level FROM trigger_mastery WHERE user_id=? AND trigger=?",
        (user_id, trigger_name)
    )
    row = await cursor.fetchone()
    if row:
        xp, level = row
        new_level = 1 + xp // 100
        if new_level > level:
            await db.execute(
                "UPDATE trigger_mastery SET level=? WHERE user_id=? AND trigger=?",
                (new_level, user_id, trigger_name)
            )

# ============================================================
# UTILITY — HP BAR
# ============================================================
def hp_bar(current: int, maximum: int, length: int = 10) -> str:
    if maximum <= 0:
        return "░" * length
    filled = max(0, min(length, int(current / maximum * length)))
    return "█" * filled + "░" * (length - filled)

def stat_bar(value: int, length: int = 10) -> str:
    filled = max(0, min(length, value))
    return "█" * filled + "░" * (length - filled)

# ============================================================
# UI — PAGINATED SHOP VIEW
# ============================================================
TRIGGERS_PER_PAGE = 5

class ShopView(discord.ui.View):
    def __init__(self, page: int = 0):
        super().__init__(timeout=120)
        base  = list(TRIGGERS.items())
        combo = [(c["name"], c) for c in COMBINED_TRIGGERS.values()]
        self.trigger_list = base + combo
        self.page         = page
        self.total_pages  = max(1, (len(self.trigger_list) + TRIGGERS_PER_PAGE - 1) // TRIGGERS_PER_PAGE)
        self._refresh()

    def _refresh(self):
        for item in self.children:
            if hasattr(item, "custom_id"):
                if item.custom_id == "shop_prev":
                    item.disabled = self.page == 0
                elif item.custom_id == "shop_next":
                    item.disabled = self.page >= self.total_pages - 1

    def build_embed(self) -> discord.Embed:
        start   = self.page * TRIGGERS_PER_PAGE
        entries = self.trigger_list[start : start + TRIGGERS_PER_PAGE]
        embed   = discord.Embed(title="<:Border:1519494342799130695> Border Trigger Shop",
                                description="Purchase triggers using Credits.",
                                color=COLOR)
        for name, data in entries:
            if data.get("black_trigger"):  # <-- ADD THIS LINE
                continue                   # <-- ADD THIS LINE
            is_combo = name != data.get("name", name) or any(c["name"] == name for c in COMBINED_TRIGGERS.values())
            suffix   = " **[FUSED]**" if is_combo else ""
            buffs    = ", ".join(f"{k}+{v}" for k, v in data["buffs"].items())
            embed.add_field(
                name  = f"<:Trigger:1518993124406333661> {name}  ({data['type'].capitalize()}){suffix}",
                value = f"<:Yen:1519498350364332082> **{data['price']} Credits**  <:TrionCube:1519499035613073438> Trion: {data['trion_cost']}\n📊 {buffs}",
                inline=False)
        embed.set_footer(text=f"Page {self.page+1}/{self.total_pages} · Use /buytrigger <name>")
        return embed

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary, custom_id="shop_prev")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self._refresh()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary, custom_id="shop_next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self._refresh()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

# ============================================================
# UI — PAGINATED SIDE EFFECTS VIEW
# ============================================================
EFFECTS_PER_PAGE = 5

class SideEffectsView(discord.ui.View):
    def __init__(self, page: int = 0):
        super().__init__(timeout=120)
        self.all_effects  = ([("Common", e) for e in COMMON_EFFECTS] +
                             [("Rare",   e) for e in RARE_EFFECTS])
        self.page         = page
        self.total_pages  = max(1, (len(self.all_effects) + EFFECTS_PER_PAGE - 1) // EFFECTS_PER_PAGE)
        self._refresh()

    def _refresh(self):
        for item in self.children:
            if hasattr(item, "custom_id"):
                if item.custom_id == "se_prev":
                    item.disabled = self.page == 0
                elif item.custom_id == "se_next":
                    item.disabled = self.page >= self.total_pages - 1

    def build_embed(self) -> discord.Embed:
        start   = self.page * EFFECTS_PER_PAGE
        entries = self.all_effects[start : start + EFFECTS_PER_PAGE]
        embed   = discord.Embed(
            title       = "🧬 Side Effects Index",
            description = "**Common** — 85% chance  |  **Rare** — 15% chance\n"
                          "*(60% of agents receive a side effect at all)*",
            color       = COLOR)
        for rarity, effect in entries:
            icon    = "🟡" if rarity == "Rare" else "🔵"
            buffs   = ", ".join(f"{k}+{v}" for k, v in effect["buffs"].items())
            passive = f"\n✨ Passive: **{effect['passive']}**" if "passive" in effect else ""
            embed.add_field(
                name  = f"{icon} {effect['name']}  [{rarity}]",
                value = f"📊 {buffs}{passive}",
                inline=False)
        embed.set_footer(text=f"Page {self.page+1}/{self.total_pages}")
        return embed

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary, custom_id="se_prev")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self._refresh()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary, custom_id="se_next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self._refresh()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

# ============================================================
# UI — TURN-BASED PvE BATTLE VIEW
# ============================================================
class TurnBattleView(discord.ui.View):
    def __init__(self, channel, player: dict, ai: dict, callback, squad_operator=None):
        super().__init__(timeout=120)
        self.channel          = channel
        self.player           = player
        self.ai               = ai
        self.turn             = 1
        self.battle_log       = []
        self.callback         = callback
        self.squad_operator   = squad_operator
        self.operator_cooldown = 0
        self._build_buttons()

    def _get_main_trigger(self):
        for trig in self.player["triggers"]:
            data = get_trigger(trig)
            if data and data.get("type") == "main":
                return trig, data
        return None, None

    def _build_buttons(self):
        self.clear_items()
        trig_name, trig_data = self._get_main_trigger()
        if not trig_name or not trig_data:
            self.add_item(discord.ui.Button(label="No Main Trigger equipped", disabled=True))
            return

        mastery     = self.player.get("mastery", {}).get(trig_name, 1)
        moves       = trig_data.get("moves", [])
        avail_moves = [m for m in moves if m["level"] <= mastery] or moves[:1]

        for move in avail_moves:
            btn = discord.ui.Button(
                label="{} (⚡{})".format(move['name'], move.get('cost', 0)),
                style=discord.ButtonStyle.primary,
                custom_id="move_{}".format(move['name']),
            )
            
            # Explicitly assign the callback to handle dynamic buttons
            async def move_callback(interaction: discord.Interaction, m_name=move['name']):
                await self._handle_move(interaction, m_name)
                
            btn.callback = move_callback
            self.add_item(btn)

        btn = discord.ui.Button(label="🛡 Defend", style=discord.ButtonStyle.secondary, custom_id="defend")
        async def defend_callback(interaction: discord.Interaction):
            await self._handle_defend(interaction)
        btn.callback = defend_callback
        self.add_item(btn)

        if self.squad_operator and self.operator_cooldown <= 0:
            btn = discord.ui.Button(label="📡 Call Operator", style=discord.ButtonStyle.success, custom_id="operator")
            async def op_callback(interaction: discord.Interaction):
                await self._handle_operator(interaction)
            btn.callback = op_callback
            self.add_item(btn)

        btn = discord.ui.Button(label="🚀 Bail Out", style=discord.ButtonStyle.danger, custom_id="bailout")
        async def bail_callback(interaction: discord.Interaction):
            await self._handle_bailout(interaction)
        btn.callback = bail_callback
        self.add_item(btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.player["user"].id

    async def on_interaction(self, interaction: discord.Interaction):
        cid = interaction.data["custom_id"]
        if cid.startswith("move_"):
            await self._handle_move(interaction, cid[5:])
        elif cid == "defend":
            await self._handle_defend(interaction)
        elif cid == "operator":
            await self._handle_operator(interaction)
        elif cid == "bailout":
            await self._handle_bailout(interaction)

    async def _handle_move(self, interaction, move_name: str):
        trig_name, trig_data = self._get_main_trigger()
        if not trig_name:
            await interaction.response.send_message("No main trigger equipped!", ephemeral=True)
            return

        move = next((m for m in trig_data["moves"] if m["name"] == move_name), None)
        if not move:
            await interaction.response.send_message("Invalid move.", ephemeral=True)
            return

        # Move cost is drawn from the agent's Trion pool (the permanent stat).
        # Battle HP is tracked separately via ``hp`` so survivability no longer
        # doubles as a move-resource meter.
        cost = move.get("cost", 0)
        if self.player["trion"] < cost:
            await interaction.response.send_message("<:TrionCube:1519499035613073438> Not enough Trion to use that move!", ephemeral=True)
            return

        self.player["trion"] -= cost

        effective_move = dict(move)
        if self.player.get("operator_buff"):
            effective_move["dmg"] = move.get("dmg", 1.0) * self.player.pop("operator_buff")

        dmg = await calculate_damage(
            self.player["user"].id, self.player["base_trion"],
            side_effect     = self.player["side_effect"],
            triggers        = self.player["triggers"],
            stats           = self.player["stats"],
            attacker_class  = self.player["class"],
            faction         = self.player["faction"],
            move            = effective_move,
            skills          = self.player.get("skills"),
        )
        self.ai["trion"] = max(0, self.ai["trion"] - dmg)
        self.battle_log.append(f"**{self.player['name']}** uses **{move_name}** — {dmg} dmg.")

        if self.ai["trion"] <= 0:
            await self._end_battle(interaction, won=True)
            return

        ai_dmg = max(1, int(self.ai["damage"] * (0.8 + random.random() * 0.6)))
        self.player["hp"] = max(0, self.player["hp"] - ai_dmg)
        self.battle_log.append(f"**{self.ai['name']}** hits back — {ai_dmg} dmg.")

        if self.player["hp"] <= 0:
            await self._end_battle(interaction, won=False)
            return

        if self.operator_cooldown > 0:
            self.operator_cooldown -= 1
        self.turn += 1
        self._build_buttons()
        await self._update_message(interaction)

    async def _handle_defend(self, interaction):
        ai_dmg = max(1, int(self.ai["damage"] * 0.4))
        self.player["hp"] = max(0, self.player["hp"] - ai_dmg)
        self.battle_log.append(f"**{self.player['name']}** defends. Took only {ai_dmg} dmg.")
        if self.player["hp"] <= 0:
            await self._end_battle(interaction, won=False)
            return
        if self.operator_cooldown > 0:
            self.operator_cooldown -= 1
        self.turn += 1
        self._build_buttons()
        await self._update_message(interaction)

    async def _handle_operator(self, interaction):
        op    = self.squad_operator
        effect = OPERATORS.get(op, {}).get("battle_effect")
        if not effect:
            await interaction.response.send_message("Operator has no battle ability.", ephemeral=True)
            return
        if effect["type"] == "next_move_dmg_mult":
            self.player["operator_buff"] = effect["value"]
            self.battle_log.append(f"📡 **{op}** boosts your next attack!")
        elif effect["type"] == "add_damage":
            self.ai["trion"] = max(0, self.ai["trion"] - effect["value"])
            self.battle_log.append(f"📡 **{op}** calls in a strike for {effect['value']} damage!")
            if self.ai["trion"] <= 0:
                await self._end_battle(interaction, won=True)
                return
        self.operator_cooldown = 3
        self._build_buttons()
        await self._update_message(interaction)

    async def _handle_bailout(self, interaction):
        cost = max(1, self.player["hp"] // 3)
        self.player["hp"] = max(0, self.player["hp"] - cost)
        self.battle_log.append(f"🚀 **{self.player['name']}** bails out! Lost {cost} HP.")
        await self._end_battle(interaction, won=False, bailout=True)

    def _status_text(self) -> str:
        p_bar  = hp_bar(self.player["hp"], self.player["max_hp"])
        ai_bar = hp_bar(self.ai["trion"],     self.ai["max_trion"])
        lines  = [
            f"## ⚔️ Turn {self.turn}",
            f"🛡️ **{self.player['name']}**  {p_bar}  {self.player['hp']} HP  ·  <:TrionCube:1519499035613073438> {self.player['trion']}",
            f"👾 **{self.ai['name']}**  {ai_bar}  {self.ai['trion']} HP",
            "",
        ] + self.battle_log[-4:]
        return "\n".join(lines)

    async def _update_message(self, interaction):
        await interaction.response.edit_message(content=self._status_text(), view=self)

    async def _end_battle(self, interaction, won: bool, bailout: bool = False):
        for child in self.children:
            child.disabled = True

        result = "🏆 **Victory!**" if won else "💀 **Defeated!**"
        if bailout:
            result += " (Bailed Out)"

        embed = discord.Embed(title="⚔️ Battle Ended", color=COLOR if won else 0xe74c3c)
        embed.add_field(name="🛡️ You",    value=f"{self.player['hp']} HP",  inline=True)
        embed.add_field(name="👾 Enemy",  value=f"{self.ai['trion']} HP",        inline=True)
        embed.add_field(name="Result",    value=result,                              inline=False)
        embed.description = "\n".join(self.battle_log[-8:])

        await interaction.response.edit_message(content=None, embed=embed, view=self)
        self.stop()
        if self.callback:
            # Pass final HP; callbacks use base_trion for the permanent stat.
            await self.callback(won, bailout, self.player["hp"])

# ============================================================
# UI — TURN-BASED PvP DUEL VIEW
# ============================================================
class DuelTurnView(discord.ui.View):
    def __init__(self, player1: dict, player2: dict, callback):
        super().__init__(timeout=180)
        self.player1         = player1
        self.player2         = player2
        self.current         = player1
        self.turn            = 1
        self.battle_log      = []
        self.callback        = callback
        self.op_cooldowns    = {}
        self._build_buttons()

    def _get_main_trigger(self, player: dict):
        for trig in player["triggers"]:
            data = get_trigger(trig)
            if data and data.get("type") == "main":
                return trig, data
        return None, None

    def _build_buttons(self):
        self.clear_items()
        trig_name, trig_data = self._get_main_trigger(self.current)
        if not trig_name or not trig_data:
            self.add_item(discord.ui.Button(label="No Main Trigger", disabled=True))
            return

        mastery     = self.current.get("mastery", {}).get(trig_name, 1)
        moves       = trig_data.get("moves", [])
        avail_moves = [m for m in moves if m["level"] <= mastery] or moves[:1]

        for move in avail_moves:
            btn = discord.ui.Button(
                label     = f"{move['name']} (⚡{move.get('cost', 0)})",
                style     = discord.ButtonStyle.primary,
                custom_id = f"move_{move['name']}",
            )
            
            # Explicitly assign the callback to handle dynamic buttons
            async def move_cb(interaction: discord.Interaction, m_name=move['name']):
                await self._handle_move(interaction, m_name)
                
            btn.callback = move_cb
            self.add_item(btn)

        btn = discord.ui.Button(label="🛡 Defend", style=discord.ButtonStyle.secondary, custom_id="defend")
        async def defend_cb(interaction: discord.Interaction):
            await self._handle_defend(interaction)
        btn.callback = defend_cb
        self.add_item(btn)

        op = self.current.get("squad_operator")
        if op and self.op_cooldowns.get(op, 0) <= 0:
            btn = discord.ui.Button(label="📡 Call Operator", style=discord.ButtonStyle.success, custom_id="operator")
            async def op_cb(interaction: discord.Interaction):
                await self._handle_operator(interaction)
            btn.callback = op_cb
            self.add_item(btn)

        btn = discord.ui.Button(label="🚀 Bail Out", style=discord.ButtonStyle.danger, custom_id="bailout")
        async def bail_cb(interaction: discord.Interaction):
            await self._handle_bailout(interaction)
        btn.callback = bail_cb
        self.add_item(btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.current["user"].id

    async def on_interaction(self, interaction: discord.Interaction):
        cid = interaction.data["custom_id"]
        if cid.startswith("move_"):
            await self._handle_move(interaction, cid[5:])
        elif cid == "defend":
            await self._handle_defend(interaction)
        elif cid == "operator":
            await self._handle_operator(interaction)
        elif cid == "bailout":
            await self._handle_bailout(interaction)

    def _other(self) -> dict:
        return self.player2 if self.current is self.player1 else self.player1

    async def _handle_move(self, interaction, move_name: str):
        attacker = self.current
        defender = self._other()
        trig_name, trig_data = self._get_main_trigger(attacker)
        if not trig_name:
            return
        move = next((m for m in trig_data["moves"] if m["name"] == move_name), None)
        if not move:
            return
        cost = move.get("cost", 0)
        if attacker["trion"] < cost:
            await interaction.response.send_message("<:TrionCube:1519499035613073438> Not enough Trion!", ephemeral=True)
            return
        attacker["trion"] -= cost

        effective_move = dict(move)
        if attacker.get("operator_buff"):
            effective_move["dmg"] = move.get("dmg", 1.0) * attacker.pop("operator_buff")

        dmg = await calculate_damage(
            attacker["user"].id, attacker["base_trion"],
            side_effect    = attacker["side_effect"],
            triggers       = attacker["triggers"],
            stats          = attacker["stats"],
            attacker_class = attacker["class"],
            defender_class = defender["class"],
            faction        = attacker["faction"],
            move           = effective_move,
            skills         = attacker.get("skills"),
        )
        defender["hp"] = max(0, defender["hp"] - dmg)
        self.battle_log.append(f"**{attacker['name']}** → **{defender['name']}** | {move_name}: {dmg} dmg")

        op = attacker.get("squad_operator")
        if op and self.op_cooldowns.get(op, 0) > 0:
            self.op_cooldowns[op] -= 1

        if defender["hp"] <= 0:
            await self._end_battle(interaction, winner=attacker, loser=defender)
            return

        self.current = defender
        self.turn   += 1
        self._build_buttons()
        await self._update_message(interaction)

    async def _handle_defend(self, interaction):
        attacker = self.current
        self.battle_log.append(f"**{attacker['name']}** takes a defensive stance.")
        op = attacker.get("squad_operator")
        if op and self.op_cooldowns.get(op, 0) > 0:
            self.op_cooldowns[op] -= 1
        self.current = self._other()
        self.turn   += 1
        self._build_buttons()
        await self._update_message(interaction)

    async def _handle_operator(self, interaction):
        attacker = self.current
        op       = attacker.get("squad_operator")
        if not op:
            return
        if self.op_cooldowns.get(op, 0) > 0:
            await interaction.response.send_message("Operator still on cooldown.", ephemeral=True)
            return
        effect = OPERATORS.get(op, {}).get("battle_effect")
        if not effect:
            await interaction.response.send_message("Operator has no battle ability.", ephemeral=True)
            return
        if effect["type"] == "next_move_dmg_mult":
            attacker["operator_buff"] = effect["value"]
            self.battle_log.append(f"📡 **{op}** boosts {attacker['name']}'s next attack!")
        elif effect["type"] == "add_damage":
            defender = self._other()
            defender["hp"] = max(0, defender["hp"] - effect["value"])
            self.battle_log.append(f"📡 **{op}** strikes {defender['name']} for {effect['value']}!")
            if defender["hp"] <= 0:
                await self._end_battle(interaction, winner=attacker, loser=defender)
                return
        self.op_cooldowns[op] = 3
        self._build_buttons()
        await self._update_message(interaction)

    async def _handle_bailout(self, interaction):
        attacker = self.current
        cost     = max(1, attacker["hp"] // 3)
        attacker["hp"] = max(0, attacker["hp"] - cost)
        self.battle_log.append(f"🚀 **{attacker['name']}** bails out! Lost {cost} HP.")
        winner = self._other()
        await self._end_battle(interaction, winner=winner, loser=attacker)

    def _status_text(self) -> str:
        p1_bar = hp_bar(self.player1["hp"], self.player1["max_hp"])
        p2_bar = hp_bar(self.player2["hp"], self.player2["max_hp"])
        lines  = [
            f"## ⚔️ Turn {self.turn}  —  {self.current['name']}'s turn",
            f"🛡️ **{self.player1['name']}**  {p1_bar}  {self.player1['hp']} HP  ·  <:TrionCube:1519499035613073438> {self.player1['trion']}",
            f"🛡️ **{self.player2['name']}**  {p2_bar}  {self.player2['hp']} HP  ·  <:TrionCube:1519499035613073438> {self.player2['trion']}",
            "",
        ] + self.battle_log[-4:]
        return "\n".join(lines)

    async def _update_message(self, interaction):
        await interaction.response.edit_message(content=self._status_text(), view=self)

    async def _end_battle(self, interaction, winner: dict, loser: dict):
        for child in self.children:
            child.disabled = True

        embed = discord.Embed(title="⚔️ Duel Ended", color=COLOR)
        embed.add_field(name="🏆 Winner", value=winner["name"], inline=True)
        embed.add_field(name="💀 Loser",  value=loser["name"],  inline=True)
        embed.add_field(name="🛡️ " + self.player1["name"], value=f"{self.player1['hp']} HP", inline=True)
        embed.add_field(name="🛡️ " + self.player2["name"], value=f"{self.player2['hp']} HP", inline=True)
        embed.description = "\n".join(self.battle_log[-8:])

        await interaction.response.edit_message(content=None, embed=embed, view=self)
        self.stop()
        if self.callback:
            await self.callback(
                winner     = winner,
                loser      = loser,
                final_trion1 = self.player1["hp"],
                final_trion2 = self.player2["hp"],
            )

# ============================================================
# UI — DUEL ACCEPT VIEW
# ============================================================
class DuelAcceptView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent   = opponent

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Only the challenged player can accept.", ephemeral=True)
            return
        self.stop()
        await interaction.response.edit_message(content="⚔️ Duel accepted! Loading…", view=None)
        await _start_duel(interaction, self.challenger, self.opponent)

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Only the challenged player can decline.", ephemeral=True)
            return
        self.stop()
        await interaction.response.edit_message(content="Duel declined.", view=None)

# ============================================================
# DATABASE SETUP
# ============================================================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                user_id        INTEGER PRIMARY KEY,
                trion          INTEGER DEFAULT 2,
                side_effect    TEXT,
                spins          INTEGER DEFAULT 0,
                credits        INTEGER DEFAULT 0,
                elo            INTEGER DEFAULT 1000,
                wins           INTEGER DEFAULT 0,
                losses         INTEGER DEFAULT 0,
                class          TEXT    DEFAULT NULL,
                faction        TEXT    DEFAULT NULL,
                expedition_end REAL    DEFAULT 0,
                skill_points   INTEGER DEFAULT 0
            )""")

        for col, definition in [
            ("class",          "TEXT    DEFAULT NULL"),
            ("faction",        "TEXT    DEFAULT NULL"),
            ("expedition_end", "REAL    DEFAULT 0"),
            ("skill_points",   "INTEGER DEFAULT 0"),
        ]:
            try:
                await db.execute(f"ALTER TABLE agents ADD COLUMN {col} {definition}")
            except Exception:
                pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS triggers (
                user_id INTEGER,
                trigger TEXT,
                PRIMARY KEY (user_id, trigger)
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS loadouts (
                user_id INTEGER,
                trigger TEXT,
                slot    TEXT,
                PRIMARY KEY (user_id, slot)
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS story_progress (
                user_id INTEGER PRIMARY KEY,
                arc     TEXT    DEFAULT 'Prologue',
                chapter INTEGER DEFAULT 1,
                mission INTEGER DEFAULT 1
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS story_missions (
                arc           TEXT,
                chapter       INTEGER,
                mission       INTEGER,
                type          TEXT,
                description   TEXT,
                choices       TEXT,
                reward_type   TEXT,
                reward_amount INTEGER,
                reward_trigger TEXT,
                replayable    INTEGER DEFAULT 0,
                PRIMARY KEY (arc, chapter, mission)
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_stats (
                user_id       INTEGER PRIMARY KEY,
                attack        INTEGER DEFAULT 1,
                defense       INTEGER DEFAULT 1,
                mobility      INTEGER DEFAULT 1,
                intelligence  INTEGER DEFAULT 1,
                trion_control INTEGER DEFAULT 1,
                perception    INTEGER DEFAULT 1,
                stat_points   INTEGER DEFAULT 0
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS squads (
                squad_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT UNIQUE,
                leader_id  INTEGER,
                division   TEXT    DEFAULT 'C-Rank',
                elo        INTEGER DEFAULT 1000,
                operator   TEXT    DEFAULT NULL
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS squad_members (
                squad_id INTEGER,
                user_id  INTEGER,
                role     TEXT
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS trigger_mastery (
                user_id INTEGER,
                trigger TEXT,
                xp      INTEGER DEFAULT 0,
                level   INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, trigger)
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_skills (
                user_id    INTEGER,
                skill_name TEXT,
                level      INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, skill_name)
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_missions (
                user_id    INTEGER,
                mission_id INTEGER,
                progress   INTEGER DEFAULT 0,
                target     INTEGER,
                completed  INTEGER DEFAULT 0,
                date       TEXT,
                PRIMARY KEY (user_id, mission_id, date)
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS base_defense (
                id         INTEGER PRIMARY KEY DEFAULT 1,
                level      INTEGER DEFAULT 1,
                hp         INTEGER DEFAULT 10000,
                last_event REAL    DEFAULT 0
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS redeemed_codes (
                user_id INTEGER,
                code    TEXT,
                PRIMARY KEY (user_id, code)
            )""")

        cursor = await db.execute("SELECT COUNT(*) FROM base_defense")
        if (await cursor.fetchone())[0] == 0:
            await db.execute("INSERT INTO base_defense (id, level, hp, last_event) VALUES (1, 1, 10000, 0)")

        await db.commit()

        cursor = await db.execute("SELECT COUNT(*) FROM story_missions")
        if (await cursor.fetchone())[0] == 0:
            await _populate_story(db)
            await db.commit()
            print("✅ Story missions populated.")

# ============================================================
# STORY POPULATION
# ============================================================
async def _populate_story(db):
    arc      = "Prologue"
    missions = [
        (1, 1, "exploration",
         "You arrive at Mikado City for your first Border assignment. Explore the area.",
         None, "credits", 50, None, 1),
        (1, 2, "choice",
         "You hear a suspicious signal. Investigate carefully or rush in?",
         json.dumps([{"id": "investigate", "label": "Investigate Carefully"},
                     {"id": "rush",        "label": "Rush In"}]),
         "spins", 2, None, 0),
        (1, 3, "arena",
         "Neighbors are attacking civilians nearby. Engage them!",
         None, "credits", 100, None, 0),
        (2, 1, "exploration",
         "Investigate a suspicious warehouse. Look for clues and gather intel.",
         None, "credits", 75, None, 1),
        (2, 2, "choice",
         "A civilian asks for help. Escort them or continue the investigation?",
         json.dumps([{"id": "escort",      "label": "Escort Civilian"},
                     {"id": "investigate", "label": "Continue Investigation"}]),
         "spins", 3, None, 0),
        (2, 3, "arena",
         "A small group of Neighbors attacks! Defend the civilians!",
         None, "credits", 150, None, 0),
        (3, 1, "boss",
         "The main Neighbor threat appears in Mikado City. Prepare for a boss battle!",
         None, "trigger", 1, "Grasshopper", 0),
         # ─── CHAPTER 4: AFTOKRATOR INVASION ───
        (4, 1, "boss",
         "A massive Trion gate opens! Viza of Aftokrator appears, wielding the Black Trigger 'Organon'.",
         None, "trigger", 1, "Organon", 0),
        (4, 2, "boss",
         "Enedora attacks with his Black Trigger 'Vorvoros', turning his body into toxic liquid!",
         None, "trigger", 1, "Vorvoros", 0),
        (4, 3, "boss",
         "Hyrein, the commander, unleashes 'Alektor'. Defeat him to end the invasion!",
         None, "trigger", 1, "Alektor", 0),
    ]
    for chapter, mission, m_type, desc, choices, r_type, r_amount, r_trigger, replayable in missions:
        await db.execute("""
            INSERT OR REPLACE INTO story_missions
            (arc, chapter, mission, type, description, choices,
             reward_type, reward_amount, reward_trigger, replayable)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (arc, chapter, mission, m_type, desc, choices,
              r_type, r_amount, r_trigger, replayable))

# ============================================================
# REDEEM CODES
# ============================================================
redeem_codes: dict = {}

def load_redeem_codes():
    global redeem_codes
    raw = os.getenv("REDEEM_CODES", "")
    if raw:
        try:
            redeem_codes = json.loads(raw)
            print(f"✅ Loaded {len(redeem_codes)} redeem codes.")
        except Exception:
            print("❌ REDEEM_CODES env var is not valid JSON.")
    else:
        print("ℹ️ No REDEEM_CODES env var found — redeem system idle.")

# ============================================================
# BOT SETUP
# ============================================================
intents                 = discord.Intents.default()
intents.message_content = True
intents.members         = True
bot = commands.Bot(command_prefix="!", intents=intents)

_arena_cooldowns: dict = {}
ARENA_COOLDOWN        = 30
EXPEDITION_DURATION   = 4 * 3600

# /train cooldown — 1 hour per agent (in-memory, same pattern as arena)
_train_cooldowns: dict = {}
TRAIN_COOLDOWN        = 3600  # 1 hour in seconds

LOADOUT_SLOTS          = ["Main", "Sub", "Optional"]
MAIN_COMPATIBLE_SLOTS  = ["Main", "Sub"]
OPT_COMPATIBLE_SLOTS   = ["Optional"]

# ── Flask web server ──────────────────────────────
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return send_file('index.html')
# ───────────────────────────────────────────────────

# ============================================================
# HELPERS
# ============================================================
async def agent_exists(user_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT 1 FROM agents WHERE user_id=?", (user_id,))
        return await cursor.fetchone() is not None

async def agent_required(interaction: discord.Interaction) -> bool:
    if not await agent_exists(interaction.user.id):
        await interaction.response.send_message(
            embed=discord.Embed(
                title       = "⚠️ Not Registered",
                description = "You need to join **Border** first!\nUse **`/joinborder`** to become an agent.",
                color       = 0xe67e22,
            ),
            ephemeral=True,
        )
        return False
    return True

def cooldown_embed(remaining: float) -> discord.Embed:
    return discord.Embed(
        title       = "⏳ Cooldown",
        description = f"Please wait **{int(remaining)}** more seconds.",
        color       = 0xe67e22,
    )

async def check_expedition(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT expedition_end FROM agents WHERE user_id=?", (user_id,))
        row    = await cursor.fetchone()
        if row and 0 < row[0] <= time.time():
            credits = random.randint(500, 2000)
            spins   = random.randint(3, 10)
            await db.execute(
                "UPDATE agents SET credits=credits+?, spins=spins+?, expedition_end=0 WHERE user_id=?",
                (credits, spins, user_id))
            await db.commit()
            return credits, spins
    return None, None

async def assign_daily_missions(user_id: int):
    date = datetime.date.today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT 1 FROM daily_missions WHERE user_id=? AND date=?", (user_id, date))
        if await cursor.fetchone():
            return
        missions = random.sample(range(len(DAILY_MISSION_POOL)), min(3, len(DAILY_MISSION_POOL)))
        for idx in missions:
            await db.execute(
                "INSERT INTO daily_missions (user_id, mission_id, target, date) VALUES (?,?,?,?)",
                (user_id, idx, DAILY_MISSION_POOL[idx]["target"], date))
        await db.commit()

async def update_daily_missions(user_id: int, mission_type: str, trigger: str = None, count: int = 1):
    """Increment daily-mission progress.

    ``count`` lets a single event advance a mission by more than one step
    (e.g. defeating a 3-Neighbor wave grants 3 ``neighbor_kills`` at once).
    """
    date = datetime.date.today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT mission_id, target, progress FROM daily_missions "
            "WHERE user_id=? AND date=? AND completed=0",
            (user_id, date))
        rows = await cursor.fetchall()
        for mission_id, target, progress in rows:
            pool_entry = DAILY_MISSION_POOL[mission_id]
            if pool_entry["type"] != mission_type:
                continue
            if mission_type == "trigger_move" and trigger != pool_entry.get("trigger"):
                continue
            new_progress = min(progress + count, target)
            if new_progress >= target:
                await db.execute(
                    "UPDATE daily_missions SET progress=?, completed=1 WHERE user_id=? AND mission_id=? AND date=?",
                    (target, user_id, mission_id, date))
                c = pool_entry.get("reward_credits", 0)
                s = pool_entry.get("reward_spins",   0)
                await db.execute(
                    "UPDATE agents SET credits=credits+?, spins=spins+? WHERE user_id=?",
                    (c, s, user_id))
            else:
                await db.execute(
                    "UPDATE daily_missions SET progress=? WHERE user_id=? AND mission_id=? AND date=?",
                    (new_progress, user_id, mission_id, date))
        await db.commit()

async def _fetch_player_combat_data(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT trion, side_effect, elo, wins, losses, class, faction FROM agents WHERE user_id=?",
            (user_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        trion, side, elo, wins, losses, cls, faction = row
        side = json.loads(side) if side else None

        cursor   = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (user_id,))
        triggers = [r[0] for r in await cursor.fetchall()]

        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception FROM agent_stats WHERE user_id=?",
            (user_id,))
        s = await cursor.fetchone() or (1, 1, 1, 1, 1, 1)
        stats = {"attack": s[0], "defense": s[1], "mobility": s[2],
                 "intelligence": s[3], "trion_control": s[4], "perception": s[5]}

        cursor  = await db.execute("SELECT trigger, level FROM trigger_mastery WHERE user_id=?", (user_id,))
        mastery = {r[0]: r[1] for r in await cursor.fetchall()}

        cursor = await db.execute("SELECT skill_name, level FROM agent_skills WHERE user_id=?", (user_id,))
        skills = {r[0]: r[1] for r in await cursor.fetchall()}

        cursor    = await db.execute(
            "SELECT s.operator FROM squads s "
            "JOIN squad_members sm ON s.squad_id=sm.squad_id "
            "WHERE sm.user_id=? LIMIT 1",
            (user_id,))
        op_row    = await cursor.fetchone()
        operator  = op_row[0] if op_row else None

    return {
        "trion":          trion,
        "max_trion":      trion,
        "base_trion":     trion,
        # Battle HP is derived from trion so even low-trion agents can survive
        # a few hits.  ``base_trion`` is still used for damage calculation, so
        # raw damage output is unchanged — only survivability improves.
        "hp":             trion * 10,
        "max_hp":         trion * 10,
        "side_effect":    side,
        "elo":            elo,
        "wins":           wins,
        "losses":         losses,
        "class":          cls,
        "faction":        faction,
        "triggers":       triggers,
        "stats":          stats,
        "mastery":        mastery,
        "skills":         skills,
        "squad_operator": operator,
    }

# ============================================================
# STORY HELPERS
# ============================================================
async def _advance_story(db, user_id: int, arc: str, chapter: int, mission_num: int):
    next_m = mission_num + 1
    cursor = await db.execute(
        "SELECT 1 FROM story_missions WHERE arc=? AND chapter=? AND mission=?",
        (arc, chapter, next_m))
    if await cursor.fetchone():
        await db.execute(
            "UPDATE story_progress SET mission=? WHERE user_id=?", (next_m, user_id))
    else:
        next_c = chapter + 1
        cursor = await db.execute(
            "SELECT 1 FROM story_missions WHERE arc=? AND chapter=?", (arc, next_c))
        if await cursor.fetchone():
            await db.execute(
                "UPDATE story_progress SET chapter=?, mission=1 WHERE user_id=?",
                (next_c, user_id))

async def _give_story_rewards(db, user_id: int, r_type: str, r_amount: int, r_trigger: str | None, won: bool):
    if not won:
        return
    if r_type == "credits":
        await db.execute("UPDATE agents SET credits=credits+? WHERE user_id=?", (r_amount, user_id))
    elif r_type == "spins":
        await db.execute("UPDATE agents SET spins=spins+? WHERE user_id=?", (r_amount, user_id))
    elif r_type == "trigger" and r_trigger:
        await db.execute("INSERT OR IGNORE INTO triggers (user_id, trigger) VALUES (?,?)", (user_id, r_trigger))
    await db.execute("UPDATE agent_stats SET stat_points=stat_points+1 WHERE user_id=?", (user_id,))
    cursor = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (user_id,))
    for row in await cursor.fetchall():
        await gain_trigger_xp(db, user_id, row[0], random.randint(8, 15))

# ============================================================
# /help
# ============================================================
@bot.tree.command(name="help", description="Show all available commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ Border Bot — Command List", color=COLOR)
    embed.add_field(name="🚀 Getting Started",
                    value="`/joinborder`  `/setclass`  `/faction`  `/profile`", inline=False)
    embed.add_field(name="⚔️ Combat",
                    value="`/arena`  `/duel`  `/mission`  `/bailout`  `/combostats`", inline=False)
    embed.add_field(name="📖 Story",
                    value="`/story`  `/storymission`", inline=False)
    embed.add_field(name="🌌 Expedition",
                    value="`/expedition` *(B-Rank+)*", inline=False)
    embed.add_field(name="🛒 Triggers & Loadout",
                    value="`/shop`  `/sideeffects`  `/buytrigger`  `/equip`  `/loadout`  `/inventory`  `/triggerforge`  `/dismantle`", inline=False)
    embed.add_field(name="📊 Stats & Ranking",
                    value="`/stats`  `/upgradestat`  `/trionrank`  `/leaderboard`  `/spin`", inline=False)
    embed.add_field(name="⚔️ Classes & Factions",
                    value="`/classes`  `/faction`", inline=False)
    embed.add_field(name="🧩 Skills",
                    value="`/skilltree`  `/upgradeskill`", inline=False)
    embed.add_field(name="👥 Squads & Operators",
                    value="`/squadcreate`  `/squadinvite`  `/squadinfo`  `/squadleave`  `/operator`", inline=False)
    embed.add_field(name="🎖️ Mastery & Daily",
                    value="`/triggers_mastered`  `/missionsboard`", inline=False)
    embed.add_field(name="🏢 Info",
                    value="`/baseinfo`  `/base`  `/neighborhood`  `/trainers`  `/train`  `/simulation`  `/redeem`  `/ping`", inline=False)
    embed.set_footer(text="Use any command to get started!")
    await interaction.response.send_message(embed=embed)

# ============================================================
# /joinborder
# ============================================================
@bot.tree.command(name="joinborder", description="Become a Border agent")
async def joinborder(interaction: discord.Interaction):
    user_id = interaction.user.id
    if await agent_exists(user_id):
        await interaction.response.send_message(
            embed=discord.Embed(title="⚠️ Already Registered",
                                description="You are already a Border agent.",
                                color=0xe67e22),
            ephemeral=True)
        return

    trion     = roll_trion()
    side      = roll_side_effect()
    side_json = json.dumps(side) if side else None

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO agents (user_id,trion,side_effect,spins,credits,elo,wins,losses) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (user_id, trion, side_json, 5, 100, 1000, 0, 0))
        await db.execute("INSERT OR IGNORE INTO agent_stats    (user_id) VALUES (?)", (user_id,))
        await db.execute("INSERT OR IGNORE INTO story_progress (user_id) VALUES (?)", (user_id,))
        await db.commit()

    embed = discord.Embed(
        title       = "🛡 Border Agent Registered",
        description = f"Welcome to **Border**, {interaction.user.display_name}.",
        color       = COLOR)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(name="<:TrionCube:1519499035613073438> Trion Level",     value=f"{trion} ({trion_rarity(trion)})", inline=True)
    embed.add_field(name="🧬 Side Effect",     value=side["name"] if side else "None",    inline=True)
    embed.add_field(name="🎰 Starting Spins",  value=5,                                   inline=True)
    embed.add_field(name="<:Yen:1519498350364332082> Starting Credits",value=100,                                  inline=True)
    embed.add_field(name="⚔️ Next Steps",
                    value="1️⃣ `/setclass` — pick Attacker / Sniper / Gunner / Shooter / All Rounder\n"
                          "2️⃣ `/faction` — join Kido, Shinoda, or Tamakoma\n"
                          "3️⃣ `/shop` then `/buytrigger` — arm yourself\n"
                          "4️⃣ `/equip` — load your trigger\n"
                          "5️⃣ `/arena` — fight!",
                    inline=False)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /setclass
# ============================================================
@bot.tree.command(name="setclass", description="Choose your Border combat class")
@app_commands.describe(class_name="Attacker / Sniper / Gunner / Shooter / All Rounder")
async def setclass(interaction: discord.Interaction, class_name: str):
    if not await agent_required(interaction):
        return
    matched = next((c for c in CLASSES if c.lower() == class_name.lower()), None)
    if not matched:
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Invalid Class",
                                description=f"Choose from: {', '.join(CLASSES.keys())}",
                                color=0xe74c3c),
            ephemeral=True)
        return
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE agents SET class=? WHERE user_id=?", (matched, interaction.user.id))
        await db.commit()
        
    cls = CLASSES[matched]
    embed = discord.Embed(title=f"{cls['emoji']} Class Set: {matched}",
                          description=cls["description"], color=COLOR)
    embed.add_field(name="⚡ Strong Against", value=cls["strong_against"])
    embed.add_field(name="💥 Damage Bonus",   value=f"+{int((CLASS_ADVANTAGE_MULT-1)*100)}% vs {cls['strong_against']}")
    
    # Set the GIF/image
    if "image" in cls:
        embed.set_image(url=cls["image"])
        
    await interaction.response.send_message(embed=embed)

# ============================================================
# /faction
# ============================================================
@bot.tree.command(name="faction", description="Join a Border faction")
@app_commands.describe(faction_name="Kido / Shinoda / Tamakoma")
async def faction(interaction: discord.Interaction, faction_name: str):
    if not await agent_required(interaction):
        return
    faction_name = faction_name.title()
    if faction_name not in FACTIONS:
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Invalid Faction",
                                description=f"Choose from: {', '.join(FACTIONS.keys())}",
                                color=0xe74c3c),
            ephemeral=True)
        return
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE agents SET faction=? WHERE user_id=?", (faction_name, interaction.user.id))
        await db.commit()
    fac   = FACTIONS[faction_name]
    buffs = ", ".join(f"{k}+{v}" for k, v in fac["buffs"].items())
    embed = discord.Embed(title=f"{fac['emoji']} Faction Joined: {faction_name}",
                          description=fac["description"], color=COLOR)
    embed.add_field(name="📈 Faction Bonus", value=buffs)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /classes
# ============================================================
@bot.tree.command(name="classes", description="View all classes and matchups")
async def classes(interaction: discord.Interaction):
    embed = discord.Embed(
        title       = "<:Border:1519494342799130695> Border Combat Classes",
        description = f"Each class deals **+{int((CLASS_ADVANTAGE_MULT-1)*100)}% damage** against its counter.",
        color       = COLOR)
    for name, data in CLASSES.items():
        embed.add_field(
            name  = f"{data['emoji']} {name}",
            value = f"**Beats:** {data['strong_against']}\n{data['description']}",
            inline=False)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /profile
# ============================================================
@bot.tree.command(name="profile", description="View your agent profile")
async def profile(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not await agent_required(interaction):
        return

    credits_earned, spins_earned = await check_expedition(user_id)
    await assign_daily_missions(user_id)

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT trion, side_effect, spins, credits, elo, wins, losses, class, faction, skill_points "
            "FROM agents WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        trion, side, spins, credits, elo, wins, losses, cls, fac, skill_pts = row

        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception, stat_points "
            "FROM agent_stats WHERE user_id=?", (user_id,))
        s = await cursor.fetchone()
        stats      = {"Attack": s[0], "Defense": s[1], "Mobility": s[2],
                      "Intelligence": s[3], "Trion Control": s[4], "Perception": s[5]}
        stat_pts   = s[6]

        cursor   = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (user_id,))
        triggers = [r[0] for r in await cursor.fetchall()]

        cursor = await db.execute("SELECT arc, mission FROM story_progress WHERE user_id=?", (user_id,))
        story_row = await cursor.fetchone()
        story_arc, story_mission = story_row if story_row else ("Prologue", 1)

        cursor = await db.execute("SELECT skill_name, level FROM agent_skills WHERE user_id=?", (user_id,))
        skills = {r[0]: r[1] for r in await cursor.fetchall()}

        date   = datetime.date.today().isoformat()
        cursor = await db.execute(
            "SELECT mission_id, progress, target, completed FROM daily_missions WHERE user_id=? AND date=?",
            (user_id, date))
        daily  = await cursor.fetchall()

    rank = get_rank(elo)
    cap  = get_stat_cap(elo)
    used = sum(stats.values()) - 6

    embed = discord.Embed(title=f"<:Border:1519494342799130695> {interaction.user.display_name}", color=COLOR)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    side_name = json.loads(side)["name"] if side else "None"
    embed.add_field(name="<:TrionCube:1519499035613073438> Trion",       value=f"{trion} ({trion_rarity(trion)})", inline=True)
    embed.add_field(name="🧬 Side Effect", value=side_name,                          inline=True)
    if cls:
        embed.add_field(name="⚔️ Class",   value=f"{CLASSES[cls]['emoji']} {cls}", inline=True)
    if fac:
        embed.add_field(name="🏛️ Faction", value=f"{FACTIONS[fac]['emoji']} {fac}", inline=True)

    elo_bar = hp_bar(min(elo, 2000), 2000)
    embed.add_field(name="🏆 ELO", value=f"{elo} ({rank})\n{elo_bar}", inline=False)
    embed.add_field(name="W / L",         value=f"{wins} / {losses}",   inline=True)
    embed.add_field(name="🎰 Spins",      value=spins,                  inline=True)
    embed.add_field(name="<:Yen:1519498350364332082> Credits",    value=credits,                inline=True)
    embed.add_field(name="🌟 Skill Pts",  value=skill_pts,              inline=True)

    stat_text = ""
    for name_, val in stats.items():
        bar = stat_bar(min(val, 10))
        stat_text += f"**{name_}**: {val}  {bar}\n"
    embed.add_field(name=f"📊 Stats  ({used}/{cap} cap  ·  {rank})",
                    value=stat_text, inline=False)
    embed.add_field(name="⭐ Unspent Stat Pts", value=stat_pts, inline=True)

    if skills:
        skill_text = "  ".join(f"**{k}** Lv.{v}" for k, v in skills.items())
        embed.add_field(name="🧩 Skills", value=skill_text, inline=False)

    embed.add_field(name="⚡ Loadout",    value=", ".join(triggers) if triggers else "Empty", inline=False)
    embed.add_field(name="📖 Story",      value=f"{story_arc} — Mission {story_mission}", inline=True)

    if credits_earned:
        embed.add_field(name="🌌 Expedition Returned!",
                        value=f"+{credits_earned} Credits · +{spins_earned} Spins", inline=False)

    if daily:
        mission_text = ""
        for m_id, prog, targ, comp in daily:
            status        = "✅" if comp else f"{prog}/{targ}"
            mission_text += f"• {DAILY_MISSION_POOL[m_id]['desc']} [{status}]\n"
        embed.add_field(name="📋 Daily Missions", value=mission_text, inline=False)

    await interaction.response.send_message(embed=embed)

# ============================================================
# /shop  /sideeffects
# ============================================================
@bot.tree.command(name="shop", description="Browse the Border Trigger Shop")
async def shop(interaction: discord.Interaction):
    view = ShopView()
    await interaction.response.send_message(embed=view.build_embed(), view=view)

@bot.tree.command(name="sideeffects", description="Browse all possible side effects")
async def sideeffects(interaction: discord.Interaction):
    view = SideEffectsView()
    await interaction.response.send_message(embed=view.build_embed(), view=view)

# ============================================================
# /buytrigger
# ============================================================
@bot.tree.command(name="buytrigger", description="Buy a trigger from the shop")
@app_commands.describe(trigger="Trigger name (e.g. Kogetsu)")
async def buytrigger(interaction: discord.Interaction, trigger: str):
    if not await agent_required(interaction):
        return
    user_id    = interaction.user.id
    trig_name  = trigger.title()
    trig_data  = get_trigger(trig_name)
    if not trig_data:
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Trigger Not Found",
                                description="Use `/shop` to see available triggers.",
                                color=0xe74c3c),
            ephemeral=True)
        return
    price = trig_data["price"]

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT credits FROM agents WHERE user_id=?", (user_id,))
        row    = await cursor.fetchone()
        if row[0] < price:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ Not Enough Credits",
                                    description=f"Need **{price}** credits. You have **{row[0]}**.",
                                    color=0xe74c3c),
                ephemeral=True)
            return

        cursor = await db.execute("SELECT 1 FROM triggers WHERE user_id=? AND trigger=?", (user_id, trig_name))
        if await cursor.fetchone():
            await interaction.response.send_message(
                embed=discord.Embed(title="⚠️ Already Owned", description=f"You already own **{trig_name}**.", color=0xf1c40f),
                ephemeral=True)
            return

        await db.execute("UPDATE agents  SET credits=credits-? WHERE user_id=?", (price, user_id))
        await db.execute("INSERT INTO triggers (user_id, trigger) VALUES (?,?)", (user_id, trig_name))
        await db.commit()

    slot_hint = "Main or Sub" if trig_data["type"] == "main" else "Optional"
    embed = discord.Embed(title="✅ Trigger Purchased", description=f"You bought **{trig_name}**!", color=0x2ecc71)
    embed.add_field(name="Slot",   value=slot_hint)
    embed.add_field(name="Next",   value=f"`/equip {trig_name} {slot_hint.split()[0]}`")
    await interaction.response.send_message(embed=embed)

# ============================================================
# /loadout  /equip
# ============================================================
@bot.tree.command(name="loadout", description="View your trigger loadout")
async def loadout(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT trigger, slot FROM loadouts WHERE user_id=?", (interaction.user.id,))
        data   = await cursor.fetchall()
    equipped = {slot: "None" for slot in LOADOUT_SLOTS}
    for trig, slot in data:
        equipped[slot] = trig
    embed = discord.Embed(title=f"⚡ {interaction.user.display_name}'s Loadout", color=COLOR)
    for slot in LOADOUT_SLOTS:
        trig  = equipped[slot]
        tdata = get_trigger(trig) if trig != "None" else None
        extra = f"  *(Trion: {tdata['trion_cost']})*" if tdata else ""
        embed.add_field(name=f"{slot} Slot", value=trig + extra, inline=False)
    embed.set_footer(text="Main-type: Main or Sub  |  Optional: Optional only")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="equip", description="Equip a trigger into a loadout slot")
@app_commands.describe(trigger="Trigger name", slot="Main / Sub / Optional")
async def equip(interaction: discord.Interaction, trigger: str, slot: str):
    if not await agent_required(interaction):
        return
    user_id    = interaction.user.id
    trig_name  = trigger.title()
    slot       = slot.title()

    if slot not in LOADOUT_SLOTS:
        await interaction.response.send_message("Slot must be **Main**, **Sub**, or **Optional**.", ephemeral=True)
        return

    trig_data = get_trigger(trig_name)
    if not trig_data:
        await interaction.response.send_message("Trigger not found. Use `/shop`.", ephemeral=True)
        return

    t_type = trig_data["type"]
    is_black = trig_data.get("black_trigger", False)

    # Black Triggers are all-consuming — in World Trigger lore a Black Trigger
    # draws on the wielder's entire trion supply and cannot be paired with
    # other triggers.  Restrict them to the Main slot only.
    if is_black and slot != "Main":
        await interaction.response.send_message(
            f"🌑 **{trig_name}** is a Black Trigger — it demands the **Main** slot exclusively.\n"
            f"*(A Black Trigger consumes the wielder's full trion focus.)*",
            ephemeral=True)
        return

    if t_type == "main"     and slot not in MAIN_COMPATIBLE_SLOTS:
        await interaction.response.send_message(f"**{trig_name}** (Main-type) can only go in **Main** or **Sub**.", ephemeral=True)
        return
    if t_type == "optional" and slot not in OPT_COMPATIBLE_SLOTS:
        await interaction.response.send_message(f"**{trig_name}** (Optional) can only go in the **Optional** slot.", ephemeral=True)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT 1 FROM triggers WHERE user_id=? AND trigger=?", (user_id, trig_name))
        if not await cursor.fetchone():
            await interaction.response.send_message(f"You don't own **{trig_name}**.", ephemeral=True)
            return

        # Equipping a Black Trigger to Main clears the Sub slot (lore: you
        # cannot sustain a second trigger alongside a Black Trigger).
        if is_black and slot == "Main":
            await db.execute("DELETE FROM loadouts WHERE user_id=? AND slot='Sub'", (user_id,))

        await db.execute(
            "INSERT OR REPLACE INTO loadouts (user_id, trigger, slot) VALUES (?,?,?)",
            (user_id, trig_name, slot))
        await db.commit()

    await interaction.response.send_message(
        embed=discord.Embed(title="✅ Equipped",
                            description=f"**{trig_name}** → **{slot}** slot.",
                            color=COLOR))

# ============================================================
# /inventory  (all owned triggers + credits in one view)
# ============================================================
@bot.tree.command(name="inventory", description="View all your triggers and credits")
async def inventory(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT trion, spins, credits, elo, class, faction FROM agents WHERE user_id=?",
            (user_id,))
        trion, spins, credits, elo, cls, faction = await cursor.fetchone()

        cursor = await db.execute("SELECT trigger FROM triggers WHERE user_id=?", (user_id,))
        owned_triggers = [r[0] for r in await cursor.fetchall()]

        cursor = await db.execute("SELECT trigger, slot FROM loadouts WHERE user_id=?", (user_id,))
        loadout_rows = await cursor.fetchall()

        cursor = await db.execute("SELECT trigger, level FROM trigger_mastery WHERE user_id=?", (user_id,))
        mastery = {r[0]: r[1] for r in await cursor.fetchall()}

    equipped_map = {slot: trig for trig, slot in loadout_rows}

    embed = discord.Embed(
        title       = f"🎒 {interaction.user.display_name}'s Inventory",
        description = f"<:Border:1519494342799130695> Border Agent  ·  **{get_rank(elo)}**",
        color       = COLOR)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    # Currency row
    embed.add_field(name="<:TrionCube:1519499035613073438> Trion", value=f"**{trion}** ({trion_rarity(trion)})", inline=True)
    embed.add_field(name="<:Yen:1519498350364332082> Credits", value=f"**{credits}**", inline=True)
    embed.add_field(name="🎰 Spins", value=f"**{spins}**", inline=True)

    # Equipped loadout
    loadout_lines = []
    for slot in LOADOUT_SLOTS:
        trig = equipped_map.get(slot, "—")
        if trig != "—":
            tdata = get_trigger(trig)
            tag = ""
            if tdata and tdata.get("black_trigger"):
                tag = " 🌑"
            loadout_lines.append(f"**{slot}:** <:Trigger:1518993124406333661> {trig}{tag}")
        else:
            loadout_lines.append(f"**{slot}:** —")
    embed.add_field(name="⚡ Equipped Loadout", value="\n".join(loadout_lines), inline=False)

    # All owned triggers
    if owned_triggers:
        trigger_lines = []
        for trig in owned_triggers:
            tdata = get_trigger(trig)
            t_type = tdata["type"].capitalize() if tdata else "?"
            black_tag = " 🌑 Black" if tdata and tdata.get("black_trigger") else ""
            lvl = mastery.get(trig, 1)
            equipped_tag = " ✅" if trig in equipped_map.values() else ""
            trigger_lines.append(
                f"<:Trigger:1518993124406333661> **{trig}**  ·  {t_type}{black_tag}  ·  Lv.{lvl}{equipped_tag}")
        # Discord embed field value max 1024 chars — chunk if needed
        text = "\n".join(trigger_lines)
        if len(text) <= 1024:
            embed.add_field(name=f"📦 Owned Triggers ({len(owned_triggers)})", value=text, inline=False)
        else:
            # Split into two fields
            mid = len(trigger_lines) // 2
            embed.add_field(name=f"📦 Owned Triggers ({len(owned_triggers)}) — 1/2",
                            value="\n".join(trigger_lines[:mid]), inline=False)
            embed.add_field(name=f"📦 Owned Triggers — 2/2",
                            value="\n".join(trigger_lines[mid:]), inline=False)
    else:
        embed.add_field(name="📦 Owned Triggers", value="*No triggers owned yet. Use `/shop` to buy some!*", inline=False)

    embed.set_footer(text="🌑 = Black Trigger  |  ✅ = Currently equipped  |  Use /equip to change loadout")
    await interaction.response.send_message(embed=embed)

# ============================================================
# /spin  (interactive embed with spin buttons)
# ============================================================
class SpinView(discord.ui.View):
    """An interactive spin panel.  Click a button to spend a spin and reroll."""

    def __init__(self, user_id: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.last_result = None
        self._refresh_state()

    async def _refresh_state(self):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT spins, trion, side_effect FROM agents WHERE user_id=?", (self.user_id,))
            self.spins, self.trion, self.side_json = await cursor.fetchone()
        self.side = json.loads(self.side_json) if self.side_json else None

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title       = "🎰 Trion Spin Panel",
            description = "Spend a spin to reroll your **Trion** level or **Side Effect**.\n"
                          "Each spin is final — choose wisely!",
            color       = COLOR)
        embed.add_field(name="<:TrionCube:1519499035613073438> Current Trion",
                        value=f"**{self.trion}** ({trion_rarity(self.trion)})", inline=True)
        embed.add_field(name="🧬 Current Side Effect",
                        value=self.side["name"] if self.side else "None", inline=True)
        embed.add_field(name="🎰 Spins Remaining", value=f"**{self.spins}**", inline=False)
        if self.last_result:
            embed.add_field(name="🎲 Last Result", value=self.last_result, inline=False)
        if self.spins <= 0:
            embed.set_footer(text="Out of spins — earn more via missions, expeditions & duels!")
        return embed

    def _update_buttons(self):
        for child in self.children:
            child.disabled = self.spins <= 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your spin panel!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Spin Trion", style=discord.ButtonStyle.primary, emoji="<:TrionCube:1519499035613073438>")
    async def spin_trion(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._do_spin(interaction, "trion")

    @discord.ui.button(label="Spin Side Effect", style=discord.ButtonStyle.success, emoji="🧬")
    async def spin_side(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._do_spin(interaction, "side_effect")

    async def _do_spin(self, interaction: discord.Interaction, spin_type: str):
        await self._refresh_state()
        if self.spins <= 0:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ No Spins Left",
                                    description="You've used all your spins.",
                                    color=0xe74c3c), ephemeral=True)
            return

        new_spins = self.spins - 1
        async with aiosqlite.connect(DB_NAME) as db:
            if spin_type == "trion":
                old_val = self.trion
                new_val = roll_trion()
                await db.execute("UPDATE agents SET trion=?, spins=? WHERE user_id=?",
                                 (new_val, new_spins, self.user_id))
                self.last_result = (f"<:TrionCube:1519499035613073438> Trion: **{old_val}** → **{new_val}** "
                                    f"({trion_rarity(new_val)})")
            else:
                old_name = self.side["name"] if self.side else "None"
                new_side = roll_side_effect()
                new_name = new_side["name"] if new_side else "None"
                await db.execute("UPDATE agents SET side_effect=?, spins=? WHERE user_id=?",
                                 (json.dumps(new_side) if new_side else None, new_spins, self.user_id))
                self.last_result = f"🧬 Side Effect: **{old_name}** → **{new_name}**"
            await db.commit()
        await self._refresh_state()
        self._update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


@bot.tree.command(name="spin", description="Open the spin panel to reroll Trion or Side Effect")
async def spin(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    view = SpinView(interaction.user.id)
    await view._refresh_state()
    view._update_buttons()
    await interaction.response.send_message(embed=view.build_embed(), view=view)

# ============================================================
# /stats  /upgradestat
# ============================================================
@bot.tree.command(name="stats", description="View your agent stats")
async def stats(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception, stat_points "
            "FROM agent_stats WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        cursor2 = await db.execute("SELECT elo FROM agents WHERE user_id=?", (user_id,))
        elo_row = await cursor2.fetchone()

    attack, defense, mobility, intelligence, trion_control, perception, points = row
    elo  = elo_row[0] if elo_row else 1000
    rank = get_rank(elo)
    cap  = get_stat_cap(elo)
    used = (attack + defense + mobility + intelligence + trion_control + perception) - 6

    embed = discord.Embed(title="📊 Agent Stats", color=COLOR)
    for name_, val in [("⚔️ Attack", attack), ("🛡 Defense", defense), ("🏃 Mobility", mobility),
                       ("🧠 Intelligence", intelligence), ("<:TrionCube:1519499035613073438> Trion Control", trion_control), ("👁 Perception", perception)]:
        embed.add_field(name=name_, value=f"{val}  {stat_bar(min(val, 10))}", inline=True)
    embed.add_field(name="⭐ Unspent Points", value=points, inline=False)
    embed.add_field(name="📈 Cap",
                    value=f"{used}/{cap} used · **{rank}**" +
                          (" · B-Rank unlocks more" if rank == "C-Rank" else
                           " · A-Rank unlocks more" if rank == "B-Rank" else " · Max"),
                    inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="upgradestat", description="Spend a stat point")
@app_commands.describe(stat="attack / defense / mobility / intelligence / trion_control / perception")
async def upgradestat(interaction: discord.Interaction, stat: str):
    if not await agent_required(interaction):
        return
    user_id     = interaction.user.id
    stat        = stat.lower()
    valid_stats = ["attack", "defense", "mobility", "intelligence", "trion_control", "perception"]
    if stat not in valid_stats:
        await interaction.response.send_message(f"Invalid stat. Choose: {', '.join(valid_stats)}", ephemeral=True)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception, stat_points "
            "FROM agent_stats WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        if not row or row[6] <= 0:
            await interaction.response.send_message("No stat points available.", ephemeral=True)
            return

        cursor2 = await db.execute("SELECT elo FROM agents WHERE user_id=?", (user_id,))
        elo_row = await cursor2.fetchone()
        elo     = elo_row[0] if elo_row else 1000
        used    = sum(row[:6]) - 6
        cap     = get_stat_cap(elo)
        rank    = get_rank(elo)

        if used >= cap:
            next_rank = "B-Rank" if rank == "C-Rank" else "A-Rank" if rank == "B-Rank" else None
            msg = f"You've hit the **{rank}** cap ({cap} points)."
            if next_rank:
                msg += f"\nReach **{next_rank}** to unlock more."
            await interaction.response.send_message(
                embed=discord.Embed(title="⛔ Stat Cap Reached", description=msg, color=0xe74c3c),
                ephemeral=True)
            return

        await db.execute(
            f"UPDATE agent_stats SET {stat}={stat}+1, stat_points=stat_points-1 WHERE user_id=?",
            (user_id,))
        await db.commit()

    await interaction.response.send_message(
        embed=discord.Embed(title="✅ Stat Upgraded",
                            description=f"**{stat.replace('_', ' ').title()}** +1",
                            color=COLOR))

# ============================================================
# /leaderboard
# ============================================================
@bot.tree.command(name="leaderboard", description="Top 10 agents by ELO")
async def leaderboard(interaction: discord.Interaction):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT user_id, elo, class FROM agents ORDER BY elo DESC LIMIT 10")
        data = await cursor.fetchall()
    if not data:
        await interaction.response.send_message("No agents yet.", ephemeral=True)
        return
    embed = discord.Embed(title="🏆 Top Border Agents", color=0xf1c40f)
    for i, (uid, elo, cls) in enumerate(data, 1):
        try:
            user = await bot.fetch_user(uid)
            name = user.display_name
        except Exception:
            name = f"Agent {uid}"
        cls_emoji = CLASSES[cls]["emoji"] if cls and cls in CLASSES else "❓"
        embed.add_field(
            name  = f"{i}. {name}",
            value = f"{cls_emoji} {get_rank(elo)} · ELO: {elo}",
            inline=False)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /arena  (turn-based PvE)
# ============================================================
@bot.tree.command(name="arena", description="Enter the turn-based Solo Arena")
async def arena(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id

    now  = time.time()
    last = _arena_cooldowns.get(user_id, 0)
    if now - last < ARENA_COOLDOWN:
        await interaction.response.send_message(
            embed=cooldown_embed(ARENA_COOLDOWN - (now - last)), ephemeral=True)
        return
    _arena_cooldowns[user_id] = now

    data = await _fetch_player_combat_data(user_id)
    if not data:
        await interaction.response.send_message("Registration data not found.", ephemeral=True)
        return

    # ── Balanced Neighbor wave ──
    # Previously the AI's HP was ``total_dmg * 10`` (huge) and its per-turn
    # damage was the SUM of every neighbour's damage (often 1-shotting rookies).
    # Now: AI HP = sum of individual neighbour HP (reasonable), and AI damage =
    # the AVERAGE neighbour damage (one attack per turn, not a combined nuke).
    wave_count  = random.randint(2, 3)
    enemy_names = []
    total_hp    = 0
    total_dmg   = 0
    for _ in range(wave_count):
        name, hp, dmg = random_neighbor()
        enemy_names.append(name)
        total_hp  += hp
        total_dmg += dmg
    avg_dmg = total_dmg // max(1, wave_count)

    ai = {
        "name":      f"Neighbor Wave: {', '.join(enemy_names)}",
        "trion":     total_hp,
        "max_trion": total_hp,
        "damage":    avg_dmg,
    }

    player = {
        "user": interaction.user,
        "name": interaction.user.display_name,
        **data,
    }

    elo   = data["elo"]
    wins  = data["wins"]
    losses= data["losses"]
    triggers = data["triggers"]

    async def arena_callback(won: bool, bailout: bool, final_hp: int):
        async with aiosqlite.connect(DB_NAME) as db:
            new_elo = win_elo(elo) if won else lose_elo(elo)
            w = wins   + (1 if won  else 0)
            l = losses + (0 if won  else 1)
            if won:
                await db.execute("UPDATE agent_stats SET stat_points=stat_points+1 WHERE user_id=?", (user_id,))
                await db.execute("UPDATE agents SET skill_points=skill_points+1 WHERE user_id=?", (user_id,))
                for t in triggers:
                    await gain_trigger_xp(db, user_id, t, random.randint(8, 15))
                await update_daily_missions(user_id, "arena_wins")
                # Each neighbour in the defeated wave counts toward kill missions.
                await update_daily_missions(user_id, "neighbor_kills", count=wave_count)
            # Trion is a permanent stat — do NOT overwrite it with battle HP.
            await db.execute(
                "UPDATE agents SET elo=?, wins=?, losses=? WHERE user_id=?",
                (new_elo, w, l, user_id))
            await db.commit()

    view = TurnBattleView(
        channel        = interaction.channel,
        player         = player,
        ai             = ai,
        callback       = arena_callback,
        squad_operator = data["squad_operator"],
    )
    await interaction.response.send_message(
        f"⚔️ **{interaction.user.display_name}** enters the arena!\n"
        f"Turn 1 — make your move!\n"
        f"👾 {wave_count} Neighbours incoming: {', '.join(enemy_names)}",
        view=view)

# ============================================================
# /duel  (turn-based PvP)
# ============================================================
@bot.tree.command(name="duel", description="Challenge another player to a turn-based duel")
@app_commands.describe(opponent="The player to challenge")
async def duel(interaction: discord.Interaction, opponent: discord.Member):
    if not await agent_required(interaction):
        return
    if opponent.id == interaction.user.id:
        await interaction.response.send_message("You can't duel yourself!", ephemeral=True)
        return
    if opponent.bot:
        await interaction.response.send_message("You can't duel a bot!", ephemeral=True)
        return
    if not await agent_exists(opponent.id):
        await interaction.response.send_message(f"{opponent.mention} is not a Border agent.", ephemeral=True)
        return

    embed = discord.Embed(
        title       = "⚔️ Duel Challenge!",
        description = f"{interaction.user.mention} challenges {opponent.mention}!",
        color       = 0xe74c3c)
    embed.set_footer(text="The challenged player has 60 seconds to accept.")
    await interaction.response.send_message(
        embed  = embed,
        view   = DuelAcceptView(interaction.user, opponent))

async def _start_duel(interaction: discord.Interaction, challenger: discord.Member, opponent: discord.Member):
    p1_data = await _fetch_player_combat_data(challenger.id)
    p2_data = await _fetch_player_combat_data(opponent.id)
    if not p1_data or not p2_data:
        await interaction.followup.send("One player's data was not found.", ephemeral=True)
        return

    async def duel_callback(winner, loser, final_trion1, final_trion2):
        async with aiosqlite.connect(DB_NAME) as db:
            if winner:
                w_id = winner["user"].id
                l_id = loser["user"].id
                w_elo = win_elo(p1_data["elo"] if w_id == challenger.id else p2_data["elo"])
                l_elo = lose_elo(p1_data["elo"] if l_id == challenger.id else p2_data["elo"])
                await db.execute("UPDATE agents SET elo=?, wins=wins+1 WHERE user_id=?",   (w_elo, w_id))
                await db.execute("UPDATE agents SET elo=?, losses=losses+1 WHERE user_id=?", (l_elo, l_id))
                await db.execute("UPDATE agent_stats SET stat_points=stat_points+1 WHERE user_id=?", (w_id,))
                await db.execute("UPDATE agents SET skill_points=skill_points+1 WHERE user_id=?", (w_id,))
                for t in winner["triggers"]:
                    await gain_trigger_xp(db, w_id, t, random.randint(8, 15))
                await update_daily_missions(w_id, "duel_wins")
            # Trion is permanent — battle HP is no longer written back to the DB.
            await db.commit()

    player1 = {"user": challenger, "name": challenger.display_name, **p1_data}
    player2 = {"user": opponent,   "name": opponent.display_name,   **p2_data}

    view = DuelTurnView(player1, player2, callback=duel_callback)
    await interaction.followup.send(
        f"⚔️ **{challenger.display_name}** vs **{opponent.display_name}**!\n"
        f"Turn 1 — {challenger.display_name}'s move!",
        view=view)

# ============================================================
# /mission  (random defense mission, turn-based PvE)
# ============================================================
@bot.tree.command(name="mission", description="Accept a random defence mission")
async def mission(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id

    now  = time.time()
    last = _arena_cooldowns.get(user_id, 0)
    if now - last < ARENA_COOLDOWN:
        await interaction.response.send_message(
            embed=cooldown_embed(ARENA_COOLDOWN - (now - last)), ephemeral=True)
        return
    _arena_cooldowns[user_id] = now

    data = await _fetch_player_combat_data(user_id)
    if not data:
        return

    mission_types = ["Civilian Rescue", "Neighbor Ambush", "Supply Defence", "HQ Breach Response"]
    mission_desc  = random.choice(mission_types)
    wave_count    = random.randint(2, 4)
    enemy_names   = []
    total_hp      = 0
    total_dmg     = 0
    for _ in range(wave_count):
        name, hp, dmg = random_neighbor()
        enemy_names.append(name)
        total_hp  += hp
        total_dmg += dmg
    avg_dmg = total_dmg // max(1, wave_count)

    ai = {
        "name":      f"{mission_desc} — {', '.join(enemy_names)}",
        "trion":     total_hp,
        "max_trion": total_hp,
        "damage":    avg_dmg,
    }
    player   = {"user": interaction.user, "name": interaction.user.display_name, **data}
    triggers = data["triggers"]

    async def mission_callback(won: bool, bailout: bool, final_hp: int):
        async with aiosqlite.connect(DB_NAME) as db:
            if won:
                bonus_credits = random.randint(50, 200)
                await db.execute("UPDATE agents SET credits=credits+?, spins=spins+1 WHERE user_id=?",
                                 (bonus_credits, user_id))
                await db.execute("UPDATE agent_stats SET stat_points=stat_points+1 WHERE user_id=?", (user_id,))
                for t in triggers:
                    await gain_trigger_xp(db, user_id, t, random.randint(10, 20))
                await update_daily_missions(user_id, "mission_wins")
                await update_daily_missions(user_id, "neighbor_kills", count=wave_count)
            # Trion is a permanent stat — do not overwrite with battle HP.
            await db.commit()

    view = TurnBattleView(
        channel        = interaction.channel,
        player         = player,
        ai             = ai,
        callback       = mission_callback,
        squad_operator = data["squad_operator"],
    )
    await interaction.response.send_message(
        f"🆘 **{mission_desc}!** Defend against the Neighbors!\nTurn 1 — make your move!",
        view=view)

# ============================================================
# /story  /storymission
# ============================================================
@bot.tree.command(name="story", description="View your current story mission")
async def story(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT arc, chapter, mission FROM story_progress WHERE user_id=?", (user_id,))
        row    = await cursor.fetchone()
        if not row:
            await db.execute("INSERT OR IGNORE INTO story_progress (user_id) VALUES (?)", (user_id,))
            await db.commit()
            arc, chapter, mission_num = "Prologue", 1, 1
        else:
            arc, chapter, mission_num = row

        cursor = await db.execute(
            "SELECT type, description, choices, reward_type, reward_amount, reward_trigger, replayable "
            "FROM story_missions WHERE arc=? AND chapter=? AND mission=?",
            (arc, chapter, mission_num))
        mission_data = await cursor.fetchone()

    if not mission_data:
        await interaction.response.send_message(
            embed=discord.Embed(title="📖 Story Complete",
                                description="You've finished all current missions. More coming soon!",
                                color=COLOR))
        return

    m_type, desc, choices_json, r_type, r_amount, r_trigger, replayable = mission_data
    embed = discord.Embed(
        title       = f"📖 {arc} — Chapter {chapter}, Mission {mission_num}",
        description = desc,
        color       = COLOR)
    if m_type == "choice":
        embed.add_field(name="Choices", value="Use `/storymission` to make your choice.", inline=False)
    embed.add_field(name="🎁 Reward",
                    value=f"{r_amount} {r_type}" + (f" · Trigger: {r_trigger}" if r_trigger else ""),
                    inline=True)
    embed.add_field(name="🔁 Type", value="Replayable" if replayable else "One-time", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="storymission", description="Play your current story mission")
async def storymission(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT arc, chapter, mission FROM story_progress WHERE user_id=?", (user_id,))
        row    = await cursor.fetchone()
        if not row:
            await db.execute("INSERT OR IGNORE INTO story_progress (user_id) VALUES (?)", (user_id,))
            await db.commit()
            arc, chapter, mission_num = "Prologue", 1, 1
        else:
            arc, chapter, mission_num = row

        cursor = await db.execute(
            "SELECT type, description, choices, reward_type, reward_amount, reward_trigger, replayable "
            "FROM story_missions WHERE arc=? AND chapter=? AND mission=?",
            (arc, chapter, mission_num))
        mission_data = await cursor.fetchone()

    if not mission_data:
        await interaction.response.send_message("No mission found — you may have finished the story!")
        return

    m_type, desc, choices_json, r_type, r_amount, r_trigger, _ = mission_data

    if m_type in ("arena", "boss"):
        await _story_arena(interaction, arc, chapter, mission_num, m_type, r_type, r_amount, r_trigger)
    elif m_type == "choice":
        await _story_choice(interaction, arc, chapter, mission_num, choices_json, r_type, r_amount, r_trigger)
    elif m_type == "exploration":
        await _story_exploration(interaction, arc, chapter, mission_num, desc, r_type, r_amount, r_trigger)

async def _story_arena(interaction, arc, chapter, mission_num, m_type, r_type, r_amount, r_trigger):
    user_id = interaction.user.id

    # ── Build the enemy ──────────────────────────────────────
    # Boss missions use the lore-accurate boss (Viza, Enedora, Hyrein, Radar)
    # rather than a random neighbour.  Arena missions still use neighbour waves.
    boss_key = BOSS_MISSIONS.get((chapter, mission_num))
    is_boss  = m_type == "boss"

    if is_boss and boss_key and boss_key in BOSSES:
        boss       = BOSSES[boss_key]
        boss_hp    = boss["hp"]
        boss_dmg   = boss["damage"]
        boss_name  = boss_key
        boss_title = boss["title"]
        boss_desc  = boss["description"]
    elif is_boss:
        # Fallback — should not normally happen, but keeps the bot alive.
        boss_name, boss_hp, boss_dmg = random_neighbor()
        boss_title = "Mysterious Foe"
        boss_desc  = "An unknown enemy appears!"
    else:
        boss_name = None  # arena — use a neighbour wave

    # Fetch the player's combat data (loads trion, side effect, triggers,
    # stats, mastery, skills, squad operator all at once).
    data = await _fetch_player_combat_data(user_id)
    if not data:
        await interaction.response.send_message("Registration data not found.", ephemeral=True)
        return

    triggers = data["triggers"]
    player   = {"user": interaction.user, "name": interaction.user.display_name, **data}

    wave_count_holder = 0  # set properly below for arena missions

    # Build the AI dict for the TurnBattleView.
    if is_boss:
        ai = {
            "name":      f"🌑 {boss_name} — {boss_title}",
            "trion":     boss_hp,
            "max_trion": boss_hp,
            "damage":    boss_dmg,
        }
        intro = (f"🛡️ **Boss Fight!**\n{boss_desc}\n\n"
                 f"🌑 **{boss_name}** ({boss_title}) blocks your path!\n"
                 f"Turn 1 — make your move!")
    else:
        wave_count  = random.randint(2, 3)
        enemy_names = []
        total_hp    = 0
        total_dmg   = 0
        for _ in range(wave_count):
            name_, hp, dmg = random_neighbor()
            enemy_names.append(name_)
            total_hp  += hp
            total_dmg += dmg
        avg_dmg = total_dmg // max(1, wave_count)
        ai = {
            "name":      f"Neighbor Squad: {', '.join(enemy_names)}",
            "trion":     total_hp,
            "max_trion": total_hp,
            "damage":    avg_dmg,
        }
        wave_count_holder = wave_count
        intro = (f"⚔️ **Story Battle**\n"
                 f"Turn 1 — make your move!\n"
                 f"👾 {wave_count} Neighbours incoming: {', '.join(enemy_names)}")

    async def story_callback(won: bool, bailout: bool, final_hp: int):
        async with aiosqlite.connect(DB_NAME) as db:
            await _give_story_rewards(db, user_id, r_type, r_amount, r_trigger, won)
            if won:
                if is_boss:
                    await update_daily_missions(user_id, "boss_kills")
                    await update_daily_missions(user_id, "neighbor_kills", count=1)
                else:
                    await update_daily_missions(user_id, "neighbor_kills", count=wave_count_holder)
            await _advance_story(db, user_id, arc, chapter, mission_num)
            await db.commit()

    view = TurnBattleView(
        channel        = interaction.channel,
        player         = player,
        ai             = ai,
        callback       = story_callback,
        squad_operator = data["squad_operator"],
    )
    await interaction.response.send_message(intro, view=view)

async def _story_choice(interaction, arc, chapter, mission_num, choices_json, r_type, r_amount, r_trigger):
    choices = json.loads(choices_json)
    view    = discord.ui.View(timeout=60)

    async def _on_choice(inter: discord.Interaction, choice_label: str):
        async with aiosqlite.connect(DB_NAME) as db:
            await _give_story_rewards(db, inter.user.id, r_type, r_amount, r_trigger, True)
            await _advance_story(db, inter.user.id, arc, chapter, mission_num)
            await db.commit()
        await inter.response.edit_message(
            content=f"You chose **{choice_label}**. The story continues…", embed=None, view=None)

    for c in choices:
        btn          = discord.ui.Button(label=c["label"], style=discord.ButtonStyle.primary)
        btn.callback = lambda inter, lbl=c["label"]: _on_choice(inter, lbl)
        view.add_item(btn)

    embed = discord.Embed(title="📜 Choice Mission", description="Choose your path wisely.", color=COLOR)
    embed.set_footer(text=f"Reward: {r_amount} {r_type}" + (f" · {r_trigger}" if r_trigger else ""))
    await interaction.response.send_message(embed=embed, view=view)

async def _story_exploration(interaction, arc, chapter, mission_num, desc, r_type, r_amount, r_trigger):
    embed = discord.Embed(title="🔍 Exploration Mission", description=desc, color=COLOR)
    embed.set_footer(text=f"Reward: {r_amount} {r_type}" + (f" · {r_trigger}" if r_trigger else ""))
    await interaction.response.send_message(embed=embed)
    async with aiosqlite.connect(DB_NAME) as db:
        await _give_story_rewards(db, interaction.user.id, r_type, r_amount, r_trigger, True)
        await _advance_story(db, interaction.user.id, arc, chapter, mission_num)
        await db.commit()

# ============================================================
# SQUAD COMMANDS
# ============================================================
@bot.tree.command(name="squadcreate", description="Create a squad")
@app_commands.describe(name="Squad name")
async def squadcreate(interaction: discord.Interaction, name: str):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT 1 FROM squad_members WHERE user_id=?", (user_id,))
        if await cursor.fetchone():
            await interaction.response.send_message("You are already in a squad.", ephemeral=True)
            return
        await db.execute("INSERT INTO squads (name, leader_id) VALUES (?,?)", (name, user_id))
        cursor   = await db.execute("SELECT squad_id FROM squads WHERE leader_id=?", (user_id,))
        squad_id = (await cursor.fetchone())[0]
        await db.execute("INSERT INTO squad_members (squad_id, user_id, role) VALUES (?,?,?)",
                         (squad_id, user_id, "Leader"))
        await db.commit()
    await interaction.response.send_message(
        embed=discord.Embed(title="🛡 Squad Created", description=f"**{name}** is ready!", color=COLOR))

@bot.tree.command(name="squadinvite", description="Invite a player to your squad")
@app_commands.describe(member="The player to invite")
async def squadinvite(interaction: discord.Interaction, member: discord.Member):
    if not await agent_required(interaction):
        return
    if not await agent_exists(member.id):
        await interaction.response.send_message(f"{member.mention} is not a Border agent.", ephemeral=True)
        return
    inviter = interaction.user.id
    target  = member.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT squad_id, role FROM squad_members WHERE user_id=?", (inviter,))
        row    = await cursor.fetchone()
        if not row or row[1] != "Leader":
            await interaction.response.send_message("Only squad leaders can invite.", ephemeral=True)
            return
        squad_id = row[0]

        cursor = await db.execute("SELECT 1 FROM squad_members WHERE user_id=?", (target,))
        if await cursor.fetchone():
            await interaction.response.send_message("That player is already in a squad.", ephemeral=True)
            return

        cursor = await db.execute("SELECT COUNT(*) FROM squad_members WHERE squad_id=?", (squad_id,))
        if (await cursor.fetchone())[0] >= 5:
            await interaction.response.send_message("Squad is full (max 5).", ephemeral=True)
            return

        await db.execute("INSERT INTO squad_members (squad_id, user_id, role) VALUES (?,?,?)",
                         (squad_id, target, "Member"))
        await db.commit()
    await interaction.response.send_message(
        embed=discord.Embed(title="📨 Squad Update",
                            description=f"{member.mention} has joined your squad!",
                            color=COLOR))

@bot.tree.command(name="squadinfo", description="View your squad info")
async def squadinfo(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT squad_id FROM squad_members WHERE user_id=?", (user_id,))
        row    = await cursor.fetchone()
        if not row:
            await interaction.response.send_message("You are not in a squad.", ephemeral=True)
            return
        squad_id = row[0]
        cursor   = await db.execute("SELECT name, division, elo, operator FROM squads WHERE squad_id=?", (squad_id,))
        name, division, elo, operator = await cursor.fetchone()
        cursor   = await db.execute("SELECT user_id, role FROM squad_members WHERE squad_id=?", (squad_id,))
        members  = await cursor.fetchall()

    lines = ""
    for uid, role in members:
        try:
            u = await bot.fetch_user(uid)
            lines += f"**{u.display_name}** — {role}\n"
        except Exception:
            lines += f"Unknown ({uid}) — {role}\n"

    embed = discord.Embed(title=f"🛡 Squad: {name}", color=COLOR)
    embed.add_field(name="Division", value=division)
    embed.add_field(name="ELO",      value=elo)
    embed.add_field(name="Operator", value=operator or "None")
    embed.add_field(name="Members",  value=lines or "None", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="squadleave", description="Leave your squad")
async def squadleave(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM squad_members WHERE user_id=?", (interaction.user.id,))
        await db.commit()
    await interaction.response.send_message(
        embed=discord.Embed(title="🚪 Left Squad", description="You've left your squad.", color=COLOR))

# ============================================================
# /operator
# ============================================================
@bot.tree.command(name="operator", description="Assign an operator to your squad")
@app_commands.describe(operator_name="Shiori / Asami / Hana")
async def operator(interaction: discord.Interaction, operator_name: str):
    if not await agent_required(interaction):
        return
    operator_name = operator_name.title()
    if operator_name not in OPERATORS:
        await interaction.response.send_message(
            f"Invalid operator. Choose from: {', '.join(OPERATORS.keys())}", ephemeral=True)
        return
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT squad_id FROM squad_members WHERE user_id=? AND role='Leader'", (user_id,))
        row = await cursor.fetchone()
        if not row:
            await interaction.response.send_message("You must be a squad leader.", ephemeral=True)
            return
        await db.execute("UPDATE squads SET operator=? WHERE squad_id=?", (operator_name, row[0]))
        await db.commit()
    op = OPERATORS[operator_name]
    await interaction.response.send_message(
        embed=discord.Embed(title=f"📡 Operator Assigned: {operator_name}",
                            description=f"Battle ability: **{op['battle_effect']['type']}**",
                            color=COLOR))

# ============================================================
# /expedition
# ============================================================
@bot.tree.command(name="expedition", description="Go on a 4-hour expedition (B-Rank+)")
async def expedition(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT elo, expedition_end FROM agents WHERE user_id=?", (user_id,))
        elo, end_time = await cursor.fetchone()

    if get_rank(elo) not in ("B-Rank", "A-Rank"):
        await interaction.response.send_message("You must be **B-Rank** or higher.", ephemeral=True)
        return

    now = time.time()
    if end_time and end_time > now:
        remaining = int(end_time - now)
        await interaction.response.send_message(
            embed=discord.Embed(title="🌌 Already on Expedition",
                                description=f"Returns in **{remaining//3600}h {(remaining%3600)//60}m**.",
                                color=0xe67e22),
            ephemeral=True)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE agents SET expedition_end=? WHERE user_id=?", (now + EXPEDITION_DURATION, user_id))
        await db.commit()
    await update_daily_missions(user_id, "expedition")
    await interaction.response.send_message(
        embed=discord.Embed(title="🌌 Expedition Started",
                            description="You've headed into the field. Check `/profile` in 4 hours for rewards!",
                            color=COLOR))

# ============================================================
# /bailout
# ============================================================
@bot.tree.command(name="bailout", description="Emergency bail-out — costs Trion")
async def bailout(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT trion FROM agents WHERE user_id=?", (user_id,))
        trion  = (await cursor.fetchone())[0]
        if trion <= 1:
            await interaction.response.send_message("Not enough Trion to bail out.", ephemeral=True)
            return
        cost = max(1, trion // 3)
        await db.execute("UPDATE agents SET trion=trion-? WHERE user_id=?", (cost, user_id))
        await db.commit()
    await interaction.response.send_message(
        embed=discord.Embed(title="🚀 Bail Out!",
                            description=f"You escaped safely. Lost **{cost}** Trion.",
                            color=0x3498db))

# ============================================================
# /trionrank
# ============================================================
@bot.tree.command(name="trionrank", description="Check your Border division rank")
async def trionrank(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT elo, class FROM agents WHERE user_id=?", (interaction.user.id,))
        elo, cls = await cursor.fetchone()

    rank    = get_rank(elo)
    descs   = {"C-Rank": "New trainees learning the ropes.",
               "B-Rank": "Experienced agents trusted with dangerous missions.",
               "A-Rank": "Elite operators — the backbone of Border."}
    next_elo = "1200+" if rank == "C-Rank" else "1600+" if rank == "B-Rank" else "MAX"

    embed = discord.Embed(title=f"🏅 Border Rank: {rank}", description=descs[rank],
                          color=RANK_COLORS[rank])
    embed.add_field(name="ELO",        value=elo)
    embed.add_field(name="Class",      value=f"{CLASSES[cls]['emoji']} {cls}" if cls else "None")
    embed.add_field(name="Next Rank",  value=next_elo)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /simulation
# ============================================================
@bot.tree.command(name="simulation", description="Practice your trigger combo risk-free")
async def simulation(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor   = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (user_id,))
        triggers = [r[0] for r in await cursor.fetchall()]

    if not triggers:
        await interaction.response.send_message("You have no triggers equipped. Use `/equip` first.", ephemeral=True)
        return

    lines = "\n".join(
        f"⚙️ **{t}** — {get_trigger(t)['type'].capitalize()}" for t in triggers if get_trigger(t))
    embed = discord.Embed(title="🎮 Trigger Simulation", description="Risk-free practice session.", color=COLOR)
    embed.add_field(name="Equipped Loadout", value=lines or "None", inline=False)
    embed.add_field(name="Result", value="✅ All triggers fired successfully. No Trion consumed.", inline=False)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /combostats
# ============================================================
@bot.tree.command(name="combostats", description="Preview your estimated damage output (uses your real stats)")
async def combostats(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT trion, side_effect, class, faction FROM agents WHERE user_id=?", (user_id,))
        trion, side, cls, fac = await cursor.fetchone()
        side = json.loads(side) if side else None

        cursor   = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (user_id,))
        triggers = [r[0] for r in await cursor.fetchall()]

        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception FROM agent_stats WHERE user_id=?",
            (user_id,))
        s = await cursor.fetchone() or (1,1,1,1,1,1)
        stats = {"attack":s[0],"defense":s[1],"mobility":s[2],
                 "intelligence":s[3],"trion_control":s[4],"perception":s[5]}

        cursor = await db.execute("SELECT skill_name, level FROM agent_skills WHERE user_id=?", (user_id,))
        skills = {r[0]: r[1] for r in await cursor.fetchall()}

        cursor = await db.execute("SELECT trigger, level FROM trigger_mastery WHERE user_id=?", (user_id,))
        mastery = {r[0]: r[1] for r in await cursor.fetchall()}

    # ── Damage breakdown ──
    # calculate_damage() DOES use stats, but the old /combostats only showed a
    # single random number, making it look like stats were ignored.  Now we
    # compute several variants side-by-side so the contribution of each layer
    # is visible, plus a per-move breakdown for the equipped main trigger.

    # 1. Base — trion only, no stats/triggers/faction/skills (no move multiplier)
    base_only = await calculate_damage(user_id, trion, None, None,
                                        {k: 0 for k in stats}, faction=None, skills=None)
    # 2. Trion + stats only (no triggers, no faction, no skills)
    with_stats = await calculate_damage(user_id, trion, None, None, stats, faction=None, skills=None)
    # 3. Trion + stats + triggers
    with_triggers = await calculate_damage(user_id, trion, None, triggers, stats, faction=None, skills=None)
    # 4. Everything (stats + triggers + faction + skills + side effect)
    full = await calculate_damage(user_id, trion, side, triggers, stats,
                                   attacker_class=cls, faction=fac, skills=skills)

    embed = discord.Embed(title="💥 Combo Analysis", color=COLOR)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    embed.add_field(name="<:TrionCube:1519499035613073438> Trion", value=f"**{trion}** ({trion_rarity(trion)})", inline=True)
    embed.add_field(name="⚔️ Class", value=f"{CLASSES[cls]['emoji']} {cls}" if cls else "None", inline=True)
    embed.add_field(name="🏛️ Faction", value=f"{FACTIONS[fac]['emoji']} {fac}" if fac else "None", inline=True)

    embed.add_field(name="⚡ Loadout",
                    value=" | ".join(triggers) if triggers else "*Empty — equip a trigger!*",
                    inline=False)

    # Damage layer breakdown — proves stats are used
    breakdown = (f"`Base (trion only)`  →  **{base_only}**\n"
                 f"`+ Stats`             →  **{with_stats}**  *(+{with_stats - base_only})*\n"
                 f"`+ Triggers`          →  **{with_triggers}**  *(+{with_triggers - with_stats})*\n"
                 f"`+ Faction + Skills + Side Effect`  →  **{full}**  *(+{full - with_triggers})*")
    embed.add_field(name="📊 Damage Breakdown (stats ARE used!)", value=breakdown, inline=False)

    # Per-move breakdown for the main trigger
    main_trig_name = None
    main_trig_data = None
    for trig in triggers:
        tdata = get_trigger(trig)
        if tdata and tdata.get("type") == "main":
            main_trig_name = trig
            main_trig_data = tdata
            break

    if main_trig_name and main_trig_data:
        mastery_lvl = mastery.get(main_trig_name, 1)
        moves = main_trig_data.get("moves", [])
        avail_moves = [m for m in moves if m["level"] <= mastery_lvl] or moves[:1]
        move_lines = []
        for move in avail_moves:
            move_dmg = await calculate_damage(user_id, trion, side, triggers, stats,
                                               attacker_class=cls, faction=fac,
                                               skills=skills, move=move)
            cost_tag = f" ⚡{move.get('cost',0)}" if move.get('cost', 0) else ""
            move_lines.append(f"**{move['name']}**{cost_tag} → **~{move_dmg}** dmg")
        embed.add_field(name=f"🗡️ {main_trig_name} Moves (Mastery Lv.{mastery_lvl})",
                        value="\n".join(move_lines), inline=False)
    else:
        embed.add_field(name="🗡️ Moves", value="*Equip a main trigger to see per-move damage.*", inline=False)

    embed.set_footer(text="Damage has ±10 random variance per hit. Class advantage adds +30%.")
    await interaction.response.send_message(embed=embed)

# ============================================================
# /triggers_mastered
# ============================================================
@bot.tree.command(name="triggers_mastered", description="View your trigger mastery levels")
async def triggers_mastered(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT trigger, xp, level FROM trigger_mastery WHERE user_id=? ORDER BY level DESC, xp DESC",
            (interaction.user.id,))
        mastery = await cursor.fetchall()

    if not mastery:
        await interaction.response.send_message(
            "Use triggers in battle to gain mastery XP!", ephemeral=True)
        return

    embed = discord.Embed(title="🎖️ Trigger Mastery", color=COLOR)
    for trig, xp, level in mastery[:10]:
        next_xp = (level * 100)
        bar     = hp_bar(xp % 100, 100)
        embed.add_field(name=f"**{trig}**",
                        value=f"Level **{level}** · {xp} XP\n{bar} → Lv.{level+1} at {next_xp} XP",
                        inline=False)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /neighborhood
# ============================================================
@bot.tree.command(name="neighborhood", description="Scout the area for Neighbor activity")
async def neighborhood(interaction: discord.Interaction):
    name_, hp, dmg = random_neighbor()
    threat = "🟢 Low" if dmg < 5 else "🟡 Medium" if dmg < 8 else "🔴 High"
    embed  = discord.Embed(title="👁️ Neighborhood Scout Report",
                           description=f"Detected: **{name_}**", color=0xe67e22)
    embed.add_field(name="Threat Level", value=threat)
    embed.add_field(name="HP",           value=hp)
    embed.add_field(name="Damage",       value=dmg)
    embed.add_field(name="Recommended",  value="Use `/arena` to engage or `/bailout` to retreat.", inline=False)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /baseinfo  /base  /basedefend
# ============================================================
@bot.tree.command(name="baseinfo", description="Check Border HQ statistics")
async def baseinfo(interaction: discord.Interaction):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor        = await db.execute("SELECT COUNT(*) FROM agents")
        total_agents  = (await cursor.fetchone())[0]
        cursor        = await db.execute("SELECT COUNT(*) FROM squads")
        total_squads  = (await cursor.fetchone())[0]
        cursor        = await db.execute("SELECT COALESCE(SUM(credits), 0) FROM agents")
        total_credits = (await cursor.fetchone())[0]

    embed = discord.Embed(title="🏢 Border HQ Status", color=COLOR)
    embed.add_field(name="🛡 Total Agents",        value=total_agents)
    embed.add_field(name="👥 Total Squads",         value=total_squads)
    embed.add_field(name="<:Yen:1519498350364332082> Credits Circulating", value=total_credits)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="base", description="View Border Base defence status")
async def base(interaction: discord.Interaction):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor     = await db.execute("SELECT level, hp FROM base_defense LIMIT 1")
        row        = await cursor.fetchone()
        level, hp  = row if row else (1, 10000)
    bar   = hp_bar(hp, 10000)
    embed = discord.Embed(title="<:Border:1519494342799130695> Border Base", color=COLOR)
    embed.add_field(name="Level", value=level)
    embed.add_field(name="HP",    value=f"{hp:,} / 10,000  {bar}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="basedefend", description="Join the base defence (cooperative — coming soon)")
async def basedefend(interaction: discord.Interaction):
    await interaction.response.send_message(
        embed=discord.Embed(title="<:Border:1519494342799130695> Base Defence",
                            description="Cooperative base defence events are coming soon!",
                            color=COLOR))

# ============================================================
# /trainers  /train
# ============================================================
@bot.tree.command(name="trainers", description="View available Border trainers")
async def trainers(interaction: discord.Interaction):
    embed = discord.Embed(title="👨‍🏫 Border Trainers", color=COLOR)
    for trainer, d in TRAINERS.items():
        if isinstance(d["boost"], tuple):
            boost_text = f"+1 Attack, +1 Defense"
        else:
            boost_text = f"+{d['boost']} {d['specialty']}"
        embed.add_field(name=f"🧑 {trainer}",
                        value=f"{boost_text} · Cost: **{d['cost']} Credits**",
                        inline=False)
    embed.set_footer(text="Use /train <trainer_name>  ·  ⏳ 1-hour cooldown between sessions")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="train", description="Train with a Border trainer (1h cooldown)")
@app_commands.describe(trainer_name="Shinoda / Kido / Karasuma / Yūma")
async def train(interaction: discord.Interaction, trainer_name: str):
    if not await agent_required(interaction):
        return
    trainer_name = trainer_name.title()
    if trainer_name not in TRAINERS:
        await interaction.response.send_message("Invalid trainer. Use `/trainers` to see options.", ephemeral=True)
        return

    user_id = interaction.user.id

    # ── 1-hour cooldown check ──
    now  = time.time()
    last = _train_cooldowns.get(user_id, 0)
    if now - last < TRAIN_COOLDOWN:
        remaining = int(TRAIN_COOLDOWN - (now - last))
        hrs  = remaining // 3600
        mins = (remaining % 3600) // 60
        secs = remaining % 60
        time_str = f"{hrs}h {mins}m {secs}s" if hrs else (f"{mins}m {secs}s" if mins else f"{secs}s")
        await interaction.response.send_message(
            embed=discord.Embed(
                title       = "⏳ Training Cooldown",
                description = f"You can train again in **{time_str}**.\n"
                              f"Training sessions require rest between workouts.",
                color       = 0xe67e22),
            ephemeral=True)
        return

    d = TRAINERS[trainer_name]

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT credits FROM agents WHERE user_id=?", (user_id,))
        creds  = (await cursor.fetchone())[0]
        if creds < d["cost"]:
            await interaction.response.send_message(f"Need **{d['cost']}** credits.", ephemeral=True)
            return

        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception FROM agent_stats WHERE user_id=?",
            (user_id,))
        stats = await cursor.fetchone()
        cursor2 = await db.execute("SELECT elo FROM agents WHERE user_id=?", (user_id,))
        elo_row = await cursor2.fetchone()
        elo     = elo_row[0] if elo_row else 1000
        used    = sum(stats) - 6
        cap     = get_stat_cap(elo)

        boost_needed = 2 if isinstance(d["boost"], tuple) else d["boost"]
        if used + boost_needed > cap:
            await interaction.response.send_message(
                f"Not enough stat cap space. ({used}/{cap} used)", ephemeral=True)
            return

        if isinstance(d["boost"], tuple):
            s1, s2 = d["stats"]
            await db.execute(
                f"UPDATE agent_stats SET {s1}={s1}+1, {s2}={s2}+1 WHERE user_id=?", (user_id,))
        else:
            await db.execute(
                f"UPDATE agent_stats SET {d['stat']}={d['stat']}+{d['boost']} WHERE user_id=?", (user_id,))

        await db.execute("UPDATE agents SET credits=credits-? WHERE user_id=?", (d["cost"], user_id))
        await db.commit()

    # Start the cooldown AFTER a successful training session
    _train_cooldowns[user_id] = time.time()

    await interaction.response.send_message(
        embed=discord.Embed(title="💪 Training Complete!",
                            description=f"Trained with **{trainer_name}**!\n"
                                        f"⏳ Next training available in **1 hour**.",
                            color=COLOR))

# ============================================================
# /redeem
# ============================================================
@bot.tree.command(name="redeem", description="Redeem a special code for rewards")
@app_commands.describe(code="The code to redeem")
async def redeem(interaction: discord.Interaction, code: str):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id
    code    = code.upper()

    if code not in redeem_codes:
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Invalid Code", description="That code doesn't exist.", color=0xe74c3c),
            ephemeral=True)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT 1 FROM redeemed_codes WHERE user_id=? AND code=?", (user_id, code))
        if await cursor.fetchone():
            await interaction.response.send_message("You've already redeemed that code.", ephemeral=True)
            return

        rewards = redeem_codes[code]
        c       = rewards.get("credits",  0)
        s       = rewards.get("spins",    0)
        trigs   = rewards.get("triggers", [])

        await db.execute("UPDATE agents SET credits=credits+?, spins=spins+? WHERE user_id=?", (c, s, user_id))
        for t in trigs:
            await db.execute("INSERT OR IGNORE INTO triggers (user_id, trigger) VALUES (?,?)", (user_id, t))
        await db.execute("INSERT INTO redeemed_codes (user_id, code) VALUES (?,?)", (user_id, code))
        await db.commit()

    msg = []
    if c:    msg.append(f"<:Yen:1519498350364332082> +{c} Credits")
    if s:    msg.append(f"🎰 +{s} Spins")
    if trigs: msg.append(f"<:Trigger:1518993124406333661> Triggers: {', '.join(trigs)}")
    await interaction.response.send_message(
        embed=discord.Embed(title="✅ Code Redeemed!",
                            description="\n".join(msg) or "Nothing received.",
                            color=COLOR))

# ============================================================
# /triggerforge  /dismantle
# ============================================================
@bot.tree.command(name="triggerforge", description="Fuse two Main triggers into a combined trigger")
@app_commands.describe(trigger1="First trigger", trigger2="Second trigger")
async def triggerforge(interaction: discord.Interaction, trigger1: str, trigger2: str):
    if not await agent_required(interaction):
        return
    user_id  = interaction.user.id
    t1, t2   = trigger1.title(), trigger2.title()
    if t1 == t2:
        await interaction.response.send_message("Can't fuse a trigger with itself.", ephemeral=True)
        return

    combo_key = get_combo_key(t1, t2)
    if not combo_key:
        await interaction.response.send_message(
            "Those triggers can't be fused. Check `/shop` for fusable combinations.", ephemeral=True)
        return
    combo = COMBINED_TRIGGERS[combo_key]
    price = combo["price"]

    async with aiosqlite.connect(DB_NAME) as db:
        for trig in (t1, t2):
            cursor = await db.execute("SELECT 1 FROM triggers WHERE user_id=? AND trigger=?", (user_id, trig))
            if not await cursor.fetchone():
                await interaction.response.send_message(f"You don't own **{trig}**.", ephemeral=True)
                return

        cursor = await db.execute("SELECT credits FROM agents WHERE user_id=?", (user_id,))
        creds  = (await cursor.fetchone())[0]
        if creds < price:
            await interaction.response.send_message(
                f"Need **{price}** credits to forge.", ephemeral=True)
            return

        await db.execute("DELETE FROM triggers WHERE user_id=? AND trigger=?", (user_id, t1))
        await db.execute("DELETE FROM triggers WHERE user_id=? AND trigger=?", (user_id, t2))
        await db.execute("INSERT OR IGNORE INTO triggers (user_id, trigger) VALUES (?,?)",
                         (user_id, combo["name"]))
        await db.execute("UPDATE agents SET credits=credits-? WHERE user_id=?", (price, user_id))
        await db.commit()

    buffs = ", ".join(f"{k}+{v}" for k, v in combo["buffs"].items())
    await interaction.response.send_message(
        embed=discord.Embed(title="⚡ Trigger Fusion!",
                            description=f"**{t1}** + **{t2}** → **{combo['name']}**",
                            color=COLOR).add_field(name="Buffs", value=buffs))

@bot.tree.command(name="dismantle", description="Break a combined trigger back into its components")
@app_commands.describe(combined_trigger="Name of the combined trigger")
async def dismantle(interaction: discord.Interaction, combined_trigger: str):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id
    c_name  = combined_trigger.title()

    components = None
    for (t1, t2), combo in COMBINED_TRIGGERS.items():
        if combo["name"].lower() == c_name.lower():
            components = (t1, t2)
            c_name     = combo["name"]
            break
    if not components:
        await interaction.response.send_message("Not a valid combined trigger name.", ephemeral=True)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT 1 FROM triggers WHERE user_id=? AND trigger=?", (user_id, c_name))
        if not await cursor.fetchone():
            await interaction.response.send_message(f"You don't own **{c_name}**.", ephemeral=True)
            return
        await db.execute("DELETE FROM triggers WHERE user_id=? AND trigger=?", (user_id, c_name))
        for t in components:
            await db.execute("INSERT OR IGNORE INTO triggers (user_id, trigger) VALUES (?,?)", (user_id, t))
        await db.commit()

    await interaction.response.send_message(
        embed=discord.Embed(title="🔧 Trigger Dismantled",
                            description=f"**{c_name}** → **{components[0]}** + **{components[1]}**",
                            color=COLOR))

# ============================================================
# /skilltree  /upgradeskill
# ============================================================
@bot.tree.command(name="skilltree", description="View your class skill tree")
async def skilltree(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT class, skill_points FROM agents WHERE user_id=?", (user_id,))
        row    = await cursor.fetchone()
        if not row or not row[0]:
            await interaction.response.send_message("You need to set a class first with `/setclass`.", ephemeral=True)
            return
        cls, sp = row

        tree = SKILL_TREES.get(cls)
        if not tree:
            await interaction.response.send_message("Your class has no skill tree yet.", ephemeral=True)
            return

        cursor = await db.execute("SELECT skill_name, level FROM agent_skills WHERE user_id=?", (user_id,))
        player_skills = {r[0]: r[1] for r in await cursor.fetchall()}

    embed = discord.Embed(title=f"🧩 {cls} Skill Tree", color=COLOR)
    embed.add_field(name="🌟 Available Skill Points", value=sp, inline=False)
    for node in tree:
        current = player_skills.get(node["name"], 0)
        max_lvl = node.get("max_level", 3)
        bar     = stat_bar(current, length=max_lvl)
        embed.add_field(
            name  = f"{node['name']}  ({current}/{max_lvl})",
            value = f"Cost: {node['cost']} SP · {bar}\nEffect: {node['effect']}",
            inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="upgradeskill", description="Spend skill points to level up a skill")
@app_commands.describe(skill_name="The skill to upgrade")
async def upgradeskill(interaction: discord.Interaction, skill_name: str):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT class, skill_points FROM agents WHERE user_id=?", (user_id,))
        row    = await cursor.fetchone()
        if not row or not row[0]:
            await interaction.response.send_message("Set a class first with `/setclass`.", ephemeral=True)
            return
        cls, sp = row

        tree = SKILL_TREES.get(cls, [])
        node = next((n for n in tree if n["name"].lower() == skill_name.lower()), None)
        if not node:
            await interaction.response.send_message("Skill not found in your class tree.", ephemeral=True)
            return
        if sp < node["cost"]:
            await interaction.response.send_message(
                f"Not enough skill points (need {node['cost']}, have {sp}).", ephemeral=True)
            return

        cursor  = await db.execute(
            "SELECT level FROM agent_skills WHERE user_id=? AND skill_name=?", (user_id, node["name"]))
        cur_row = await cursor.fetchone()
        current = cur_row[0] if cur_row else 0
        if current >= node.get("max_level", 3):
            await interaction.response.send_message("Skill already at max level.", ephemeral=True)
            return

        new_lvl = current + 1
        await db.execute(
            "INSERT INTO agent_skills (user_id, skill_name, level) VALUES (?,?,?) "
            "ON CONFLICT(user_id, skill_name) DO UPDATE SET level=?",
            (user_id, node["name"], new_lvl, new_lvl))
        await db.execute("UPDATE agents SET skill_points=skill_points-? WHERE user_id=?",
                         (node["cost"], user_id))
        await db.commit()

    await interaction.response.send_message(
        embed=discord.Embed(title="🧩 Skill Upgraded",
                            description=f"**{node['name']}** is now Level **{new_lvl}**!",
                            color=COLOR))

# ============================================================
# /missionsboard
# ============================================================
@bot.tree.command(name="missionsboard", description="View your daily missions")
async def missionsboard(interaction: discord.Interaction):
    if not await agent_required(interaction):
        return
    user_id = interaction.user.id
    await assign_daily_missions(user_id)
    date = datetime.date.today().isoformat()

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT mission_id, progress, target, completed FROM daily_missions WHERE user_id=? AND date=?",
            (user_id, date))
        missions = await cursor.fetchall()

    if not missions:
        await interaction.response.send_message("No daily missions found.", ephemeral=True)
        return

    embed = discord.Embed(title="📋 Daily Missions", color=COLOR)
    for m_id, prog, targ, comp in missions:
        pool    = DAILY_MISSION_POOL[m_id]
        status  = "✅ Done!" if comp else f"{prog}/{targ}"
        rewards = f"+{pool.get('reward_credits',0)} Credits" + (f" · +{pool['reward_spins']} Spins" if pool.get("reward_spins") else "")
        embed.add_field(name=pool["desc"], value=f"{status} · Reward: {rewards}", inline=False)
    embed.set_footer(text="Missions reset daily at midnight.")
    await interaction.response.send_message(embed=embed)

# ============================================================
# /rankwar
# ============================================================
@bot.tree.command(name="rankwar", description="Challenge a squad to a Rank War (coming soon)")
@app_commands.describe(opponent_leader="Leader of the opposing squad")
async def rankwar(interaction: discord.Interaction, opponent_leader: discord.Member):
    await interaction.response.send_message(
        embed=discord.Embed(title="⚔️ Rank Wars",
                            description="3v3 squad Rank Wars are coming in a future update!",
                            color=COLOR))

# ============================================================
# /updatelog
# ============================================================
@bot.tree.command(name="updatelog", description="Show the latest update log")
async def updatelog(interaction: discord.Interaction):
    try:
        with open("updatelog.txt", "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        await interaction.response.send_message("Update log file not found.", ephemeral=True)
        return

    if not content.strip():
        await interaction.response.send_message("Update log is empty.", ephemeral=True)
        return

    # Simple single embed if content fits
    if len(content) <= 4096:
        embed = discord.Embed(title="📜 Update Log", description=content, color=COLOR)
        await interaction.response.send_message(embed=embed)
        return

    # Multi‑page embed with buttons
    pages = [content[i:i+4096] for i in range(0, len(content), 4096)]
    current_page = 0

    def build_embed(page_num):
        return discord.Embed(
            title=f"📜 Update Log ({page_num+1}/{len(pages)})",
            description=pages[page_num],
            color=COLOR
        )

    class Paginator(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=180)
            self.current = 0
            self._update_buttons()

        def _update_buttons(self):
            self.clear_items()
            prev_btn = discord.ui.Button(label="◀ Prev", style=discord.ButtonStyle.secondary, custom_id="prev", disabled=self.current == 0)
            next_btn = discord.ui.Button(label="Next ▶", style=discord.ButtonStyle.secondary, custom_id="next", disabled=self.current == len(pages)-1)
            prev_btn.callback = self.prev_callback
            next_btn.callback = self.next_callback
            self.add_item(prev_btn)
            self.add_item(next_btn)

        async def prev_callback(self, interaction: discord.Interaction):
            self.current -= 1
            self._update_buttons()
            await interaction.response.edit_message(embed=build_embed(self.current), view=self)

        async def next_callback(self, interaction: discord.Interaction):
            self.current += 1
            self._update_buttons()
            await interaction.response.edit_message(embed=build_embed(self.current), view=self)

    view = Paginator()
    await interaction.response.send_message(embed=build_embed(0), view=view)

# ============================================================
# /about
# ============================================================
@bot.tree.command(name="about", description="Description on Trigger Bot 2")
async def about(interaction: discord.Interaction):
    # Create the embed structure
    embed = discord.Embed(
        title="Trigger Bot 2",
        description=(
            "**This is the new & improved Trigger Bot based off of the anime 'World Trigger'.**\n\n"
            "⚠️ **This Discord bot is a HUGE work in progress!** There's currently no database system "
            "in place, so any data you create won't be saved. Treat this as a playtest until the release "
            "candidate, as all data may be wiped at any time. ⚠️"
        ),
        color=COLOR
    )

    # Add the main visual image asset
    embed.set_image(url="https://github.com/user-attachments/assets/0ecadd1a-fcbf-4e6a-89ca-28fec7beca92")

    # Construct the formatted sections
    embed.add_field(
        name="🔗 Quick Access",
        value="👉 **[Invite link for Trigger Bot 2](https://discord.com/oauth2/authorize?client_id=1483152396418023424&permissions=8&integration_type=0&scope=bot)**",
        inline=False
    )

    embed.add_field(
        name="❒ Features",
        value=(
            "• Turn‑based tactical arena, duels and missions\n"
            "• 25+ World Trigger weapons with skill trees and fusions\n"
            "• Squad system with operators (Shiori, Asami, Hana)\n"
            "• Kido, Shinoda, Tamakoma factions with stat bonuses\n"
            "• Daily missions, story mode, expeditions, base defense\n"
            "• Trigger mastery, stat/skill progression, redeem codes\n\n"
            "*Use `/help` to see the full list in Discord.*"
        ),
        inline=False
    )

    embed.add_field(
        name="❒ How to Play",
        value=(
            "1. Start with `/joinborder` – you'll get a Trion level and a side effect.\n"
            "2. Choose a class (`/setclass`) and a faction (`/faction`).\n"
            "3. Buy triggers from `/shop` and equip them with `/equip`.\n"
            "4. Enter `/arena` or `/mission` to fight Neighbors, earn credits, stat points, and trigger XP.\n"
            "5. Level up your triggers and spend skill points to unlock new moves.\n"
            "6. Form a squad, assign an operator, and challenge other players in `/duel`.\n"
            "7. Climb the ranks from C‑Rank to A‑Rank."
        ),
        inline=False
    )

    embed.set_footer(
        text="❒ License: This bot's source code is proprietary and protected by copyright. Unauthorised copying, modification, or redistribution of the code is strictly prohibited. The bot itself may be used freely via Discord – enjoy the game!"
    )

    await interaction.response.send_message(embed=embed)
# ============================================================
# EVENTS
# ============================================================
@bot.event
async def on_ready():
    print(f"🔑 Logged in as {bot.user}")
    try:
        await init_db()
        print("🗄️ Database ready.")
    except Exception:
        print("❌ Database setup failed:")
        traceback.print_exc()
    load_redeem_codes()
    try:
        synced = await bot.tree.sync()
        print(f"⚡ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if bot.user in message.mentions:
        await message.channel.send(
            embed=discord.Embed(
                title       = "<:Replica:1519462887351914496> Welcome Agent!",
                description = f"Hello {message.author.mention}! Start your journey with **/joinborder**.",
                color       = COLOR))
    await bot.process_commands(message)

# ============================================================
# MAIN
# ============================================================
async def main():
    print("🚀 Starting Trigger Bot 2…")
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    # Start Flask in a background thread
    port = int(os.environ.get('PORT', 5000))
    flask_thread = threading.Thread(
        target=lambda: flask_app.run(host='0.0.0.0', port=port, debug=False),
        daemon=True
    )
    flask_thread.start()

    # Start the bot (exactly as before)
    asyncio.run(main())
