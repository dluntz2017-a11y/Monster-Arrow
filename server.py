from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ======================== MODELS ========================

class ItemType(str, Enum):
    POWERUP = "powerup"
    COSMETIC = "cosmetic"
    CURRENCY = "currency"
    LIFE = "life"

class ShopItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    item_type: ItemType
    price_coins: int = 0
    price_gems: int = 0
    icon: str
    effect_value: int = 0  # e.g., +3 lives, +500 coins, etc.

class Player(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    coins: int = 100
    gems: int = 10
    lives: int = 5
    max_lives: int = 5
    high_score: int = 0
    total_monsters_killed: int = 0
    equipped_skin: str = "default"
    owned_skins: List[str] = ["default"]
    owned_powerups: Dict[str, int] = {}  # powerup_id: quantity
    ads_watched: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_played: datetime = Field(default_factory=datetime.utcnow)

class PlayerCreate(BaseModel):
    name: str

class PlayerUpdate(BaseModel):
    coins: Optional[int] = None
    gems: Optional[int] = None
    lives: Optional[int] = None
    high_score: Optional[int] = None
    total_monsters_killed: Optional[int] = None
    equipped_skin: Optional[str] = None

class PurchaseRequest(BaseModel):
    player_id: str
    item_id: str
    currency: str  # "coins" or "gems"

class AdRewardRequest(BaseModel):
    player_id: str
    ad_type: str  # "rewarded", "interstitial"

class GameResult(BaseModel):
    player_id: str
    score: int
    monsters_killed: int
    coins_earned: int

class LeaderboardEntry(BaseModel):
    player_id: str
    name: str
    high_score: int
    total_monsters_killed: int

# ======================== SHOP ITEMS DATA ========================

DEFAULT_SHOP_ITEMS = [
    # Power-ups
    {
        "id": "powerup_multishot",
        "name": "Multi-Shot",
        "description": "Shoot 3 arrows at once for 30 seconds",
        "item_type": "powerup",
        "price_coins": 200,
        "price_gems": 0,
        "icon": "target",
        "effect_value": 30
    },
    {
        "id": "powerup_slowmo",
        "name": "Slow Motion",
        "description": "Slow down monsters for 20 seconds",
        "item_type": "powerup",
        "price_coins": 150,
        "price_gems": 0,
        "icon": "clock",
        "effect_value": 20
    },
    {
        "id": "powerup_magnet",
        "name": "Coin Magnet",
        "description": "Auto-collect coins for 45 seconds",
        "item_type": "powerup",
        "price_coins": 0,
        "price_gems": 5,
        "icon": "magnet",
        "effect_value": 45
    },
    {
        "id": "powerup_shield",
        "name": "Shield",
        "description": "Block one hit from monsters",
        "item_type": "powerup",
        "price_coins": 0,
        "price_gems": 8,
        "icon": "shield",
        "effect_value": 1
    },
    # Lives
    {
        "id": "life_1",
        "name": "+1 Life",
        "description": "Restore 1 life",
        "item_type": "life",
        "price_coins": 100,
        "price_gems": 0,
        "icon": "heart",
        "effect_value": 1
    },
    {
        "id": "life_5",
        "name": "+5 Lives",
        "description": "Restore 5 lives (Best Value!)",
        "item_type": "life",
        "price_coins": 400,
        "price_gems": 0,
        "icon": "heart",
        "effect_value": 5
    },
    {
        "id": "life_full",
        "name": "Full Refill",
        "description": "Restore all lives instantly",
        "item_type": "life",
        "price_coins": 0,
        "price_gems": 3,
        "icon": "heart",
        "effect_value": 99
    },
    # Currency packs
    {
        "id": "coins_500",
        "name": "500 Coins",
        "description": "A small pile of coins",
        "item_type": "currency",
        "price_coins": 0,
        "price_gems": 5,
        "icon": "coins",
        "effect_value": 500
    },
    {
        "id": "coins_2000",
        "name": "2000 Coins",
        "description": "A treasure chest of coins!",
        "item_type": "currency",
        "price_coins": 0,
        "price_gems": 15,
        "icon": "coins",
        "effect_value": 2000
    },
    {
        "id": "gems_20",
        "name": "20 Gems",
        "description": "Precious gems bundle",
        "item_type": "currency",
        "price_coins": 1000,
        "price_gems": 0,
        "icon": "gem",
        "effect_value": 20
    },
    # Cosmetics (skins)
    {
        "id": "skin_golden",
        "name": "Golden Archer",
        "description": "A legendary golden bow",
        "item_type": "cosmetic",
        "price_coins": 0,
        "price_gems": 50,
        "icon": "star",
        "effect_value": 0
    },
    {
        "id": "skin_fire",
        "name": "Fire Archer",
        "description": "Flames trail your arrows",
        "item_type": "cosmetic",
        "price_coins": 0,
        "price_gems": 30,
        "icon": "flame",
        "effect_value": 0
    },
    {
        "id": "skin_ice",
        "name": "Ice Archer",
        "description": "Freeze your enemies in style",
        "item_type": "cosmetic",
        "price_coins": 2500,
        "price_gems": 0,
        "icon": "snowflake",
        "effect_value": 0
    },
    {
        "id": "skin_shadow",
        "name": "Shadow Archer",
        "description": "Strike from the darkness",
        "item_type": "cosmetic",
        "price_coins": 5000,
        "price_gems": 0,
        "icon": "moon",
        "effect_value": 0
    },
]

# ======================== PLAYER ENDPOINTS ========================

@api_router.get("/")
async def root():
    return {"message": "Monster Arrow Treasure Game API"}

@api_router.post("/players", response_model=Player)
async def create_player(player_data: PlayerCreate):
    """Create a new player"""
    player = Player(name=player_data.name)
    await db.players.insert_one(player.dict())
    return player

@api_router.get("/players/{player_id}", response_model=Player)
async def get_player(player_id: str):
    """Get player by ID"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return Player(**player)

@api_router.put("/players/{player_id}", response_model=Player)
async def update_player(player_id: str, update_data: PlayerUpdate):
    """Update player data"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    update_dict["last_played"] = datetime.utcnow()
    
    await db.players.update_one(
        {"id": player_id},
        {"$set": update_dict}
    )
    
    updated_player = await db.players.find_one({"id": player_id})
    return Player(**updated_player)

# ======================== SHOP ENDPOINTS ========================

@api_router.get("/shop/items", response_model=List[ShopItem])
async def get_shop_items():
    """Get all shop items"""
    return [ShopItem(**item) for item in DEFAULT_SHOP_ITEMS]

@api_router.get("/shop/items/{item_type}", response_model=List[ShopItem])
async def get_shop_items_by_type(item_type: str):
    """Get shop items by type"""
    items = [item for item in DEFAULT_SHOP_ITEMS if item["item_type"] == item_type]
    return [ShopItem(**item) for item in items]

@api_router.post("/shop/purchase")
async def purchase_item(request: PurchaseRequest):
    """Purchase an item from the shop"""
    player = await db.players.find_one({"id": request.player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Find the item
    item = next((i for i in DEFAULT_SHOP_ITEMS if i["id"] == request.item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Check price and deduct
    if request.currency == "coins":
        price = item["price_coins"]
        if price == 0:
            raise HTTPException(status_code=400, detail="Item cannot be purchased with coins")
        if player["coins"] < price:
            raise HTTPException(status_code=400, detail="Not enough coins")
        player["coins"] -= price
    elif request.currency == "gems":
        price = item["price_gems"]
        if price == 0:
            raise HTTPException(status_code=400, detail="Item cannot be purchased with gems")
        if player["gems"] < price:
            raise HTTPException(status_code=400, detail="Not enough gems")
        player["gems"] -= price
    else:
        raise HTTPException(status_code=400, detail="Invalid currency")
    
    # Apply item effect
    item_type = item["item_type"]
    effect_value = item["effect_value"]
    
    if item_type == "life":
        if effect_value == 99:  # Full refill
            player["lives"] = player["max_lives"]
        else:
            player["lives"] = min(player["lives"] + effect_value, player["max_lives"])
    
    elif item_type == "currency":
        if "coins" in item["id"]:
            player["coins"] += effect_value
        elif "gems" in item["id"]:
            player["gems"] += effect_value
    
    elif item_type == "powerup":
        if "owned_powerups" not in player:
            player["owned_powerups"] = {}
        current = player["owned_powerups"].get(request.item_id, 0)
        player["owned_powerups"][request.item_id] = current + 1
    
    elif item_type == "cosmetic":
        if "owned_skins" not in player:
            player["owned_skins"] = ["default"]
        skin_id = request.item_id.replace("skin_", "")
        if skin_id not in player["owned_skins"]:
            player["owned_skins"].append(skin_id)
    
    # Update player in database
    await db.players.update_one(
        {"id": request.player_id},
        {"$set": player}
    )
    
    return {
        "success": True,
        "message": f"Purchased {item['name']}!",
        "player": Player(**player)
    }

# ======================== AD REWARDS ENDPOINTS ========================

@api_router.post("/ads/reward")
async def claim_ad_reward(request: AdRewardRequest):
    """Claim reward for watching an ad"""
    player = await db.players.find_one({"id": request.player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    reward = {}
    
    if request.ad_type == "rewarded":
        # Rewarded video gives bigger rewards
        import random
        reward_type = random.choice(["coins", "gems", "life"])
        if reward_type == "coins":
            amount = random.randint(50, 150)
            player["coins"] += amount
            reward = {"type": "coins", "amount": amount}
        elif reward_type == "gems":
            amount = random.randint(2, 5)
            player["gems"] += amount
            reward = {"type": "gems", "amount": amount}
        else:
            if player["lives"] < player["max_lives"]:
                player["lives"] += 1
                reward = {"type": "life", "amount": 1}
            else:
                player["coins"] += 100
                reward = {"type": "coins", "amount": 100}
    
    elif request.ad_type == "interstitial":
        # Interstitial gives smaller rewards
        player["coins"] += 25
        reward = {"type": "coins", "amount": 25}
    
    player["ads_watched"] = player.get("ads_watched", 0) + 1
    
    await db.players.update_one(
        {"id": request.player_id},
        {"$set": player}
    )
    
    return {
        "success": True,
        "reward": reward,
        "player": Player(**player)
    }

# ======================== GAME ENDPOINTS ========================

@api_router.post("/game/result")
async def submit_game_result(result: GameResult):
    """Submit game result and update player stats"""
    player = await db.players.find_one({"id": result.player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Update stats
    if result.score > player.get("high_score", 0):
        player["high_score"] = result.score
    
    player["total_monsters_killed"] = player.get("total_monsters_killed", 0) + result.monsters_killed
    player["coins"] = player.get("coins", 0) + result.coins_earned
    player["last_played"] = datetime.utcnow()
    
    await db.players.update_one(
        {"id": result.player_id},
        {"$set": player}
    )
    
    return {
        "success": True,
        "new_high_score": result.score == player["high_score"],
        "player": Player(**player)
    }

@api_router.post("/game/use-life")
async def use_life(player_id: str):
    """Use a life to continue playing"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if player["lives"] <= 0:
        raise HTTPException(status_code=400, detail="No lives remaining")
    
    player["lives"] -= 1
    
    await db.players.update_one(
        {"id": player_id},
        {"$set": {"lives": player["lives"]}}
    )
    
    return {
        "success": True,
        "lives_remaining": player["lives"],
        "player": Player(**player)
    }

@api_router.post("/game/use-powerup")
async def use_powerup(player_id: str, powerup_id: str):
    """Use a powerup from inventory"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    owned = player.get("owned_powerups", {})
    if powerup_id not in owned or owned[powerup_id] <= 0:
        raise HTTPException(status_code=400, detail="Powerup not owned")
    
    owned[powerup_id] -= 1
    if owned[powerup_id] == 0:
        del owned[powerup_id]
    
    await db.players.update_one(
        {"id": player_id},
        {"$set": {"owned_powerups": owned}}
    )
    
    # Find powerup details
    powerup = next((i for i in DEFAULT_SHOP_ITEMS if i["id"] == powerup_id), None)
    
    return {
        "success": True,
        "powerup": powerup,
        "remaining": owned.get(powerup_id, 0)
    }

# ======================== LEADERBOARD ENDPOINTS ========================

@api_router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(limit: int = 10):
    """Get top players leaderboard"""
    # Use projection to fetch only required fields for performance
    players = await db.players.find(
        {},
        {"id": 1, "name": 1, "high_score": 1, "total_monsters_killed": 1}
    ).sort("high_score", -1).limit(limit).to_list(limit)
    return [
        LeaderboardEntry(
            player_id=p["id"],
            name=p["name"],
            high_score=p.get("high_score", 0),
            total_monsters_killed=p.get("total_monsters_killed", 0)
        )
        for p in players
    ]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
