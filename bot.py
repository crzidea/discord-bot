import os
import discord
import pydub
import logging

logging.basicConfig(level=logging.INFO)

# Read token from environment variable
token = os.getenv("DISCORD_TOKEN")

# Create intents object
intents = discord.Intents.none()
intents.voice_states = True
intents.guilds = True
intents.guild_messages = True
# intents.message_content = True

# Create the bot instance
bot = discord.Bot(intents=intents, command_prefix="/")


@bot.command(name="join", description="Join a voice channel")
async def join_command(
    ctx: discord.ApplicationContext, *, channel: discord.VoiceChannel = None
):
    if channel is None:
        if ctx.author.voice and ctx.author.voice.channel:
            channel = ctx.author.voice.channel
        else:
            await ctx.response.send_message(
                "You must either be in a voice channel or specify one to join."
            )
            return

    interaction = await ctx.response.send_message(
        f"Joining {channel.name}!", ephemeral=True
    )
    if ctx.guild.voice_client:
        await interaction.edit_original_response(
            content=f"Already connected to a voice channel, leaving and joining {channel.name}!"
        )
        await ctx.guild.voice_client.disconnect()
    await channel.connect(cls=AudioReceiver)
    # Start listening for audio
    await interaction.edit_original_response(content=f"Joined {channel.name}!")


@bot.command(name="leave", description="Leave the current voice channel")
async def leave_command(ctx: discord.ApplicationContext):
    voice_client = ctx.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        await ctx.response.send_message("Left the voice channel.")
    else:
        await ctx.response.send_message("Not connected to any voice channel.")


@bot.event
async def on_ready():
    # await bot.sync_commands(force=True)
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message):
    print(f"Received message from {message.author}: {message.content}")
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    # Sync command if end with !sync
    if message.content.endswith("!sync"):
        await bot.sync_commands(force=True)
        await message.channel.send("Synced commands!")


@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel:
        print(f"User {member.name} left {before.channel}")
    if after.channel:
        print(f"User {member.name} joined {after.channel}")


class AudioReceiver(discord.VoiceClient):
    def __init__(self, client, channel):
        super().__init__(client, channel)

    async def on_voice_packet(self, data, user):
        print(f"Received audio data from {user}: {data}")
        audio_segment = pydub.AudioSegment.from_raw(
            data, frame_rate=48000, channels=2, sample_width=2, frame_format="s16le"
        )
        # Do something with the AudioSegment object
        print(f"Transformed audio segment: {audio_segment}")


bot.run(token)
