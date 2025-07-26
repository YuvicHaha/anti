import os
import threading
import base64
import requests
from flask import Flask
import discord
from discord.ext import commands

# === Flask for Railway health check ===
app = Flask(__name__)

@app.route("/healthz")
def healthz():
    return "OK", 200

def run_health():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_health).start()

# === Environment Variables ===
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "yuvic123/StandLIST"
FILE_PATH = "list"
FILE_PATH_BYPASS = "Stand%20Bypass%20Premium"
BRANCH = "main"

# === GitHub Headers ===
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# === Discord Bot Setup ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

# === Helper Functions for File Handling ===
def get_file():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}?ref={BRANCH}"
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    data = res.json()
    content = base64.b64decode(data["content"]).decode()
    sha = data["sha"]
    return content, sha

def update_file(new_content, sha, message="Updated whitelist"):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    encoded_content = base64.b64encode(new_content.encode()).decode()
    data = {
        "message": message,
        "content": encoded_content,
        "sha": sha,
        "branch": BRANCH
    }
    res = requests.put(url, headers=headers, json=data)
    res.raise_for_status()
    return res.json()

def get_bypass_file():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH_BYPASS}?ref={BRANCH}"
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    data = res.json()
    content = base64.b64decode(data["content"]).decode()
    sha = data["sha"]
    return content, sha

def update_bypass_file(new_content, sha, message="Updated Stand Bypass Premium list"):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH_BYPASS}"
    encoded_content = base64.b64encode(new_content.encode()).decode()
    data = {
        "message": message,
        "content": encoded_content,
        "sha": sha,
        "branch": BRANCH
    }
    res = requests.put(url, headers=headers, json=data)
    res.raise_for_status()
    return res.json()

# === Command Access Control ===
allowed_users = {
    1279868613628657860,
    598460565387476992,
    1272478153201422420,
    1197823319123165218,
    835401509373476885,
}

# === Commands ===
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content.startswith(".antirep"):
        try:
            args = message.content.split()
            if len(args) != 3:
                await message.channel.send("⚠️ Usage: `.antirep <oldid> <newid>`")
                return
            oldid = int(args[1])
            newid = int(args[2])
            discord_id = str(message.author.id)
            content, sha = get_file()
            lines = content.splitlines()
            found = False
            updated_lines = []
            if any(f"{newid}," in line for line in lines):
                await message.channel.send("⚠️ That new Roblox ID already exists in the list.")
                return
            for line in lines:
                if f"{oldid}," in line and f"--- {discord_id}" in line:
                    new_line = line.replace(f"{oldid},", f"{newid},")
                    updated_lines.append(new_line)
                    found = True
                else:
                    updated_lines.append(line)
            if not found:
                await message.channel.send("❌ You can only replace your own userid")
                return
            new_content = "\n".join(updated_lines)
            update_file(new_content, sha, message=f"{message.author} replaced {oldid} with {newid}")
            await message.channel.send(f"✅ Replaced `{oldid}` with `{newid}` successfully!")
        except Exception as e:
            await message.channel.send(f"⚠️ Error: {e}")
    await bot.process_commands(message)

@bot.command()
async def anticheck(ctx):
    discord_id = str(ctx.author.id)
    try:
        content, _ = get_file()
        lines = content.splitlines()
        for line in lines:
            if f"--- {discord_id}" in line:
                roblox_id = line.split(",")[0].strip()
                res = requests.get(f"https://users.roblox.com/v1/users/{roblox_id}")
                if res.status_code == 200:
                    data = res.json()
                    username = data.get("name", "Unknown")
                    embed = discord.Embed(title="Your Anti Stand is Linked To", color=discord.Color.purple())
                    embed.add_field(name="Roblox ID", value=f"`{roblox_id}`", inline=False)
                    embed.add_field(name="Username", value=f"**{username}**", inline=False)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"⚠️ Found Roblox ID `{roblox_id}`, but failed to get username.")
                return
        await ctx.send("❌ You don't have any Roblox ID registered.")
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

@bot.command(name="addanti")
async def addanti(ctx, target: discord.User, roblox_id: int):
    if ctx.author.id not in allowed_users:
        await ctx.send("❌ You are not authorized to use this command.")
        return
    try:
        content, sha = get_file()
        lines = content.splitlines()
        if any(f"{roblox_id}," in line for line in lines):
            await ctx.send("⚠️ This Roblox ID is already registered.")
            return
        for i in reversed(range(len(lines))):
            if lines[i].strip() == "}":
                insert_index = i
                break
        else:
            await ctx.send("❌ Invalid Lua file structure: missing closing `}`.")
            return
        new_line = f"    {roblox_id},     --- {target.id}"
        lines.insert(insert_index, new_line)
        new_content = "\n".join(lines)
        update_file(new_content, sha, message=f"{ctx.author} added {roblox_id} for {target}")
        await ctx.send(f"✅ Added Roblox ID `{roblox_id}` for <@{target.id}>")
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

@bot.command(name="antiremove")
async def antiremove(ctx, roblox_id: int):
    if ctx.author.id not in allowed_users:
        await ctx.send("❌ You are not authorized to use this command.")
        return
    try:
        content, sha = get_file()
        lines = content.splitlines()
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{roblox_id},"):
                found = True
                continue
            new_lines.append(line)
        if not found:
            await ctx.send("⚠️ Roblox ID not found in the list.")
            return
        new_content = "\n".join(new_lines)
        update_file(new_content, sha, message=f"{ctx.author} removed {roblox_id}")
        await ctx.send(f"✅ Removed Roblox ID `{roblox_id}` from the list.")
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

@bot.command(name="addbypass")
async def addbypass(ctx, target: discord.User, roblox_id: int):
    if ctx.author.id not in allowed_users:
        await ctx.send("❌ You are not authorized to use this command.")
        return
    try:
        content, sha = get_bypass_file()
        lines = content.splitlines()
        if any(f"{roblox_id}," in line for line in lines):
            await ctx.send("⚠️ This Roblox ID is already registered in the bypass list.")
            return
        for i in reversed(range(len(lines))):
            if lines[i].strip() == "}":
                insert_index = i
                break
        else:
            await ctx.send("❌ Invalid Lua file structure: missing closing `}`.")
            return
        new_line = f"    {roblox_id},     --- {target.id}"
        lines.insert(insert_index, new_line)
        new_content = "\n".join(lines)
        update_bypass_file(new_content, sha, message=f"{ctx.author} added bypass {roblox_id} for {target}")
        await ctx.send(f"✅ Bypass ID `{roblox_id}` added for <@{target.id}>")
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

@bot.command(name="bypasscheck")
async def bypasscheck(ctx):
    discord_id = str(ctx.author.id)
    try:
        content, _ = get_bypass_file()
        lines = content.splitlines()
        for line in lines:
            if f"--- {discord_id}" in line:
                roblox_id = line.split(",")[0].strip()
                res = requests.get(f"https://users.roblox.com/v1/users/{roblox_id}")
                if res.status_code == 200:
                    data = res.json()
                    username = data.get("name", "Unknown")
                    embed = discord.Embed(title="Your Stand Bypass Premium ID", color=discord.Color.gold())
                    embed.add_field(name="Roblox ID", value=f"`{roblox_id}`", inline=False)
                    embed.add_field(name="Username", value=f"**{username}**", inline=False)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"⚠️ Roblox ID `{roblox_id}` found, but username lookup failed.")
                return
        await ctx.send("❌ You don't have any Roblox ID registered in the bypass list.")
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

@bot.command(name="bypassreplace")
async def bypassreplace(ctx, oldid: int, newid: int):
    discord_id = str(ctx.author.id)
    try:
        content, sha = get_bypass_file()
        lines = content.splitlines()
        found = False
        updated_lines = []
        if any(f"{newid}," in line for line in lines):
            await ctx.send("⚠️ That new Roblox ID already exists in the bypass list.")
            return
        for line in lines:
            if f"{oldid}," in line and f"--- {discord_id}" in line:
                new_line = line.replace(f"{oldid},", f"{newid},")
                updated_lines.append(new_line)
                found = True
            else:
                updated_lines.append(line)
        if not found:
            await ctx.send("❌ You can only replace your own bypass ID.")
            return
        new_content = "\n".join(updated_lines)
        update_bypass_file(new_content, sha, message=f"{ctx.author} replaced bypass {oldid} with {newid}")
        await ctx.send(f"✅ Replaced bypass ID `{oldid}` with `{newid}` successfully!")
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

@bot.command(name="bypassremove")
async def bypassremove(ctx, roblox_id: int):
    if ctx.author.id not in allowed_users:
        await ctx.send("❌ You are not authorized to use this command.")
        return
    try:
        content, sha = get_bypass_file()
        lines = content.splitlines()
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{roblox_id},"):
                found = True
                continue
            new_lines.append(line)
        if not found:
            await ctx.send("⚠️ Roblox ID not found in the bypass list.")
            return
        new_content = "\n".join(new_lines)
        update_bypass_file(new_content, sha, message=f"{ctx.author} removed bypass {roblox_id}")
        await ctx.send(f"✅ Removed bypass ID `{roblox_id}` from the list.")
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

bot.run(DISCORD_TOKEN)
