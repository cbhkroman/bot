import discord
from discord.ext import commands, tasks
import asyncio
import datetime
import re
import openai  # Assuming Gemini API is used via OpenAI's API
from collections import deque
import yt_dlp
import os
import youtube_dl

# Bot Configuration
TOKEN = "MTM0NjE3NDg5ODU5NDI1MDkwMw.GKNO-1.KnJx3gQd8tW_7Q4_f-dBBa7TVgAj3AYzJLi31Q"
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# In-Memory Data Storage
reminders = {}
music_queue = deque()

# --- CHAT FUNCTIONALITY (Using Gemini API via OpenAI) ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Adjust based on API provider
        messages=[{"role": "user", "content": message.content}]
    ).choices[0].message["content"]
    await message.channel.send(response["choices"][0]["message"]["content"])
    await bot.process_commands(message)

# --- REMINDER FUNCTIONALITY ---
@bot.command()
async def remind(ctx, time: str, *, reminder: str):
    """Set a reminder with a specific time format (e.g., 10m, 1h, 1d)."""
    match = re.match(r"(\d+)([smhd])", time)
    if not match:
        await ctx.send("Invalid time format! Use s (seconds), m (minutes), h (hours), or d (days).")
        return
    
    amount, unit = int(match.group(1)), match.group(2)
    delta = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit] * amount
    future_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=delta)
    reminders[ctx.author.id] = (future_time, reminder)
    await ctx.send(f"Reminder set for {ctx.author.mention} in {time}!")
    await asyncio.sleep(delta)
    if ctx.author.id in reminders:
        await ctx.send(f"⏰ {ctx.author.mention}, reminder: {reminder}")
        del reminders[ctx.author.id]

# --- POLL FUNCTIONALITY ---
@bot.command()
async def poll(ctx, question: str, *options: str):
    """Create a poll with up to 10 options."""
    if len(options) < 2 or len(options) > 10:
        await ctx.send("Poll must have 2-10 options.")
        return
    
    reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    description = "\n".join(f"{reactions[i]} {option}" for i, option in enumerate(options))
    embed = discord.Embed(title=question, description=description, color=discord.Color.blue())
    message = await ctx.send(embed=embed)
    for i in range(len(options)):
        await message.add_reaction(reactions[i])

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Process commands properly
    await bot.process_commands(message)  

# --- CUSTOM WELCOME MESSAGES ---
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="general")  # Adjust as needed
    if channel:
        await channel.send(f"Welcome {member.mention} to {member.guild.name}! 🎉")

# --- AI-POWERED SUMMARIES ---
@bot.command()
async def summarize(ctx, *, text):
    try:
        client = openai.OpenAI(api_key="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")  # Ensure your API key is set correctly

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Summarize this: {text}"}]
        )

        summary = response.choices[0].message.content  # Extract the bot's response
        await ctx.send(f"**Summary:** {summary}")

    except Exception as e:
        await ctx.send(f"Error: {e}")
# --- MUSIC QUEUE FUNCTIONALITY --- 
# --- MUSIC FUNCTIONALITY ---
@bot.command()
async def join(ctx):
    """Join the voice channel."""
    if ctx.author.voice:
        global voice_client
        voice_client = await ctx.author.voice.channel.connect()
    else:
        await ctx.send("You need to be in a voice channel first!")

@bot.command()
async def leave(ctx):
    """Leave the voice channel."""
    global voice_client
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        voice_client = None
        await ctx.send("Left the voice channel.")
    else:
        await ctx.send("I'm not in a voice channel!")

@bot.command()
async def play(ctx, url: str):
    """Play a song from YouTube."""
    music_queue.append(url)
    await ctx.send(f"Added to queue: {url}")
    if len(music_queue) == 1:
        await play_next(ctx)

async def play_next(ctx):
    """Play the next song in the queue."""
    global voice_client
    if not music_queue:
        return
    
    if not voice_client or not voice_client.is_connected():
        await join(ctx)
    
    url = music_queue.popleft()
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'song.mp3',
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    voice_client.play(discord.FFmpegPCMAudio("song.mp3"), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
    await ctx.send(f"Now playing: {url}")

@bot.command()
async def skip(ctx):
    """Skip the current song."""
    global voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Skipping song...")
        await play_next(ctx)
    else:
        await ctx.send("No song is currently playing!")

@bot.command()
async def queue(ctx):
    """Display the music queue."""
    if music_queue:
        await ctx.send("Current Queue: " + ", ".join(music_queue))
    else:
        await ctx.send("The queue is empty.")
# Start Bot 
bot.run(TOKEN)
