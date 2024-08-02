import discord
import io
import logging
import os
import pydub

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

connections = {}


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
    await channel.connect(timeout=3)
    # Start listening for audio
    await interaction.edit_original_response(content=f"Joined {channel.name}!")

    # https://guide.pycord.dev/voice/receiving
    vc = ctx.guild.voice_client
    connections.update(
        {ctx.guild.id: vc}
    )  # Updating the cache with the guild and channel.

    vc.start_recording(
        MySink(),  # The sink type to use.
        once_done,  # What to do once done.
        # ctx.channel,  # The channel to disconnect from.
    )
    await interaction.edit_original_response(content="Started recording!")

# Implenment a sink that convert audio data into AudioSegment
class MySink(discord.sinks.Sink):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audio_segments = {}

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
        if user not in self.audio_segments:
            self.audio_segments.update({user: []})
        # self.audio_segments[user].append(audio_segment)

    def cleanup(self):
        self.finished = True
        for user, segments in self.audio_segments.items():
            # Concatenate the audio segments
            audio_segment = pydub.AudioSegment.empty()
            for segment in segments:
                audio_segment += segment
            # Save the audio segment to a file
            audio_segment.export(f"{user}.wav", format="wav")


# Define a callback function to be called when recording is finished
async def once_done(
    sink: discord.sinks, channel: discord.TextChannel, *args
):  # Our voice client already passes these in.
    pass
    # recorded_users = [  # A list of recorded users
    #     f"<@{user_id}>" for user_id, audio in sink.audio_data.items()
    # ]
    # await sink.vc.disconnect()  # Disconnect from the voice channel.
    # files = [
    #     discord.File(audio.file, f"{user_id}.{sink.encoding}")
    #     for user_id, audio in sink.audio_data.items()
    # ]  # List down the files.
    # await channel.send(
    #     f"finished recording audio for: {', '.join(recorded_users)}.", files=files
    # )  # Send a message with the accumulated files.


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


bot.run(token)
