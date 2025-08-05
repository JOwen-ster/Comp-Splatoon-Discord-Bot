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

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            try:
                await member.ban(reason='BOT auto ban')
                getlog().info(f'{member.name} was banned due to being a BOT')
            except Exception as e:
                getlog().error(f'{e}')

    @app_commands.command(name='post', description='Create an embed post!')
    @app_commands.describe(message='Please input your message', channel_id='channel to send the message')
    async def create_post(self, interaction: discord.Interaction, message: str, channel_id: str):
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

    @app_commands.command(name='code', description="Link to this bot's source code")
    async def code_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=BotMessageEmbed(
            title='Bot developed by @typos. on Discord',
            description='https://github.com/JOwen-ster/Comp-Splatoon-Discord-Bot')
        )

# Add the cog to your discord bot.
async def setup(bot):
    await bot.add_cog(Moderation(bot))
