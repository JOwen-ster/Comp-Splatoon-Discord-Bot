import discord
from discord.ext import commands
from discord import app_commands
import utils.roledropdown as rdd
from utils.embeds import BotMessageEmbed, BotErrorEmbed
import re


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Just register the persistent views - that's it!
        self.bot.add_view(rdd.RoleView(region_key='jp', bot=self.bot))
        self.bot.add_view(rdd.RoleView(region_key='na', bot=self.bot))

    def filter_xp_roles(self, key: str, iterable):
        filtered_roles = []
        for role in iterable:
            match = re.search(r'(\d+)', role.name)
            xp = int(match.group(1)) if match else 0
            if 2000 <= xp <= 2900 and "xp" in role.name.lower() and key in role.name.lower():
                filtered_roles.append(role)
        return filtered_roles

    @app_commands.command(name="jp-roles", description="Get a dropdown to assign/remove roles")
    async def role_dropdown_jp(self, interaction: discord.Interaction):
        if interaction.user.id not in self.bot.whitelist:
            return

        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(embed=BotErrorEmbed(
                description="❌ I don't have the `Manage Roles` permission!"),
                ephemeral=True
            )
            return

        jp_xp_roles = self.filter_xp_roles(key='jp', iterable=interaction.guild.roles)
        view = rdd.RoleView(region_key='jp', bot=self.bot)
        view.update_roles(jp_xp_roles)
        
        embed = BotMessageEmbed(title="Japan XP Roles", description="Select Your Takoroka Division Power")
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="na-roles", description="Get a dropdown to assign/remove roles")
    async def role_dropdown_na(self, interaction: discord.Interaction):
        if interaction.user.id not in self.bot.whitelist:
            return

        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(embed=BotErrorEmbed(
                description="❌ I don't have the `Manage Roles` permission!"),
                ephemeral=True
            )
            return

        na_xp_roles = self.filter_xp_roles(key='na', iterable=interaction.guild.roles)
        view = rdd.RoleView(region_key='na', bot=self.bot)
        view.update_roles(na_xp_roles)
        
        embed = BotMessageEmbed(title="Western XP Roles", description="Select Your Tentatek Division Power")
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Roles(bot))
