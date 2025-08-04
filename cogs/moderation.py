import discord
from discord import app_commands
from discord.ext import commands
from cogs import extensions
from utils.embeds import BotMessageEmbed, BotConfirmationEmbed
from utils.loggingsetup import getlog


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.cog_counter += 1
        getlog().info(F'{__name__} ready ({self.bot.cog_counter}/{len(extensions)})')

    @app_commands.command(name='post', description='Create a embed post!')
    @app_commands.describe(message='Please input your message', channel_id='channel to send the message')
    async def createPost(self, interaction: discord.Interaction, message: str, channel_id: str):
        if interaction.user.id not in self.bot.whitelist:
            return
        else:
            try:
                dest = await self.bot.fetch_channel(int(channel_id))
                built_embed = BotMessageEmbed(description=message)
                built_embed.set_author(
                    name=interaction.user.name,
                    icon_url=interaction.user.avatar.url
                )
                await dest.send(embed=built_embed)
                await interaction.response.send_message(embed=BotConfirmationEmbed(description='Sent!'), ephemeral=True)
            except Exception as e:
                getlog().error(f'{e}')


# Add the cog to your discord bot.
async def setup(bot):
    await bot.add_cog(Moderation(bot))
