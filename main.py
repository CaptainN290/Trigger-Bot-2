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
import aiohttp
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# ============================================================
# CONFIG
# ============================================================
load_dotenv()
TOKEN   = os.getenv("TOKEN")
DB_NAME = "world_trigger.db"
COLOR   = 0x1abc9c

# ============================================================
# DATA — CLASSES
# Rock-paper-scissors: Attacker > Sniper > Gunner > Shooter > All Rounder > Attacker
# ============================================================
CLASSES = {
    "Attacker":    {"emoji": "⚔️",  "strong_against": "Sniper",
                    "description": "Close combat specialist. Closes distance quickly to overwhelm snipers."},
    "Sniper":      {"emoji": "🎯",  "strong_against": "Gunner",
                    "description": "Long-range precision. Outranges and punishes gunner positioning."},
    "Gunner":      {"emoji": "🔫",  "strong_against": "Shooter",
                    "description": "Accurate suppressive fire. More reliable than unpredictable shooter trajectories."},
    "Shooter":     {"emoji": "💥",  "strong_against": "All Rounder",
                    "description": "Unpredictable trajectories that overwhelm balanced all-rounders."},
    "All Rounder": {"emoji": "🌟",  "strong_against": "Attacker",
                    "description": "Versatile and adaptive. Handles close combat rushdown with ease."},
}
CLASS_ADVANTAGE_MULT = 1.3  # 30% damage bonus when your class counters the opponent

# ============================================================
# DATA — TRIGGERS
# ============================================================
TRIGGERS = {
    # ── Attacker Triggers (Main) ──────────────────────────────
    # Kogetsu: katana-type attacker trigger, most common blade
    "Kogetsu":        {"price": 80,  "trion_cost": 2, "type": "main", "buffs": {"attack": 5, "defense": 1}},
    # Raygust: heavy blade/shield hybrid used by Osamu
    "Raygust":        {"price": 90,  "trion_cost": 3, "type": "main", "buffs": {"attack": 3, "defense": 4}},
    # Scorpion: shapeshifting blade used by Yuma, high mobility
    "Scorpion":       {"price": 100, "trion_cost": 2, "type": "main", "buffs": {"attack": 4, "mobility": 3}},

    # ── Shooter Triggers (Main) ───────────────────────────────
    # Asteroid: standard straight-line trion bullet
    "Asteroid":       {"price": 50,  "trion_cost": 1, "type": "main", "buffs": {"attack": 3}},
    # Meteor: explosive area damage
    "Meteor":         {"price": 80,  "trion_cost": 3, "type": "main", "buffs": {"attack": 5, "trion_control": 1}},
    # Hound: homing trion bullet
    "Hound":          {"price": 90,  "trion_cost": 2, "type": "main", "buffs": {"attack": 4, "intelligence": 1}},
    # Viper: custom-trajectory bullet, high skill ceiling
    "Viper":          {"price": 120, "trion_cost": 3, "type": "main", "buffs": {"attack": 4, "intelligence": 2}},

    # ── Sniper Triggers (Main) ────────────────────────────────
    # Ibis: heaviest sniper, massive damage, used by Chika
    "Ibis":           {"price": 150, "trion_cost": 5, "type": "main", "buffs": {"attack": 8, "trion_control": 2}},
    # Egret: balanced sniper
    "Egret":          {"price": 100, "trion_cost": 3, "type": "main", "buffs": {"attack": 5, "perception": 1}},
    # Lightning: fastest sniper bullet
    "Lightning":      {"price": 80,  "trion_cost": 2, "type": "main", "buffs": {"attack": 4, "mobility": 1}},

    # ── Optional Triggers ─────────────────────────────────────
    # Grasshopper: creates jump pads, extreme mobility boost (Yuma's signature)
    "Grasshopper":    {"price": 60,  "trion_cost": 1, "type": "optional", "buffs": {"mobility": 5}},
    # Bagworm: stealth cloak, hides from radar
    "Bagworm":        {"price": 50,  "trion_cost": 1, "type": "optional", "buffs": {"evasion": 3, "mobility": 1}},
    # Shield: standard defense barrier
    "Shield":         {"price": 40,  "trion_cost": 1, "type": "optional", "buffs": {"defense": 4}},
    # Chameleon: full invisibility
    "Chameleon":      {"price": 90,  "trion_cost": 2, "type": "optional", "buffs": {"evasion": 5}},
    # Spider: wire trap trigger
    "Spider":         {"price": 70,  "trion_cost": 2, "type": "optional", "buffs": {"attack": 2, "intelligence": 1}},
    # Escudo: defensive barrier that bursts outward
    "Escudo":         {"price": 75,  "trion_cost": 2, "type": "optional", "buffs": {"defense": 5, "attack": 1}},
    # Thruster: rocket booster, burst movement
    "Thruster":       {"price": 80,  "trion_cost": 2, "type": "optional", "buffs": {"mobility": 4, "attack": 1}},
    # Silencer: suppresses trion bullet sound
    "Silencer":       {"price": 60,  "trion_cost": 1, "type": "optional", "buffs": {"evasion": 2, "perception": 1}},
    # Dummy Beacon: creates fake radar signal
    "Dummy Beacon":   {"price": 55,  "trion_cost": 1, "type": "optional", "buffs": {"intelligence": 3}},

    # ── Custom / Non-Canon ────────────────────────────────────
    "Shadow Cloak":   {"price": 120, "trion_cost": 2, "type": "optional", "buffs": {"evasion": 5}},
    "Wallbreaker":    {"price": 70,  "trion_cost": 1, "type": "optional", "buffs": {"attack": 3}},
}

# ============================================================
# DATA — NEIGHBORS
# ============================================================
NEIGHBORS = {
    "Bamster": {"hp": 120, "damage": 10},
    "Marmod":  {"hp": 80,  "damage": 18},
    "Rabbit":  {"hp": 200, "damage": 25},
    "Ilgar":   {"hp": 150, "damage": 20},
    "Bander":  {"hp": 110, "damage": 16},
    "Rad":     {"hp": 30,  "damage": 5},
    "Dog":     {"hp": 60,  "damage": 12},
    "Idra":    {"hp": 90,  "damage": 15},
}

def random_neighbor():
    name  = random.choice(list(NEIGHBORS.keys()))
    stats = NEIGHBORS[name]
    return name, stats["hp"], stats["damage"]

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
# DATA — TRION
# ============================================================
def roll_trion():
    roll = random.randint(1, 100)
    if roll <= 50:  return random.randint(2, 6)
    if roll <= 85:  return random.randint(7, 12)
    if roll <= 97:  return random.randint(13, 20)
    return random.randint(21, 38)

# ============================================================
# DATA — STAT CAPS PER RANK
# Extra points = sum of all stats minus the baseline of 6 (1 per stat)
# ============================================================
RANK_CAPS = {
    "C-Rank": {"elo_min": 0,    "elo_max": 1199, "cap": 15},
    "B-Rank": {"elo_min": 1200, "elo_max": 1599, "cap": 30},
    "A-Rank": {"elo_min": 1600, "elo_max": 9999, "cap": 50},
}

def get_rank(elo):
    if elo >= 1600: return "A-Rank"
    if elo >= 1200: return "B-Rank"
    return "C-Rank"

def get_stat_cap(elo):
    return RANK_CAPS[get_rank(elo)]["cap"]

# ============================================================
# UTILITY — ELO
# ============================================================
def win_elo(current):
    return current + random.randint(15, 30)

def lose_elo(current):
    return max(current - random.randint(15, 30), 0)

# ============================================================
# UTILITY — DAMAGE CALCULATION
# attacker_class / defender_class enable the rock-paper-scissors advantage
# ============================================================
async def calculate_damage(user_id, trion, side_effect=None, triggers=None, stats=None,
                            attacker_class=None, defender_class=None):
    if stats is None:
        stats = {"attack": 1, "defense": 1, "mobility": 1,
                 "intelligence": 1, "trion_control": 1, "perception": 1}

    base            = trion * 10
    buff            = 0
    remaining_trion = trion

    if side_effect:
        for stat, value in side_effect.get("buffs", {}).items():
            weights = {"attack": 5, "mobility": 2, "perception": 2,
                       "intelligence": 3, "trion_control": 4, "defense": 1, "evasion": 1}
            buff += value * weights.get(stat, 1)

    if triggers:
        for trig_name in triggers:
            trig = TRIGGERS.get(trig_name)
            if not trig:
                continue
            cost = trig.get("trion_cost", 0)
            if remaining_trion >= cost:
                remaining_trion -= cost
                for stat, value in trig.get("buffs", {}).items():
                    weights = {"attack": 5, "mobility": 2, "defense": 3,
                               "evasion": 1, "intelligence": 3, "trion_control": 4, "perception": 2}
                    buff += value * weights.get(stat, 1)

    buff += stats.get("attack", 1)        * 5
    buff += stats.get("mobility", 1)      * 2
    buff += stats.get("intelligence", 1)  * 3
    buff += stats.get("trion_control", 1) * 4
    buff += stats.get("perception", 1)    * 2
    buff += stats.get("defense", 1)       * 1

    damage = base + buff + random.randint(0, 10)

    if side_effect and side_effect.get("passive") == "crit":
        if random.random() < 0.2:
            damage *= 1.5

    # Class advantage — 30% bonus if your class counters the opponent
    if attacker_class and defender_class:
        cls = CLASSES.get(attacker_class)
        if cls and cls["strong_against"] == defender_class:
            damage *= CLASS_ADVANTAGE_MULT

    return damage

# ============================================================
# UTILITY — PROFILE CARD (Pillow)
# ============================================================
TEMP_FOLDER = "temp_profiles"
os.makedirs(TEMP_FOLDER, exist_ok=True)

def generate_profile_card(username, avatar_path, trion, side_effect,
                           spins, credits, elo, wins, losses,
                           stats, triggers, story_arc, story_mission, user_id, agent_class=None):
    temp_file = os.path.join(TEMP_FOLDER, f"{user_id}.png")
    if os.path.exists(temp_file):
        os.remove(temp_file)

    card = Image.new("RGB", (600, 420), (26, 188, 156))
    draw = ImageDraw.Draw(card)

    try:
        font_title = ImageFont.truetype("arial.ttf", 28)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font_title = ImageFont.load_default()
        font_small = ImageFont.load_default()

    avatar = Image.open(avatar_path).convert("RGBA").resize((100, 100))
    mask   = Image.new("L", avatar.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 100, 100), fill=255)
    card.paste(avatar, (20, 20), mask)

    WHITE = (255, 255, 255)
    draw.text((140, 20),  username,                                               fill=WHITE, font=font_title)
    cls_info = f"  [{CLASSES[agent_class]['emoji']} {agent_class}]" if agent_class and agent_class in CLASSES else ""
    draw.text((140, 55),  f"🔋 Trion: {trion}{cls_info}",                         fill=WHITE, font=font_small)
    draw.text((140, 80),  f"🧬 Side Effect: {side_effect or 'None'}",            fill=WHITE, font=font_small)
    draw.text((140, 105), f"🎰 Spins: {spins}   💳 Credits: {credits}",           fill=WHITE, font=font_small)
    draw.text((140, 130), f"🏆 ELO: {elo}   W/L: {wins}/{losses}",                fill=WHITE, font=font_small)

    y = 170
    for name, val in stats.items():
        draw.text((20, y), f"🔹 {name}: {val}", fill=WHITE, font=font_small)
        y += 25

    trigger_text = " | ".join(triggers) if triggers else "None"
    draw.text((20, y + 10), f"🎯 Triggers: {trigger_text}",         fill=WHITE, font=font_small)
    draw.text((20, y + 35), f"📖 Story: {story_arc} → {story_mission}", fill=WHITE, font=font_small)

    card.save(temp_file)
    return temp_file

# ============================================================
# UI — PAGINATED SHOP VIEW
# ============================================================
TRIGGERS_PER_PAGE = 5

class ShopView(discord.ui.View):
    def __init__(self, page=0):
        super().__init__(timeout=120)
        self.page         = page
        self.trigger_list = list(TRIGGERS.items())
        self.total_pages  = max(1, (len(self.trigger_list) + TRIGGERS_PER_PAGE - 1) // TRIGGERS_PER_PAGE)
        self._refresh_buttons()

    def _refresh_buttons(self):
        for item in self.children:
            if hasattr(item, "custom_id"):
                if item.custom_id == "shop_prev":
                    item.disabled = self.page == 0
                elif item.custom_id == "shop_next":
                    item.disabled = self.page >= self.total_pages - 1

    def get_embed(self):
        start        = self.page * TRIGGERS_PER_PAGE
        page_entries = self.trigger_list[start : start + TRIGGERS_PER_PAGE]
        embed = discord.Embed(title="🛒 Border Trigger Shop",
                              description="Purchase triggers using Credits.",
                              color=COLOR)
        for name, data in page_entries:
            buff_text = ", ".join(f"{k}+{v}" for k, v in data["buffs"].items())
            embed.add_field(
                name=f"⚙️ {name}  ({data['type'].capitalize()})",
                value=f"💰 **{data['price']} Credits**  ⚡ Trion Cost: {data['trion_cost']}\n📊 {buff_text}",
                inline=False)
        embed.set_footer(text=f"Page {self.page+1}/{self.total_pages} · /buytrigger <name> to purchase")
        return embed

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary, custom_id="shop_prev")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary, custom_id="shop_next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

# ============================================================
# UI — PAGINATED SIDE EFFECTS VIEW
# ============================================================
EFFECTS_PER_PAGE = 5

class SideEffectsView(discord.ui.View):
    def __init__(self, page=0):
        super().__init__(timeout=120)
        self.page         = page
        self.all_effects  = (
            [("Common", e) for e in COMMON_EFFECTS] +
            [("Rare",   e) for e in RARE_EFFECTS]
        )
        self.total_pages  = max(1, (len(self.all_effects) + EFFECTS_PER_PAGE - 1) // EFFECTS_PER_PAGE)
        self._refresh_buttons()

    def _refresh_buttons(self):
        for item in self.children:
            if hasattr(item, "custom_id"):
                if item.custom_id == "se_prev":
                    item.disabled = self.page == 0
                elif item.custom_id == "se_next":
                    item.disabled = self.page >= self.total_pages - 1

    def get_embed(self):
        start        = self.page * EFFECTS_PER_PAGE
        page_entries = self.all_effects[start : start + EFFECTS_PER_PAGE]
        embed = discord.Embed(title="🧬 Side Effects Index",
                              description=f"**Common** — 85% chance when a side effect rolls\n"
                                           f"**Rare** — 15% chance when a side effect rolls\n"
                                           f"*(60% of agents receive a side effect at all)*",
                              color=COLOR)
        for rarity, effect in page_entries:
            colour  = "🟡" if rarity == "Rare" else "🔵"
            buffs   = ", ".join(f"{k}+{v}" for k, v in effect["buffs"].items())
            passive = f"\n✨ Passive: **{effect['passive']}**" if "passive" in effect else ""
            embed.add_field(
                name=f"{colour} {effect['name']}  [{rarity}]",
                value=f"📊 {buffs}{passive}",
                inline=False)
        embed.set_footer(text=f"Page {self.page+1}/{self.total_pages}")
        return embed

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary, custom_id="se_prev")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary, custom_id="se_next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

# ============================================================
# DATABASE SETUP
# ============================================================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                user_id INTEGER PRIMARY KEY,
                trion INTEGER DEFAULT 2,
                side_effect TEXT,
                spins INTEGER DEFAULT 0,
                credits INTEGER DEFAULT 0,
                elo INTEGER DEFAULT 1000,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                class TEXT DEFAULT NULL
            )""")
        # Migration: add class column if upgrading from old DB without it
        try:
            await db.execute("ALTER TABLE agents ADD COLUMN class TEXT DEFAULT NULL")
        except Exception:
            pass  # column already exists

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
                slot TEXT,
                PRIMARY KEY (user_id, slot)
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS redeem_codes (
                code TEXT PRIMARY KEY,
                reward_type TEXT,
                reward_amount INTEGER,
                reward_trigger TEXT,
                max_uses INTEGER,
                expires TIMESTAMP
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS redeemed (
                user_id INTEGER,
                code TEXT,
                PRIMARY KEY (user_id, code)
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS story_progress (
                user_id INTEGER PRIMARY KEY,
                arc TEXT DEFAULT 'Prologue',
                chapter INTEGER DEFAULT 1,
                mission INTEGER DEFAULT 1
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS story_missions (
                arc TEXT,
                chapter INTEGER,
                mission INTEGER,
                type TEXT,
                description TEXT,
                choices TEXT,
                reward_type TEXT,
                reward_amount INTEGER,
                reward_trigger TEXT,
                replayable INTEGER DEFAULT 0,
                PRIMARY KEY (arc, chapter, mission)
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_stats (
                user_id INTEGER PRIMARY KEY,
                attack INTEGER DEFAULT 1,
                defense INTEGER DEFAULT 1,
                mobility INTEGER DEFAULT 1,
                intelligence INTEGER DEFAULT 1,
                trion_control INTEGER DEFAULT 1,
                perception INTEGER DEFAULT 1,
                stat_points INTEGER DEFAULT 0
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS squads (
                squad_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                leader_id INTEGER,
                division TEXT DEFAULT 'C-Rank',
                elo INTEGER DEFAULT 1000
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS squad_members (
                squad_id INTEGER,
                user_id INTEGER,
                role TEXT
            )""")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trigger_mastery (
                user_id INTEGER,
                trigger TEXT,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, trigger)
            )""")
        await db.commit()

        # Populate story missions if table is empty
        cursor = await db.execute("SELECT COUNT(*) FROM story_missions")
        count  = (await cursor.fetchone())[0]
        if count == 0:
            try:
                await populate_story(db)
                await db.commit()
                print(f"✅ Story missions populated")
            except Exception:
                print("❌ Failed to populate story missions:")
                traceback.print_exc()
        else:
            print(f"📖 Story missions: {count} loaded from DB")

# ============================================================
# STORY POPULATION
# ============================================================
async def populate_story(db):
    arc      = "Prologue"
    missions = [
        (1, 1, "exploration",
         "You arrive at Mikado City for your first Border assignment. Explore the area.",
         None, "credits", 50, None, 1),
        (1, 2, "choice",
         "You hear a suspicious signal. Do you investigate carefully or rush in?",
         json.dumps([{"id": "investigate", "label": "Investigate Carefully"},
                     {"id": "rush",        "label": "Rush In"}]),
         "spins", 2, None, 0),
        (1, 3, "arena",
         "Neighbors are attacking civilians nearby. Engage them!",
         None, "credits", 100, None, 0),
        (2, 1, "exploration",
         "You investigate a suspicious warehouse. Look for clues and gather intel.",
         None, "credits", 75, None, 1),
        (2, 2, "choice",
         "A civilian asks for help. Escort them or continue your investigation?",
         json.dumps([{"id": "escort",      "label": "Escort Civilian"},
                     {"id": "investigate", "label": "Continue Investigation"}]),
         "spins", 3, None, 0),
        (2, 3, "arena",
         "A small group of Neighbors attacks! Defend the civilians!",
         None, "credits", 150, None, 0),
        (3, 1, "boss",
         "The main Neighbor threat appears in Mikado City. Prepare for a boss battle!",
         None, "trigger", 1, "Grasshopper", 0),
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
# BOT
# ============================================================
intents                 = discord.Intents.default()
intents.message_content = True
intents.members         = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Arena state
_arena_queue     = []
_arena_cooldowns = {}
ARENA_COOLDOWN   = 30

# Main triggers can also go in the Sub slot — only optional stays Optional
LOADOUT_SLOTS         = ["Main", "Sub", "Optional"]
MAIN_COMPATIBLE_SLOTS = ["Main", "Sub"]   # main-type triggers
OPT_COMPATIBLE_SLOTS  = ["Optional"]      # optional-type triggers

# ============================================================
# /joinborder
# ============================================================
@bot.tree.command(name="joinborder", description="Become a Border agent")
async def joinborder(interaction: discord.Interaction):
    user_id  = interaction.user.id
    username = interaction.user.display_name
    avatar   = interaction.user.display_avatar.url

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT user_id FROM agents WHERE user_id=?", (user_id,))
        if await cursor.fetchone():
            await interaction.response.send_message(
                embed=discord.Embed(title="⚠️ Already Registered",
                                    description="You are already a Border agent.",
                                    color=0xe67e22),
                ephemeral=True)
            return

        trion     = roll_trion()
        side      = roll_side_effect()
        side_json = json.dumps(side) if side else None

        # INSERT OR IGNORE on all three so partial rows from a previous failed attempt
        # don't block re-registration
        await db.execute(
            "INSERT OR IGNORE INTO agents (user_id,trion,side_effect,spins,credits,elo,wins,losses) VALUES (?,?,?,?,?,?,?,?)",
            (user_id, trion, side_json, 5, 100, 1000, 0, 0))
        await db.execute("INSERT OR IGNORE INTO agent_stats (user_id) VALUES (?)", (user_id,))
        await db.execute("INSERT OR IGNORE INTO story_progress (user_id) VALUES (?)", (user_id,))
        await db.commit()

    if trion <= 6:    rarity = "Low"
    elif trion <= 12: rarity = "Average"
    elif trion <= 20: rarity = "High"
    else:             rarity = "EXTREMELY RARE"

    embed = discord.Embed(title="🛡 Border Agent Registered",
                          description=f"Welcome to **Border**, {username}.",
                          color=COLOR)
    embed.set_thumbnail(url=avatar)
    embed.add_field(name="🔋 Trion Level",      value=f"{trion} ({rarity})", inline=True)
    embed.add_field(name="🧬 Side Effect",      value=side["name"] if side else "None", inline=True)
    embed.add_field(name="🎰 Starting Spins",   value=5,   inline=True)
    embed.add_field(name="💳 Starting Credits", value=100, inline=True)
    embed.add_field(name="📖 Story Progress",   value="Prologue — Chapter 1", inline=False)
    embed.add_field(name="⚔️ Next Step",        value="Choose your class with `/setclass`", inline=False)
    embed.set_footer(text="Your journey as a Border Agent begins now.")
    await interaction.response.send_message(embed=embed)

# ============================================================
# /setclass
# ============================================================
@bot.tree.command(name="setclass", description="Choose your Border combat class")
@app_commands.describe(class_name="Attacker / Sniper / Gunner / Shooter / All Rounder")
async def setclass(interaction: discord.Interaction, class_name: str):
    user_id = interaction.user.id

    # Allow flexible input casing
    matched = next((c for c in CLASSES if c.lower() == class_name.lower()), None)
    if not matched:
        names = ", ".join(CLASSES.keys())
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Invalid Class",
                                description=f"Choose from: {names}",
                                color=0xe74c3c),
            ephemeral=True)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT user_id FROM agents WHERE user_id=?", (user_id,))
        if not await cursor.fetchone():
            await interaction.response.send_message("Use `/joinborder` first.", ephemeral=True)
            return
        await db.execute("UPDATE agents SET class=? WHERE user_id=?", (matched, user_id))
        await db.commit()

    cls = CLASSES[matched]
    embed = discord.Embed(
        title=f"{cls['emoji']} Class Set: {matched}",
        description=cls["description"],
        color=COLOR)
    embed.add_field(name="⚡ Strong Against", value=cls["strong_against"])
    embed.add_field(name="💥 Advantage",      value=f"+{int((CLASS_ADVANTAGE_MULT-1)*100)}% damage vs {cls['strong_against']}")
    await interaction.response.send_message(embed=embed)

# ============================================================
# /classes  — browse the class chart
# ============================================================
@bot.tree.command(name="classes", description="View all classes and their matchups")
async def classes(interaction: discord.Interaction):
    embed = discord.Embed(title="⚔️ Border Combat Classes",
                          description=f"Each class deals **+{int((CLASS_ADVANTAGE_MULT-1)*100)}% damage** against its counter.\nUse `/setclass` to choose yours.",
                          color=COLOR)
    for name, data in CLASSES.items():
        embed.add_field(
            name=f"{data['emoji']} {name}",
            value=f"Strong vs **{data['strong_against']}**\n{data['description']}",
            inline=False)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /profile
# ============================================================
@bot.tree.command(name="profile", description="View your agent profile")
async def profile(interaction: discord.Interaction):
    user_id = interaction.user.id

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT trion, side_effect, spins, credits, elo, wins, losses, class FROM agents WHERE user_id=?",
            (user_id,))
        agent = await cursor.fetchone()
        if not agent:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ Not Registered",
                                    description="Use /joinborder first.",
                                    color=0xe74c3c),
                ephemeral=True)
            return

        trion, side, spins, credits, elo, wins, losses, agent_class = agent

        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception FROM agent_stats WHERE user_id=?",
            (user_id,))
        s = await cursor.fetchone()
        stats = {"Attack": s[0], "Defense": s[1], "Mobility": s[2],
                 "Intelligence": s[3], "Trion Control": s[4], "Perception": s[5]}

        cursor   = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (user_id,))
        triggers = [row[0] for row in await cursor.fetchall()]

        cursor = await db.execute("SELECT arc, mission FROM story_progress WHERE user_id=?", (user_id,))
        story_row = await cursor.fetchone()
        story_arc, story_mission = story_row if story_row else ("Prologue", 1)

    avatar_url  = interaction.user.display_avatar.url
    avatar_path = f"temp_avatar_{user_id}.png"
    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as resp:
            with open(avatar_path, "wb") as f:
                f.write(await resp.read())

    card_path = await asyncio.to_thread(
        generate_profile_card,
        username=interaction.user.display_name,
        avatar_path=avatar_path,
        trion=trion, side_effect=side, spins=spins, credits=credits,
        elo=elo, wins=wins, losses=losses, stats=stats, triggers=triggers,
        story_arc=story_arc, story_mission=story_mission, user_id=user_id,
        agent_class=agent_class)

    await interaction.response.send_message(file=discord.File(card_path))
    if os.path.exists(avatar_path):
        os.remove(avatar_path)

# ============================================================
# /shop  — paginated
# ============================================================
@bot.tree.command(name="shop", description="Browse the Border Trigger Shop")
async def shop(interaction: discord.Interaction):
    view = ShopView(page=0)
    await interaction.response.send_message(embed=view.get_embed(), view=view)

# ============================================================
# /sideeffects  — paginated index
# ============================================================
@bot.tree.command(name="sideeffects", description="Browse all possible side effects")
async def sideeffects(interaction: discord.Interaction):
    view = SideEffectsView(page=0)
    await interaction.response.send_message(embed=view.get_embed(), view=view)

# ============================================================
# /buytrigger
# ============================================================
@bot.tree.command(name="buytrigger", description="Buy a trigger from the shop")
@app_commands.describe(trigger="Name of the trigger")
async def buytrigger(interaction: discord.Interaction, trigger: str):
    user_id = interaction.user.id
    trigger = trigger.title()

    if trigger not in TRIGGERS:
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Trigger Not Found",
                                description="That trigger does not exist. Use `/shop` to browse.",
                                color=0xe74c3c),
            ephemeral=True)
        return

    price = TRIGGERS[trigger]["price"]

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT credits FROM agents WHERE user_id=?", (user_id,))
        agent  = await cursor.fetchone()
        if not agent:
            await interaction.response.send_message("Use `/joinborder` first.", ephemeral=True)
            return
        if agent[0] < price:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ Not Enough Credits",
                                    description=f"You need **{price} Credits**. You have **{agent[0]}**.",
                                    color=0xe74c3c),
                ephemeral=True)
            return

        cursor = await db.execute("SELECT 1 FROM triggers WHERE user_id=? AND trigger=?", (user_id, trigger))
        if await cursor.fetchone():
            await interaction.response.send_message(
                embed=discord.Embed(title="⚠️ Already Owned",
                                    description=f"You already own **{trigger}**.",
                                    color=0xf1c40f),
                ephemeral=True)
            return

        await db.execute("UPDATE agents SET credits = credits - ? WHERE user_id=?", (price, user_id))
        await db.execute("INSERT INTO triggers (user_id, trigger) VALUES (?,?)", (user_id, trigger))
        await db.commit()

    t = TRIGGERS[trigger]
    slot_hint = "Main or Sub" if t["type"] == "main" else "Optional"
    embed = discord.Embed(title="✅ Trigger Purchased",
                          description=f"You bought **{trigger}**!", color=0x2ecc71)
    embed.add_field(name="Slot",      value=slot_hint)
    embed.add_field(name="Next Step", value=f"`/equip {trigger} {slot_hint.split()[0]}`")
    await interaction.response.send_message(embed=embed)

# ============================================================
# /loadout
# ============================================================
@bot.tree.command(name="loadout", description="View your trigger loadout")
async def loadout(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT trigger, slot FROM loadouts WHERE user_id=?", (user_id,))
        data   = await cursor.fetchall()

    equipped = {slot: "None" for slot in LOADOUT_SLOTS}
    for trig, slot in data:
        equipped[slot] = trig

    embed = discord.Embed(title=f"⚡ {interaction.user.display_name}'s Loadout", color=COLOR)
    for slot in LOADOUT_SLOTS:
        embed.add_field(name=f"{slot} Trigger", value=equipped[slot], inline=False)
    embed.set_footer(text="Main-type triggers: Main or Sub slot | Optional triggers: Optional slot only")
    await interaction.response.send_message(embed=embed)

# ============================================================
# /equip
# Main-type triggers can go in Main OR Sub.
# Optional-type triggers can only go in Optional.
# ============================================================
@bot.tree.command(name="equip", description="Equip a trigger into a loadout slot")
@app_commands.describe(trigger="Trigger name", slot="Main / Sub / Optional")
async def equip(interaction: discord.Interaction, trigger: str, slot: str):
    user_id = interaction.user.id
    trigger = trigger.title()
    slot    = slot.title()

    if slot not in LOADOUT_SLOTS:
        await interaction.response.send_message(
            "Slot must be: **Main**, **Sub**, or **Optional**.", ephemeral=True)
        return
    if trigger not in TRIGGERS:
        await interaction.response.send_message(
            "That trigger does not exist. Use `/shop` to browse.", ephemeral=True)
        return

    t_type = TRIGGERS[trigger]["type"]

    # Enforce slot/type compatibility
    if t_type == "main" and slot not in MAIN_COMPATIBLE_SLOTS:
        await interaction.response.send_message(
            f"**{trigger}** is a Main-type trigger. It can only go in **Main** or **Sub**.", ephemeral=True)
        return
    if t_type == "optional" and slot not in OPT_COMPATIBLE_SLOTS:
        await interaction.response.send_message(
            f"**{trigger}** is an Optional trigger. It can only go in the **Optional** slot.", ephemeral=True)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT 1 FROM triggers WHERE user_id=? AND trigger=?", (user_id, trigger))
        if not await cursor.fetchone():
            await interaction.response.send_message(
                f"You don't own **{trigger}**. Buy it with `/buytrigger {trigger}`.", ephemeral=True)
            return

        await db.execute(
            "INSERT OR REPLACE INTO loadouts (user_id, trigger, slot) VALUES (?,?,?)",
            (user_id, trigger, slot))
        await db.commit()

    await interaction.response.send_message(
        embed=discord.Embed(title="✅ Equipped",
                            description=f"**{trigger}** equipped as **{slot} Trigger**.",
                            color=COLOR))

# ============================================================
# /spin  — choose trion or side_effect specifically
# ============================================================
@bot.tree.command(name="spin", description="Spend a spin to reroll Trion or Side Effect")
@app_commands.describe(spin_type="What to reroll: trion or side_effect")
@app_commands.choices(spin_type=[
    app_commands.Choice(name="Trion",       value="trion"),
    app_commands.Choice(name="Side Effect", value="side_effect"),
])
async def spin(interaction: discord.Interaction, spin_type: str):
    user_id = interaction.user.id

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT spins, trion, side_effect FROM agents WHERE user_id=?", (user_id,))
        data = await cursor.fetchone()
        if not data:
            await interaction.response.send_message("Use /joinborder first!", ephemeral=True)
            return

        spins, current_trion, current_side = data
        if spins <= 0:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ No Spins",
                                    description="You have no spins left!",
                                    color=0xe74c3c),
                ephemeral=True)
            return

        spins -= 1

        if spin_type == "trion":
            new_trion = roll_trion()
            await db.execute("UPDATE agents SET trion=?, spins=? WHERE user_id=?",
                             (new_trion, spins, user_id))
            await db.commit()
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🎲 Trion Rerolled",
                    description=f"**{current_trion}** → **{new_trion}**\nSpins remaining: {spins}",
                    color=COLOR))

        else:  # side_effect
            new_side      = roll_side_effect()
            new_side_json = json.dumps(new_side) if new_side else None
            old_name      = json.loads(current_side)["name"] if current_side else "None"
            new_name      = new_side["name"] if new_side else "None"
            await db.execute("UPDATE agents SET side_effect=?, spins=? WHERE user_id=?",
                             (new_side_json, spins, user_id))
            await db.commit()
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🎲 Side Effect Rerolled",
                    description=f"**{old_name}** → **{new_name}**\nSpins remaining: {spins}",
                    color=COLOR))

# ============================================================
# /stats
# ============================================================
@bot.tree.command(name="stats", description="View your agent stats")
async def stats(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception, stat_points FROM agent_stats WHERE user_id=?",
            (user_id,))
        data = await cursor.fetchone()
        cursor2 = await db.execute("SELECT elo FROM agents WHERE user_id=?", (user_id,))
        elo_row = await cursor2.fetchone()

    if not data:
        await interaction.response.send_message("Use `/joinborder` first.", ephemeral=True)
        return

    attack, defense, mobility, intelligence, trion_control, perception, points = data
    elo  = elo_row[0] if elo_row else 1000
    rank = get_rank(elo)
    cap  = get_stat_cap(elo)
    used = (attack + defense + mobility + intelligence + trion_control + perception) - 6

    embed = discord.Embed(title="📊 Agent Stats", color=COLOR)
    embed.add_field(name="⚔️ Attack",        value=attack)
    embed.add_field(name="🛡 Defense",        value=defense)
    embed.add_field(name="🏃 Mobility",       value=mobility)
    embed.add_field(name="🧠 Intelligence",   value=intelligence)
    embed.add_field(name="🔋 Trion Control",  value=trion_control)
    embed.add_field(name="👁 Perception",     value=perception)
    embed.add_field(name="⭐ Unspent Points", value=points, inline=False)
    embed.add_field(name="📈 Stat Cap",
                    value=f"{used}/{cap} used · {rank} · {'B-Rank unlocks more' if rank == 'C-Rank' else 'A-Rank unlocks more' if rank == 'B-Rank' else 'Max rank'}",
                    inline=False)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /upgradestat
# ============================================================
@bot.tree.command(name="upgradestat", description="Spend a stat point to upgrade a stat")
@app_commands.describe(stat="attack / defense / mobility / intelligence / trion_control / perception")
async def upgradestat(interaction: discord.Interaction, stat: str):
    user_id     = interaction.user.id
    stat        = stat.lower()
    valid_stats = ["attack", "defense", "mobility", "intelligence", "trion_control", "perception"]

    if stat not in valid_stats:
        await interaction.response.send_message(
            "Invalid stat. Choose from: " + ", ".join(valid_stats), ephemeral=True)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception, stat_points FROM agent_stats WHERE user_id=?",
            (user_id,))
        result = await cursor.fetchone()
        if not result:
            await interaction.response.send_message("Use `/joinborder` first.", ephemeral=True)
            return

        attack, defense, mobility, intelligence, trion_control, perception, points = result

        if points <= 0:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ No Stat Points",
                                    description="You have no stat points to spend.",
                                    color=0xe74c3c),
                ephemeral=True)
            return

        # Check stat cap for current rank
        cursor2  = await db.execute("SELECT elo FROM agents WHERE user_id=?", (user_id,))
        elo_row  = await cursor2.fetchone()
        elo      = elo_row[0] if elo_row else 1000
        rank     = get_rank(elo)
        cap      = get_stat_cap(elo)
        used     = (attack + defense + mobility + intelligence + trion_control + perception) - 6

        if used >= cap:
            next_rank = "B-Rank" if rank == "C-Rank" else "A-Rank" if rank == "B-Rank" else None
            msg = f"You've hit the **{rank}** stat cap ({cap} points)."
            if next_rank:
                msg += f" Reach **{next_rank}** (ELO {1200 if next_rank == 'B-Rank' else 1600}) to unlock more."
            await interaction.response.send_message(
                embed=discord.Embed(title="⛔ Stat Cap Reached", description=msg, color=0xe74c3c),
                ephemeral=True)
            return

        await db.execute(
            f"UPDATE agent_stats SET {stat} = {stat} + 1, stat_points = stat_points - 1 WHERE user_id=?",
            (user_id,))
        await db.commit()

    await interaction.response.send_message(
        embed=discord.Embed(title="✅ Stat Upgraded",
                            description=f"**{stat.replace('_', ' ').title()}** increased by 1.",
                            color=COLOR))

# ============================================================
# /leaderboard
# ============================================================
@bot.tree.command(name="leaderboard", description="View the top agents by ELO")
async def leaderboard(interaction: discord.Interaction):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT user_id, elo, class FROM agents ORDER BY elo DESC LIMIT 10")
        data = await cursor.fetchall()

    if not data:
        await interaction.response.send_message("No agents yet!", ephemeral=True)
        return

    embed = discord.Embed(title="🏆 Top Border Agents by ELO", color=0xf1c40f)
    for i, (uid, elo, agent_class) in enumerate(data, 1):
        try:
            user = await bot.fetch_user(uid)
            name = user.display_name
        except Exception:
            name = f"Unknown ({uid})"
        cls_emoji = CLASSES[agent_class]["emoji"] if agent_class and agent_class in CLASSES else "❓"
        rank      = get_rank(elo)
        embed.add_field(name=f"{i}. {name}", value=f"{cls_emoji} {rank} · ELO: {elo}", inline=False)

    await interaction.response.send_message(embed=embed)

# ============================================================
# /arena
# ============================================================
@bot.tree.command(name="arena", description="Enter Solo Arena matchmaking")
async def arena(interaction: discord.Interaction):
    user_id  = interaction.user.id
    username = interaction.user.display_name

    now  = time.time()
    last = _arena_cooldowns.get(user_id, 0)
    if now - last < ARENA_COOLDOWN:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⏳ Arena Cooldown",
                description=f"Wait {int(ARENA_COOLDOWN - (now - last))}s before entering again.",
                color=0xe67e22),
            ephemeral=True)
        return
    _arena_cooldowns[user_id] = now

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT trion, side_effect, elo, wins, losses, class FROM agents WHERE user_id=?", (user_id,))
        player = await cursor.fetchone()

    if not player:
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Not Registered",
                                description="Use /joinborder first.",
                                color=0xe74c3c),
            ephemeral=True)
        return

    await interaction.response.send_message(
        embed=discord.Embed(title="⚔️ Arena Queue",
                            description=f"**{username}** entered the Solo Arena queue...",
                            color=COLOR))

    _arena_queue.append((interaction.user, player))
    await asyncio.sleep(5)

    opponent = next((q for q in _arena_queue if q[0].id != user_id), None)

    if opponent:
        _arena_queue.remove((interaction.user, player))
        _arena_queue.remove(opponent)
        await _run_battle(interaction.channel, interaction.user, player,
                          opponent[0], opponent[1], pvp=True)
    else:
        _arena_queue.remove((interaction.user, player))
        wave_count      = random.randint(2, 3)
        enemy_names     = []
        total_enemy_hp  = 0
        total_enemy_dmg = 0
        for _ in range(wave_count):
            name, hp, dmg = random_neighbor()
            enemy_names.append(name)
            total_enemy_hp  += hp
            total_enemy_dmg += dmg
        ai_name  = f"Neighbor Wave: {', '.join(enemy_names)}"
        ai_stats = (total_enemy_hp // 10, None, 1000, 0, 0, None)
        await _run_battle(interaction.channel, interaction.user, player,
                          ai_name, ai_stats, pvp=False)

async def _run_battle(channel, user1, stats1, user2, stats2, pvp=True):
    trion1, side1, elo1, wins1, losses1, class1 = stats1
    trion2, side2, elo2, wins2, losses2, class2 = stats2

    side1 = json.loads(side1) if isinstance(side1, str) else side1
    side2 = json.loads(side2) if isinstance(side2, str) else side2

    async with aiosqlite.connect(DB_NAME) as db:
        cursor    = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (user1.id,))
        triggers1 = [row[0] for row in await cursor.fetchall()]
        cursor    = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception FROM agent_stats WHERE user_id=?",
            (user1.id,))
        s = await cursor.fetchone()

    sd          = {"attack":1,"defense":1,"mobility":1,"intelligence":1,"trion_control":1,"perception":1}
    stats1_dict = {"attack":s[0],"defense":s[1],"mobility":s[2],
                   "intelligence":s[3],"trion_control":s[4],"perception":s[5]} if s else sd

    dmg1 = await calculate_damage(user1.id, trion1, side1, triggers1, stats1_dict,
                                   attacker_class=class1, defender_class=class2)
    dmg2 = await calculate_damage(user1.id, trion2, side2, [], sd,
                                   attacker_class=class2, defender_class=class1)

    name1     = user1.display_name
    name2     = user2.display_name if pvp else user2
    cls1_tag  = f" [{CLASSES[class1]['emoji']}]" if class1 and class1 in CLASSES else ""
    cls2_tag  = f" [{CLASSES[class2]['emoji']}]" if class2 and class2 in CLASSES else ""

    # Class advantage note
    advantage_note = ""
    if class1 and class2:
        if CLASSES.get(class1, {}).get("strong_against") == class2:
            advantage_note = f"\n⚡ **Class advantage:** {name1} counters {name2}!"
        elif CLASSES.get(class2, {}).get("strong_against") == class1:
            advantage_note = f"\n⚡ **Class advantage:** {name2} counters {name1}!"

    log  = f"**Battle Start!**{advantage_note}\n"
    log += f"{name1}{cls1_tag} deals **{int(dmg1)}** damage.\n"
    log += f"{name2}{cls2_tag} deals **{int(dmg2)}** damage.\n"

    if dmg1 > dmg2:
        new_elo1 = win_elo(elo1); new_elo2 = lose_elo(elo2)
        wins1 += 1; losses2 += 1
        log += f"🏆 **Winner: {name1}**"
    elif dmg2 > dmg1:
        new_elo1 = lose_elo(elo1); new_elo2 = win_elo(elo2)
        wins2 += 1; losses1 += 1
        log += f"🏆 **Winner: {name2}**"
    else:
        new_elo1 = elo1; new_elo2 = elo2
        log += "⚔️ **It's a tie!**"

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE agents SET elo=?, wins=?, losses=? WHERE user_id=?",
                         (new_elo1, wins1, losses1, user1.id))
        if pvp:
            await db.execute("UPDATE agents SET elo=?, wins=?, losses=? WHERE user_id=?",
                             (new_elo2, wins2, losses2, user2.id))
        await db.commit()

    await channel.send(embed=discord.Embed(title="⚔️ Arena Battle", description=log, color=COLOR))

# ============================================================
# /story
# ============================================================
@bot.tree.command(name="story", description="View your current story mission")
async def story(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT arc, chapter, mission FROM story_progress WHERE user_id=?", (user_id,))
        progress = await cursor.fetchone()
        if not progress:
            await db.execute("INSERT OR IGNORE INTO story_progress (user_id) VALUES (?)", (user_id,))
            await db.commit()
            arc, chapter, mission = "Prologue", 1, 1
        else:
            arc, chapter, mission = progress

        cursor = await db.execute(
            "SELECT type, description, choices, reward_type, reward_amount, reward_trigger, replayable "
            "FROM story_missions WHERE arc=? AND chapter=? AND mission=?",
            (arc, chapter, mission))
        mission_data = await cursor.fetchone()

    if not mission_data:
        await interaction.response.send_message(
            embed=discord.Embed(title="📖 Story Mode",
                                description="You've completed all current missions. More coming soon!",
                                color=COLOR))
        return

    m_type, desc, choices_json, r_type, r_amount, r_trigger, replayable = mission_data
    embed = discord.Embed(title=f"📖 {arc} — Chapter {chapter}, Mission {mission}",
                          description=desc, color=COLOR)
    if m_type == "choice":
        embed.add_field(name="Choices", value="Use `/mission` to make your choice.", inline=False)
    embed.add_field(name="🎁 Reward",
                    value=f"{r_amount} {r_type}" + (f" · Trigger: {r_trigger}" if r_trigger else ""),
                    inline=True)
    embed.add_field(name="🔁 Type", value="Replayable" if replayable else "One-time", inline=True)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /mission
# ============================================================
@bot.tree.command(name="mission", description="Start your current story mission")
async def mission(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT arc, chapter, mission FROM story_progress WHERE user_id=?", (user_id,))
        progress = await cursor.fetchone()
        if not progress:
            await db.execute("INSERT OR IGNORE INTO story_progress (user_id) VALUES (?)", (user_id,))
            await db.commit()
            arc, chapter, mission_num = "Prologue", 1, 1
        else:
            arc, chapter, mission_num = progress

        cursor = await db.execute(
            "SELECT type, description, choices, reward_type, reward_amount, reward_trigger, replayable "
            "FROM story_missions WHERE arc=? AND chapter=? AND mission=?",
            (arc, chapter, mission_num))
        mission_data = await cursor.fetchone()

    if not mission_data:
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ No Mission Found",
                                description="All current missions completed. More coming soon!",
                                color=0xe74c3c))
        return

    m_type, desc, choices_json, r_type, r_amount, r_trigger, replayable = mission_data

    # Run the mission
    completed = True
    if m_type in ("arena", "boss"):
        completed = await _story_arena_mission(interaction, m_type, r_type, r_amount, r_trigger)
    elif m_type == "choice":
        await _story_choice_mission(interaction, choices_json, r_type, r_amount, r_trigger)
    elif m_type == "exploration":
        await _story_exploration(interaction, desc, r_type, r_amount, r_trigger)

    if not completed:
        return  # arena mission returned False (not registered) — don't advance

    # Always advance progress after the mission runs
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            next_mission = mission_num + 1

            cursor = await db.execute(
                "SELECT 1 FROM story_missions WHERE arc=? AND chapter=? AND mission=?",
                (arc, chapter, next_mission))
            exists = await cursor.fetchone()

            if exists:
                await db.execute(
                    "UPDATE story_progress SET mission=? WHERE user_id=?",
                    (next_mission, user_id))
            else:
                # Last mission of this chapter — advance to next chapter
                next_chapter = chapter + 1
                cursor = await db.execute(
                    "SELECT 1 FROM story_missions WHERE arc=? AND chapter=?",
                    (arc, next_chapter))
                chapter_exists = await cursor.fetchone()

                if chapter_exists:
                    await db.execute(
                        "UPDATE story_progress SET chapter=?, mission=1 WHERE user_id=?",
                        (next_chapter, user_id))
                # else: story complete, progress stays — /story shows completion message

            await db.commit()
    except Exception:
        print("❌ Error advancing story progress:")
        traceback.print_exc()

async def _story_arena_mission(interaction, m_type, r_type, r_amount, r_trigger):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT trion, side_effect, elo, wins, losses FROM agents WHERE user_id=?", (user_id,))
        agent = await cursor.fetchone()
        if not agent:
            await interaction.response.send_message("Use `/joinborder` first.", ephemeral=True)
            return False
        cursor2  = await db.execute("SELECT trigger FROM loadouts WHERE user_id=?", (user_id,))
        triggers = [row[0] for row in await cursor2.fetchall()]
        cursor3  = await db.execute(
            "SELECT attack, defense, mobility, intelligence, trion_control, perception FROM agent_stats WHERE user_id=?",
            (user_id,))
        s = await cursor3.fetchone()

    trion, side, elo, wins, losses = agent
    side = json.loads(side) if side else None
    sd   = {"attack":1,"defense":1,"mobility":1,"intelligence":1,"trion_control":1,"perception":1}
    stats_dict = {"attack":s[0],"defense":s[1],"mobility":s[2],
                  "intelligence":s[3],"trion_control":s[4],"perception":s[5]} if s else sd

    dmg1 = await calculate_damage(user_id, trion, side, triggers, stats_dict)

    wave_count = random.randint(2, 3) if m_type != "boss" else 1
    enemy_names     = []
    total_enemy_hp  = 0
    total_enemy_dmg = 0
    for _ in range(wave_count):
        name, hp, dmg = random_neighbor()
        # Boss fights have stronger enemies
        if m_type == "boss":
            hp  = int(hp  * 1.8)
            dmg = int(dmg * 1.5)
        enemy_names.append(name)
        total_enemy_hp  += hp
        total_enemy_dmg += dmg
    dmg2 = total_enemy_hp + total_enemy_dmg // 2

    log = (f"**Battle Start!**\n{interaction.user.display_name} deals **{int(dmg1)}** damage.\n"
           f"Neighbors ({', '.join(enemy_names)}) deal **{dmg2}** damage.\n")
    won = dmg1 >= dmg2
    log += "🏆 **You won!**" if won else "⚔️ **You lost!**"

    if won:
        async with aiosqlite.connect(DB_NAME) as db:
            if r_type == "credits":
                await db.execute("UPDATE agents SET credits=credits+? WHERE user_id=?", (r_amount, user_id))
            elif r_type == "spins":
                await db.execute("UPDATE agents SET spins=spins+? WHERE user_id=?", (r_amount, user_id))
            elif r_type == "trigger" and r_trigger:
                await db.execute("INSERT OR IGNORE INTO triggers (user_id, trigger) VALUES (?,?)",
                                 (user_id, r_trigger))
            await db.commit()

    embed = discord.Embed(
        title="🛡️ Boss Fight" if m_type == "boss" else "⚔️ Mission Arena",
        description=log, color=COLOR)
    embed.set_footer(text=f"Reward: {r_amount} {r_type}" + (f" · Trigger: {r_trigger}" if r_trigger else ""))
    await interaction.response.send_message(embed=embed)
    return True

async def _story_choice_mission(interaction, choices_json, r_type, r_amount, r_trigger):
    choices = json.loads(choices_json)
    view    = discord.ui.View()
    for c in choices:
        view.add_item(discord.ui.Button(label=c["label"], custom_id=c["id"]))
    embed = discord.Embed(title="📜 Choice Mission",
                          description="Make your choice wisely! ⚔️", color=COLOR)
    embed.set_footer(text=f"Reward: {r_amount} {r_type}" + (f" · Trigger: {r_trigger}" if r_trigger else ""))
    await interaction.response.send_message(embed=embed, view=view)

async def _story_exploration(interaction, desc, r_type, r_amount, r_trigger):
    embed = discord.Embed(title="🔍 Exploration Mission", description=desc, color=COLOR)
    embed.set_footer(text=f"Reward: {r_amount} {r_type}" + (f" · Trigger: {r_trigger}" if r_trigger else ""))
    await interaction.response.send_message(embed=embed)

    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        if r_type == "credits":
            await db.execute("UPDATE agents SET credits=credits+? WHERE user_id=?", (r_amount, user_id))
        elif r_type == "spins":
            await db.execute("UPDATE agents SET spins=spins+? WHERE user_id=?", (r_amount, user_id))
        elif r_type == "trigger" and r_trigger:
            await db.execute("INSERT OR IGNORE INTO triggers (user_id, trigger) VALUES (?,?)",
                             (user_id, r_trigger))
        await db.commit()

# ============================================================
# /squadcreate
# ============================================================
@bot.tree.command(name="squadcreate", description="Create a squad")
@app_commands.describe(name="Squad name")
async def squadcreate(interaction: discord.Interaction, name: str):
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
        embed=discord.Embed(title="🛡 Squad Created",
                            description=f"Squad **{name}** has been created.",
                            color=COLOR))

# ============================================================
# /squadinvite
# ============================================================
@bot.tree.command(name="squadinvite", description="Invite a player to your squad")
@app_commands.describe(member="The player to invite")
async def squadinvite(interaction: discord.Interaction, member: discord.Member):
    inviter = interaction.user.id
    target  = member.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT squad_id, role FROM squad_members WHERE user_id=?", (inviter,))
        inviter_data = await cursor.fetchone()
        if not inviter_data or inviter_data[1] != "Leader":
            await interaction.response.send_message("Only squad leaders can invite.", ephemeral=True)
            return

        squad_id = inviter_data[0]
        cursor   = await db.execute("SELECT 1 FROM squad_members WHERE user_id=?", (target,))
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
                            description=f"{member.mention} has joined your squad.",
                            color=COLOR))

# ============================================================
# /squadinfo
# ============================================================
@bot.tree.command(name="squadinfo", description="View your squad info")
async def squadinfo(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT squad_id FROM squad_members WHERE user_id=?", (user_id,))
        row    = await cursor.fetchone()
        if not row:
            await interaction.response.send_message("You are not in a squad.", ephemeral=True)
            return

        squad_id = row[0]
        cursor   = await db.execute(
            "SELECT name, division, elo FROM squads WHERE squad_id=?", (squad_id,))
        name, division, elo = await cursor.fetchone()

        cursor  = await db.execute(
            "SELECT user_id, role FROM squad_members WHERE squad_id=?", (squad_id,))
        members = await cursor.fetchall()

    member_lines = ""
    for uid, role in members:
        try:
            user = await bot.fetch_user(uid)
            member_lines += f"{user.name} — {role}\n"
        except Exception:
            member_lines += f"Unknown ({uid}) — {role}\n"

    embed = discord.Embed(title=f"🛡 Squad: {name}", color=COLOR)
    embed.add_field(name="Division", value=division)
    embed.add_field(name="ELO",      value=elo)
    embed.add_field(name="Members",  value=member_lines or "None", inline=False)
    await interaction.response.send_message(embed=embed)

# ============================================================
# /squadleave
# ============================================================
@bot.tree.command(name="squadleave", description="Leave your squad")
async def squadleave(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM squad_members WHERE user_id=?", (user_id,))
        await db.commit()
    await interaction.response.send_message(
        embed=discord.Embed(title="🚪 Left Squad",
                            description="You have left your squad.",
                            color=COLOR))

# ============================================================
# EVENTS
# ============================================================
@bot.event
async def on_ready():
    print(f"🔑 Logged in as {bot.user}")
    try:
        await init_db()
        print("🗄️ Database ready")
    except Exception:
        print("❌ Database setup failed:")
        traceback.print_exc()
    try:
        synced = await bot.tree.sync()
        print(f"⚡ Synced {len(synced)} slash commands")
    except Exception:
        print("❌ Failed to sync commands:")
        traceback.print_exc()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if bot.user in message.mentions:
        await message.channel.send(
            embed=discord.Embed(
                title="👋 Welcome Agent!",
                description=f"Hello {message.author.mention}! Start your journey with **/joinborder**.",
                color=COLOR))
    await bot.process_commands(message)

# ============================================================
# MAIN
# ============================================================
async def main():
    print("🚀 Starting bot...")
    try:
        print("🔥 Connecting to Discord...")
        await bot.start(TOKEN)
    except Exception:
        print("❌ Bot crashed:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
