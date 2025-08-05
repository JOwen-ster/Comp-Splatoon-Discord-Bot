import discord
from discord.ext import commands
from discord import app_commands
import utils.roledropdown as rdd
from utils.embeds import BotMessageEmbed, BotErrorEmbed
import re

class RoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def filter_xp_roles(self, key: str, iterable):
        filtered_roles = []

        # Nested helper
        def scrape_xp(role_name):
            match = re.search(r'(\d+)', role_name)
            return int(match.group(1)) if match else 0

        for role in iterable:
            xp = scrape_xp(role.name)
            if 2000 <= xp <= 2900 and role.name != "@everyone" and "xp" in role.name.lower() and key in role.name.lower():
                filtered_roles.append(role)
        
        return filtered_roles

    @app_commands.command(name="jp-roles", description="Get a dropdown to assign/remove roles")
    async def role_dropdown_jp(self, interaction: discord.Interaction):
        # Check if the bot has manage_roles permission
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(embed=BotErrorEmbed(
                description="❌ I don't have the `Manage Roles` permission!"),
                ephemeral=True
            )
            return

        # Create the view with role dropdown
        jp_xp_roles = self.filter_xp_roles(key='jp', iterable=interaction.guild.roles)
        view = rdd.RoleView(roles=jp_xp_roles)
        embed = BotMessageEmbed(title="Japan XP Roles", description="Select Your Takoroka Division Power")
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="na-roles", description="Get a dropdown to assign/remove roles")
    async def role_dropdown_na(self, interaction: discord.Interaction):
        # Check if the bot has manage_roles permission
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(embed=BotErrorEmbed(
                description="❌ I don't have the `Manage Roles` permission!"),
                ephemeral=True
            )
            return

        # Create the view with role dropdown
        jp_xp_roles = self.filter_xp_roles(key='na', iterable=interaction.guild.roles)
        view = rdd.RoleView(roles=jp_xp_roles)
        embed = BotMessageEmbed(title="Western XP Roles", description="Select Your Tentatek Division Power")
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(RoleCog(bot))
