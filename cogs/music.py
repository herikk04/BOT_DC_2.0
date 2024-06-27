import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from youtube_dl import YoutubeDL
import os

class TutorialButton(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None
        self.timeout = 600

        botaourl = discord.ui.Button(label="Crie vergonha na cara",)
        self.add_item(botaourl)

class Music(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.guild_queues = {}

    def get_guild_queue(self, guild_id):
        if guild_id not in self.guild_queues:
            self.guild_queues[guild_id] = {
                'is_playing': False,
                'music_queue': [],
                'vc': None
            }
        return self.guild_queues[guild_id]

    def search_yt(self, item):
        YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist':'True'}
        with YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info("ytsearch:%s" % item, download=False)['entries'][0]
            except Exception:
                return False
        return {'source': info['formats'][0]['url'], 'title': info['title']}

    def play_next(self, guild_id):
        guild_queue = self.get_guild_queue(guild_id)
        if len(guild_queue['music_queue']) > 0:
            guild_queue['is_playing'] = True
            m_url = guild_queue['music_queue'][0]['source']
            guild_queue['music_queue'].pop(0)
            guild_queue['vc'].play(discord.FFmpegPCMAudio(m_url, **guild_queue['FFMPEG_OPTIONS']), after=lambda e: self.play_next(guild_id))
        else:
            guild_queue['is_playing'] = False

    async def play_music(self, guild_id):
        guild_queue = self.get_guild_queue(guild_id)
        if len(guild_queue['music_queue']) > 0:
            guild_queue['is_playing'] = True
            m_url = guild_queue['music_queue'][0]['source']
            if guild_queue['vc'] == "" or not guild_queue['vc'].is_connected() or guild_queue['vc'] == None:
                guild_queue['vc'] = await guild_queue['music_queue'][0]['channel'].connect()
            else:
                await guild_queue['vc'].move_to(guild_queue['music_queue'][0]['channel'])
            guild_queue['music_queue'].pop(0)
            guild_queue['vc'].play(discord.FFmpegPCMAudio(m_url, **guild_queue['FFMPEG_OPTIONS']), after=lambda e: self.play_next(guild_id))
        else:
            guild_queue['is_playing'] = False
            await guild_queue['vc'].disconnect()

    @app_commands.command(name="ajuda", description="Mostre um comando de ajuda.")
    async def help(self, interaction: discord.Interaction):
        helptxt = "`/ajuda` - Veja esse guia!\n`/play` - Toque uma música do YouTube!\n`/fila` - Veja a fila de músicas na Playlist\n`/pular` - Pule para a próxima música da fila"
        embedhelp = discord.Embed(
            colour=1646116,
            title=f'Comandos do {self.client.user.name}',
            description=helptxt
        )
        try:
            embedhelp.set_thumbnail(url=self.client.user.avatar.url)
        except:
            pass
        await interaction.response.send_message(embed=embedhelp, view=TutorialButton())

    @app_commands.command(name="play", description="Toca uma música do YouTube.")
    @app_commands.describe(busca="Digite o nome da música no YouTube")
    async def play(self, interaction: discord.Interaction, busca: str):
        query = busca
        guild_id = interaction.guild_id
        guild_queue = self.get_guild_queue(guild_id)
        try:
            voice_channel = interaction.user.voice.channel
        except:
            embedvc = discord.Embed(
                colour=1646116,
                description='Para tocar uma música, primeiro se conecte a um canal de voz.'
            )
            await interaction.response.send_message(embed=embedvc)
            return
        else:
            song = self.search_yt(query)
            if not song:
                embedvc = discord.Embed(
                    colour=12255232,
                    description='Algo deu errado! Tente novamente!'
                )
                await interaction.response.send_message(embed=embedvc)
            else:
                embedvc = discord.Embed(
                    colour=32768,
                    description=f"Você adicionou a música **{song['title']}** à fila!"
                )
                await interaction.response.send_message(embed=embedvc, view=TutorialButton())
                guild_queue['music_queue'].append({'source': song['source'], 'title': song['title'], 'channel': voice_channel})

                if not guild_queue['is_playing']:
                    await self.play_music(guild_id)

    @app_commands.command(name="fila", description="Mostra as atuais músicas da fila.")
    async def q(self, interaction: discord.Interaction):
        guild_queue = self.get_guild_queue(interaction.guild_id)
        retval = ""
        for i in range(0, len(guild_queue['music_queue'])):
            retval += f'**{i+1} - **' + guild_queue['music_queue'][i]['title'] + "\n"

        if retval != "":
            embedvc = discord.Embed(
                colour=12255232,
                description=f"{retval}"
            )
            await interaction.response.send_message(embed=embedvc)
        else:
            embedvc = discord.Embed(
                colour=1646116,
                description='Não existe músicas na fila no momento.'
            )
            await interaction.response.send_message(embed=embedvc)

    @app_commands.command(name="pular", description="Pula a atual música que está tocando.")
    @app_commands.default_permissions(manage_channels=True)
    async def pular(self, interaction: discord.Interaction):
        guild_queue = self.get_guild_queue(interaction.guild_id)
        if guild_queue['vc'] != "" and guild_queue['vc']:
            guild_queue['vc'].stop()
            await self.play_music(interaction.guild_id)
            embedvc = discord.Embed(
                colour=1646116,
                description=f"Você pulou a música."
            )
            await interaction.response.send_message(embed=embedvc)

    @pular.error
    async def skip_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, commands.MissingPermissions):
            embedvc = discord.Embed(
                colour=12255232,
                description=f"Você precisa da permissão **Gerenciar canais** para pular músicas."
            )
            await interaction.response.send_message(embed=embedvc)
        else:
            raise error

class Disconnect(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="disconnect", description="Desconecta o bot do canal de voz.")
    async def disconnect_command(self, interaction: discord.Interaction):
        guild_queue = self.get_guild_queue(interaction.guild_id)
        if not interaction.user.voice:
            await interaction.response.send_message("Você não está conectado a nenhum canal de voz.")
            return

        if guild_queue['vc'] is None or guild_queue['vc'].channel is None:
            await interaction.response.send_message("O bot não está tocando nada.")
            return

        if guild_queue['vc'].channel.id != interaction.user.voice.channel.id:
            await interaction.response.send_message(
                "Entre no canal de voz onde o bot está tocando para desconectá-lo."
            )
            return

        await self.disconnect_player(interaction.guild)
        await interaction.response.send_message(
            f"Desconectado por {interaction.user.mention} em {discord.utils.format_dt(datetime.now())}."
        )

    async def disconnect_player(self, guild: discord.Guild):
        vc = discord.utils.get(self.client.voice_clients, guild=guild)
        if vc is not None:
            await vc.disconnect()

async def setup(client):
    await client.add_cog(Music(client))
    await client.add_cog(Disconnect(client))
