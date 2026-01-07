import discord
from discord.ext import commands
import json
import random
import os
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import io

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Load tarot cards data
with open('data/tarot_cards.json', 'r', encoding='utf-8') as f:
    tarot_cards = json.load(f)

# Spreading options
SPREADS = {
    "single": ["Present"],
    "three_card": ["Past", "Present", "Future"],
    "celtic_cross": ["1. Present", "2. Challenge", "3. Past", "4. Future", 
                     "5. Above", "6. Below", "7. Advice", "8. External", 
                     "9. Hopes/Fears", "10. Outcome"],
    "relationship": ["You", "Partner", "Connection", "Advice"],
    "career": ["Current Situation", "Challenges", "Opportunities", "Outcome"]
}

class TarotReading:
    def __init__(self, cards, spread_type, question=None):
        self.cards = cards
        self.spread_type = spread_type
        self.question = question
        self.positions = SPREADS.get(spread_type, [])
    
    def generate_reading(self):
        """Generate reading text"""
        reading = f"## 🔮 Tarot Reading - {self.spread_type.replace('_', ' ').title()}\n"
        
        if self.question:
            reading += f"**Question:** {self.question}\n\n"
        
        for i, (card, position) in enumerate(zip(self.cards, self.positions)):
            # Random orientation (upright or reversed)
            is_reversed = random.choice([True, False])
            orientation = "Reversed 🔄" if is_reversed else "Upright ⬆️"
            
            reading += f"### {position}\n"
            reading += f"**Card:** {card['name']} ({orientation})\n"
            reading += f"**Arcana:** {card['arcana'].title()}\n"
            
            if card['suit']:
                reading += f"**Suit:** {card['suit'].title()}\n"
            
            reading += f"**Keywords:** {', '.join(card['keywords'])}\n"
            
            if is_reversed:
                meaning = card['meaning_rev']
            else:
                meaning = card['meaning_up']
            
            reading += f"**Interpretation:** {meaning}\n\n"
        
        return reading
    
    async def create_card_image(self, card, position, is_reversed):
        """Create an image for a single card"""
        # Create a blank image
        img = Image.new('RGB', (400, 600), color=(30, 30, 40))
        draw = ImageDraw.Draw(img)
        
        try:
            # Try to load card image
            card_filename = f"{card['number']}_{card['name'].lower().replace(' ', '_')}.jpg"
            card_path = os.path.join('card_images', card_filename)
            
            if os.path.exists(card_path):
                card_img = Image.open(card_path)
                if is_reversed:
                    card_img = card_img.rotate(180)
                img.paste(card_img.resize((380, 580)), (10, 10))
            else:
                # Draw placeholder if image doesn't exist
                draw.rectangle([10, 10, 390, 590], outline=(100, 100, 150), width=3)
                draw.text((200, 300), card['name'], fill=(200, 200, 255), anchor="mm")
        except:
            pass
        
        # Add position label
        draw.rectangle([0, 550, 400, 600], fill=(50, 50, 70))
        draw.text((200, 575), position, fill=(255, 255, 200), anchor="mm")
        
        # Add orientation indicator
        orient_text = "Reversed" if is_reversed else "Upright"
        draw.text((200, 25), orient_text, fill=(255, 200, 200), anchor="mm")
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes

@bot.event
async def on_ready():
    print(f'✅ {bot.user} has connected to Discord!')
    print(f'🔮 Tarot bot is ready with {len(tarot_cards)} cards loaded!')
    
    # Set bot status
    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name="!tarot help"
    )
    await bot.change_presence(activity=activity)

@bot.command(name='tarot')
async def tarot_reading(ctx, spread_type="single", *, question=None):
    """Draw tarot cards for a reading"""
    
    if spread_type not in SPREADS:
        # Show available spreads
        embed = discord.Embed(
            title="🔮 Available Tarot Spreads",
            description="Choose a spread type:",
            color=discord.Color.purple()
        )
        
        for spread, positions in SPREADS.items():
            embed.add_field(
                name=spread.replace('_', ' ').title(),
                value=f"{len(positions)} cards\n`!tarot {spread} [question]`",
                inline=True
            )
        
        await ctx.send(embed=embed)
        return
    
    # Get number of cards needed
    num_cards = len(SPREADS[spread_type])
    
    # Draw random cards
    drawn_cards = random.sample(tarot_cards, num_cards)
    orientations = [random.choice([True, False]) for _ in range(num_cards)]
    
    # Create reading
    reading = TarotReading(drawn_cards, spread_type, question)
    reading_text = reading.generate_reading()
    
    # Create embed
    embed = discord.Embed(
        title=f"🔮 Tarot Reading - {spread_type.replace('_', ' ').title()}",
        description=reading_text[:4096],  # Discord embed limit
        color=discord.Color.dark_purple()
    )
    
    if question:
        embed.add_field(name="Question", value=question, inline=False)
    
    embed.set_footer(text=f"Reading for {ctx.author.display_name}")
    
    await ctx.send(embed=embed)
    
    # Send card images
    for i, (card, position) in enumerate(zip(drawn_cards, SPREADS[spread_type])):
        img_bytes = await reading.create_card_image(card, position, orientations[i])
        file = discord.File(img_bytes, filename=f"card_{i+1}.png")
        await ctx.send(file=file)

@bot.command(name='card')
async def single_card(ctx, *, card_name=None):
    """Get information about a specific tarot card"""
    
    if not card_name:
        # Show random card
        card = random.choice(tarot_cards)
    else:
        # Find card by name (case-insensitive)
        card = next((c for c in tarot_cards 
                    if card_name.lower() in c['name'].lower()), None)
        
        if not card:
            await ctx.send(f"❌ Card '{card_name}' not found. Try `!cards` to see all cards.")
            return
    
    # Create embed for card
    embed = discord.Embed(
        title=f"🃏 {card['name']}",
        color=discord.Color.gold() if card['arcana'] == 'major' else discord.Color.blue()
    )
    
    embed.add_field(name="Number", value=card['number'], inline=True)
    embed.add_field(name="Arcana", value=card['arcana'].title(), inline=True)
    
    if card['suit']:
        embed.add_field(name="Suit", value=card['suit'].title(), inline=True)
    
    embed.add_field(name="Keywords", value=', '.join(card['keywords']), inline=False)
    embed.add_field(name="Upright Meaning", value=card['meaning_up'], inline=False)
    embed.add_field(name="Reversed Meaning", value=card['meaning_rev'], inline=False)
    
    embed.set_footer(text="Draw this card with !tarot command")
    
    await ctx.send(embed=embed)
    
    # Send card image if available
    try:
        card_filename = f"{card['number']}_{card['name'].lower().replace(' ', '_')}.jpg"
        card_path = os.path.join('card_images', card_filename)
        
        if os.path.exists(card_path):
            file = discord.File(card_path, filename="tarot_card.jpg")
            embed.set_image(url="attachment://tarot_card.jpg")
            await ctx.send(file=file)
    except:
        pass

@bot.command(name='cards')
async def list_cards(ctx):
    """List all tarot cards"""
    major_cards = [c for c in tarot_cards if c['arcana'] == 'major']
    minor_cards = [c for c in tarot_cards if c['arcana'] == 'minor']
    
    embed = discord.Embed(
        title="🃏 Tarot Deck Contents",
        color=discord.Color.dark_green()
    )
    
    embed.add_field(
        name="Major Arcana (22 cards)",
        value='\n'.join([f"{c['number']}. {c['name']}" for c in major_cards]),
        inline=True
    )
    
    # Group minor cards by suit
    suits = set(c['suit'] for c in minor_cards if c['suit'])
    for suit in suits:
        suit_cards = [c for c in minor_cards if c['suit'] == suit]
        embed.add_field(
            name=f"{suit.title()} (14 cards)",
            value='\n'.join([f"{c['name']}" for c in suit_cards[:10]]),
            inline=True
        )
    
    embed.set_footer(text=f"Total: {len(tarot_cards)} cards")
    await ctx.send(embed=embed)

@bot.command(name='daily')
async def daily_draw(ctx):
    """Get your daily tarot card"""
    card = random.choice(tarot_cards)
    is_reversed = random.choice([True, False])
    
    meaning = card['meaning_rev'] if is_reversed else card['meaning_up']
    orientation = "Reversed 🔄" if is_reversed else "Upright ⬆️"
    
    embed = discord.Embed(
        title=f"📅 Your Daily Tarot Card",
        description=f"**{card['name']}** ({orientation})",
        color=discord.Color.dark_blue()
    )
    
    embed.add_field(name="Message for Today", value=meaning, inline=False)
    embed.add_field(name="Keywords", value=', '.join(card['keywords']), inline=False)
    
    if is_reversed:
        advice = "This card reversed suggests you may need to reconsider this area of your life."
    else:
        advice = "This card upright is a positive sign. Embrace its energy today."
    
    embed.add_field(name="Advice", value=advice, inline=False)
    embed.set_footer(text=f"For {ctx.author.display_name}")
    
    await ctx.send(embed=embed)

@bot.command(name='help')
async def bot_help(ctx):
    """Show help menu"""
    embed = discord.Embed(
        title="🔮 Tarot Reading Bot - Help Guide",
        description="A spiritual guide to your questions through tarot cards",
        color=discord.Color.dark_purple()
    )
    
    commands_list = [
        ("!tarot [spread] [question]", "Get a tarot reading\nSpreads: single, three_card, celtic_cross, relationship, career"),
        ("!tarot help", "Show available spreads"),
        ("!card [name]", "Get information about a specific card"),
        ("!cards", "List all tarot cards in the deck"),
        ("!daily", "Get your daily tarot card"),
        ("!help", "Show this help menu")
    ]
    
    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=False)
    
    embed.add_field(
        name="📚 How to Use",
        value="1. Use `!tarot three_card` for a simple reading\n2. Add your question: `!tarot career What path should I take?`\n3. The bot will send both text interpretation and card images",
        inline=False
    )
    
    embed.set_footer(text="Remember: Tarot is a guide, not destiny. Trust your intuition.")
    
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found. Use `!help` to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required argument. Use `!help` for command usage.")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")

# Run the bot
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not found in .env file!")
        print("Please create a .env file with: DISCORD_TOKEN=your_token_here")
    else:
        bot.run(TOKEN)