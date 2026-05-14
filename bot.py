import discord
from discord.ext import commands
import asyncio
import os
from gtts import gTTS
from dotenv import load_dotenv
import shutil

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
FFMPEG_PATH = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

guild_state = {}


def get_state(guild_id):
    if guild_id not in guild_state:
        guild_state[guild_id] = {
            "voice_channel": None,
            "leave_task": None,
            "in_voice": False,
        }
    return guild_state[guild_id]


def create_tts(text, filename="welcome.mp3"):
    tts = gTTS(text=text, lang="th")
    tts.save(filename)
    return filename


async def schedule_leave(guild_id):
    await asyncio.sleep(30)
    state = get_state(guild_id)
    guild = bot.get_guild(guild_id)
    if guild and state["in_voice"]:
        voice_client = guild.voice_client
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            state["in_voice"] = False
            state["voice_channel"] = None
            print(f"Bot ออกจากห้องเสียงเพราะไม่มีใครเข้ามาเกิน 30 วินาที")


@bot.event
async def on_ready():
    print(f"✅ Bot พร้อมใช้งาน: {bot.user} (ID: {bot.user.id})")
    print(f"FFMPEG path: {FFMPEG_PATH}")


@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    guild = member.guild
    state = get_state(guild.id)

    if after.channel is not None and before.channel != after.channel:
        voice_channel = after.channel

        await voice_channel.send(f"🎉 ยินดีต้อนรับ **{member.display_name}**!")

        if state["leave_task"] and not state["leave_task"].done():
            state["leave_task"].cancel()
            state["leave_task"] = None

        if not state["in_voice"]:
            try:
                voice_client = await voice_channel.connect()
                state["in_voice"] = True
                state["voice_channel"] = voice_channel
                print(f"Bot เข้าห้อง: {voice_channel.name}")
                await asyncio.sleep(1)

                filename = create_tts(f"ยินดีต้อนรับ {member.display_name}")
                voice_client.play(
                    discord.FFmpegPCMAudio(filename, executable=FFMPEG_PATH),
                    after=lambda e: os.remove(filename) if os.path.exists(filename) else None
                )

            except Exception as e:
                print(f"เกิดข้อผิดพลาด: {e}")
                state["in_voice"] = False
        else:
            try:
                voice_client = guild.voice_client
                if voice_client and not voice_client.is_playing():
                    filename = create_tts(f"ยินดีต้อนรับ {member.display_name}")
                    voice_client.play(
                        discord.FFmpegPCMAudio(filename, executable=FFMPEG_PATH),
                        after=lambda e: os.remove(filename) if os.path.exists(filename) else None
                    )
            except Exception as e:
                print(f"เกิดข้อผิดพลาดขณะพูด: {e}")

        state["leave_task"] = asyncio.create_task(schedule_leave(guild.id))

    elif before.channel is not None and after.channel is None:
        if state["in_voice"] and state["voice_channel"] == before.channel:
            human_members = [m for m in before.channel.members if not m.bot]
            if not human_members:
                if state["leave_task"] and not state["leave_task"].done():
                    state["leave_task"].cancel()
                state["leave_task"] = asyncio.create_task(schedule_leave(guild.id))


bot.run(TOKEN)
