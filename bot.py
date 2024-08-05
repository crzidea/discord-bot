import asyncio
import discord
import io
import logging
import os
import pydub
import struct

logging.basicConfig(level=logging.INFO)

# Read token from environment variable
token = os.getenv("DISCORD_TOKEN")
if token is None:
    token = userdata.get("DISCORD_TOKEN")


# discord.VoiceClient.supported_modes = "xsalsa20_poly1305"
# Override code to fix protocol
def strip_header_ext(self, data):
    if len(data) == 0:
        return data
    if data[0] == 0xBE and data[1] == 0xDE and len(data) > 4:
        _, length = struct.unpack_from(">HH", data)
        offset = 4 + length * 4
        data = data[offset:]
    return data

discord.VoiceClient.strip_header_ext = strip_header_ext 

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
        await ctx.guild.voice_client.disconnect(force=True)

    # Retry if timeout exceed
    async def retry(
        channel: discord.VoiceChannel, interaction, maxRetryTimes, retryTimes
    ):
        try:
            await asyncio.wait_for(channel.connect(), 3)
        except asyncio.TimeoutError:
            await channel.guild.voice_client.disconnect(force=True)
            if retryTimes < maxRetryTimes:
                await interaction.edit_original_response(
                    content=f"Failed to join {channel.name} {retryTimes} times! Timeout exceeded."
                )
                await retry(channel, interaction, maxRetryTimes, retryTimes + 1)
            else:
                await interaction.edit_original_response(
                    content=f"Failed to join {channel.name}! Max retry times exceeded."
                )
                raise

    await retry(channel, interaction, 3, 1)
    # await channel.connect(timeout=3)
    await ctx.guild.change_voice_state(channel=channel, self_mute=True)

    # Start listening for audio
    await interaction.edit_original_response(content=f"Joined {channel.name}!")

    # https://guide.pycord.dev/voice/receiving
    vc = channel.guild.voice_client

    vc.start_recording(
        MySink(),  # The sink type to use.
        once_done,  # What to do once done.
        # ctx.channel,  # The channel to disconnect from.
    )
    await interaction.edit_original_response(content="Started recording!")


# Implenment a sink that convert audio data into AudioSegment
class MySink(discord.sinks.Sink):
    audio_segments = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @discord.sinks.Filters.container
    def write(self, data, user):
        # Decode the audio data
        file = io.BytesIO()
        file.write(data)
        audio_segment = pydub.AudioSegment.from_raw(
            file,
            frame_rate=48000,
            sample_width=2,
            channels=2,
            frame_format="s16le",
        )
        last_chunk = self.audio_segments.get(user)
        # TODO
        last_chunk = audio_segment
        # Process the audio segment
        self.audio_segments.update({user: last_chunk})
        # process_audio_segment(user, None)
        # process_audio_segment(audio_segment, last_chunk)

    def cleanup(self):
        self.finished = True
        self.audio_segments.clear()
        print("Cleanup called")


# Define a callback function to be called when recording is finished
async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    pass


@bot.command(name="leave", description="Leave the current voice channel")
async def leave_command(ctx: discord.ApplicationContext):
    voice_client = ctx.guild.voice_client
    if voice_client:
        await voice_client.disconnect(force=True)
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


# bot.run(token)


def process_audio_segment():
    pass


try:
    loop = asyncio.get_running_loop()
    loop.create_task(bot.run(token))
except RuntimeError:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.run(token))
